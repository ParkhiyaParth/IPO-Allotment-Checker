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

Runs on an Oracle Cloud Always Free instance (`VM.Standard.E2.1.Micro` — 1
OCPU, 1GB RAM is enough; this backend is small and I/O-bound, not CPU/RAM
heavy). Caddy handles HTTPS via a free `sslip.io` hostname (Let's Encrypt
won't issue a cert for a bare IP, so this is the simplest way to get real
HTTPS without owning a domain) and reverse-proxies to uvicorn, which only
listens on `127.0.0.1` — never exposed directly to the internet.

**One-time setup**, after creating the instance and SSH-ing in:
```
git clone https://github.com/ParkhiyaParth/IPO-Allotment-Checker.git
bash IPO-Allotment-Checker/backend/deploy/setup.sh
```
That installs Python, Caddy, a 2GB swapfile, clones the repo, sets up the
venv, and installs+starts the `ipo-backend` systemd service. It'll then
print two things you still have to do by hand:
1. Edit `backend/deploy/Caddyfile` with the instance's real IP (dashes
   instead of dots) and reload Caddy.
2. Open ports 80/443 in the **Oracle Cloud Security List** for that
   instance's subnet — this is a cloud-network-level firewall separate
   from the OS's own, and blocks traffic regardless of OS firewall rules.

**Ongoing deploys**: pushing to `main` (touching anything under `backend/`)
triggers `.github/workflows/deploy-backend.yml`, which SSHs into the server
and runs `backend/deploy/deploy.sh` (git pull, reinstall deps, restart the
service). Requires these repo secrets (GitHub repo → Settings → Secrets and
variables → Actions):
- `DEPLOY_HOST` — the instance's public IP
- `DEPLOY_USER` — `ubuntu`
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
