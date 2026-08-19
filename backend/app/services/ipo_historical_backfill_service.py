"""Merges investorgain's two historical reports (performance + subscription
-- see investorgain_history_client.py) by normalized company name into
ipo_historical_outcomes rows. Safe to re-run repeatedly (upsert, not
insert) -- called both by the one-off backfill script and, going forward,
by the daily refresh loop in main.py, so the dataset keeps growing as new
IPOs list rather than needing a human to remember to re-run a script.
"""

import logging

from app.scrapers.market_data import investorgain_history_client
from app.services import ipo_historical_repository
from app.services.ipo_historical_repository import HistoricalOutcome
from app.utils.name_matching import normalize_company_name

logger = logging.getLogger(__name__)


def _outcome_id(company_name: str) -> str:
    return f"hist-{normalize_company_name(company_name).replace(' ', '-').lower()}"


async def backfill() -> int:
    outcomes: dict[str, HistoricalOutcome] = {}

    try:
        performance_rows = await investorgain_history_client.get_performance_history()
    except Exception:
        logger.exception("investorgain performance-history fetch failed")
        performance_rows = []

    for row in performance_rows:
        outcome_id = _outcome_id(row.company_name)
        outcomes[outcome_id] = HistoricalOutcome(
            id=outcome_id,
            company_name=row.company_name,
            listing_date=row.listing_date,
            issue_size_cr=row.issue_size_cr,
            issue_price=row.issue_price,
            listing_gain_percent=row.listing_gain_percent,
            current_gain_percent=row.current_gain_percent,
        )

    try:
        subscription_rows = await investorgain_history_client.get_subscription_history()
    except Exception:
        logger.exception("investorgain subscription-history fetch failed")
        subscription_rows = []

    for row in subscription_rows:
        outcome_id = _outcome_id(row.company_name)
        target = outcomes.get(outcome_id) or HistoricalOutcome(id=outcome_id, company_name=row.company_name)
        target.issue_size_cr = target.issue_size_cr or row.issue_size_cr
        target.issue_price = target.issue_price or row.issue_price
        target.pe_ratio = row.pe_ratio
        target.sub_qib_times = row.sub_qib_times
        target.sub_hni_times = row.sub_hni_times
        target.sub_retail_times = row.sub_retail_times
        target.sub_total_times = row.sub_total_times
        target.gmp_percent_at_close = row.gmp_percent_at_close
        outcomes[outcome_id] = target

    if outcomes:
        ipo_historical_repository.upsert_many(list(outcomes.values()))

    return len(outcomes)
