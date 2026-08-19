import json
from pathlib import Path

from app.scrapers.market_data import investorgain_history_client as hc
from tests.conftest import FakeAsyncClient, FakeResponse

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


async def test_get_performance_history_parses_real_fixture(monkeypatch):
    fake_client = FakeAsyncClient(
        {hc.PERFORMANCE_HISTORY_URL: FakeResponse(json_data=_load("investorgain_performance_history.json"))}
    )
    monkeypatch.setattr(hc, "get_http_client", lambda: fake_client)

    rows = await hc.get_performance_history()

    assert len(rows) == 6
    behari = next(r for r in rows if r.company_name == "Behari Lal Engineering")
    assert behari.listing_date == "2026-08-19"
    assert behari.issue_size_cr == 301.62
    # Real fixture embeds the price as "&#8377;285.00" -- the HTML entity's
    # own numeric code ("8377") must never leak into the parsed value.
    assert behari.issue_price == 285.0
    assert behari.subscription_total == 118.07
    assert behari.listing_gain_percent == 63.16
    assert behari.current_gain_percent == 0.0

    # Milky Mist has a real non-zero LTP (current price) gain, distinct
    # from its listing-day gain -- the two must not be conflated.
    milky = next(r for r in rows if r.company_name == "Milky Mist Dairy Food")
    assert milky.listing_gain_percent == 17.86
    assert milky.current_gain_percent == 29.64


async def test_get_subscription_history_parses_real_fixture(monkeypatch):
    fake_client = FakeAsyncClient(
        {hc.SUBSCRIPTION_HISTORY_URL: FakeResponse(json_data=_load("investorgain_subscription_history.json"))}
    )
    monkeypatch.setattr(hc, "get_http_client", lambda: fake_client)

    rows = await hc.get_subscription_history()

    assert len(rows) == 6
    sunshine = next(r for r in rows if r.company_name == "Sunshine Pictures")
    # Real fixture's "IPO" field mixes the plain company name with embedded
    # status/GMP badges as HTML -- company_name must be just the name.
    assert sunshine.close_date == "2026-08-20"
    assert sunshine.issue_size_cr == 282.14
    assert sunshine.issue_price == 360.0
    assert sunshine.pe_ratio == 23.7
    assert sunshine.sub_qib_times == 0.08
    assert sunshine.sub_hni_times == 25.56  # NII
    assert sunshine.sub_retail_times == 16.95  # RII
    assert sunshine.sub_total_times == 13.97
    assert sunshine.gmp_percent_at_close == 21.39

    # Negative P/E (loss-making company) must survive as a real negative
    # number, not get clipped to None by the digit-stripping regex.
    horizon = next(r for r in rows if r.company_name == "Horizon Industrial Parks")
    assert horizon.pe_ratio == -72.29
