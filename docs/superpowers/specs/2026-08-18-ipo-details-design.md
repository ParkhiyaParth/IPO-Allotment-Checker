# IPO Details Feature — Design Spec

Date: 2026-08-18

## Goal

Extend the IPO allotment checker with an IPO-details feature: three tabs
(Open / Upcoming / Closed), each showing IPO cards with open/close dates,
price band, lot size, issue size, live GMP (grey market premium), live
subscription (bid vs offered by investor category), and — for closed/listed
IPOs — listing price vs current market price. Tapping "View" opens a rich
detail screen; tapping "Allotment" (only shown when a registrar link
exists) opens the existing PAN-allotment-check flow.

This is additive to the existing allotment-check feature, not a
replacement of its data or logic.

## Non-goals (deferred to a later phase)

- About / Strength Factors / Risk Factors prospectus text
- DRHP/RHP, Capital Structure, Anchor file links
- Lot(s) Distribution table, IPO Reservation breakup table
- QIB Interest Cost per share table
- Fuzzy/ML-based company-name matching across sources

## Data sources

| Source | Used for | Access pattern |
|---|---|---|
| NSE (`nseindia.com`) | Calendar (open/close dates, price band, lot size, issue size), live subscription by category (QIB/HNI/Retail), current market price post-listing | Plain `httpx` GET against public JSON endpoints (`/api/ipo-current-issue`, `/api/ipo-active-category`, `/api/quote-equity`), browser User-Agent, no session/cookie dance required per spike research |
| Chittorgarh (`chittorgarh.com`) | GMP, as a fallback/supplement for subscription | Regex-scrape of the server-rendered `/ipo_subscription/<slug>/<id>/`-style subpages (confirmed real data embedded in HTML, distinct from the site's JS-rendered SPA shell) |
| Existing registrar cache (`ipo_cache`) | Linking to the existing PAN-allotment-check flow | Matched by normalized company name; no new scraping |

GMP is inherently unofficial data with no exchange-published source —
Chittorgarh's subscription-subpage pattern is our best current lead: if its
GMP-specific subpage doesn't hold up under implementation, GMP degrades
gracefully to "—" for that IPO rather than blocking the rest of the record.

## Data model

New table `ipo_catalog` (separate from `ipo_cache`, which is untouched):

```
id                        TEXT PRIMARY KEY   -- synthetic, e.g. "catalog-<normalized-name-hash>"
company_name              TEXT NOT NULL
nse_symbol                TEXT               -- nullable, once known
chittorgarh_slug          TEXT               -- nullable
open_date                 TEXT               -- ISO date, nullable until known
close_date                TEXT               -- ISO date, nullable
price_band_low            REAL               -- nullable
price_band_high           REAL               -- nullable
lot_size                  INTEGER            -- nullable
issue_size_cr             REAL               -- nullable
gmp_value                 REAL               -- nullable
gmp_percent               REAL               -- nullable
gmp_updated_at            TEXT               -- ISO datetime, nullable
sub_qib_offered           INTEGER            -- nullable
sub_qib_applied           INTEGER            -- nullable
sub_hni_offered           INTEGER            -- nullable
sub_hni_applied           INTEGER            -- nullable
sub_retail_offered        INTEGER            -- nullable
sub_retail_applied        INTEGER            -- nullable
sub_updated_at            TEXT               -- ISO datetime, nullable
listing_date              TEXT               -- ISO date, nullable
listing_price             REAL               -- nullable
current_price             REAL               -- nullable
current_price_updated_at  TEXT               -- ISO datetime, nullable
linked_registrar_ipo_id   TEXT               -- nullable FK into ipo_cache.id
first_seen_at             TEXT NOT NULL
last_seen_at              TEXT NOT NULL
```

Status (`open` / `upcoming` / `closed`) is computed at read time from
`open_date`/`close_date` against the current date — not stored, so it's
always consistent with "now" without a separate write path.

Identity matching: company names are normalized (uppercase; strip
"LIMITED", "LTD", "PRIVATE", "PVT", "IPO", punctuation) and compared for
exact match across NSE, Chittorgarh, and `ipo_cache` records. No fuzzy
matching library — an unmatched IPO simply has a null
`linked_registrar_ipo_id` and shows no Allotment button. This may miss
some links where a registrar's name differs more than the normalization
handles; acceptable for v1 given the Allotment button is a bonus link, not
this feature's core value.

## Backend components

- `app/scrapers/market_data/nse_client.py` — `get_current_issues()`,
  `get_subscription(symbol)`, `get_quote(symbol)`. Documents the exact
  endpoints and headers found live, same style as the existing registrar
  client docstrings.
- `app/scrapers/market_data/chittorgarh_client.py` — `get_gmp(slug)`,
  `get_subscription(slug)` (fallback if NSE data is thin for an IPO not
  yet reflected in NSE's own feed). Documents what was found live and any
  uncertainty.
- `app/services/ipo_catalog_service.py` — `refresh()` (pulls NSE +
  Chittorgarh independently, each failure logged and skipped without
  blocking the other or previously-cached data; merges by normalized
  name; upserts into `ipo_catalog`), `get_by_status(status)`,
  `get_by_id(id)`.
- `app/services/ipo_catalog_repository.py` — SQLite access for the new
  table, same shape as `ipo_repository.py`.
- `app/db/database.py` — add `ipo_catalog` table to `_SCHEMA`.
- `app/api/routes_ipos.py` — add `GET /ipos/catalog?status=` and
  `GET /ipos/catalog/{id}`.
- `app/models/schemas.py` — add `IPOCatalogSummary`, `IPOCatalogDetail`.
- `app/main.py` — add a second periodic refresh task for
  `ipo_catalog_service.refresh()`: every 15 min during 9:00–17:00 IST
  (market hours, when GMP/subscription actually move), every 2 hours
  off-hours — mirroring the existing evening-window pattern already used
  for the allotment-check refresh.

## Mobile components

- `IPOListScreen` becomes a 3-tab (segmented control: Open / Upcoming /
  Closed) view backed by a new `useIpoCatalog(status)` hook hitting
  `GET /ipos/catalog?status=`.
- New `IPOCard` component: company name, dates, price band, lot size,
  issue size, GMP, and View + (conditional) Allotment buttons — replacing
  `IPOListItem` for this screen.
- New `IPODetailScreen` (rich detail: dates, price band, lot size, issue
  size, GMP, subscription table by category, listing price vs current
  price for closed/listed IPOs). Missing fields render as "—" rather than
  hiding the row.
- The *existing* `IPODetailScreen` (PAN-check results against
  `useCheckAllotment`) is renamed to `AllotmentCheckScreen` and reached via
  the Allotment button, not tap-to-open.
- `mobile/src/navigation/types.ts` — `IPOsStackParamList` updated:
  `IPOList`, `IPODetail: { ipoId }` (new rich screen),
  `AllotmentCheck: { ipoId, companyName }` (renamed from old `IPODetail`).
- `mobile/src/types/api.ts` — add types matching the new schemas.
- New `mobile/src/api/ipoCatalog.ts` — fetch functions for the new
  endpoints.

## Error handling

- Any field with no data from any source renders as "—" in both card and
  detail screen; it never blocks rendering the rest of the record.
- A source-fetch failure (NSE down, Chittorgarh page changed) is logged
  and that source is skipped for that refresh cycle; previously-cached
  values for other fields are kept as-is (no field is ever nulled out by a
  failed refresh — same "don't lose known-good cached data" principle as
  `ipo_list_service.refresh`).
- If NSE and Chittorgarh disagree on a value that both provide (unlikely
  for v1's field set, since they're mostly non-overlapping), NSE (official
  exchange data) wins.

## Testing

- Backend: unit tests for `nse_client`/`chittorgarh_client` parsers against
  saved sample JSON/HTML fixtures (mirroring how the registrar clients are
  tested — parse correctness must not depend on live network access in
  CI). Unit tests for the name-normalization/matching function. Unit tests
  for `ipo_catalog_service.refresh()`'s partial-failure behavior (one
  source down doesn't wipe the other's data).
- Mobile: component tests for `IPOCard` across states (each tab, with/without
  Allotment button, missing-data placeholders). Manual run-through in the
  dev app: all 3 tabs populate, View opens the rich detail screen,
  Allotment opens the PAN-check screen only when a registrar link exists.

## Open risks

- Chittorgarh's exact GMP subpage structure hasn't been confirmed the way
  its subscription subpage was — first implementation pass should verify
  this specifically and fall back to "—" gracefully if it doesn't hold up,
  without blocking the rest of the feature.
- NSE is known to rate-limit/WAF at scale; the market-hours refresh
  cadence (15 min) is chosen to stay well under any reasonable threshold,
  but this should be watched in production logs after launch.
