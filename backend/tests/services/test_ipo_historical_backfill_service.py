from app.scrapers.market_data.investorgain_history_client import PerformanceHistoryRow, SubscriptionHistoryRow
from app.services import ipo_historical_backfill_service, ipo_historical_repository


async def test_backfill_merges_both_reports_by_company_name(monkeypatch):
    async def fake_performance():
        return [
            PerformanceHistoryRow(
                company_name="Acme Ltd",
                listing_date="2026-08-01",
                issue_size_cr=100.0,
                issue_price=50.0,
                subscription_total=10.0,
                listing_gain_percent=20.0,
                current_gain_percent=25.0,
            )
        ]

    async def fake_subscription():
        return [
            SubscriptionHistoryRow(
                company_name="Acme Limited",  # "Limited" suffix -- must still match "Acme Ltd" via normalization
                close_date="2026-07-30",
                pe_ratio=15.0,
                sub_qib_times=1.0,
                sub_hni_times=2.0,
                sub_retail_times=3.0,
                sub_total_times=2.0,
                gmp_percent_at_close=18.0,
            )
        ]

    monkeypatch.setattr(ipo_historical_backfill_service.investorgain_history_client, "get_performance_history", fake_performance)
    monkeypatch.setattr(ipo_historical_backfill_service.investorgain_history_client, "get_subscription_history", fake_subscription)

    count = await ipo_historical_backfill_service.backfill()

    assert count == 1
    outcome = ipo_historical_repository.get_all()[0]
    assert outcome.company_name == "Acme Ltd"
    assert outcome.listing_gain_percent == 20.0  # from performance report
    assert outcome.pe_ratio == 15.0  # from subscription report
    assert outcome.sub_qib_times == 1.0


async def test_backfill_handles_company_only_in_one_report(monkeypatch):
    async def fake_performance():
        return [PerformanceHistoryRow(company_name="Solo Ltd", listing_gain_percent=5.0)]

    async def fake_subscription():
        return []

    monkeypatch.setattr(ipo_historical_backfill_service.investorgain_history_client, "get_performance_history", fake_performance)
    monkeypatch.setattr(ipo_historical_backfill_service.investorgain_history_client, "get_subscription_history", fake_subscription)

    count = await ipo_historical_backfill_service.backfill()

    assert count == 1
    assert ipo_historical_repository.get_all()[0].company_name == "Solo Ltd"


async def test_backfill_survives_one_source_failing(monkeypatch):
    async def failing_performance():
        raise RuntimeError("site is down")

    async def fake_subscription():
        return [SubscriptionHistoryRow(company_name="Still Works Ltd", pe_ratio=10.0)]

    monkeypatch.setattr(ipo_historical_backfill_service.investorgain_history_client, "get_performance_history", failing_performance)
    monkeypatch.setattr(ipo_historical_backfill_service.investorgain_history_client, "get_subscription_history", fake_subscription)

    count = await ipo_historical_backfill_service.backfill()  # must not raise

    assert count == 1
