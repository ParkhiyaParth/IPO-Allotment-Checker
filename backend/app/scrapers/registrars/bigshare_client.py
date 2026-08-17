"""Low-level client for the Bigshare IPO status AJAX API.

Reverse-engineered from the public JS inline in
https://ipo.bigshareonline.com/IPO_Status.html: the visible captcha there is
drawn on a <canvas> purely client-side (generateCaptcha() in that page),
with the plaintext answer stored in sessionStorage and compared to the
input *in JavaScript only* before the real search fires. The actual search
AJAX call (Data.aspx/FetchIpodetails) never transmits a captcha value and
doesn't require one — verified live. Nothing here defeats a server-side
protection; it's the same request the page's own button issues once its
client-side check passes.
"""

import re
from dataclasses import dataclass

from app.utils.http_client import get_http_client

BASE_URL = "https://ipo.bigshareonline.com"
SELECTION_TYPE_PAN = "PN"


@dataclass
class BigshareCompany:
    company_id: str
    company_name: str


@dataclass
class BigshareSearchResult:
    dp_id: str | None
    name: str | None
    applied: str | None
    allotted: str | None
    found: bool


async def get_active_companies() -> list[BigshareCompany]:
    client = get_http_client()
    resp = await client.get(f"{BASE_URL}/IPO_Status.html")
    resp.raise_for_status()
    html = resp.text

    match = re.search(r'<select id="ddlCompany">(.*?)</select>', html, re.S)
    if not match:
        return []
    block = match.group(1)
    block_no_comments = re.sub(r"<!--.*?-->", "", block, flags=re.S)
    companies = []
    for company_id, name in re.findall(r'<option value="(\d+)">([^<]+)</option>', block_no_comments):
        companies.append(BigshareCompany(company_id=company_id, company_name=name.strip()))
    return companies


async def search_by_pan(company_id: str, pan: str) -> BigshareSearchResult:
    client = get_http_client()
    resp = await client.post(
        f"{BASE_URL}/Data.aspx/FetchIpodetails",
        json={
            "Applicationno": "",
            "Company": company_id,
            "SelectionType": SELECTION_TYPE_PAN,
            "PanNo": pan,
            "txtcsdl": "",
            "txtDPID": "",
            "txtClId": "",
            "ddlType": "0",
            "lang": "en",
        },
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    resp.raise_for_status()
    data = resp.json()["d"]

    dp_id = data.get("DPID")
    if not dp_id or dp_id == "No data found":
        return BigshareSearchResult(dp_id=None, name=None, applied=None, allotted=None, found=False)

    return BigshareSearchResult(
        dp_id=dp_id,
        name=data.get("Name"),
        applied=data.get("APPLIED"),
        allotted=data.get("ALLOTED"),
        found=True,
    )
