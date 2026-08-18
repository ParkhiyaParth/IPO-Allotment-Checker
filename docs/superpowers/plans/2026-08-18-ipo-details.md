# IPO Details Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an IPO-details feature — Open/Upcoming/Closed tabs, IPO cards with dates/price band/lot size/issue size/GMP, and a detail screen with subscription-by-category and listing-vs-current price — sourced from NSE's public JSON endpoints and Chittorgarh's server-rendered GMP page, without touching the existing allotment-check feature's data or logic.

**Architecture:** New backend subsystem (`ipo_catalog` table + repository + service + two scraper clients) refreshed on its own periodic schedule, exposed via two new `GET /ipos/catalog*` endpoints. Mobile: `IPOListScreen` becomes a 3-tab view over the new endpoint; a new `IPODetailScreen` shows the rich detail; the *existing* PAN-check screen is renamed to `AllotmentCheckScreen` and reached via a separate button instead of tap-to-open.

**Tech Stack:** FastAPI/httpx/SQLite (backend, matching existing patterns), React Native/Expo/React Query/TypeScript (mobile, matching existing patterns). New: `pytest` + `pytest-asyncio` (backend had no test infra), `jest-expo` + `@testing-library/react-native` (mobile had no test infra).

**Spec:** `docs/superpowers/specs/2026-08-18-ipo-details-design.md`

## Global Constraints

- No official GMP source exists — Chittorgarh scraping is best-effort; any field it can't supply renders as "—", never blocks the rest of a record.
- A source-fetch failure during refresh must never null out previously-cached values for other fields (partial-failure tolerant, same principle as `ipo_list_service.refresh`).
- Identity matching across NSE/Chittorgarh/registrar records uses exact normalized-name matching only — no fuzzy-matching library.
- Status (`open`/`upcoming`/`closed`) is computed at read time from dates, never stored.
- Catalog refresh cadence: every 15 min during 9:00–17:00 IST, every 2 hours off-hours (mirrors the existing evening-window pattern in `main.py`).
- v1 scope excludes: About/Strength/Risk factors, DRHP/RHP/Capital-Structure/Anchor file links, Lot Distribution table, IPO Reservation breakup, QIB Interest Cost table.

---

## Task 1: Backend test infrastructure

**Files:**
- Create: `backend/requirements-dev.txt`
- Create: `backend/pytest.ini`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_smoke.py`

**Interfaces:**
- Produces: an autouse `_isolated_db` fixture (every test gets its own temp SQLite file instead of touching the real `data/ipo_cache.sqlite3`) and a `FakeAsyncClient`/`FakeResponse` pair other tasks' tests will import from `tests.conftest` to mock `app.utils.http_client.get_http_client`.

- [ ] **Step 1: Add dev dependencies**

`backend/requirements-dev.txt`:
```
-r requirements.txt
pytest
pytest-asyncio
```

- [ ] **Step 2: Add pytest config**

`backend/pytest.ini`:
```ini
[pytest]
pythonpath = .
asyncio_mode = auto
```

- [ ] **Step 3: Write conftest.py with DB isolation and HTTP fakes**

`backend/tests/conftest.py`:
```python
import pytest

from app.db import database


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test_ipo_cache.sqlite3")


class FakeResponse:
    def __init__(self, json_data=None, text_data="", status_code=200):
        self._json_data = json_data
        self.text = text_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeAsyncClient:
    """Maps an exact URL to a canned FakeResponse. Tests key responses by
    the exact URL each client is expected to call; params are accepted but
    ignored for matching (clients under test use fixed base URLs)."""

    def __init__(self, responses: dict):
        self._responses = responses

    async def get(self, url, params=None, **kwargs):
        return self._responses[url]

    async def post(self, url, json=None, **kwargs):
        return self._responses[url]
```

- [ ] **Step 4: Write a smoke test to prove the harness works**

`backend/tests/test_smoke.py`:
```python
from app.db.database import get_connection


def test_isolated_db_creates_tables():
    conn = get_connection()
    try:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert "ipo_cache" in tables
        assert "push_tokens" in tables
    finally:
        conn.close()
```

- [ ] **Step 5: Run it**

Run (from `backend/`): `pip install -r requirements-dev.txt && python -m pytest tests/test_smoke.py -v`
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/requirements-dev.txt backend/pytest.ini backend/tests/conftest.py backend/tests/test_smoke.py
git commit -m "test: add backend pytest infrastructure with DB isolation and HTTP fakes"
```

---

## Task 2: `ipo_repository.get_all()`

**Files:**
- Modify: `backend/app/services/ipo_repository.py`
- Test: `backend/tests/services/test_ipo_repository.py`

**Interfaces:**
- Produces: `ipo_repository.get_all() -> list[CachedIpo]` — every cached registrar IPO, unfiltered/unlimited. Needed by Task 7 (`ipo_catalog_service`) to build the full name-matching index (existing `get_recent(limit)` only returns the top N).

- [ ] **Step 1: Write the failing test**

`backend/tests/services/test_ipo_repository.py`:
```python
from app.services import ipo_repository
from app.services.ipo_repository import CachedIpo


def test_get_all_returns_every_cached_ipo():
    records = [
        CachedIpo(
            id="linkintime-1",
            company_name="Alpha Ltd",
            registrar="linkintime",
            registrar_ipo_identifier="1",
            automation_supported=True,
            first_seen_at="2026-08-01T00:00:00+00:00",
        ),
        CachedIpo(
            id="bigshare-2",
            company_name="Beta Ltd",
            registrar="bigshare",
            registrar_ipo_identifier="2",
            automation_supported=True,
            first_seen_at="2026-08-02T00:00:00+00:00",
        ),
    ]
    ipo_repository.upsert_many(records)

    all_records = ipo_repository.get_all()

    assert {r.id for r in all_records} == {"linkintime-1", "bigshare-2"}
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest tests/services/test_ipo_repository.py -v`
Expected: FAIL with `AttributeError: module 'app.services.ipo_repository' has no attribute 'get_all'`

- [ ] **Step 3: Implement `get_all()`**

Add to `backend/app/services/ipo_repository.py` (after `get_recent`):
```python
def get_all() -> list[CachedIpo]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM ipo_cache").fetchall()
        return [_row_to_record(row) for row in rows]
    finally:
        conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest tests/services/test_ipo_repository.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ipo_repository.py backend/tests/services/test_ipo_repository.py
git commit -m "feat: add ipo_repository.get_all() for catalog name-matching"
```

---

## Task 3: Company-name normalization utility

**Files:**
- Create: `backend/app/utils/name_matching.py`
- Test: `backend/tests/utils/test_name_matching.py`

**Interfaces:**
- Produces: `normalize_company_name(name: str) -> str` — used by Task 7 to match the same IPO across NSE, Chittorgarh, and the registrar cache.

- [ ] **Step 1: Write the failing test**

`backend/tests/utils/test_name_matching.py`:
```python
from app.utils.name_matching import normalize_company_name


def test_strips_common_suffixes_and_punctuation():
    assert normalize_company_name("Technocrats Plasma Systems Ltd.") == normalize_company_name(
        "TECHNOCRATS PLASMA SYSTEMS LIMITED"
    )


def test_strips_ipo_and_private_pvt():
    assert normalize_company_name("Gaja Alternative Asset Management Pvt Ltd") == normalize_company_name(
        "Gaja Alternative Asset Management Private Limited IPO"
    )


def test_collapses_whitespace_and_case():
    assert normalize_company_name("  Sham   Foam  LTD ") == normalize_company_name("SHAM FOAM")


def test_different_companies_stay_different():
    assert normalize_company_name("Alpha Ltd") != normalize_company_name("Beta Ltd")
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest tests/utils/test_name_matching.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.utils.name_matching'`

- [ ] **Step 3: Implement it**

`backend/app/utils/name_matching.py`:
```python
import re

_SUFFIX_WORDS = {"LIMITED", "LTD", "PRIVATE", "PVT", "IPO"}
_PUNCTUATION = re.compile(r"[^\w\s]")
_WHITESPACE = re.compile(r"\s+")


def normalize_company_name(name: str) -> str:
    """Normalizes a company name for exact-match identity matching across
    NSE, Chittorgarh, and registrar records — not a fuzzy match, so it only
    strips the handful of suffix words/punctuation that vary between
    sources for the same company, never approximates similarity."""
    upper = _PUNCTUATION.sub(" ", name.upper())
    words = [w for w in upper.split() if w not in _SUFFIX_WORDS]
    return _WHITESPACE.sub(" ", " ".join(words)).strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest tests/utils/test_name_matching.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/name_matching.py backend/tests/utils/test_name_matching.py
git commit -m "feat: add company-name normalization for cross-source IPO matching"
```

---

## Task 4: `ipo_catalog` table + repository

**Files:**
- Modify: `backend/app/db/database.py`
- Create: `backend/app/services/ipo_catalog_repository.py`
- Test: `backend/tests/services/test_ipo_catalog_repository.py`

**Interfaces:**
- Consumes: `app.db.database.get_connection()`
- Produces: `CatalogRecord` dataclass, `upsert_many(records: list[CatalogRecord]) -> None`, `get_all() -> list[CatalogRecord]`, `get_by_id(catalog_id: str) -> CatalogRecord | None` — used by Task 7 (`ipo_catalog_service`).

- [ ] **Step 1: Add the table to the schema**

Modify `backend/app/db/database.py`, add to `_SCHEMA` (after the `ipo_cache` table definition, before `push_tokens`):
```sql
CREATE TABLE IF NOT EXISTS ipo_catalog (
    id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    nse_symbol TEXT,
    chittorgarh_slug TEXT,
    open_date TEXT,
    close_date TEXT,
    price_band_low REAL,
    price_band_high REAL,
    lot_size INTEGER,
    issue_size_cr REAL,
    gmp_value REAL,
    gmp_percent REAL,
    gmp_updated_at TEXT,
    sub_qib_offered INTEGER,
    sub_qib_applied INTEGER,
    sub_hni_offered INTEGER,
    sub_hni_applied INTEGER,
    sub_retail_offered INTEGER,
    sub_retail_applied INTEGER,
    sub_updated_at TEXT,
    listing_date TEXT,
    listing_price REAL,
    current_price REAL,
    current_price_updated_at TEXT,
    linked_registrar_ipo_id TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);
```

- [ ] **Step 2: Write the failing repository test**

`backend/tests/services/test_ipo_catalog_repository.py`:
```python
from app.services import ipo_catalog_repository
from app.services.ipo_catalog_repository import CatalogRecord


def _record(**overrides) -> CatalogRecord:
    defaults = dict(
        id="catalog-acme",
        company_name="Acme Ltd",
        nse_symbol="ACME",
        chittorgarh_slug=None,
        open_date="2026-08-14",
        close_date="2026-08-18",
        price_band_low=125.0,
        price_band_high=132.0,
        lot_size=1000,
        issue_size_cr=60.98,
        gmp_value=30.0,
        gmp_percent=23.0,
        gmp_updated_at="2026-08-17T14:34:00+00:00",
        sub_qib_offered=877000,
        sub_qib_applied=782000,
        sub_hni_offered=660000,
        sub_hni_applied=3793000,
        sub_retail_offered=1538000,
        sub_retail_applied=12978000,
        sub_updated_at="2026-08-18T09:59:07+00:00",
        listing_date=None,
        listing_price=None,
        current_price=None,
        current_price_updated_at=None,
        linked_registrar_ipo_id="linkintime-1",
        first_seen_at="2026-08-14T00:00:00+00:00",
        last_seen_at="2026-08-14T00:00:00+00:00",
    )
    defaults.update(overrides)
    return CatalogRecord(**defaults)


def test_upsert_and_get_by_id_roundtrip():
    ipo_catalog_repository.upsert_many([_record()])

    result = ipo_catalog_repository.get_by_id("catalog-acme")

    assert result is not None
    assert result.company_name == "Acme Ltd"
    assert result.gmp_value == 30.0
    assert result.sub_qib_applied == 782000


def test_get_all_returns_every_row():
    ipo_catalog_repository.upsert_many([_record(), _record(id="catalog-beta", company_name="Beta Ltd")])

    assert {r.id for r in ipo_catalog_repository.get_all()} == {"catalog-acme", "catalog-beta"}


def test_get_by_id_returns_none_when_missing():
    assert ipo_catalog_repository.get_by_id("does-not-exist") is None


def test_upsert_does_not_null_out_previously_known_fields():
    ipo_catalog_repository.upsert_many([_record()])

    # A refresh where GMP scraping failed omits gmp_value/gmp_percent —
    # the previously-cached values must survive, not be overwritten with None.
    ipo_catalog_repository.upsert_many([_record(gmp_value=None, gmp_percent=None, gmp_updated_at=None)])

    result = ipo_catalog_repository.get_by_id("catalog-acme")
    assert result.gmp_value == 30.0
    assert result.gmp_percent == 23.0
```

- [ ] **Step 3: Run test to verify it fails**

Run (from `backend/`): `python -m pytest tests/services/test_ipo_catalog_repository.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ipo_catalog_repository'`

- [ ] **Step 4: Implement the repository**

`backend/app/services/ipo_catalog_repository.py`:
```python
"""SQLite-backed cache of IPO calendar/GMP/subscription/price data sourced
from NSE and Chittorgarh — separate from ipo_cache (the registrar-based
allotment-check cache), linked to it only via linked_registrar_ipo_id.

Upserts use COALESCE so a refresh where one source failed (and so omits
some fields) never nulls out previously-known values for those fields —
only a field the incoming record actually has data for overwrites the
cached one.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.db.database import get_connection

_FIELDS = [
    "company_name", "nse_symbol", "chittorgarh_slug", "open_date", "close_date",
    "price_band_low", "price_band_high", "lot_size", "issue_size_cr",
    "gmp_value", "gmp_percent", "gmp_updated_at",
    "sub_qib_offered", "sub_qib_applied", "sub_hni_offered", "sub_hni_applied",
    "sub_retail_offered", "sub_retail_applied", "sub_updated_at",
    "listing_date", "listing_price", "current_price", "current_price_updated_at",
    "linked_registrar_ipo_id",
]


@dataclass
class CatalogRecord:
    id: str
    company_name: str
    nse_symbol: str | None = None
    chittorgarh_slug: str | None = None
    open_date: str | None = None
    close_date: str | None = None
    price_band_low: float | None = None
    price_band_high: float | None = None
    lot_size: int | None = None
    issue_size_cr: float | None = None
    gmp_value: float | None = None
    gmp_percent: float | None = None
    gmp_updated_at: str | None = None
    sub_qib_offered: int | None = None
    sub_qib_applied: int | None = None
    sub_hni_offered: int | None = None
    sub_hni_applied: int | None = None
    sub_retail_offered: int | None = None
    sub_retail_applied: int | None = None
    sub_updated_at: str | None = None
    listing_date: str | None = None
    listing_price: float | None = None
    current_price: float | None = None
    current_price_updated_at: str | None = None
    linked_registrar_ipo_id: str | None = None
    first_seen_at: str = ""
    last_seen_at: str = ""


def upsert_many(records: list[CatalogRecord]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        for r in records:
            values = [getattr(r, f) for f in _FIELDS]
            set_clause = ", ".join(f"{f} = COALESCE(excluded.{f}, ipo_catalog.{f})" for f in _FIELDS)
            conn.execute(
                f"""
                INSERT INTO ipo_catalog (id, {", ".join(_FIELDS)}, first_seen_at, last_seen_at)
                VALUES (?, {", ".join("?" for _ in _FIELDS)}, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    {set_clause},
                    last_seen_at = excluded.last_seen_at
                """,
                (r.id, *values, r.first_seen_at or now, now),
            )
        conn.commit()
    finally:
        conn.close()


def get_all() -> list[CatalogRecord]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM ipo_catalog").fetchall()
        return [_row_to_record(row) for row in rows]
    finally:
        conn.close()


def get_by_id(catalog_id: str) -> CatalogRecord | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM ipo_catalog WHERE id = ?", (catalog_id,)).fetchone()
        return _row_to_record(row) if row else None
    finally:
        conn.close()


def _row_to_record(row) -> CatalogRecord:
    return CatalogRecord(**{f: row[f] for f in ["id", *_FIELDS, "first_seen_at", "last_seen_at"]})
```

- [ ] **Step 5: Run test to verify it passes**

Run (from `backend/`): `python -m pytest tests/services/test_ipo_catalog_repository.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/db/database.py backend/app/services/ipo_catalog_repository.py backend/tests/services/test_ipo_catalog_repository.py
git commit -m "feat: add ipo_catalog table and repository with partial-failure-safe upserts"
```

---

## Task 5: NSE client

**Files:**
- Create: `backend/app/scrapers/market_data/__init__.py` (empty)
- Create: `backend/app/scrapers/market_data/nse_client.py`
- Create: `backend/tests/fixtures/nse_current_issue.json`
- Create: `backend/tests/fixtures/nse_active_category.json`
- Create: `backend/tests/fixtures/nse_quote.json`
- Test: `backend/tests/scrapers/test_nse_client.py`

**Interfaces:**
- Consumes: `app.utils.http_client.get_http_client()`, `tests.conftest.FakeAsyncClient`/`FakeResponse`
- Produces: `NseIpoIssue` dataclass (`symbol, company_name, open_date, close_date, price_band_low, price_band_high, lot_size, issue_size_cr` — dates as `"YYYY-MM-DD"` strings or `None`), `NseCategorySubscription` dataclass (`category, offered, applied, times`), `async get_current_issues() -> list[NseIpoIssue]`, `async get_subscription(symbol: str) -> list[NseCategorySubscription]`, `async get_quote(symbol: str) -> float | None` — used by Task 7.

- [ ] **Step 1: Capture live fixtures**

NSE's exact field names weren't captured during the earlier feasibility research (only that the endpoints return data was confirmed) — capture real responses now, before writing any parsing code, so the parser is built against ground truth rather than guessed field names.

Run (from anywhere with network access):
```bash
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" \
  "https://www.nseindia.com/api/ipo-current-issue" -o backend/tests/fixtures/nse_current_issue.json

# Pick one symbol from the current-issue response above (e.g. its "symbol" field) and substitute it below:
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" \
  "https://www.nseindia.com/api/ipo-active-category?symbol=<SYMBOL>&series=EQ" -o backend/tests/fixtures/nse_active_category.json

curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" \
  "https://www.nseindia.com/api/quote-equity?symbol=RELIANCE" -o backend/tests/fixtures/nse_quote.json
```

If any request returns a 401/403 or an empty body instead of JSON, NSE is requiring session cookies for that endpoint after all — open the fixture file and check before proceeding; if it's blocked, add a step here to first `GET https://www.nseindia.com/` to capture cookies and replay them on the subsequent request (`curl -c cookies.txt ... nseindia.com/ && curl -b cookies.txt ...`), and note this in the client's docstring as a discovered requirement.

Inspect each saved fixture file and note the actual field names before Step 2 — the test code below assumes representative field names (`symbol`, `companyName`/`companyname`/`name`, `issueStartDate`/`biddingStartDate`, `issueEndDate`/`biddingEndDate`, `minPrice`/`maxPrice` or `priceRange`, `lotSize`, `issueSize`); **adjust the test fixtures and parser to match whatever the real payload actually contains** — the shapes below are a starting scaffold, not a guarantee of NSE's exact schema.

- [ ] **Step 2: Write the failing parser tests against the captured fixtures**

`backend/tests/scrapers/test_nse_client.py`:
```python
import json
from pathlib import Path

import pytest

from app.scrapers.market_data import nse_client
from tests.conftest import FakeAsyncClient, FakeResponse

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.asyncio
async def test_get_current_issues_parses_calendar_fields(monkeypatch):
    fake_client = FakeAsyncClient(
        {"https://www.nseindia.com/api/ipo-current-issue": FakeResponse(json_data=_load("nse_current_issue.json"))}
    )
    monkeypatch.setattr(nse_client, "get_http_client", lambda: fake_client)

    issues = await nse_client.get_current_issues()

    assert len(issues) > 0
    first = issues[0]
    assert first.symbol
    assert first.company_name


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

    categories = await nse_client.get_subscription("SOMESYMBOL")

    assert len(categories) > 0
    assert all(c.category for c in categories)


@pytest.mark.asyncio
async def test_get_quote_returns_last_price(monkeypatch):
    fake_client = FakeAsyncClient(
        {"https://www.nseindia.com/api/quote-equity": FakeResponse(json_data=_load("nse_quote.json"))}
    )
    monkeypatch.setattr(nse_client, "get_http_client", lambda: fake_client)

    price = await nse_client.get_quote("RELIANCE")

    assert price is None or isinstance(price, float)
```

- [ ] **Step 3: Run test to verify it fails**

Run (from `backend/`): `python -m pytest tests/scrapers/test_nse_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.scrapers.market_data'`

- [ ] **Step 4: Implement the client against the real captured fixture shape**

Create `backend/app/scrapers/market_data/__init__.py` (empty).

`backend/app/scrapers/market_data/nse_client.py` — write the parser to match whatever field names Step 1's fixtures actually contain. Use this as the starting structure and adjust field-name lookups (the `row.get(...)` chains) to the real captured keys:
```python
"""Low-level client for NSE's public IPO data APIs.

Confirmed live (see backend/tests/fixtures/nse_*.json for captured
samples): a plain browser-UA GET against these endpoints returns JSON
directly, no login or cookie/session dance required at the time of
capture (recheck the fixtures if this client starts getting empty/401
responses — NSE is known to add session requirements over time).
"""

from dataclasses import dataclass

from app.utils.http_client import get_http_client
from app.utils.parsing import to_int

BASE_URL = "https://www.nseindia.com/api"


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
class NseCategorySubscription:
    category: str
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


def _parse_issue(row: dict) -> NseIpoIssue:
    return NseIpoIssue(
        symbol=row.get("symbol", ""),
        company_name=row.get("companyName") or row.get("companyname") or row.get("name", ""),
        open_date=row.get("issueStartDate") or row.get("biddingStartDate"),
        close_date=row.get("issueEndDate") or row.get("biddingEndDate"),
        price_band_low=_to_float(row.get("minPrice") or row.get("priceRangeLow")),
        price_band_high=_to_float(row.get("maxPrice") or row.get("priceRangeHigh")),
        lot_size=to_int(str(row.get("lotSize"))) if row.get("lotSize") is not None else None,
        issue_size_cr=_to_float(row.get("issueSize")),
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
        offered=to_int(str(row.get("noOfSharesOffered"))) if row.get("noOfSharesOffered") is not None else None,
        applied=to_int(str(row.get("noOfSharesBid"))) if row.get("noOfSharesBid") is not None else None,
        times=_to_float(row.get("noOfTimesSubscribed") or row.get("subscriptionTimes")),
    )


async def get_subscription(symbol: str) -> list[NseCategorySubscription]:
    client = get_http_client()
    resp = await client.get(f"{BASE_URL}/ipo-active-category", params={"symbol": symbol, "series": "EQ"})
    resp.raise_for_status()
    data = resp.json()
    rows = data if isinstance(data, list) else data.get("data", [])
    return [_parse_category(row) for row in rows]


async def get_quote(symbol: str) -> float | None:
    client = get_http_client()
    resp = await client.get(f"{BASE_URL}/quote-equity", params={"symbol": symbol})
    resp.raise_for_status()
    data = resp.json()
    price_info = data.get("priceInfo", data) if isinstance(data, dict) else {}
    return _to_float(price_info.get("lastPrice"))
```

- [ ] **Step 5: Run test to verify it passes**

Run (from `backend/`): `python -m pytest tests/scrapers/test_nse_client.py -v`
Expected: PASS. If it fails because the real fixture shape differs from the field-name guesses above, adjust the `_parse_issue`/`_parse_category`/`get_quote` lookups to match the actual captured JSON, then re-run.

- [ ] **Step 6: Commit**

```bash
git add backend/app/scrapers/market_data/__init__.py backend/app/scrapers/market_data/nse_client.py backend/tests/fixtures/nse_*.json backend/tests/scrapers/test_nse_client.py
git commit -m "feat: add NSE client for IPO calendar, subscription, and quote data"
```

---

## Task 6: Chittorgarh GMP client

**Files:**
- Create: `backend/app/scrapers/market_data/chittorgarh_client.py`
- Create: `backend/tests/fixtures/chittorgarh_gmp.html`
- Test: `backend/tests/scrapers/test_chittorgarh_client.py`

**Interfaces:**
- Consumes: `app.utils.http_client.get_http_client()`
- Produces: `ChittorgarhGmpRow` dataclass (`company_name, gmp_value, gmp_percent`), `async get_gmp_for_all() -> list[ChittorgarhGmpRow]` — used by Task 7.

- [ ] **Step 1: Capture a live fixture and confirm it's server-rendered**

The earlier feasibility research confirmed Chittorgarh's `/ipo_subscription/<slug>/<id>/` subpage is server-rendered HTML (not the JS-rendered SPA shell), but did not confirm the exact GMP listing page/URL. Find and verify it now, before writing the parser:

```bash
curl -s -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36" \
  "https://www.chittorgarh.com/report/latest-ipo-gmp-grey-market-premium/26/" -o /tmp/chittorgarh_gmp_check.html
grep -i "gmp" /tmp/chittorgarh_gmp_check.html | head -20
```

If the page is server-rendered, `grep` will show GMP numbers/company names directly in the HTML. If instead you see an empty table shell or `id="__next"` with no data rows (the same failure mode found for InvestorGain), try the alternate URL pattern `https://www.chittorgarh.com/ipo/` and its listed GMP-report link, or `https://www.chittorgarh.com/report/ipo-gmp-live/`. Once a working URL is confirmed, save the successful response as the fixture:

```bash
cp /tmp/chittorgarh_gmp_check.html backend/tests/fixtures/chittorgarh_gmp.html
```

If none of these hold up as server-rendered, stop here and flag it back — GMP for that source would need to fall back to "—" everywhere (still valid per this feature's error-handling rules, just means GMP won't populate until a different source is found later).

- [ ] **Step 2: Write the failing parser test against the captured fixture**

`backend/tests/scrapers/test_chittorgarh_client.py`:
```python
from pathlib import Path

import pytest

from app.scrapers.market_data import chittorgarh_client
from tests.conftest import FakeAsyncClient, FakeResponse

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_get_gmp_for_all_parses_rows(monkeypatch):
    html = (FIXTURES / "chittorgarh_gmp.html").read_text(encoding="utf-8", errors="ignore")
    fake_client = FakeAsyncClient({chittorgarh_client.GMP_URL: FakeResponse(text_data=html)})
    monkeypatch.setattr(chittorgarh_client, "get_http_client", lambda: fake_client)

    rows = await chittorgarh_client.get_gmp_for_all()

    assert len(rows) > 0
    assert all(r.company_name for r in rows)
```

- [ ] **Step 3: Run test to verify it fails**

Run (from `backend/`): `python -m pytest tests/scrapers/test_chittorgarh_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.scrapers.market_data.chittorgarh_client'`

- [ ] **Step 4: Implement the client against the real captured HTML structure**

`backend/app/scrapers/market_data/chittorgarh_client.py` — set `GMP_URL` to whatever URL Step 1 confirmed works, and write the regex/parsing to match that page's actual row structure (inspect the saved fixture's table markup before finalizing the regex below):
```python
"""Scrapes Chittorgarh's GMP listing page.

Confirmed live (see backend/tests/fixtures/chittorgarh_gmp.html): this
specific report page is server-rendered HTML with GMP figures embedded
directly in the markup, unlike the site's main Next.js-rendered app shell
(same distinction found for its /ipo_subscription/ subscription subpage).
If this page's structure changes and the regex below stops matching,
get_gmp_for_all() returns an empty list rather than raising — the caller
(ipo_catalog_service.refresh) already treats "no GMP rows" as
"leave GMP as-is for this refresh cycle", so a broken scrape degrades
gracefully instead of blocking calendar/subscription data.
"""

import re
from dataclasses import dataclass

from app.utils.http_client import get_http_client

GMP_URL = "https://www.chittorgarh.com/report/latest-ipo-gmp-grey-market-premium/26/"

# Matches a table row containing a company name cell and a GMP value cell.
# Adjust this pattern to the actual markup found in the captured fixture.
_ROW_PATTERN = re.compile(
    r'<tr[^>]*>.*?<a[^>]*>([^<]+)</a>.*?class="[^"]*gmp[^"]*"[^>]*>\s*([\d.]+)\s*(?:\(([\d.]+)%\))?',
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class ChittorgarhGmpRow:
    company_name: str
    gmp_value: float | None = None
    gmp_percent: float | None = None


async def get_gmp_for_all() -> list[ChittorgarhGmpRow]:
    client = get_http_client()
    resp = await client.get(GMP_URL)
    resp.raise_for_status()
    html = resp.text

    rows = []
    for match in _ROW_PATTERN.finditer(html):
        company_name, gmp_value, gmp_percent = match.groups()
        rows.append(
            ChittorgarhGmpRow(
                company_name=company_name.strip(),
                gmp_value=float(gmp_value) if gmp_value else None,
                gmp_percent=float(gmp_percent) if gmp_percent else None,
            )
        )
    return rows
```

- [ ] **Step 5: Run test to verify it passes**

Run (from `backend/`): `python -m pytest tests/scrapers/test_chittorgarh_client.py -v`
Expected: PASS. If `_ROW_PATTERN` doesn't match the real fixture, inspect the fixture's actual table HTML and adjust the regex (or switch to a small HTML parse via `re` on a narrower per-row slice) until it extracts real rows.

- [ ] **Step 6: Commit**

```bash
git add backend/app/scrapers/market_data/chittorgarh_client.py backend/tests/fixtures/chittorgarh_gmp.html backend/tests/scrapers/test_chittorgarh_client.py
git commit -m "feat: add Chittorgarh GMP scraper client"
```

---

## Task 7: `ipo_catalog_service`

**Files:**
- Create: `backend/app/services/ipo_catalog_service.py`
- Test: `backend/tests/services/test_ipo_catalog_service.py`

**Interfaces:**
- Consumes: `nse_client.get_current_issues/get_subscription/get_quote`, `chittorgarh_client.get_gmp_for_all`, `ipo_catalog_repository.upsert_many/get_all/get_by_id`, `ipo_repository.get_all`, `name_matching.normalize_company_name`
- Produces: `compute_status(open_date: str | None, close_date: str | None, today: date) -> str`, `async refresh() -> int`, `get_by_status(status: str) -> list[CatalogRecord]`, `get_by_id(catalog_id: str) -> CatalogRecord | None` — used by Task 9 (API routes).

- [ ] **Step 1: Write the failing tests for `compute_status`**

`backend/tests/services/test_ipo_catalog_service.py`:
```python
from datetime import date

from app.services import ipo_catalog_service


def test_upcoming_when_open_date_in_future():
    assert ipo_catalog_service.compute_status("2026-09-01", "2026-09-05", today=date(2026, 8, 18)) == "upcoming"


def test_open_when_today_within_window():
    assert ipo_catalog_service.compute_status("2026-08-14", "2026-08-18", today=date(2026, 8, 16)) == "open"


def test_open_when_today_is_open_date():
    assert ipo_catalog_service.compute_status("2026-08-18", "2026-08-20", today=date(2026, 8, 18)) == "open"


def test_open_when_today_is_close_date():
    assert ipo_catalog_service.compute_status("2026-08-14", "2026-08-18", today=date(2026, 8, 18)) == "open"


def test_closed_when_today_after_close_date():
    assert ipo_catalog_service.compute_status("2026-08-01", "2026-08-05", today=date(2026, 8, 18)) == "closed"


def test_upcoming_when_dates_unknown():
    assert ipo_catalog_service.compute_status(None, None, today=date(2026, 8, 18)) == "upcoming"


def test_open_when_open_date_known_past_but_close_date_unknown():
    assert ipo_catalog_service.compute_status("2026-08-14", None, today=date(2026, 8, 18)) == "open"
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest tests/services/test_ipo_catalog_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.ipo_catalog_service'`

- [ ] **Step 3: Implement `compute_status` and stub the rest**

`backend/app/services/ipo_catalog_service.py`:
```python
"""Aggregates NSE calendar/subscription data and Chittorgarh GMP data into
the ipo_catalog cache, linking each entry to the existing registrar-based
ipo_cache by normalized company name so the mobile app can offer an
Allotment-check button only where that link exists.

Each source is fetched independently — one failing (site redesign, rate
limit, network blip) never blocks the other or discards previously-cached
values for fields it doesn't currently supply (see
ipo_catalog_repository.upsert_many's COALESCE-based merge).
"""

import logging
from datetime import date, datetime, timezone

from app.scrapers.market_data import chittorgarh_client, nse_client
from app.services import ipo_catalog_repository, ipo_repository
from app.services.ipo_catalog_repository import CatalogRecord
from app.utils.name_matching import normalize_company_name

logger = logging.getLogger(__name__)


def compute_status(open_date: str | None, close_date: str | None, today: date) -> str:
    parsed_open = date.fromisoformat(open_date) if open_date else None
    parsed_close = date.fromisoformat(close_date) if close_date else None

    if parsed_open is not None and today < parsed_open:
        return "upcoming"
    if parsed_close is not None and today > parsed_close:
        return "closed"
    if parsed_open is None:
        return "upcoming"
    return "open"


async def refresh() -> int:
    now_iso = datetime.now(timezone.utc).isoformat()
    ok_count = 0
    records: dict[str, CatalogRecord] = {}

    registrar_by_name = {
        normalize_company_name(r.company_name): r.id for r in ipo_repository.get_all()
    }

    try:
        issues = await nse_client.get_current_issues()
        ok_count += 1
    except Exception:
        logger.exception("NSE IPO calendar refresh failed")
        issues = []

    for issue in issues:
        normalized = normalize_company_name(issue.company_name)
        record_id = f"catalog-{normalized.replace(' ', '-').lower()}"

        subscription: list = []
        try:
            subscription = await nse_client.get_subscription(issue.symbol)
        except Exception:
            logger.exception("NSE subscription fetch failed for %s", issue.symbol)

        sub_by_category = {s.category.upper(): s for s in subscription}
        qib = sub_by_category.get("QIB")
        hni = sub_by_category.get("HNI") or sub_by_category.get("NII")
        retail = sub_by_category.get("RETAIL") or sub_by_category.get("RII")

        records[record_id] = CatalogRecord(
            id=record_id,
            company_name=issue.company_name,
            nse_symbol=issue.symbol,
            open_date=issue.open_date,
            close_date=issue.close_date,
            price_band_low=issue.price_band_low,
            price_band_high=issue.price_band_high,
            lot_size=issue.lot_size,
            issue_size_cr=issue.issue_size_cr,
            sub_qib_offered=qib.offered if qib else None,
            sub_qib_applied=qib.applied if qib else None,
            sub_hni_offered=hni.offered if hni else None,
            sub_hni_applied=hni.applied if hni else None,
            sub_retail_offered=retail.offered if retail else None,
            sub_retail_applied=retail.applied if retail else None,
            sub_updated_at=now_iso if subscription else None,
            linked_registrar_ipo_id=registrar_by_name.get(normalized),
            first_seen_at=now_iso,
        )

    try:
        gmp_rows = await chittorgarh_client.get_gmp_for_all()
        ok_count += 1
    except Exception:
        logger.exception("Chittorgarh GMP refresh failed")
        gmp_rows = []

    for row in gmp_rows:
        normalized = normalize_company_name(row.company_name)
        record_id = f"catalog-{normalized.replace(' ', '-').lower()}"
        if record_id in records:
            records[record_id].gmp_value = row.gmp_value
            records[record_id].gmp_percent = row.gmp_percent
            records[record_id].gmp_updated_at = now_iso
        else:
            records[record_id] = CatalogRecord(
                id=record_id,
                company_name=row.company_name,
                gmp_value=row.gmp_value,
                gmp_percent=row.gmp_percent,
                gmp_updated_at=now_iso,
                linked_registrar_ipo_id=registrar_by_name.get(normalized),
                first_seen_at=now_iso,
            )

    # IPOs no longer in NSE's current-issue feed (bidding closed, dropped
    # from that endpoint) still need a current price so the mobile app can
    # show listing vs current price. Re-fetch a quote for each already-closed
    # catalog row that has a known NSE symbol; the first successfully
    # captured price also seeds listing_price as a best-effort proxy for the
    # actual listing-day price, since NSE's public API doesn't expose a
    # dedicated "listing price" field separate from the live quote.
    for existing in ipo_catalog_repository.get_all():
        if not existing.nse_symbol:
            continue
        if compute_status(existing.open_date, existing.close_date, date.today()) != "closed":
            continue
        try:
            price = await nse_client.get_quote(existing.nse_symbol)
        except Exception:
            logger.exception("NSE quote fetch failed for %s", existing.nse_symbol)
            continue
        if price is None:
            continue
        target = records.get(existing.id) or CatalogRecord(
            id=existing.id, company_name=existing.company_name, first_seen_at=existing.first_seen_at
        )
        target.current_price = price
        target.current_price_updated_at = now_iso
        if existing.listing_price is None and target.listing_price is None:
            target.listing_price = price
        records[existing.id] = target

    if records:
        ipo_catalog_repository.upsert_many(list(records.values()))

    return ok_count


def get_by_status(status: str) -> list[CatalogRecord]:
    today = date.today()
    return [r for r in ipo_catalog_repository.get_all() if compute_status(r.open_date, r.close_date, today) == status]


def get_by_id(catalog_id: str) -> CatalogRecord | None:
    return ipo_catalog_repository.get_by_id(catalog_id)
```

- [ ] **Step 4: Run `compute_status` tests to verify they pass**

Run (from `backend/`): `python -m pytest tests/services/test_ipo_catalog_service.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Write and run the `refresh()` partial-failure test**

Append to `backend/tests/services/test_ipo_catalog_service.py`:
```python
from datetime import timedelta

import pytest

from app.scrapers.market_data import chittorgarh_client, nse_client
from app.scrapers.market_data.chittorgarh_client import ChittorgarhGmpRow
from app.scrapers.market_data.nse_client import NseCategorySubscription, NseIpoIssue
from app.services import ipo_catalog_repository
from app.services.ipo_catalog_repository import CatalogRecord


@pytest.mark.asyncio
async def test_refresh_merges_nse_and_chittorgarh_by_normalized_name(monkeypatch):
    today = date.today()
    open_date = (today - timedelta(days=2)).isoformat()
    close_date = (today + timedelta(days=2)).isoformat()  # stays "open" so no quote-enrichment call happens

    async def fake_get_current_issues():
        return [
            NseIpoIssue(
                symbol="ACME",
                company_name="Acme Ltd",
                open_date=open_date,
                close_date=close_date,
                price_band_low=125.0,
                price_band_high=132.0,
                lot_size=1000,
                issue_size_cr=60.98,
            )
        ]

    async def fake_get_subscription(symbol):
        return [NseCategorySubscription(category="QIB", offered=877000, applied=782000, times=0.89)]

    async def fake_get_gmp_for_all():
        return [ChittorgarhGmpRow(company_name="ACME LIMITED", gmp_value=30.0, gmp_percent=23.0)]

    async def unexpected_get_quote(symbol):
        raise AssertionError("get_quote should not be called for an IPO that is still open")

    monkeypatch.setattr(nse_client, "get_current_issues", fake_get_current_issues)
    monkeypatch.setattr(nse_client, "get_subscription", fake_get_subscription)
    monkeypatch.setattr(nse_client, "get_quote", unexpected_get_quote)
    monkeypatch.setattr(chittorgarh_client, "get_gmp_for_all", fake_get_gmp_for_all)

    ok_count = await ipo_catalog_service.refresh()

    assert ok_count == 2
    records = ipo_catalog_repository.get_all()
    assert len(records) == 1
    merged = records[0]
    assert merged.nse_symbol == "ACME"
    assert merged.gmp_value == 30.0
    assert merged.sub_qib_applied == 782000


@pytest.mark.asyncio
async def test_refresh_keeps_nse_data_when_chittorgarh_fails(monkeypatch):
    today = date.today()
    open_date = (today - timedelta(days=2)).isoformat()
    close_date = (today + timedelta(days=2)).isoformat()

    async def fake_get_current_issues():
        return [NseIpoIssue(symbol="ACME", company_name="Acme Ltd", open_date=open_date, close_date=close_date)]

    async def fake_get_subscription(symbol):
        return []

    async def failing_get_gmp_for_all():
        raise RuntimeError("chittorgarh unreachable")

    async def unexpected_get_quote(symbol):
        raise AssertionError("get_quote should not be called for an IPO that is still open")

    monkeypatch.setattr(nse_client, "get_current_issues", fake_get_current_issues)
    monkeypatch.setattr(nse_client, "get_subscription", fake_get_subscription)
    monkeypatch.setattr(nse_client, "get_quote", unexpected_get_quote)
    monkeypatch.setattr(chittorgarh_client, "get_gmp_for_all", failing_get_gmp_for_all)

    ok_count = await ipo_catalog_service.refresh()

    assert ok_count == 1
    records = ipo_catalog_repository.get_all()
    assert len(records) == 1
    assert records[0].nse_symbol == "ACME"
    assert records[0].gmp_value is None


@pytest.mark.asyncio
async def test_refresh_enriches_closed_ipos_with_current_price(monkeypatch):
    today = date.today()
    # Already closed and no longer in NSE's current-issue feed — only exists
    # because a prior refresh cached it.
    ipo_catalog_repository.upsert_many(
        [
            CatalogRecord(
                id="catalog-acme",
                company_name="Acme Ltd",
                nse_symbol="ACME",
                open_date=(today - timedelta(days=10)).isoformat(),
                close_date=(today - timedelta(days=6)).isoformat(),
                first_seen_at="2026-08-01T00:00:00+00:00",
            )
        ]
    )

    async def empty_get_current_issues():
        return []

    async def fake_get_quote(symbol):
        assert symbol == "ACME"
        return 155.0

    async def empty_get_gmp_for_all():
        return []

    monkeypatch.setattr(nse_client, "get_current_issues", empty_get_current_issues)
    monkeypatch.setattr(nse_client, "get_quote", fake_get_quote)
    monkeypatch.setattr(chittorgarh_client, "get_gmp_for_all", empty_get_gmp_for_all)

    await ipo_catalog_service.refresh()

    updated = ipo_catalog_repository.get_by_id("catalog-acme")
    assert updated.current_price == 155.0
    assert updated.listing_price == 155.0  # first captured price seeds listing_price as a best-effort proxy


@pytest.mark.asyncio
async def test_refresh_keeps_current_price_when_quote_fetch_fails(monkeypatch):
    today = date.today()
    ipo_catalog_repository.upsert_many(
        [
            CatalogRecord(
                id="catalog-acme",
                company_name="Acme Ltd",
                nse_symbol="ACME",
                open_date=(today - timedelta(days=10)).isoformat(),
                close_date=(today - timedelta(days=6)).isoformat(),
                current_price=150.0,
                listing_price=140.0,
                first_seen_at="2026-08-01T00:00:00+00:00",
            )
        ]
    )

    async def empty_get_current_issues():
        return []

    async def failing_get_quote(symbol):
        raise RuntimeError("NSE unreachable")

    async def empty_get_gmp_for_all():
        return []

    monkeypatch.setattr(nse_client, "get_current_issues", empty_get_current_issues)
    monkeypatch.setattr(nse_client, "get_quote", failing_get_quote)
    monkeypatch.setattr(chittorgarh_client, "get_gmp_for_all", empty_get_gmp_for_all)

    await ipo_catalog_service.refresh()

    unchanged = ipo_catalog_repository.get_by_id("catalog-acme")
    assert unchanged.current_price == 150.0
    assert unchanged.listing_price == 140.0
```

Run (from `backend/`): `python -m pytest tests/services/test_ipo_catalog_service.py -v`
Expected: PASS (11 tests total)

- [ ] **Step 6: Write and run `get_by_status` test**

Append to `backend/tests/services/test_ipo_catalog_service.py` (dates are computed relative to `date.today()` rather than hardcoded, so this test stays valid no matter when it's actually run):
```python
def test_get_by_status_filters_by_computed_status():
    today = date.today()
    ipo_catalog_repository.upsert_many(
        [
            CatalogRecord(
                id="catalog-open-one", company_name="Open One",
                open_date=(today - timedelta(days=2)).isoformat(),
                close_date=(today + timedelta(days=2)).isoformat(),
                first_seen_at="2026-08-14T00:00:00+00:00",
            ),
            CatalogRecord(
                id="catalog-upcoming-one", company_name="Upcoming One",
                open_date=(today + timedelta(days=10)).isoformat(),
                close_date=(today + timedelta(days=14)).isoformat(),
                first_seen_at="2026-08-14T00:00:00+00:00",
            ),
        ]
    )

    open_ipos = ipo_catalog_service.get_by_status("open")

    assert {r.id for r in open_ipos} == {"catalog-open-one"}
```

Run (from `backend/`): `python -m pytest tests/services/test_ipo_catalog_service.py -v`
Expected: PASS (12 tests total)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/ipo_catalog_service.py backend/tests/services/test_ipo_catalog_service.py
git commit -m "feat: add ipo_catalog_service with cross-source merge and status computation"
```

---

## Task 8: Schemas

**Files:**
- Modify: `backend/app/models/schemas.py`

**Interfaces:**
- Produces: `SubscriptionCategory`, `IPOCatalogSummary`, `IPOCatalogDetail`, `IPOCatalogListResponse` — used by Task 9 (routes).

- [ ] **Step 1: Add the schemas**

Append to `backend/app/models/schemas.py`:
```python
class SubscriptionCategory(BaseModel):
    offered: int | None = None
    applied: int | None = None
    times: float | None = None


class IPOCatalogSummary(BaseModel):
    id: str
    company_name: str
    status: str
    open_date: date | None = None
    close_date: date | None = None
    price_band_low: float | None = None
    price_band_high: float | None = None
    lot_size: int | None = None
    issue_size_cr: float | None = None
    gmp_value: float | None = None
    gmp_percent: float | None = None
    listing_price: float | None = None
    current_price: float | None = None
    linked_registrar_ipo_id: str | None = None


class IPOCatalogDetail(IPOCatalogSummary):
    listing_date: date | None = None
    gmp_updated_at: datetime | None = None
    subscription_qib: SubscriptionCategory
    subscription_hni: SubscriptionCategory
    subscription_retail: SubscriptionCategory


class IPOCatalogListResponse(BaseModel):
    ipos: list[IPOCatalogSummary]
    generated_at: datetime
```

This task has no standalone test — schema correctness is exercised by Task 9's API tests (a `response_model` mismatch fails those tests loudly via a 500/validation error).

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/schemas.py
git commit -m "feat: add IPO catalog Pydantic schemas"
```

---

## Task 9: API routes

**Files:**
- Modify: `backend/app/api/routes_ipos.py`
- Test: `backend/tests/api/test_routes_ipos_catalog.py`

**Interfaces:**
- Consumes: `ipo_catalog_service.get_by_status/get_by_id/compute_status`
- Produces: `GET /ipos/catalog?status=` and `GET /ipos/catalog/{catalog_id}` — used by mobile Task 12.

- [ ] **Step 1: Write the failing API tests**

`backend/tests/api/test_routes_ipos_catalog.py`:
```python
from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.services import ipo_catalog_repository
from app.services.ipo_catalog_repository import CatalogRecord

client = TestClient(app)


def test_get_catalog_by_status_returns_matching_ipos():
    today = date.today()
    ipo_catalog_repository.upsert_many(
        [
            CatalogRecord(
                id="catalog-open-one",
                company_name="Open One",
                open_date=(today - timedelta(days=1)).isoformat(),
                close_date=(today + timedelta(days=1)).isoformat(),
                gmp_value=30.0,
                gmp_percent=23.0,
                first_seen_at="2026-08-14T00:00:00+00:00",
            )
        ]
    )

    response = client.get("/ipos/catalog", params={"status": "open"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["ipos"]) == 1
    assert body["ipos"][0]["id"] == "catalog-open-one"
    assert body["ipos"][0]["status"] == "open"
    assert body["ipos"][0]["gmp_value"] == 30.0


def test_get_catalog_rejects_invalid_status():
    response = client.get("/ipos/catalog", params={"status": "bogus"})

    assert response.status_code == 422


def test_get_catalog_detail_returns_subscription_breakdown():
    ipo_catalog_repository.upsert_many(
        [
            CatalogRecord(
                id="catalog-detail-one",
                company_name="Detail One",
                sub_qib_offered=877000,
                sub_qib_applied=782000,
                first_seen_at="2026-08-14T00:00:00+00:00",
            )
        ]
    )

    response = client.get("/ipos/catalog/catalog-detail-one")

    assert response.status_code == 200
    body = response.json()
    assert body["subscription_qib"]["offered"] == 877000
    assert body["subscription_qib"]["applied"] == 782000
    assert body["subscription_hni"]["offered"] is None


def test_get_catalog_detail_404s_when_missing():
    response = client.get("/ipos/catalog/does-not-exist")

    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest tests/api/test_routes_ipos_catalog.py -v`
Expected: FAIL with 404s (routes don't exist yet)

- [ ] **Step 3: Implement the routes**

Add to `backend/app/api/routes_ipos.py` (new imports at top, new routes at bottom):
```python
from datetime import date

from app.models.schemas import (
    IPOCatalogDetail,
    IPOCatalogListResponse,
    IPOCatalogSummary,
    SubscriptionCategory,
)
from app.services import ipo_catalog_service
from app.services.ipo_catalog_repository import CatalogRecord

_VALID_STATUSES = {"open", "upcoming", "closed"}


def _to_summary(record: CatalogRecord, status: str) -> IPOCatalogSummary:
    return IPOCatalogSummary(
        id=record.id,
        company_name=record.company_name,
        status=status,
        open_date=record.open_date,
        close_date=record.close_date,
        price_band_low=record.price_band_low,
        price_band_high=record.price_band_high,
        lot_size=record.lot_size,
        issue_size_cr=record.issue_size_cr,
        gmp_value=record.gmp_value,
        gmp_percent=record.gmp_percent,
        listing_price=record.listing_price,
        current_price=record.current_price,
        linked_registrar_ipo_id=record.linked_registrar_ipo_id,
    )


@router.get("/catalog", response_model=IPOCatalogListResponse)
async def get_ipo_catalog(status: str) -> IPOCatalogListResponse:
    if status not in _VALID_STATUSES:
        raise HTTPException(status_code=422, detail="status must be one of: open, upcoming, closed")
    records = ipo_catalog_service.get_by_status(status)
    return IPOCatalogListResponse(
        ipos=[_to_summary(r, status) for r in records],
        generated_at=datetime.now(timezone.utc),
    )


@router.get("/catalog/{catalog_id}", response_model=IPOCatalogDetail)
async def get_ipo_catalog_detail(catalog_id: str) -> IPOCatalogDetail:
    record = ipo_catalog_service.get_by_id(catalog_id)
    if record is None:
        raise HTTPException(status_code=404, detail="IPO not found")
    status = ipo_catalog_service.compute_status(record.open_date, record.close_date, date.today())
    summary = _to_summary(record, status)
    return IPOCatalogDetail(
        **summary.model_dump(),
        listing_date=record.listing_date,
        gmp_updated_at=record.gmp_updated_at,
        subscription_qib=SubscriptionCategory(
            offered=record.sub_qib_offered, applied=record.sub_qib_applied,
            times=(record.sub_qib_applied / record.sub_qib_offered) if record.sub_qib_offered else None,
        ),
        subscription_hni=SubscriptionCategory(
            offered=record.sub_hni_offered, applied=record.sub_hni_applied,
            times=(record.sub_hni_applied / record.sub_hni_offered) if record.sub_hni_offered else None,
        ),
        subscription_retail=SubscriptionCategory(
            offered=record.sub_retail_offered, applied=record.sub_retail_applied,
            times=(record.sub_retail_applied / record.sub_retail_offered) if record.sub_retail_offered else None,
        ),
    )
```

Note `HTTPException`, `datetime`, `timezone` are already imported at the top of `routes_ipos.py` for the existing `/ipos/{ipo_id}` route — only the new imports listed above need adding.

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest tests/api/test_routes_ipos_catalog.py -v`
Expected: PASS

- [ ] **Step 5: Run the full backend test suite**

Run (from `backend/`): `python -m pytest -v`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes_ipos.py backend/tests/api/test_routes_ipos_catalog.py
git commit -m "feat: add GET /ipos/catalog and /ipos/catalog/{id} endpoints"
```

---

## Task 10: Periodic catalog refresh

**Files:**
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_main_refresh_schedule.py`

**Interfaces:**
- Consumes: `ipo_catalog_service.refresh()`
- Produces: `_next_catalog_refresh_delay_seconds() -> int` (pure, tested directly); wires a second background task into `lifespan`.

- [ ] **Step 1: Write the failing test for the delay function**

`backend/tests/test_main_refresh_schedule.py`:
```python
from datetime import datetime
from zoneinfo import ZoneInfo

from app import main

IST = ZoneInfo("Asia/Kolkata")


def test_market_hours_use_short_interval(monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 18, 12, 0, tzinfo=IST)

    monkeypatch.setattr(main, "datetime", FixedDatetime)

    assert main._next_catalog_refresh_delay_seconds() == 15 * 60


def test_off_hours_use_long_interval(monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 18, 3, 0, tzinfo=IST)

    monkeypatch.setattr(main, "datetime", FixedDatetime)

    assert main._next_catalog_refresh_delay_seconds() == 2 * 60 * 60


def test_boundary_hour_9am_is_market_hours(monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 18, 9, 0, tzinfo=IST)

    monkeypatch.setattr(main, "datetime", FixedDatetime)

    assert main._next_catalog_refresh_delay_seconds() == 15 * 60


def test_boundary_hour_5pm_is_off_hours(monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 8, 18, 17, 0, tzinfo=IST)

    monkeypatch.setattr(main, "datetime", FixedDatetime)

    assert main._next_catalog_refresh_delay_seconds() == 2 * 60 * 60
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `python -m pytest tests/test_main_refresh_schedule.py -v`
Expected: FAIL with `AttributeError: module 'app.main' has no attribute '_next_catalog_refresh_delay_seconds'`

- [ ] **Step 3: Implement the schedule and wire it in**

Modify `backend/app/main.py`:
```python
from app.services import ipo_catalog_service, ipo_list_service
```
(replacing the existing single-line `from app.services import ipo_list_service`)

Add constants near the existing ones:
```python
MARKET_HOURS_START_HOUR = 9
MARKET_HOURS_END_HOUR = 17
CATALOG_MARKET_HOURS_INTERVAL_SECONDS = 15 * 60
CATALOG_OFF_HOURS_INTERVAL_SECONDS = 2 * 60 * 60
```

Add the delay function and periodic task, next to the existing `_next_refresh_delay_seconds`/`_periodic_refresh`:
```python
def _next_catalog_refresh_delay_seconds() -> int:
    current_hour_ist = datetime.now(IST).hour
    if MARKET_HOURS_START_HOUR <= current_hour_ist < MARKET_HOURS_END_HOUR:
        return CATALOG_MARKET_HOURS_INTERVAL_SECONDS
    return CATALOG_OFF_HOURS_INTERVAL_SECONDS


async def _periodic_catalog_refresh() -> None:
    while True:
        await asyncio.sleep(_next_catalog_refresh_delay_seconds())
        try:
            ok_count = await ipo_catalog_service.refresh()
            logger.info("IPO catalog refreshed (%d/2 sources reachable)", ok_count)
        except Exception:
            logger.exception("IPO catalog refresh failed")
```

Modify `lifespan` to also start/cancel this task:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await ipo_list_service.refresh()
    except Exception:
        logger.exception("Initial IPO list refresh failed")
    try:
        await ipo_catalog_service.refresh()
    except Exception:
        logger.exception("Initial IPO catalog refresh failed")
    refresh_task = asyncio.create_task(_periodic_refresh())
    catalog_refresh_task = asyncio.create_task(_periodic_catalog_refresh())
    yield
    refresh_task.cancel()
    catalog_refresh_task.cancel()
    await close_http_client()
```

Note the test's boundary check (17:00 → off-hours) requires `<` not `<=` in the market-hours comparison, matching `MARKET_HOURS_START_HOUR <= current_hour_ist < MARKET_HOURS_END_HOUR` above.

- [ ] **Step 4: Run test to verify it passes**

Run (from `backend/`): `python -m pytest tests/test_main_refresh_schedule.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Run the full backend suite once more**

Run (from `backend/`): `python -m pytest -v`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/test_main_refresh_schedule.py
git commit -m "feat: add periodic IPO catalog refresh on a market-hours schedule"
```

---

## Task 11: Mobile test infrastructure

**Files:**
- Modify: `mobile/package.json`
- Create: `mobile/jest.config.js`
- Create: `mobile/src/utils/__tests__/smoke.test.ts`

**Interfaces:**
- Produces: a working `npm test` command other mobile tasks' component tests will run under.

- [ ] **Step 1: Add dev dependencies and test script**

Modify `mobile/package.json` — add to `"scripts"`:
```json
"test": "jest"
```
Add to `"devDependencies"`:
```json
"jest": "^29.7.0",
"jest-expo": "~57.0.0",
"@testing-library/react-native": "^12.7.2",
"react-test-renderer": "19.2.3",
"@types/jest": "^29.5.12"
```
(`react-test-renderer` version must match the `react` version already pinned in this file.)

- [ ] **Step 2: Add jest config**

`mobile/jest.config.js`:
```js
module.exports = {
  preset: 'jest-expo',
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?)|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|@unimodules/.*|unimodules|sentry-expo|native-base|react-native-svg)',
  ],
};
```

- [ ] **Step 3: Write a smoke test**

`mobile/src/utils/__tests__/smoke.test.ts`:
```ts
describe('jest setup', () => {
  it('runs a basic assertion', () => {
    expect(1 + 1).toBe(2);
  });
});
```

- [ ] **Step 4: Install and run**

Run (from `mobile/`): `npm install && npm test`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add mobile/package.json mobile/package-lock.json mobile/jest.config.js mobile/src/utils/__tests__/smoke.test.ts
git commit -m "test: add mobile jest + testing-library infrastructure"
```

---

## Task 12: Mobile API types, fetch functions, hooks

**Files:**
- Modify: `mobile/src/types/api.ts`
- Create: `mobile/src/api/ipoCatalog.ts`
- Create: `mobile/src/hooks/useIpoCatalog.ts`

**Interfaces:**
- Produces: `IPOCatalogStatus`, `SubscriptionCategory`, `IPOCatalogSummary`, `IPOCatalogDetail`, `IPOCatalogListResponse` types; `fetchIpoCatalog(status)`, `fetchIpoCatalogDetail(id)`; `useIpoCatalog(status)`, `useIpoCatalogDetail(id)` — used by Task 13 (`IPOCard`), Task 14 (`IPOListScreen`), Task 15 (`IPODetailScreen`).

- [ ] **Step 1: Add the types**

Append to `mobile/src/types/api.ts`:
```ts
export type IPOCatalogStatus = 'open' | 'upcoming' | 'closed';

export interface SubscriptionCategory {
  offered: number | null;
  applied: number | null;
  times: number | null;
}

export interface IPOCatalogSummary {
  id: string;
  company_name: string;
  status: IPOCatalogStatus;
  open_date: string | null;
  close_date: string | null;
  price_band_low: number | null;
  price_band_high: number | null;
  lot_size: number | null;
  issue_size_cr: number | null;
  gmp_value: number | null;
  gmp_percent: number | null;
  listing_price: number | null;
  current_price: number | null;
  linked_registrar_ipo_id: string | null;
}

export interface IPOCatalogDetail extends IPOCatalogSummary {
  listing_date: string | null;
  gmp_updated_at: string | null;
  subscription_qib: SubscriptionCategory;
  subscription_hni: SubscriptionCategory;
  subscription_retail: SubscriptionCategory;
}

export interface IPOCatalogListResponse {
  ipos: IPOCatalogSummary[];
  generated_at: string;
}
```

- [ ] **Step 2: Add fetch functions**

`mobile/src/api/ipoCatalog.ts`:
```ts
import { apiClient } from './client';
import type {
  IPOCatalogDetail,
  IPOCatalogListResponse,
  IPOCatalogStatus,
  IPOCatalogSummary,
} from '../types/api';

export async function fetchIpoCatalog(status: IPOCatalogStatus): Promise<IPOCatalogSummary[]> {
  const data = await apiClient.get<IPOCatalogListResponse>(`/ipos/catalog?status=${status}`);
  return data.ipos;
}

export async function fetchIpoCatalogDetail(ipoId: string): Promise<IPOCatalogDetail> {
  return apiClient.get<IPOCatalogDetail>(`/ipos/catalog/${ipoId}`);
}
```

- [ ] **Step 3: Add hooks**

`mobile/src/hooks/useIpoCatalog.ts`:
```ts
import { useQuery } from '@tanstack/react-query';
import { fetchIpoCatalog, fetchIpoCatalogDetail } from '../api/ipoCatalog';
import type { IPOCatalogStatus } from '../types/api';

export function useIpoCatalog(status: IPOCatalogStatus) {
  return useQuery({
    queryKey: ['ipos', 'catalog', status],
    queryFn: () => fetchIpoCatalog(status),
  });
}

export function useIpoCatalogDetail(ipoId: string) {
  return useQuery({
    queryKey: ['ipos', 'catalog', 'detail', ipoId],
    queryFn: () => fetchIpoCatalogDetail(ipoId),
  });
}
```

No standalone test for this task — these are thin wrappers exercised by Task 13/14/15's component tests, which mock `useIpoCatalog`/`useIpoCatalogDetail` directly.

- [ ] **Step 4: Typecheck**

Run (from `mobile/`): `npx tsc --noEmit`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add mobile/src/types/api.ts mobile/src/api/ipoCatalog.ts mobile/src/hooks/useIpoCatalog.ts
git commit -m "feat: add mobile types/fetchers/hooks for the IPO catalog endpoints"
```

---

## Task 13: `IPOCard` component

**Files:**
- Create: `mobile/src/components/IPOCard.tsx`
- Test: `mobile/src/components/__tests__/IPOCard.test.tsx`

**Interfaces:**
- Consumes: `IPOCatalogSummary` (Task 12)
- Produces: `IPOCard({ ipo, onView, onCheckAllotment? })` — used by Task 14 (`IPOListScreen`).

- [ ] **Step 1: Write the failing component tests**

`mobile/src/components/__tests__/IPOCard.test.tsx`:
```tsx
import { fireEvent, render, screen } from '@testing-library/react-native';
import { IPOCard } from '../IPOCard';
import type { IPOCatalogSummary } from '../../types/api';

const baseIpo: IPOCatalogSummary = {
  id: 'catalog-acme',
  company_name: 'Acme Ltd',
  status: 'open',
  open_date: '2026-08-14',
  close_date: '2026-08-18',
  price_band_low: 125,
  price_band_high: 132,
  lot_size: 1000,
  issue_size_cr: 60.98,
  gmp_value: 30,
  gmp_percent: 23,
  listing_price: null,
  current_price: null,
  linked_registrar_ipo_id: null,
};

describe('IPOCard', () => {
  it('renders core fields', () => {
    render(<IPOCard ipo={baseIpo} onView={() => {}} />);

    expect(screen.getByText('Acme Ltd')).toBeTruthy();
    expect(screen.getByText('₹125 - ₹132')).toBeTruthy();
    expect(screen.getByText('1000')).toBeTruthy();
    expect(screen.getByText('₹60.98 cr')).toBeTruthy();
    expect(screen.getByText('30 (23%)')).toBeTruthy();
  });

  it('renders — for missing fields instead of hiding them', () => {
    render(
      <IPOCard
        ipo={{ ...baseIpo, price_band_low: null, price_band_high: null, gmp_value: null }}
        onView={() => {}}
      />
    );

    expect(screen.getAllByText('—').length).toBeGreaterThanOrEqual(2);
  });

  it('does not show the Allotment button when no registrar link exists', () => {
    render(<IPOCard ipo={baseIpo} onView={() => {}} />);

    expect(screen.queryByText('ALLOTMENT')).toBeNull();
  });

  it('shows and wires the Allotment button when onCheckAllotment is provided', () => {
    const onCheckAllotment = jest.fn();
    render(<IPOCard ipo={baseIpo} onView={() => {}} onCheckAllotment={onCheckAllotment} />);

    fireEvent.press(screen.getByText('ALLOTMENT'));

    expect(onCheckAllotment).toHaveBeenCalledTimes(1);
  });

  it('calls onView when the View button is pressed', () => {
    const onView = jest.fn();
    render(<IPOCard ipo={baseIpo} onView={onView} />);

    fireEvent.press(screen.getByText('VIEW'));

    expect(onView).toHaveBeenCalledTimes(1);
  });

  it('shows listing vs current price only when closed and both are known', () => {
    render(
      <IPOCard
        ipo={{ ...baseIpo, status: 'closed', listing_price: 140, current_price: 155 }}
        onView={() => {}}
      />
    );

    expect(screen.getByText('₹140')).toBeTruthy();
    expect(screen.getByText('₹155')).toBeTruthy();
  });

  it('omits the listing/current price row when still open', () => {
    render(<IPOCard ipo={baseIpo} onView={() => {}} />);

    expect(screen.queryByText('Listing Price')).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `mobile/`): `npm test -- IPOCard`
Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Implement `IPOCard`**

`mobile/src/components/IPOCard.tsx`:
```tsx
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { colors } from '../theme/colors';
import { radii, spacing } from '../theme/spacing';
import type { IPOCatalogSummary } from '../types/api';

function formatDate(isoDate: string | null): string {
  if (!isoDate) return '—';
  return new Date(isoDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

function formatPriceBand(low: number | null, high: number | null): string {
  if (low == null || high == null) return '—';
  return low === high ? `₹${low}` : `₹${low} - ₹${high}`;
}

function formatGmp(value: number | null, percent: number | null): string {
  if (value == null) return '—';
  return percent != null ? `${value} (${percent.toFixed(0)}%)` : `${value}`;
}

export function IPOCard({
  ipo,
  onView,
  onCheckAllotment,
}: {
  ipo: IPOCatalogSummary;
  onView: () => void;
  onCheckAllotment?: () => void;
}) {
  const gmpColor =
    ipo.gmp_value == null
      ? colors.textSecondary
      : ipo.gmp_value >= 0
        ? colors.statusAllotted
        : colors.statusNotAllotted;

  const showPriceComparison = ipo.status === 'closed' && ipo.listing_price != null && ipo.current_price != null;

  return (
    <View style={styles.card}>
      <Text style={styles.name}>{ipo.company_name}</Text>
      <Text style={styles.meta}>
        {formatDate(ipo.open_date)} - {formatDate(ipo.close_date)}
      </Text>

      <View style={styles.row}>
        <View style={styles.field}>
          <Text style={styles.fieldLabel}>Price</Text>
          <Text style={styles.fieldValue}>{formatPriceBand(ipo.price_band_low, ipo.price_band_high)}</Text>
        </View>
        <View style={styles.field}>
          <Text style={styles.fieldLabel}>Lot Size</Text>
          <Text style={styles.fieldValue}>{ipo.lot_size ?? '—'}</Text>
        </View>
        <View style={styles.field}>
          <Text style={styles.fieldLabel}>Issue Size</Text>
          <Text style={styles.fieldValue}>{ipo.issue_size_cr != null ? `₹${ipo.issue_size_cr} cr` : '—'}</Text>
        </View>
      </View>

      <View style={styles.row}>
        <Text style={styles.fieldLabel}>GMP</Text>
        <Text style={[styles.gmpValue, { color: gmpColor }]}>{formatGmp(ipo.gmp_value, ipo.gmp_percent)}</Text>
      </View>

      {showPriceComparison ? (
        <View style={styles.row}>
          <View style={styles.field}>
            <Text style={styles.fieldLabel}>Listing Price</Text>
            <Text style={styles.fieldValue}>₹{ipo.listing_price}</Text>
          </View>
          <View style={styles.field}>
            <Text style={styles.fieldLabel}>Current Price</Text>
            <Text style={styles.fieldValue}>₹{ipo.current_price}</Text>
          </View>
        </View>
      ) : null}

      <View style={styles.buttonRow}>
        <TouchableOpacity style={styles.viewButton} onPress={onView} activeOpacity={0.7}>
          <Text style={styles.viewButtonText}>VIEW</Text>
        </TouchableOpacity>
        {onCheckAllotment ? (
          <TouchableOpacity style={styles.allotmentButton} onPress={onCheckAllotment} activeOpacity={0.7}>
            <Text style={styles.allotmentButtonText}>ALLOTMENT</Text>
          </TouchableOpacity>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radii.md,
    padding: spacing.lg,
    marginHorizontal: spacing.lg,
    marginVertical: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
  },
  name: { fontSize: 16, fontWeight: '700', color: colors.textPrimary },
  meta: { fontSize: 13, color: colors.textSecondary, marginTop: spacing.xs },
  row: { flexDirection: 'row', justifyContent: 'space-between', marginTop: spacing.md },
  field: { flex: 1 },
  fieldLabel: { fontSize: 12, color: colors.textSecondary },
  fieldValue: { fontSize: 14, fontWeight: '600', color: colors.textPrimary, marginTop: 2 },
  gmpValue: { fontSize: 14, fontWeight: '700' },
  buttonRow: { flexDirection: 'row', marginTop: spacing.lg, gap: spacing.sm },
  viewButton: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radii.sm,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  viewButtonText: { fontWeight: '700', color: colors.textPrimary },
  allotmentButton: {
    flex: 1,
    backgroundColor: colors.statusAllotted,
    borderRadius: radii.sm,
    paddingVertical: spacing.sm,
    alignItems: 'center',
  },
  allotmentButtonText: { fontWeight: '700', color: colors.textOnPrimary },
});
```

- [ ] **Step 4: Run test to verify it passes**

Run (from `mobile/`): `npm test -- IPOCard`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add mobile/src/components/IPOCard.tsx mobile/src/components/__tests__/IPOCard.test.tsx
git commit -m "feat: add IPOCard component with View/Allotment buttons and missing-data placeholders"
```

---

## Task 14: `IPOListScreen` rewrite (3 tabs)

**Files:**
- Modify: `mobile/src/screens/IPOListScreen.tsx`
- Modify: `mobile/src/navigation/types.ts`
- Test: `mobile/src/screens/__tests__/IPOListScreen.test.tsx`

**Interfaces:**
- Consumes: `useIpoCatalog` (Task 12), `IPOCard` (Task 13)
- Produces: `IPOListScreen` now renders Open/Upcoming/Closed tabs and navigates to `'IPODetail'` (rich detail, Task 15) and `'AllotmentCheck'` (Task 15) instead of the old single-list `'IPODetail'` (PAN-check).

- [ ] **Step 1: Update navigation param types**

`mobile/src/navigation/types.ts`:
```ts
export type IPOsStackParamList = {
  IPOList: undefined;
  IPODetail: { ipoId: string; companyName: string };
  AllotmentCheck: { ipoId: string; companyName: string };
};

export type PANsStackParamList = {
  PANList: undefined;
  AddEditPAN: { profileId: string } | undefined;
};
```

- [ ] **Step 2: Write the failing screen test**

`mobile/src/screens/__tests__/IPOListScreen.test.tsx`:
```tsx
import { fireEvent, render, screen } from '@testing-library/react-native';
import { IPOListScreen } from '../IPOListScreen';
import { useIpoCatalog } from '../../hooks/useIpoCatalog';

jest.mock('../../hooks/useIpoCatalog');
const mockUseIpoCatalog = useIpoCatalog as jest.Mock;

const navigation = { navigate: jest.fn() } as any;
const route = {} as any;

describe('IPOListScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseIpoCatalog.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
      isRefetching: false,
    });
  });

  it('defaults to the Open tab', () => {
    render(<IPOListScreen navigation={navigation} route={route} />);

    expect(mockUseIpoCatalog).toHaveBeenCalledWith('open');
  });

  it('switches to Upcoming when that tab is pressed', () => {
    render(<IPOListScreen navigation={navigation} route={route} />);

    fireEvent.press(screen.getByText('UPCOMING'));

    expect(mockUseIpoCatalog).toHaveBeenCalledWith('upcoming');
  });

  it('switches to Closed when that tab is pressed', () => {
    render(<IPOListScreen navigation={navigation} route={route} />);

    fireEvent.press(screen.getByText('CLOSED'));

    expect(mockUseIpoCatalog).toHaveBeenCalledWith('closed');
  });

  it('navigates to IPODetail when a card\'s View is pressed', () => {
    mockUseIpoCatalog.mockReturnValue({
      data: [
        {
          id: 'catalog-acme',
          company_name: 'Acme Ltd',
          status: 'open',
          open_date: null,
          close_date: null,
          price_band_low: null,
          price_band_high: null,
          lot_size: null,
          issue_size_cr: null,
          gmp_value: null,
          gmp_percent: null,
          listing_price: null,
          current_price: null,
          linked_registrar_ipo_id: null,
        },
      ],
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
      isRefetching: false,
    });

    render(<IPOListScreen navigation={navigation} route={route} />);
    fireEvent.press(screen.getByText('VIEW'));

    expect(navigation.navigate).toHaveBeenCalledWith('IPODetail', {
      ipoId: 'catalog-acme',
      companyName: 'Acme Ltd',
    });
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run (from `mobile/`): `npm test -- IPOListScreen`
Expected: FAIL (old screen doesn't have tabs / calls `useRecentIpos` not `useIpoCatalog`)

- [ ] **Step 4: Rewrite the screen**

Replace the full contents of `mobile/src/screens/IPOListScreen.tsx`:
```tsx
import { useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { EmptyState } from '../components/EmptyState';
import { IPOCard } from '../components/IPOCard';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { useIpoCatalog } from '../hooks/useIpoCatalog';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import type { IPOsStackParamList } from '../navigation/types';
import type { IPOCatalogStatus } from '../types/api';

type Props = NativeStackScreenProps<IPOsStackParamList, 'IPOList'>;

const TABS: { key: IPOCatalogStatus; label: string }[] = [
  { key: 'open', label: 'OPEN' },
  { key: 'upcoming', label: 'UPCOMING' },
  { key: 'closed', label: 'CLOSED' },
];

export function IPOListScreen({ navigation }: Props) {
  const [status, setStatus] = useState<IPOCatalogStatus>('open');
  const { data, isLoading, isError, refetch, isRefetching } = useIpoCatalog(status);

  return (
    <View style={styles.container}>
      <View style={styles.tabRow}>
        {TABS.map((tab) => (
          <TouchableOpacity key={tab.key} onPress={() => setStatus(tab.key)}>
            <Text style={[styles.tabLabel, status === tab.key && styles.tabLabelActive]}>{tab.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {isLoading ? (
        <SkeletonLoader />
      ) : isError ? (
        <EmptyState
          icon="📡"
          title="Couldn't load IPOs"
          subtitle="Check that the backend server is running and reachable, then pull to refresh."
        />
      ) : !data || data.length === 0 ? (
        <EmptyState icon="🗂️" title={`No ${status} IPOs`} subtitle="Pull to refresh." />
      ) : (
        <FlatList
          data={data}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <IPOCard
              ipo={item}
              onView={() => navigation.navigate('IPODetail', { ipoId: item.id, companyName: item.company_name })}
              onCheckAllotment={
                item.linked_registrar_ipo_id
                  ? () =>
                      navigation.navigate('AllotmentCheck', {
                        ipoId: item.linked_registrar_ipo_id as string,
                        companyName: item.company_name,
                      })
                  : undefined
              }
            />
          )}
          contentContainerStyle={styles.listContent}
          refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} />}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  tabRow: {
    flexDirection: 'row',
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.sm,
    gap: spacing.lg,
  },
  tabLabel: { fontSize: 14, fontWeight: '700', color: colors.textSecondary, paddingBottom: spacing.xs },
  tabLabelActive: { color: colors.primary, borderBottomWidth: 2, borderBottomColor: colors.primary },
  listContent: { paddingBottom: spacing.xl },
});
```

- [ ] **Step 5: Run test to verify it passes**

Run (from `mobile/`): `npm test -- IPOListScreen`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add mobile/src/screens/IPOListScreen.tsx mobile/src/navigation/types.ts mobile/src/screens/__tests__/IPOListScreen.test.tsx
git commit -m "feat: rewrite IPOListScreen as Open/Upcoming/Closed tabs over the catalog endpoint"
```

---

## Task 15: New `IPODetailScreen` + rename existing one to `AllotmentCheckScreen`

**Files:**
- Modify: `mobile/src/screens/IPODetailScreen.tsx` (replace contents — becomes the new rich detail screen)
- Create: `mobile/src/screens/AllotmentCheckScreen.tsx` (the *old* `IPODetailScreen.tsx` contents, renamed)
- Modify: `mobile/src/navigation/RootNavigator.tsx`
- Test: `mobile/src/screens/__tests__/IPODetailScreen.test.tsx`

**Interfaces:**
- Consumes: `useIpoCatalogDetail` (Task 12) for the new `IPODetailScreen`; `useCheckAllotment`/`usePanProfiles` (existing, unchanged) for `AllotmentCheckScreen`.
- Produces: `IPODetailScreen` (rich detail, routed from `IPOsStackParamList['IPODetail']`), `AllotmentCheckScreen` (PAN-check results, routed from `IPOsStackParamList['AllotmentCheck']`).

- [ ] **Step 1: Rename the existing screen to `AllotmentCheckScreen`**

Copy the current full contents of `mobile/src/screens/IPODetailScreen.tsx` into a new file `mobile/src/screens/AllotmentCheckScreen.tsx`, renaming only the exported function from `IPODetailScreen` to `AllotmentCheckScreen` and its `Props` type source from `'IPODetail'` to `'AllotmentCheck'`:
```tsx
import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { EmptyState } from '../components/EmptyState';
import { ResultRow } from '../components/ResultRow';
import { useCheckAllotment } from '../hooks/useCheckAllotment';
import { usePanProfiles } from '../hooks/usePanProfiles';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import type { IPOsStackParamList } from '../navigation/types';
import type { AllotmentResultItem } from '../types/api';

type Props = NativeStackScreenProps<IPOsStackParamList, 'AllotmentCheck'>;

const REVEAL_DELAY_MS = 350;

export function AllotmentCheckScreen({ route }: Props) {
  const { ipoId, companyName } = route.params;
  const { profiles, isLoading: profilesLoading } = usePanProfiles();
  const { mutate, data, isError, error } = useCheckAllotment();
  const [revealedCount, setRevealedCount] = useState(0);

  useEffect(() => {
    if (!profilesLoading && profiles.length > 0) {
      setRevealedCount(0);
      mutate({ ipoId, applicants: profiles });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ipoId, profilesLoading, profiles.length]);

  useEffect(() => {
    if (!data) return;
    if (revealedCount >= data.results.length) return;
    const timer = setTimeout(() => setRevealedCount((c) => c + 1), REVEAL_DELAY_MS);
    return () => clearTimeout(timer);
  }, [data, revealedCount]);

  const resultFor = (index: number): AllotmentResultItem | undefined => {
    if (!data || index >= revealedCount) return undefined;
    return data.results[index];
  };

  if (profilesLoading) return null;

  if (profiles.length === 0) {
    return (
      <EmptyState
        icon="🪪"
        title="No PANs saved yet"
        subtitle="Add a PAN under the My PANs tab to check allotment status."
      />
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>{companyName}</Text>
        {isError ? (
          <Text style={styles.errorText}>{error?.message ?? 'Something went wrong.'}</Text>
        ) : (
          <Text style={styles.subtitle}>
            Checking {profiles.length} saved PAN{profiles.length > 1 ? 's' : ''}
          </Text>
        )}
      </View>

      <ScrollView contentContainerStyle={styles.listContent}>
        {profiles.map((profile, index) => (
          <ResultRow key={profile.id} label={profile.name} pan={profile.pan} result={resultFor(index)} />
        ))}
      </ScrollView>

      {isError ? (
        <TouchableOpacity
          style={styles.retryButton}
          onPress={() => {
            setRevealedCount(0);
            mutate({ ipoId, applicants: profiles });
          }}
        >
          <Text style={styles.retryButtonText}>Retry</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  headerRow: { paddingHorizontal: spacing.lg, paddingTop: spacing.lg, paddingBottom: spacing.sm },
  title: { fontSize: 22, fontWeight: '700', color: colors.textPrimary },
  subtitle: { fontSize: 13, color: colors.textSecondary, marginTop: spacing.xs },
  errorText: { fontSize: 13, color: colors.statusNotAllotted, marginTop: spacing.xs },
  listContent: { paddingBottom: spacing.xl },
  retryButton: {
    margin: spacing.lg,
    backgroundColor: colors.primary,
    borderRadius: 12,
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  retryButtonText: { color: colors.textOnPrimary, fontWeight: '600', fontSize: 15 },
});
```

- [ ] **Step 2: Write the failing test for the new rich detail screen**

`mobile/src/screens/__tests__/IPODetailScreen.test.tsx`:
```tsx
import { render, screen } from '@testing-library/react-native';
import { IPODetailScreen } from '../IPODetailScreen';
import { useIpoCatalogDetail } from '../../hooks/useIpoCatalog';

jest.mock('../../hooks/useIpoCatalog');
const mockUseIpoCatalogDetail = useIpoCatalogDetail as jest.Mock;

const route = { params: { ipoId: 'catalog-acme', companyName: 'Acme Ltd' } } as any;
const navigation = {} as any;

describe('IPODetailScreen', () => {
  it('renders known fields and the subscription table', () => {
    mockUseIpoCatalogDetail.mockReturnValue({
      data: {
        id: 'catalog-acme',
        company_name: 'Acme Ltd',
        status: 'open',
        open_date: '2026-08-14',
        close_date: '2026-08-18',
        price_band_low: 125,
        price_band_high: 132,
        lot_size: 1000,
        issue_size_cr: 60.98,
        gmp_value: 30,
        gmp_percent: 23,
        listing_price: null,
        current_price: null,
        linked_registrar_ipo_id: null,
        listing_date: null,
        gmp_updated_at: null,
        subscription_qib: { offered: 877000, applied: 782000, times: 0.89 },
        subscription_hni: { offered: null, applied: null, times: null },
        subscription_retail: { offered: null, applied: null, times: null },
      },
      isLoading: false,
      isError: false,
    });

    render(<IPODetailScreen route={route} navigation={navigation} />);

    expect(screen.getByText('₹125 - ₹132')).toBeTruthy();
    expect(screen.getByText('877000')).toBeTruthy();
    expect(screen.getByText('0.89x')).toBeTruthy();
  });

  it('renders — for missing fields rather than omitting them', () => {
    mockUseIpoCatalogDetail.mockReturnValue({
      data: {
        id: 'catalog-acme',
        company_name: 'Acme Ltd',
        status: 'upcoming',
        open_date: null,
        close_date: null,
        price_band_low: null,
        price_band_high: null,
        lot_size: null,
        issue_size_cr: null,
        gmp_value: null,
        gmp_percent: null,
        listing_price: null,
        current_price: null,
        linked_registrar_ipo_id: null,
        listing_date: null,
        gmp_updated_at: null,
        subscription_qib: { offered: null, applied: null, times: null },
        subscription_hni: { offered: null, applied: null, times: null },
        subscription_retail: { offered: null, applied: null, times: null },
      },
      isLoading: false,
      isError: false,
    });

    render(<IPODetailScreen route={route} navigation={navigation} />);

    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
    expect(screen.queryByText('Listing')).toBeNull();
  });

  it('shows an error state when the fetch fails', () => {
    mockUseIpoCatalogDetail.mockReturnValue({ data: undefined, isLoading: false, isError: true });

    render(<IPODetailScreen route={route} navigation={navigation} />);

    expect(screen.getByText("Couldn't load IPO details")).toBeTruthy();
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run (from `mobile/`): `npm test -- IPODetailScreen`
Expected: FAIL (old screen still renders the PAN-check UI, not this content)

- [ ] **Step 4: Replace `IPODetailScreen.tsx` with the rich detail screen**

Replace the full contents of `mobile/src/screens/IPODetailScreen.tsx`:
```tsx
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { EmptyState } from '../components/EmptyState';
import { SkeletonLoader } from '../components/SkeletonLoader';
import { useIpoCatalogDetail } from '../hooks/useIpoCatalog';
import { colors } from '../theme/colors';
import { spacing } from '../theme/spacing';
import type { IPOsStackParamList } from '../navigation/types';
import type { SubscriptionCategory } from '../types/api';

type Props = NativeStackScreenProps<IPOsStackParamList, 'IPODetail'>;

function fmt(value: string | number | null): string {
  return value == null ? '—' : String(value);
}

function SubscriptionRow({ label, category }: { label: string; category: SubscriptionCategory }) {
  return (
    <View style={styles.tableRow}>
      <Text style={styles.tableCell}>{label}</Text>
      <Text style={styles.tableCell}>{fmt(category.offered)}</Text>
      <Text style={styles.tableCell}>{fmt(category.applied)}</Text>
      <Text style={styles.tableCell}>{category.times != null ? `${category.times}x` : '—'}</Text>
    </View>
  );
}

export function IPODetailScreen({ route }: Props) {
  const { ipoId } = route.params;
  const { data, isLoading, isError } = useIpoCatalogDetail(ipoId);

  if (isLoading) return <SkeletonLoader />;
  if (isError || !data) {
    return <EmptyState icon="📡" title="Couldn't load IPO details" subtitle="Pull to refresh from the list." />;
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>IPO Details</Text>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>Open Date</Text>
          <Text style={styles.fieldValue}>{fmt(data.open_date)}</Text>
        </View>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>Close Date</Text>
          <Text style={styles.fieldValue}>{fmt(data.close_date)}</Text>
        </View>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>Price Band</Text>
          <Text style={styles.fieldValue}>
            {data.price_band_low != null && data.price_band_high != null
              ? `₹${data.price_band_low} - ₹${data.price_band_high}`
              : '—'}
          </Text>
        </View>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>Lot Size</Text>
          <Text style={styles.fieldValue}>{fmt(data.lot_size)}</Text>
        </View>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>Issue Size</Text>
          <Text style={styles.fieldValue}>{data.issue_size_cr != null ? `₹${data.issue_size_cr} cr` : '—'}</Text>
        </View>
        <View style={styles.fieldRow}>
          <Text style={styles.fieldLabel}>GMP</Text>
          <Text style={styles.fieldValue}>
            {data.gmp_value != null
              ? `${data.gmp_value}${data.gmp_percent != null ? ` (${data.gmp_percent.toFixed(0)}%)` : ''}`
              : '—'}
          </Text>
        </View>
      </View>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Subscription Details</Text>
        <View style={styles.tableRow}>
          <Text style={[styles.tableCell, styles.tableHeaderCell]}>Category</Text>
          <Text style={[styles.tableCell, styles.tableHeaderCell]}>Offered</Text>
          <Text style={[styles.tableCell, styles.tableHeaderCell]}>Applied</Text>
          <Text style={[styles.tableCell, styles.tableHeaderCell]}>Times</Text>
        </View>
        <SubscriptionRow label="QIB" category={data.subscription_qib} />
        <SubscriptionRow label="HNI" category={data.subscription_hni} />
        <SubscriptionRow label="Retail" category={data.subscription_retail} />
      </View>

      {data.status === 'closed' ? (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Listing</Text>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Listing Date</Text>
            <Text style={styles.fieldValue}>{fmt(data.listing_date)}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Listing Price</Text>
            <Text style={styles.fieldValue}>{data.listing_price != null ? `₹${data.listing_price}` : '—'}</Text>
          </View>
          <View style={styles.fieldRow}>
            <Text style={styles.fieldLabel}>Current Price</Text>
            <Text style={styles.fieldValue}>{data.current_price != null ? `₹${data.current_price}` : '—'}</Text>
          </View>
        </View>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: spacing.lg, backgroundColor: colors.background },
  card: {
    backgroundColor: colors.surface,
    borderRadius: 12,
    padding: spacing.lg,
    marginBottom: spacing.lg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: colors.textPrimary, marginBottom: spacing.md },
  fieldRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: spacing.xs },
  fieldLabel: { fontSize: 13, color: colors.textSecondary },
  fieldValue: { fontSize: 14, fontWeight: '600', color: colors.textPrimary },
  tableRow: { flexDirection: 'row', paddingVertical: spacing.xs },
  tableCell: { flex: 1, fontSize: 13, color: colors.textPrimary, textAlign: 'center' },
  tableHeaderCell: { fontWeight: '700', color: colors.textSecondary },
});
```

Note: the "closed" fixture case in Step 2's test only checks `queryByText('Listing')` is null — but the section title is "Listing" and only renders `data.status === 'closed'`; the "renders known fields" test uses `status: 'open'` so it's absent there, and the "missing fields" test uses `status: 'upcoming'` so it's absent there too. Both assertions hold against this implementation.

- [ ] **Step 5: Wire up navigation**

Modify `mobile/src/navigation/RootNavigator.tsx`:
```tsx
import { AllotmentCheckScreen } from '../screens/AllotmentCheckScreen';
```
(add alongside the existing `IPODetailScreen` import)

Update `IPOsStackNavigator`:
```tsx
function IPOsStackNavigator() {
  return (
    <IPOsStack.Navigator screenOptions={stackHeaderOptions}>
      <IPOsStack.Screen name="IPOList" component={IPOListScreen} options={{ title: 'IPOs' }} />
      <IPOsStack.Screen
        name="IPODetail"
        component={IPODetailScreen}
        options={({ route }) => ({ title: route.params.companyName })}
      />
      <IPOsStack.Screen
        name="AllotmentCheck"
        component={AllotmentCheckScreen}
        options={({ route }) => ({ title: route.params.companyName })}
      />
    </IPOsStack.Navigator>
  );
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run (from `mobile/`): `npm test -- IPODetailScreen`
Expected: PASS (3 tests)

Run (from `mobile/`): `npx tsc --noEmit`
Expected: no errors (confirms `AllotmentCheckScreen`'s renamed `Props` type and `RootNavigator`'s wiring are all consistent)

- [ ] **Step 7: Run the full mobile test suite**

Run (from `mobile/`): `npm test`
Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add mobile/src/screens/IPODetailScreen.tsx mobile/src/screens/AllotmentCheckScreen.tsx mobile/src/navigation/RootNavigator.tsx mobile/src/screens/__tests__/IPODetailScreen.test.tsx
git commit -m "feat: add rich IPODetailScreen; rename PAN-check screen to AllotmentCheckScreen"
```

---

## Task 16: Manual verification

**Files:** none (manual QA only, per the spec's testing section — screens/navigation get a real run-through rather than exhaustive automated coverage).

- [ ] **Step 1: Start the backend**

Run (from `backend/`): `uvicorn app.main:app --reload`
Confirm in the logs: `IPO catalog refreshed (N/2 sources reachable)` appears (from the initial refresh in `lifespan`), with `N` being 2 if both NSE and Chittorgarh succeeded, or less if one is currently blocked — either is acceptable for this check, but 0 means both scrapers need debugging before continuing.

- [ ] **Step 2: Confirm the catalog endpoints return data**

Run: `curl "http://localhost:8000/ipos/catalog?status=open"` and `curl "http://localhost:8000/ipos/catalog?status=upcoming"` and `curl "http://localhost:8000/ipos/catalog?status=closed"`
Expected: each returns a 200 with a JSON `ipos` array (possibly empty for a given status if no real IPOs are currently in that window — check against what's actually on NSE's calendar right now to sanity-check, don't expect all three to be non-empty at all times).

- [ ] **Step 3: Start the mobile app and verify the UI**

Run (from `mobile/`): `npm start`, open in a simulator/device with `EXPO_PUBLIC_API_BASE_URL` pointing at the local backend.

Verify:
- The IPOs tab shows Open/Upcoming/Closed tabs, defaulting to Open.
- Switching tabs shows different (or empty-state) IPO cards.
- Each card shows dates, price band, lot size, issue size, and GMP (or "—" placeholders where data is missing).
- Pressing "VIEW" on a card opens the rich detail screen with the same data plus the subscription table.
- A card whose IPO also exists in the registrar cache (`ipo_cache`) shows an "ALLOTMENT" button; pressing it opens the PAN-check screen (`AllotmentCheckScreen`) and behaves exactly as the old allotment-check flow did.
- A card with no registrar match shows no "ALLOTMENT" button.
- A closed/listed IPO's card and detail screen show listing price vs current price when both are known.

If any of these don't hold, note which step failed — that's the next thing to fix before considering this feature done.
