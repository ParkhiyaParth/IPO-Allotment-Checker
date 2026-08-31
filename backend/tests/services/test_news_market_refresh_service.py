from datetime import date, timedelta

from app.scrapers.market_data.nse_client import NseIndexTrend
from app.scrapers.news.news_client import NewsHeadline
from app.services import (
    ipo_catalog_repository,
    market_trend_repository,
    news_headlines_repository,
    news_market_refresh_service,
    news_sentiment_repository,
)
from app.services.ipo_catalog_repository import CatalogRecord

TODAY = date.today()
YESTERDAY = (TODAY - timedelta(days=1)).isoformat()
TOMORROW = (TODAY + timedelta(days=1)).isoformat()


async def test_refresh_daily_updates_market_trend(monkeypatch):
    async def fake_indices():
        return [NseIndexTrend(index_symbol="NIFTY 50", percent_change_1d=-0.5, percent_change_30d=2.0)]

    async def fake_backfill():
        return 0

    monkeypatch.setattr(news_market_refresh_service.nse_client, "get_all_indices", fake_indices)
    monkeypatch.setattr(news_market_refresh_service.ipo_historical_backfill_service, "backfill", fake_backfill)

    await news_market_refresh_service.refresh_daily()

    trend = market_trend_repository.get("NIFTY 50")
    assert trend is not None
    assert trend.percent_change_30d == 2.0


async def test_refresh_daily_fetches_news_only_for_non_closed_ipos(monkeypatch):
    ipo_catalog_repository.upsert_many(
        [
            CatalogRecord(
                id="catalog-open", company_name="Open Co", open_date=YESTERDAY, close_date=TOMORROW, first_seen_at="2026-01-01T00:00:00Z"
            ),
            CatalogRecord(
                id="catalog-closed",
                company_name="Closed Co",
                open_date=(TODAY - timedelta(days=10)).isoformat(),
                close_date=(TODAY - timedelta(days=5)).isoformat(),
                first_seen_at="2026-01-01T00:00:00Z",
            ),
        ]
    )

    queried_companies = []

    async def fake_get_headlines(query, limit=20):
        queried_companies.append(query)
        return [
            NewsHeadline(
                title="Great news for the IPO", published_at=None, source=None, link="https://example.com/a"
            )
        ]

    async def fake_indices():
        return []

    async def fake_backfill():
        return 0

    monkeypatch.setattr(news_market_refresh_service.news_client, "get_headlines", fake_get_headlines)
    monkeypatch.setattr(news_market_refresh_service.nse_client, "get_all_indices", fake_indices)
    monkeypatch.setattr(news_market_refresh_service.ipo_historical_backfill_service, "backfill", fake_backfill)

    await news_market_refresh_service.refresh_daily()

    assert any("Open Co" in q for q in queried_companies)
    assert not any("Closed Co" in q for q in queried_companies)

    cached = news_sentiment_repository.get("catalog-open")
    assert cached is not None
    assert cached.headline_count == 1
    assert cached.sentiment_score is not None

    cached_headlines = news_headlines_repository.get("catalog-open")
    assert [h.title for h in cached_headlines] == ["Great news for the IPO"]
    assert cached_headlines[0].link == "https://example.com/a"


async def test_refresh_daily_survives_news_fetch_failure_for_one_company(monkeypatch):
    ipo_catalog_repository.upsert_many(
        [
            CatalogRecord(id="catalog-a", company_name="A Co", open_date=YESTERDAY, close_date=TOMORROW, first_seen_at="2026-01-01T00:00:00Z"),
            CatalogRecord(id="catalog-b", company_name="B Co", open_date=YESTERDAY, close_date=TOMORROW, first_seen_at="2026-01-01T00:00:00Z"),
        ]
    )

    async def flaky_get_headlines(query, limit=20):
        if "A Co" in query:
            raise RuntimeError("news source down")
        return [NewsHeadline(title="ok", published_at=None, source=None)]

    async def fake_indices():
        return []

    async def fake_backfill():
        return 0

    monkeypatch.setattr(news_market_refresh_service.news_client, "get_headlines", flaky_get_headlines)
    monkeypatch.setattr(news_market_refresh_service.nse_client, "get_all_indices", fake_indices)
    monkeypatch.setattr(news_market_refresh_service.ipo_historical_backfill_service, "backfill", fake_backfill)

    await news_market_refresh_service.refresh_daily()  # must not raise

    assert news_sentiment_repository.get("catalog-a") is None
    assert news_sentiment_repository.get("catalog-b") is not None
