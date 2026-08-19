"""Daily (not 5-min) refresh for the three data feeds ipo_potential_service
needs beyond what the existing catalog refresh already provides: the
historical-outcomes backfill, per-IPO news sentiment, and broad-market
index trend. Run from its own low-frequency periodic loop in main.py --
news and market momentum don't move fast enough to justify piggybacking
on the 5-min catalog refresh, and re-fetching news for every open/upcoming
IPO is real outbound traffic that shouldn't happen every 5 minutes on a
1 OCPU box.
"""

import logging
from datetime import date

from app.scrapers.market_data import nse_client
from app.scrapers.news import news_client
from app.services import (
    ipo_catalog_repository,
    ipo_catalog_service,
    ipo_historical_backfill_service,
    market_trend_repository,
    news_sentiment_repository,
)
from app.utils import sentiment

logger = logging.getLogger(__name__)

_NEWS_QUERY_SUFFIX = "IPO"


async def _refresh_market_trend() -> None:
    try:
        indices = await nse_client.get_all_indices()
    except Exception:
        logger.exception("NSE all-indices refresh failed")
        return
    for index in indices:
        market_trend_repository.upsert(index.index_symbol, index.percent_change_1d, index.percent_change_30d)


async def _refresh_news_sentiment() -> None:
    # Only open/upcoming IPOs are worth fresh news coverage -- once closed,
    # the apply decision this feeds is already moot.
    today = date.today()
    records = [
        r
        for r in ipo_catalog_repository.get_all()
        if ipo_catalog_service.compute_status(r.open_date, r.close_date, today) != "closed"
    ]
    for record in records:
        try:
            headlines = await news_client.get_headlines(f"{record.company_name} {_NEWS_QUERY_SUFFIX}")
            score = sentiment.score_headlines([h.title for h in headlines])
            news_sentiment_repository.upsert(record.id, score, len(headlines))
        except Exception:
            logger.exception("News sentiment refresh failed for %s", record.company_name)


async def refresh_daily() -> None:
    try:
        count = await ipo_historical_backfill_service.backfill()
        logger.info("Historical IPO outcomes backfilled (%d companies)", count)
    except Exception:
        logger.exception("Historical outcomes backfill failed")

    await _refresh_market_trend()
    await _refresh_news_sentiment()
