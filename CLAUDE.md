# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Personal IPO allotment checker with two halves that talk over HTTP:

- `backend/` — Python/FastAPI API that scrapes registrar (RTA) sites and aggregates IPO/market data.
- `mobile/` — React Native (Expo, SDK 57) app for iOS + Android; stores PAN/name entries locally on-device.

## Commands

### Backend (from `backend/`)

```
python -m venv .venv
.venv\Scripts\activate                 # Windows
pip install -r requirements-dev.txt    # includes requirements.txt + pytest

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # run (0.0.0.0 so a phone on the LAN can reach it)
pytest                                  # run all tests
pytest tests/services/test_ipo_repository.py            # single file
pytest tests/services/test_ipo_repository.py::test_name  # single test
```

`pytest.ini` sets `asyncio_mode = auto` — async test functions don't need `@pytest.mark.asyncio`. Every test gets an isolated SQLite DB automatically via the autouse `_isolated_db` fixture in `tests/conftest.py` (monkeypatches `database.DB_PATH` to a tmp path) — never share DB state across tests manually. External HTTP is faked with `FakeAsyncClient`/`FakeResponse` from `conftest.py`, keyed by exact URL.

Manual endpoint smoke-check:
```
curl http://localhost:8000/health
curl http://localhost:8000/ipos/recent
curl -X POST http://localhost:8000/ipos/linkintime-11921/check-allotment \
  -H "Content-Type: application/json" \
  -d "{\"applicants\":[{\"pan\":\"ZZZZZ0000Z\",\"label\":\"Test\"}]}"
```

### Mobile (from `mobile/`)

```
npm install
npx expo start          # Expo Go dev server (npm run android / ios / web also work)
```

No lint/typecheck/test scripts are currently defined in `mobile/package.json`; use `npx tsc --noEmit` for a manual type check if needed. Set `EXPO_PUBLIC_API_BASE_URL` in `mobile/.env` to the backend's LAN IP so a physical phone can reach it (Expo Go can't reach the PC's `localhost`).

**Before writing any mobile code**: `mobile/CLAUDE.md` (auto-loaded from this directory) flags that Expo has changed significantly — check the versioned docs at https://docs.expo.dev/versions/v57.0.0/ before assuming API shapes from training data.

## Architecture

### Backend: registrar adapter pattern

IPO allotment checks are dispatched through a registrar-agnostic interface (`app/scrapers/registrars/base.py`: `RegistrarAdapter.check_status(pan, ipo_identifier) -> AllotmentResult`). `registry.py` maps a registrar name to its adapter instance. Each IPO id in the API is `"{registrar}-{registrar_ipo_identifier}"` (e.g. `linkintime-11921`); the registrar prefix picks the adapter, the rest is passed through as an opaque, registrar-specific identifier — adapters never need to know other registrars' identifier formats.

Three registrars are actually automated (each reverse-engineered by inspecting real browser traffic, not by solving captchas — see `backend/README.md` for the specifics of each):
- **Link Intime** (`linkintime_client.py` + `linkintime_adapter.py`) — AES-encrypted token flow using the static key/IV from the site's own public JS.
- **Bigshare** (`bigshare_client.py` + `bigshare_adapter.py`) — the visible captcha never reaches the real search endpoint.
- **KFintech** (`kfintech_client.py` + `kfintech_adapter.py`) — hits the production AWS API Gateway endpoint directly, no captcha/session needed.

Cameo, Skyline, and Purva are **not** automated — `manual_fallback_adapter.py` exists structurally for them but there's no list-fetcher, so IPOs from these three registrars never appear in `/ipos/recent`.

Two independent aggregation pipelines, each with its own cache table and refresh cadence (see `app/main.py`'s periodic-refresh tasks):
- **IPO list** (`ipo_list_service.py` + `ipo_repository.py`, table `ipo_cache`) — which IPOs are open/checkable, sourced directly from the three registrars' own lists. Refreshed every 15 min during the evening allotment window (17:00+ IST), every 2h otherwise.
- **IPO catalog** (`ipo_catalog_service.py` + `ipo_catalog_repository.py`, table `ipo_catalog`) — richer market data (GMP, subscription, price, listing) from `scrapers/market_data/` (NSE, Investorgain) and `scrapers/news/`. Refreshed every 5 min during market hours (09:00–17:00 IST), every 2h otherwise. A separate once-daily job (`news_market_refresh_service.py`) handles historical-outcome backfill, news sentiment, and broad market trend — these feed `ipo_potential_service.py`'s apply/avoid signal but don't need to move fast.

There's no registrar-published allotment-finalization date anywhere, so `allotment_date` in the API is actually *the date this cache first saw the IPO*, not an authoritative date.

### Backend: persistence

Single SQLite file at `backend/data/ipo_cache.sqlite3` (`app/db/database.py`), created/migrated on every `get_connection()` call: `_SCHEMA` has the current `CREATE TABLE IF NOT EXISTS` definitions, and each historical column addition is a separate `ALTER TABLE ... ADD COLUMN` wrapped in `try/except sqlite3.OperationalError: pass`. There's no migration framework — adding a column means adding both to `_SCHEMA` (for fresh DBs) and as a new guarded `ALTER TABLE` call (for existing ones).

PANs are the one piece of PII: the per-request allotment check never persists a PAN. The opt-in "device PAN sync" feature (`device_pan_repository.py`, table `device_pans`) does persist PANs, but only AES-encrypted (`utils/encryption.py`) under `settings.pan_encryption_key`; `routes_device_pans.py` returns 503 rather than starting up with encryption unset.

### Mobile: structure

- `src/api/` — thin fetch wrappers per resource (`ipos.ts`, `allotment.ts`, `devicePans.ts`, `push.ts`), all routed through `src/api/client.ts`'s `apiClient` (adds base URL from `EXPO_PUBLIC_API_BASE_URL`, JSON headers, error unwrapping into `ApiError`).
- `src/hooks/` — TanStack Query hooks wrapping the API layer (`useRecentIpos`, `useCheckAllotment`, etc.) — screens consume these, not `api/` directly.
- `src/storage/` — on-device persistence via `expo-secure-store`. `panStore.ts` keeps all PAN/name entries as a single JSON blob under one SecureStore key (chosen because iOS caps individual SecureStore values around ~2KB, and a personal PAN list stays well under that as one blob — swap for `expo-sqlite` if the list ever needs to scale).
- `src/navigation/RootNavigator.tsx` — three independent stack navigators (IPOs, Allotment, PANs) inside one bottom tab navigator; `types.ts` holds each stack's param list.
- `src/screens/` — one component per navigator route.

### Deployment

- Backend: pushing to `main` under `backend/**` triggers `.github/workflows/deploy-backend.yml`, which SSHs into an Oracle Cloud VM and runs `backend/deploy/deploy.sh` (git pull, reinstall deps, restart the `ipo-backend` systemd service, fronted by Caddy). See `README.md` for one-time VM setup.
- Mobile: pushing to `main` under `mobile/**` triggers `.github/workflows/deploy-mobile.yml`, which runs `eas update` to ship an OTA JS update to the `preview` channel — no new APK build unless a native module changed. See `mobile/README.md` for EAS build details.
