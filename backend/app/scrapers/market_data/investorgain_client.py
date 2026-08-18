"""Client for investorgain.com's live IPO GMP report.

Replaces the original chittorgarh_client.py, which guessed a GMP report
URL on chittorgarh.com that turned out wrong (307 redirect to an unrelated
page). Chittorgarh's own IPO pages link out to investorgain.com for GMP
("Grey Market Premium" links point to
https://www.investorgain.com/report/live-ipo-gmp/331/ipo/) -- chittorgarh
doesn't host this data itself.

Reverse-engineered live via a real browser: that report page's own table
is populated by an XHR to this exact endpoint (report id 331 matches the
URL slug), no auth/cookies needed:

    GET https://webnodejs.investorgain.com/cloud/v2/report/data-read/331/1/8/2026/2026-27/0/ipo

Confirmed live (2026-08-18) to return richer data than either the original
GMP guess or NSE's current-issue endpoint: every row -- upcoming, open,
closed, and already-listed -- carries clean ISO open/close/BoA/listing
dates AND a lot size (which NSE's ipo-current-issue endpoint never
provides at all). Status is conveyed by a badge embedded in the "Name"
HTML fragment: "U" (bg-warning) = upcoming, "O" (bg-success) = open, "C"
(bg-primary) = closed/awaiting listing, no badge = already listed.
"""

import re
from dataclasses import dataclass

from app.utils.http_client import get_http_client
from app.utils.parsing import to_int

REPORT_URL = "https://webnodejs.investorgain.com/cloud/v2/report/data-read/331/1/8/2026/2026-27/0/ipo"

_GMP_VALUE_RE = re.compile(r"<b>(-?[\d.]+)</b>")
_ISSUE_SIZE_RE = re.compile(r"([\d.]+)\s*Cr")
_BADGE_RE = re.compile(r'bg-(?:warning|success|primary)[^>]*>([A-Z])<')

_STATUS_BY_BADGE = {"U": "upcoming", "O": "open", "C": "closed"}


@dataclass
class InvestorgainIpoRow:
    company_name: str
    status: str  # "upcoming" | "open" | "closed" | "listed"
    gmp_value: float | None = None
    gmp_percent: float | None = None
    lot_size: int | None = None
    issue_size_cr: float | None = None
    issue_price: float | None = None
    open_date: str | None = None
    close_date: str | None = None
    boa_date: str | None = None
    listing_date: str | None = None


def _to_float(value) -> float | None:
    if value is None or value == "" or value == "-":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_row(row: dict) -> InvestorgainIpoRow:
    badge_match = _BADGE_RE.search(row.get("Name", ""))
    status = _STATUS_BY_BADGE.get(badge_match.group(1), "listed") if badge_match else "listed"

    gmp_match = _GMP_VALUE_RE.search(row.get("GMP", ""))
    gmp_value = _to_float(gmp_match.group(1)) if gmp_match else None

    issue_size_match = _ISSUE_SIZE_RE.search(row.get("IPO Size", ""))
    issue_size_cr = _to_float(issue_size_match.group(1)) if issue_size_match else None

    return InvestorgainIpoRow(
        company_name=row.get("~ipo_name", "").strip(),
        status=status,
        gmp_value=gmp_value,
        gmp_percent=_to_float(row.get("~gmp_percent_calc")),
        lot_size=to_int(str(row.get("Lot"))) if row.get("Lot") else None,
        issue_size_cr=issue_size_cr,
        issue_price=_to_float(row.get("Price (₹)")),
        open_date=row.get("~Srt_Open") or None,
        close_date=row.get("~Srt_Close") or None,
        boa_date=row.get("~Srt_BoA_Dt") or None,
        listing_date=row.get("~Str_Listing") or None,
    )


async def get_live_report() -> list[InvestorgainIpoRow]:
    client = get_http_client()
    resp = await client.get(REPORT_URL, params={"search": "", "v": "10-49"})
    resp.raise_for_status()
    data = resp.json()
    rows = data.get("reportTableData", [])
    return [_parse_row(row) for row in rows if row.get("~ipo_name")]
