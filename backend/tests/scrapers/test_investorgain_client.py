import json
from pathlib import Path

import pytest

from app.scrapers.market_data import investorgain_client
from tests.conftest import FakeAsyncClient, FakeResponse

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_get_live_report_parses_all_status_badges(monkeypatch):
    # Real capture (2026-08-18) confirmed to include all four statuses in
    # one response: upcoming (bg-warning "U"), open (bg-success "O"),
    # closed (bg-primary "C"), and already-listed (no badge at all).
    fake_client = FakeAsyncClient(
        {
            investorgain_client.REPORT_URL: FakeResponse(
                json_data=_load("investorgain_gmp_report.json")
            )
        }
    )
    monkeypatch.setattr(investorgain_client, "get_http_client", lambda: fake_client)

    rows = await investorgain_client.get_live_report()

    assert len(rows) == 15
    statuses = {r.status for r in rows}
    assert statuses == {"upcoming", "open", "closed", "listed"}

    skyways = next(r for r in rows if r.company_name == "Skyways Air")
    assert skyways.status == "upcoming"
    assert skyways.gmp_value == 31.0
    assert skyways.gmp_percent == pytest.approx(22.46)
    assert skyways.lot_size == 100
    assert skyways.issue_size_cr == pytest.approx(582.80)
    assert skyways.open_date == "2026-08-24"
    assert skyways.close_date == "2026-08-27"
    assert skyways.listing_date == "2026-09-01"
    # Real fixture: "Rating" sends the fire emoji as a literal HTML entity
    # ("&#128293;") repeated N times, "Anchor" sends a pre-decoded unicode
    # checkmark, "~P/E" is the literal string "--" when not yet known.
    assert skyways.rating == 4
    assert skyways.has_anchor is True
    assert skyways.pe_ratio is None

    # Real fixture includes rows already past listing with no status badge
    # at all in the "Name" HTML fragment -- must default to "listed" rather
    # than raising or miscategorizing as "closed".
    already_listed = next(r for r in rows if r.company_name == "Technocraft Ventures")
    assert already_listed.status == "listed"


@pytest.mark.asyncio
async def test_get_live_report_handles_missing_gmp_gracefully(monkeypatch):
    # A row with no GMP data yet (e.g. a freshly-added upcoming IPO) has
    # "GMP":"--" or similar with no <b>NUMBER</b> to match -- must parse to
    # None, not raise.
    payload = {
        "reportTableData": [
            {
                "~ipo_name": "Test Co",
                "Name": '<a>Test Co</a> <span class="badge bg-warning">U</span>',
                "GMP": "--",
                "~gmp_percent_calc": "",
                "Lot": "",
                "IPO Size": "",
                "~Srt_Open": "2026-09-01",
                "~Srt_Close": "2026-09-03",
                "~Str_Listing": None,
            }
        ]
    }
    fake_client = FakeAsyncClient(
        {investorgain_client.REPORT_URL: FakeResponse(json_data=payload)}
    )
    monkeypatch.setattr(investorgain_client, "get_http_client", lambda: fake_client)

    rows = await investorgain_client.get_live_report()

    assert len(rows) == 1
    row = rows[0]
    assert row.status == "upcoming"
    assert row.gmp_value is None
    assert row.gmp_percent is None
    assert row.lot_size is None
    assert row.issue_size_cr is None
    assert row.listing_date is None
    # Rating/Anchor/P-E keys absent entirely (older cache shape or a row
    # missing that data) must default sanely, not raise.
    assert row.rating is None
    assert row.pe_ratio is None
    assert row.has_anchor is False
