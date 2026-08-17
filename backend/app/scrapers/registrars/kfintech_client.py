"""Low-level client for KFintech's real IPO status API.

Reverse-engineered by loading https://ipostatus.kfintech.com/ (the current
production status-check app) in a real browser and observing the network
request its own "Submit" button issues: a plain GET to KFintech's AWS API
Gateway, with the selected IPO and PAN passed as request *headers*
(client_id, reqparam) rather than query params or a body. No captcha, no
session token, no WAF challenge on this endpoint — verified it also answers
identically to a plain server-side HTTP client, not just a browser. This is
the same request the page's own Submit button makes.

The IPO dropdown's options are bundled directly into the app's JS at build
time rather than fetched from an API, so the list of {client_id, name}
pairs is scraped from the built bundle (see get_active_ipos below).
"""

import re

import httpx

from app.utils.http_client import get_http_client
from app.utils.parsing import to_int

API_URL = "https://0uz601ms56.execute-api.ap-south-1.amazonaws.com/prod/api/query"
BUNDLE_PAGE_URL = "https://ipostatus.kfintech.com/"


class KfintechIpo:
    def __init__(self, client_id: str, name: str):
        self.client_id = client_id
        self.name = name


async def get_active_ipos() -> list[KfintechIpo]:
    client = get_http_client()
    page_resp = await client.get(BUNDLE_PAGE_URL)
    page_resp.raise_for_status()
    bundle_match = re.search(r'static/js/(main\.[a-f0-9]+\.js)', page_resp.text)
    if not bundle_match:
        return []

    bundle_resp = await client.get(f"{BUNDLE_PAGE_URL}static/js/{bundle_match.group(1)}")
    bundle_resp.raise_for_status()
    bundle = bundle_resp.text

    # The dropdown options are embedded as a JSON.parse('[{"clientId":"...",
    # "name":"..."},...]') literal baked into the bundle at build time.
    ipos = [
        KfintechIpo(client_id=client_id, name=name)
        for client_id, name in re.findall(r'\{"clientId":"(\d+)","name":"([^"]+)"\}', bundle)
    ]
    return ipos


class KfintechSearchResult:
    def __init__(self, found: bool, shares_allotted: int | None = None, raw: dict | None = None):
        self.found = found
        self.shares_allotted = shares_allotted
        self.raw = raw or {}


def _is_allotted_key(key: str) -> bool:
    normalized = key.lower().replace("_", "").replace(" ", "")
    # "allot" covers most naming (allotted/ALLOT/AllotQty); "allshares" covers
    # KFintech's real, confirmed-live field name "All_Shares" (an
    # abbreviation that doesn't contain "allot" at all).
    return "allot" in normalized or normalized == "allshares"


def _extract_allotted(data: object) -> int | None:
    """Recursively searches the response for the allotted-shares field.

    The real response turned out to be wrapped in a nested
    {"data": [{...}]} envelope with abbreviated field names (confirmed live:
    Appln_No, Name, DP_CLID, Pan_No, App_Shares, All_Shares) rather than
    flat top-level fields, so this walks dicts/lists at any depth instead of
    assuming a fixed shape.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if _is_allotted_key(key):
                parsed = to_int(str(value))
                if parsed is not None:
                    return parsed
        for value in data.values():
            found = _extract_allotted(value)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _extract_allotted(item)
            if found is not None:
                return found
    return None


async def search_by_pan(client_id: str, pan: str) -> KfintechSearchResult:
    client = get_http_client()
    try:
        resp = await client.get(
            API_URL,
            params={"type": "pan"},
            headers={
                "accept": "application/json, text/plain, */*",
                "client_id": client_id,
                "reqparam": pan,
                "origin": "https://ipostatus.kfintech.com",
                "referer": "https://ipostatus.kfintech.com/",
            },
        )
    except httpx.HTTPError:
        raise

    if resp.status_code == 404:
        return KfintechSearchResult(found=False)

    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        return KfintechSearchResult(found=False)

    return KfintechSearchResult(found=True, shares_allotted=_extract_allotted(data), raw=data)
