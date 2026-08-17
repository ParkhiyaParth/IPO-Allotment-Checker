"""Low-level client for the Link Intime / MUFG Intime IPO status AJAX API.

Reverse-engineered from the public JS served alongside
https://in.mpms.mufg.com/Initial_Offer/public-issues.html (js/custom.js,
js/aes.js) — this module replicates the exact request sequence a browser
makes when a user checks their own status manually:

    1. POST IPO.aspx/GetDetails        -> current list of {company_id, companyname}
    2. POST IPO.aspx/generateToken     -> a short-lived raw token
    3. AES-128-CBC/PKCS7 encrypt the token with the *static* key/IV that
       ships in the site's own js/aes.js (key = iv = "8080808080808080"),
       base64-encode it -> the "token" field expected by step 4
    4. POST IPO.aspx/SearchOnPan       -> {clientid, PAN, IFSC, CHKVAL, token}

Notably, the client-side captcha-match check in custom.js is commented out
and SearchOnPan's payload never includes a captcha value at all — verified
live that the endpoint answers without one. No protection is being
bypassed here; this is the same request the site's own page issues.
"""

import base64
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from app.utils.http_client import get_http_client
from app.utils.parsing import to_int

BASE_URL = "https://in.mpms.mufg.com/Initial_Offer/IPO.aspx"
_AES_KEY = b"8080808080808080"
_AES_IV = b"8080808080808080"
CHKVAL_PAN = "1"


@dataclass
class LinkIntimeCompany:
    company_id: str
    company_name: str


@dataclass
class LinkIntimeRecord:
    name: str | None = None
    shares_applied: int | None = None
    shares_allotted: int | None = None
    refund_amount: float | None = None


@dataclass
class LinkIntimeSearchResult:
    records: list[LinkIntimeRecord]
    message: str | None = None


def _encrypt_token(raw_token: str) -> str:
    cipher = AES.new(_AES_KEY, AES.MODE_CBC, _AES_IV)
    ciphertext = cipher.encrypt(pad(raw_token.encode("utf-8"), AES.block_size))
    return base64.b64encode(ciphertext).decode("ascii")


async def get_companies() -> list[LinkIntimeCompany]:
    client = get_http_client()
    resp = await client.post(
        f"{BASE_URL}/GetDetails",
        json={},
        headers={"Content-Type": "application/json;charset=UTF-8"},
    )
    resp.raise_for_status()
    xml_text = resp.json()["d"]
    root = ET.fromstring(xml_text)
    companies = []
    for table in root.findall("Table"):
        company_id = table.findtext("company_id", default="").strip()
        company_name = table.findtext("companyname", default="").strip()
        if company_id and company_name:
            companies.append(LinkIntimeCompany(company_id, company_name))
    return companies


async def _generate_encrypted_token() -> str:
    client = get_http_client()
    resp = await client.post(
        f"{BASE_URL}/generateToken",
        json={},
        headers={"Content-Type": "application/json;charset=UTF-8"},
    )
    resp.raise_for_status()
    raw_token = resp.json()["d"]
    return _encrypt_token(raw_token)


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


async def search_by_pan(clientid: str, pan: str) -> LinkIntimeSearchResult:
    token = await _generate_encrypted_token()
    client = get_http_client()
    resp = await client.post(
        f"{BASE_URL}/SearchOnPan",
        json={
            "clientid": clientid,
            "PAN": pan,
            "IFSC": "",
            "CHKVAL": CHKVAL_PAN,
            "token": token,
        },
        headers={"Content-Type": "application/json;charset=UTF-8"},
    )
    resp.raise_for_status()
    xml_text = resp.json()["d"]
    root = ET.fromstring(xml_text)

    message = None
    table1 = root.find("Table1")
    if table1 is not None:
        message = table1.findtext("Msg", default=None)

    records = []
    for table in root.findall("Table"):
        records.append(
            LinkIntimeRecord(
                name=table.findtext("NAME1", default=None),
                shares_applied=to_int(table.findtext("SHARES", default=None)),
                shares_allotted=to_int(table.findtext("ALLOT", default=None)),
                refund_amount=_to_float(table.findtext("RFNDAMT", default=None)),
            )
        )

    return LinkIntimeSearchResult(records=records, message=message)
