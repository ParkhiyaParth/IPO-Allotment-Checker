# IPO Allotment Checker

Personal IPO allotment checker: save PAN/name entries locally on-device,
browse recently-available IPOs pulled live from KFintech, Link Intime, and
Bigshare, and check allotment status against all your saved PANs with one
tap. Push notifications fire when a new IPO's allotment becomes checkable.

- `backend/` — Python/FastAPI API that talks to the registrars
- `mobile/` — React Native (Expo) app for iOS + Android

See `backend/README.md` and `mobile/README.md` for details on each half.

## Local development

```
# backend
cd backend && .venv\Scripts\activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# mobile
cd mobile && npx expo start
```

Point `mobile/.env`'s `EXPO_PUBLIC_API_BASE_URL` at wherever the backend is
reachable from your phone (LAN IP, tunnel, or the production URL below).

## Production deployment (backend)

Runs on an Oracle Cloud Always Free instance, sharing a box with the mobile
dev server (see `mobile/README.md`'s "Live-testing in Expo Go" section) —
big enough (several GB RAM) for both, unlike the original single-purpose
1GB instance this backend started on. Caddy handles HTTPS via a free
`sslip.io` hostname (Let's Encrypt won't issue a cert for a bare IP, so
this is the simplest way to get real HTTPS without owning a domain) and
reverse-proxies to uvicorn, which only listens on `127.0.0.1` — never
exposed directly to the internet.

**One-time setup**: `backend/deploy/setup.sh` bootstraps a fresh **Ubuntu**
instance (apt-get, iptables) — see the comment at its top. The current
instance instead runs **Oracle Linux** (dnf, firewalld, SELinux), set up
by hand with the equivalent steps rather than this script; treat it as a
reference for the Ubuntu path, not as literally what's live.

**Ongoing deploys**: pushing to `main` (touching anything under `backend/`)
triggers `.github/workflows/deploy-backend.yml`, which SSHs into the server
and runs `backend/deploy/deploy.sh` (git pull, reinstall deps, restart the
service) — this script itself is OS-agnostic. Requires these repo secrets
(GitHub repo → Settings → Secrets and variables → Actions):
- `DEPLOY_HOST` — the instance's public IP
- `DEPLOY_USER` — `opc` (Oracle Linux's default cloud-image user; `ubuntu`
  for a Ubuntu instance)
- `DEPLOY_SSH_KEY` — the private key contents (the `.key` file from Oracle)

## Production updates (mobile)

The app uses **EAS Update** for over-the-air JS updates — most changes
(UI, logic, bug fixes) can ship to the already-installed app instantly,
without a new APK build/reinstall. A new native build (`eas build`) is
only needed when a native module changes (e.g. adding `expo-notifications`
did; a pure JS/style tweak doesn't).

```
cd mobile
eas update --channel preview --message "what changed"
```

The installed app checks for updates on launch and applies them on the
next restart.
