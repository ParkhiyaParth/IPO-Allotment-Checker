"""Low-level client for NSE's public IPO data APIs.

Confirmed live (see backend/tests/fixtures/nse_current_issue.json and
nse_active_category.json for real captured samples, taken 2026-08-18): a
plain browser-UA GET against api/ipo-current-issue and
api/ipo-active-category returns JSON directly, no login or cookie/session
dance required. The real schemas differ noticeably from a naive first
guess, which is why this client's field-name lookups look the way they do:

- api/ipo-current-issue returns a flat *list* of rows (no wrapper object).
  Real keys: symbol, companyName, issueStartDate, issueEndDate (as
  "DD-Mon-YYYY", e.g. "18-Aug-2026" -- NOT ISO, must be reparsed), issuePrice
  (a single combined string like "Rs.342 to Rs.360" -- NOT separate
  min/max fields), issueSize (a *share count*, confirmed equal to the
  row's own noOfSharesOffered -- NOT a rupee-crore amount despite the
  dataclass field being named issue_size_cr; this client derives a crore
  value from shares * average band price). There is no lotSize key at all
  in this endpoint's response, so lot_size is always None here. Some rows
  (BSE-only listings, seen live as isBse: true) omit issuePrice/issueSize/
  category entirely; those parse to an issue with None price band and size.

- api/ipo-active-category returns {"dataList": [...], "heading", "symbol",
  "updateTime"}. Real keys per row: category, noOfShareOffered (singular
  "Share", NOT "noOfSharesOffered" like the current-issue endpoint uses),
  noOfSharesBid, noOfTotalMeant (NOT noOfTimesSubscribed/subscriptionTimes).
  Numeric fields are strings, sometimes "" (blank) for categories with no
  data, sometimes in scientific notation (e.g. "3.6620314960228044E-4"),
  which float() handles natively. The dataList's *first* element is a
  header-as-data row (category="Category", other fields hold column
  labels, srNo="Sr.No.") and is filtered out here rather than exposed as a
  bogus category.

- api/allIndices (confirmed live 2026-08-19, no cookie priming needed --
  same trust level as the other two working endpoints, not quote-equity)
  returns {"data": [...]}, one row per NSE index (139 total, broad market
  AND every sector index in the same response -- no separate per-sector
  endpoint needed). Real keys: index (display name, e.g. "NIFTY 50"),
  indexSymbol (e.g. "NIFTY 50", "NIFTY AUTO"), percentChange (1-day),
  perChange30d, perChange365d.

- api/quote-equity could NOT be captured live in the dev environment: it
  (and even a bare GET of https://www.nseindia.com/) returned a persistent
  Akamai edge "403 Access Denied", reproducible across a plain
  browser-UA request, a cookie-primed request (GET / to prime cookies,
  then replay via -b), and multiple retries. This looks like an
  environment/IP-level WAF block specific to that endpoint family rather
  than an app-level session requirement (the other two endpoints needed no
  cookies at all), so there was nothing a cookie dance could fix here. The
  parsing logic below (priceInfo.lastPrice) follows NSE's widely
  documented public quote-equity schema, but is NOT confirmed against a
  real live capture -- see tests/fixtures/nse_quote.json's "_source" note.
  Because this endpoint is known to be flaky/blocked, get_quote treats any
  request failure as "price unavailable" (returns None) rather than
  raising, unlike the other two functions.
"""

import re
from dataclasses import dataclass
from datetime import datetime

from app.utils.http_client import get_http_client
from app.utils.parsing import to_int

BASE_URL = "https://www.nseindia.com/api"

_PRICE_BAND_RE = re.compile(
    r"(?:Rs\.?\s*)?(\d+(?:\.\d+)?)\s*to\s*(?:Rs\.?\s*)?(\d+(?:\.\d+)?)", re.IGNORECASE
)
_HEADER_ROW_SR_NO = "Sr.No."


@dataclass
class NseIpoIssue:
    symbol: str
    company_name: str
    open_date: str | None = None
    close_date: str | None = None
    price_band_low: float | None = None
    price_band_high: float | None = None
    lot_size: int | None = None
    issue_size_cr: float | None = None


@dataclass
class NseIndexTrend:
    index_symbol: str
    percent_change_1d: float | None = None
    percent_change_30d: float | None = None


@dataclass
class NseCategorySubscription:
    category: str
    sr_no: str | None = None
    offered: int | None = None
    applied: int | None = None
    times: float | None = None


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int_field(value) -> int | None:
    if value is None:
        return None
    return to_int(str(value))


def _parse_nse_date(value: str | None) -> str | None:
    """Converts NSE's "DD-Mon-YYYY" date strings (e.g. "18-Aug-2026") to
    ISO "YYYY-MM-DD". Returns None if the value is missing or unparsable.
    """
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d-%b-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _parse_price_band(issue_price: str | None) -> tuple[float | None, float | None]:
    """Parses NSE's combined "Rs.342 to Rs.360" band string into
    (low, high). Returns (None, None) if the field is missing or the
    format doesn't match (e.g. BSE-only rows that omit it entirely).
    """
    if not issue_price:
        return None, None
    match = _PRICE_BAND_RE.search(issue_price)
    if not match:
        return None, None
    return _to_float(match.group(1)), _to_float(match.group(2))


def _parse_issue(row: dict) -> NseIpoIssue:
    price_low, price_high = _parse_price_band(row.get("issuePrice"))

    issue_size_cr = None
    shares = _to_float(row.get("issueSize"))
    if shares is not None and price_low is not None and price_high is not None:
        avg_price = (price_low + price_high) / 2
        issue_size_cr = shares * avg_price / 1e7

    return NseIpoIssue(
        symbol=row.get("symbol", ""),
        company_name=row.get("companyName", ""),
        open_date=_parse_nse_date(row.get("issueStartDate")),
        close_date=_parse_nse_date(row.get("issueEndDate")),
        price_band_low=price_low,
        price_band_high=price_high,
        lot_size=_to_int_field(row.get("lotSize")),
        issue_size_cr=issue_size_cr,
    )


async def get_current_issues() -> list[NseIpoIssue]:
    client = get_http_client()
    resp = await client.get(f"{BASE_URL}/ipo-current-issue")
    resp.raise_for_status()
    data = resp.json()
    rows = data if isinstance(data, list) else data.get("data", [])
    return [_parse_issue(row) for row in rows]


def _parse_category(row: dict) -> NseCategorySubscription:
    return NseCategorySubscription(
        category=row.get("category", ""),
        sr_no=row.get("srNo"),
        offered=_to_int_field(row.get("noOfShareOffered")),
        applied=_to_int_field(row.get("noOfSharesBid")),
        times=_to_float(row.get("noOfTotalMeant")),
    )


async def get_subscription(symbol: str) -> list[NseCategorySubscription]:
    client = get_http_client()
    resp = await client.get(f"{BASE_URL}/ipo-active-category", params={"symbol": symbol, "series": "EQ"})
    resp.raise_for_status()
    data = resp.json()
    rows = data.get("dataList", []) if isinstance(data, dict) else data
    return [
        _parse_category(row)
        for row in rows
        if row.get("srNo") != _HEADER_ROW_SR_NO and row.get("category") != "Category"
    ]


async def get_all_indices() -> list[NseIndexTrend]:
    client = get_http_client()
    resp = await client.get(f"{BASE_URL}/allIndices")
    resp.raise_for_status()
    data = resp.json()
    rows = data.get("data", []) if isinstance(data, dict) else data
    return [
        NseIndexTrend(
            index_symbol=row.get("indexSymbol", ""),
            percent_change_1d=_to_float(row.get("percentChange")),
            percent_change_30d=_to_float(row.get("perChange30d")),
        )
        for row in rows
        if row.get("indexSymbol")
    ]


async def get_quote(symbol: str) -> float | None:
    # api/quote-equity is known to be blocked by an Akamai edge WAF at
    # times (see module docstring); treat any failure here as "price
    # unavailable" rather than letting it propagate.
    try:
        client = get_http_client()
        resp = await client.get(f"{BASE_URL}/quote-equity", params={"symbol": symbol})
        if getattr(resp, "status_code", 200) >= 400:
            return None
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    if not isinstance(data, dict):
        return None
    price_info = data.get("priceInfo", data)
    return _to_float(price_info.get("lastPrice"))
