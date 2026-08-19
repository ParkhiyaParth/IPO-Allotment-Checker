"""Clients for investorgain.com's two historical IPO reports -- confirmed
live via direct network probe (2026-08-19), same `webnodejs.investorgain.com
/cloud/v2/report/data-read/{report_id}/...` API family as the live GMP
report (investorgain_client.py), just different report ids:

- report 486 ("ipo-performance-history"): real past-IPO listing outcomes --
  listing date, issue size/price, total subscription, and BOTH the
  listing-day gain% and the current LTP gain%, each embedded in an HTML
  fragment like "<span class='text-success'><b>465.00 (63.16%)</b></span>".
- report 566 ("ipo-subscription-historical-data"): per-category
  subscription multiples (QIB/SHNI/BHNI/NII/RII/Total) for the same
  historical window, plus P/E and a GMP badge embedded in the "IPO" field's
  HTML fragment.

Confirmed live: passing a prior year in the URL's year/fiscal-year path
segments (e.g. .../2025/2025-26/...) returns only a handful of rows
instead of that whole year -- full multi-year depth needs more
reverse-engineering than this pass covered. For now this only reliably
covers the current fiscal year's IPOs (~50+ real ones as of 2026-08-19),
which is still a large improvement over this app's own near-empty
signal_accuracy_log.
"""

import html
import re
from dataclasses import dataclass

from app.utils.http_client import get_http_client

PERFORMANCE_HISTORY_URL = "https://webnodejs.investorgain.com/cloud/v2/report/data-read/486/1/8/2026/2026-27/0/ipo"
SUBSCRIPTION_HISTORY_URL = "https://webnodejs.investorgain.com/cloud/v2/report/data-read/566/1/8/2026/2026-27/0/ipo"

_TAG_RE = re.compile(r"<[^>]+>")
_PERCENT_IN_PARENS_RE = re.compile(r"\(([-\d.]+)%\)")
_ORDINAL_SUFFIX_RE = re.compile(r"(\d+)(st|nd|rd|th)")
_GMP_BADGE_RE = re.compile(r"GMP:[^\d-]*(-?[\d.]+)\s*\(([-\d.]+)%\)")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


def _to_float(value) -> float | None:
    """Confirmed live: numeric-looking fields on these two reports embed
    HTML entities directly IN the value (e.g. "&#8377;285.00", unlike the
    live GMP report where price/size values never carry an entity) --
    html.unescape() must run before stripping non-digit characters, or the
    entity's own numeric code (e.g. "8377" from "&#8377;") corrupts the
    real number."""
    if value is None or value == "" or value == "-" or value == "--":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^\d.\-]", "", html.unescape(str(value)))
    if not cleaned or cleaned in ("-", "."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _to_times(value) -> float | None:
    """Parses "118.07x" (optionally still wrapped in HTML like "<b>13.97x</b>") -> 118.07."""
    return _to_float(_strip_html(str(value)).rstrip("x")) if value else None


def _parse_dmy_date(value: str | None) -> str | None:
    """"19-Aug-2026" -> "2026-08-19". Returns None if missing/unparsable."""
    if not value:
        return None
    from datetime import datetime

    try:
        return datetime.strptime(value.strip(), "%d-%b-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _parse_ordinal_date(value: str | None) -> str | None:
    """"20th Aug 2026" -> "2026-08-20". Drops any trailing time-of-day
    (e.g. "19th Aug 14:11" has no year at all -- returns None, since a
    close/bid date without a year isn't usable)."""
    if not value:
        return None
    from datetime import datetime

    cleaned = _ORDINAL_SUFFIX_RE.sub(r"\1", value.strip())
    try:
        return datetime.strptime(cleaned, "%d %b %Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


@dataclass
class PerformanceHistoryRow:
    company_name: str
    listing_date: str | None = None
    issue_size_cr: float | None = None
    issue_price: float | None = None
    subscription_total: float | None = None
    listing_gain_percent: float | None = None
    current_gain_percent: float | None = None


def _parse_performance_row(row: dict) -> PerformanceHistoryRow:
    listing_price_html = row.get("Listing Price", "")
    gain_match = _PERCENT_IN_PARENS_RE.search(listing_price_html)

    return PerformanceHistoryRow(
        company_name=(row.get("IPO") or "").strip(),
        listing_date=_parse_dmy_date(row.get("Listing Date")),
        issue_size_cr=_to_float(row.get("IPO_Size")),
        issue_price=_to_float(row.get("IPO Price")),
        subscription_total=_to_times(row.get("Subscription")),
        listing_gain_percent=_to_float(gain_match.group(1)) if gain_match else None,
        current_gain_percent=_to_float(row.get("LTP_Percent")),
    )


async def get_performance_history() -> list[PerformanceHistoryRow]:
    client = get_http_client()
    resp = await client.get(PERFORMANCE_HISTORY_URL, params={"search": "", "v": "10-49"})
    resp.raise_for_status()
    rows = resp.json().get("reportTableData", [])
    return [_parse_performance_row(r) for r in rows if r.get("IPO")]


@dataclass
class SubscriptionHistoryRow:
    company_name: str
    close_date: str | None = None
    issue_size_cr: float | None = None
    issue_price: float | None = None
    pe_ratio: float | None = None
    sub_qib_times: float | None = None
    sub_hni_times: float | None = None  # NII -- combined non-institutional
    sub_retail_times: float | None = None  # RII
    sub_total_times: float | None = None
    gmp_percent_at_close: float | None = None


def _parse_subscription_row(row: dict) -> SubscriptionHistoryRow:
    ipo_html = html.unescape(row.get("IPO") or "")
    gmp_match = _GMP_BADGE_RE.search(ipo_html)

    return SubscriptionHistoryRow(
        company_name=_strip_html(ipo_html.split("<span", 1)[0]),
        close_date=_parse_ordinal_date(row.get("Close Date")),
        issue_size_cr=_to_float(row.get("IPO Size")),
        issue_price=_to_float(row.get("IPO Price")),
        pe_ratio=_to_float(row.get("P/E")),
        sub_qib_times=_to_times(row.get("QIB")),
        sub_hni_times=_to_times(row.get("NII")),
        sub_retail_times=_to_times(row.get("RII")),
        sub_total_times=_to_times(row.get("Total")),
        gmp_percent_at_close=_to_float(gmp_match.group(2)) if gmp_match else None,
    )


async def get_subscription_history() -> list[SubscriptionHistoryRow]:
    client = get_http_client()
    resp = await client.get(SUBSCRIPTION_HISTORY_URL, params={"search": "", "v": "10-49"})
    resp.raise_for_status()
    rows = resp.json().get("reportTableData", [])
    return [_parse_subscription_row(r) for r in rows if r.get("IPO")]
