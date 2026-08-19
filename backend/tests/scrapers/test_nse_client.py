import json
from pathlib import Path

import pytest

from app.scrapers.market_data import nse_client
from tests.conftest import FakeAsyncClient, FakeResponse

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_get_current_issues_parses_calendar_fields(monkeypatch):
    fake_client = FakeAsyncClient(
        {"https://www.nseindia.com/api/ipo-current-issue": FakeResponse(json_data=_load("nse_current_issue.json"))}
    )
    monkeypatch.setattr(nse_client, "get_http_client", lambda: fake_client)

    issues = await nse_client.get_current_issues()

    assert len(issues) > 0
    first = issues[0]
    assert first.symbol == "SUNSHINE"
    assert first.company_name == "Sunshine Pictures Limited"
    # Real fixture uses "18-Aug-2026" style dates -> normalized to ISO.
    assert first.open_date == "2026-08-18"
    assert first.close_date == "2026-08-20"
    # Real fixture combines the band into one "Rs.342 to Rs.360" string.
    assert first.price_band_low == 342.0
    assert first.price_band_high == 360.0
    # Real fixture never includes a "lotSize" key at all for current-issue rows.
    assert first.lot_size is None
    # issue_size_cr is derived (shares offered * avg price / 1e7) since the
    # real "issueSize" field is a share count, not a rupee-crore amount.
    assert first.issue_size_cr == pytest.approx(5486051 * 351 / 1e7, rel=1e-6)

    # Rows without a price band (e.g. BSE-only listings in the real fixture)
    # must not blow up parsing; they just carry no band/derived size.
    no_band = next(i for i in issues if i.symbol == "SKYTECH")
    assert no_band.price_band_low is None
    assert no_band.price_band_high is None
    assert no_band.issue_size_cr is None


@pytest.mark.asyncio
async def test_get_subscription_parses_category_breakdown(monkeypatch):
    fake_client = FakeAsyncClient(
        {
            "https://www.nseindia.com/api/ipo-active-category": FakeResponse(
                json_data=_load("nse_active_category.json")
            )
        }
    )
    monkeypatch.setattr(nse_client, "get_http_client", lambda: fake_client)

    categories = await nse_client.get_subscription("SUNSHINE")

    assert len(categories) > 0
    assert all(c.category for c in categories)
    # The real payload's first dataList row is a header masquerading as data
    # (category="Category", values are column labels) and must be filtered out.
    assert all(c.category != "Category" for c in categories)

    qib = next(c for c in categories if c.category == "Qualified Institutional Buyers(QIBs)")
    assert qib.offered == 1567436
    assert qib.applied == 574
    assert qib.times == pytest.approx(3.6620314960228044e-4)

    # Rows with blank "" numeric strings (real fixture has plenty) must parse
    # to None rather than raising or becoming 0.
    fii = next(c for c in categories if c.category == "Foreign Institutional Investors(FIIs)")
    assert fii.offered is None
    assert fii.times is None


@pytest.mark.asyncio
async def test_get_all_indices_parses_broad_and_sector_indices(monkeypatch):
    fake_client = FakeAsyncClient(
        {"https://www.nseindia.com/api/allIndices": FakeResponse(json_data=_load("nse_all_indices.json"))}
    )
    monkeypatch.setattr(nse_client, "get_http_client", lambda: fake_client)

    indices = await nse_client.get_all_indices()

    assert len(indices) == 3
    broad = next(i for i in indices if i.index_symbol == "NIFTY 50")
    assert broad.percent_change_1d == -0.42
    assert broad.percent_change_30d == -1.16

    # Same response also carries sector indices (not a separate endpoint).
    auto = next(i for i in indices if i.index_symbol == "NIFTY AUTO")
    assert auto.percent_change_30d == 7.57


@pytest.mark.asyncio
async def test_get_quote_returns_last_price(monkeypatch):
    fake_client = FakeAsyncClient(
        {"https://www.nseindia.com/api/quote-equity": FakeResponse(json_data=_load("nse_quote.json"))}
    )
    monkeypatch.setattr(nse_client, "get_http_client", lambda: fake_client)

    price = await nse_client.get_quote("RELIANCE")

    assert price is None or isinstance(price, float)


@pytest.mark.asyncio
async def test_get_quote_returns_none_on_http_error(monkeypatch):
    # api/quote-equity was found to be blocked by an Akamai edge WAF (403
    # Access Denied) in this environment, independent of session cookies —
    # get_quote must degrade to None rather than raising, since Task 7
    # treats "no live price" as an acceptable, non-fatal outcome.
    fake_client = FakeAsyncClient(
        {"https://www.nseindia.com/api/quote-equity": FakeResponse(status_code=403, text_data="Access Denied")}
    )
    monkeypatch.setattr(nse_client, "get_http_client", lambda: fake_client)

    price = await nse_client.get_quote("RELIANCE")

    assert price is None
