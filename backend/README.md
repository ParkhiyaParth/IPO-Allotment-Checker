# IPO Allotment Checker — Backend

Python/FastAPI backend that checks IPO allotment status against registrar
(RTA) sites on behalf of the mobile app. Stateless with respect to PII: PAN
values arrive only in the body of a single check-allotment request and are
never logged or persisted.

## Status

Three registrars are real, live, and working — **no captcha-solving turned
out to be necessary for any of them**. Each one's actual search API was
traced by inspecting what a real browser/page sends, and each was found to
either not check the visible captcha server-side at all, or not require one
in the first place:

- **Link Intime / MUFG Intime** (`linkintime_client.py`) — AES-encrypted
  token flow, replicated using the static key/IV in the site's own public
  `js/aes.js`. The client-side captcha check is dead code; the server
  endpoint never receives a captcha value.
- **Bigshare** (`bigshare_client.py`) — the visible captcha is a
  client-side-only `<canvas>` doodle compared against `sessionStorage`;
  the real search endpoint (`Data.aspx/FetchIpodetails`) never sees it.
- **KFintech** (`kfintech_client.py`) — the production status-check app
  (`ipostatus.kfintech.com`) calls a plain AWS API Gateway endpoint with
  the IPO and PAN passed as request headers, no captcha and no session
  token. (A *different*, legacy KFintech portal — `ris.kfintech.com` — is
  behind an aggressive bot-detection challenge; that one was abandoned in
  favor of the real production endpoint above, which has no such gate.)

**Not automated**: Cameo, Skyline, and Purva. These weren't reverse
engineered (Cameo is an Angular SPA; the other two weren't investigated) —
`manual_fallback_adapter.py` covers them structurally, but since there's no
list-fetcher for them yet, IPOs handled by these three registrars won't
currently appear in `/ipos/recent` at all. In practice this means the app
only surfaces IPOs from the three registrars above.

**IPO list** (`ipo_list_service.py` + `ipo_repository.py`): aggregated
directly from each of the three registrars' own "IPOs available to check"
list (not scraped from a third-party aggregator — Chittorgarh and
Investorgain both turned out to be JS-rendered Next.js apps without a
simple public data endpoint). Cached in SQLite (`data/ipo_cache.sqlite3`),
refreshed on startup and every 6 hours. There's no registrar-published
"allotment finalized on X date" field available anywhere, so the API's
`allotment_date` is actually *the date our cache first saw this IPO*, not
an authoritative registrar date — documented in `ipo_list_service.py`.

## Setup

```
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

## Run

```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` is required so a physical phone on the same Wi-Fi/LAN can
reach the API — Expo Go on a phone can't reach `localhost` of your PC. Find
your PC's LAN IP (`ipconfig`) and point the mobile app's
`EXPO_PUBLIC_API_BASE_URL` at `http://<that-ip>:8000`.

## Verify

```
curl http://localhost:8000/health
curl http://localhost:8000/ipos/recent
curl -X POST http://localhost:8000/ipos/linkintime-11921/check-allotment \
  -H "Content-Type: application/json" \
  -d "{\"applicants\":[{\"pan\":\"ZZZZZ0000Z\",\"label\":\"Test\"}]}"
```

The check-allotment call above hits the real Link Intime API with an
obviously-fake PAN and should return `NOT_APPLIED`. Swap the id prefix for
`bigshare-<id>` or `kfintech-<id>` (see `/ipos/recent` for current ids) to
test the other two registrars the same way.
