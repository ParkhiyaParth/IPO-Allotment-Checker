# IPO Allotment Checker — Mobile App

React Native (Expo) app for iOS + Android. Talks to the Python backend in
`../backend`.

## Dev run (Expo Go)

```
npm install
npx expo start
```

`.env`'s `EXPO_PUBLIC_API_BASE_URL` points at the production backend (see
root `README.md`) by default, so this works from any network without
further setup. For LAN-only testing against a locally-run backend instead,
point it at your PC's LAN IP (e.g. `http://192.168.3.149:8000`) and make
sure the phone's on the same Wi-Fi.

### Live-testing in Expo Go without keeping your PC running

A second, dedicated Oracle Cloud Always Free instance runs the Metro dev
server as a `systemd` service (`ipo-mobile-dev`) 24/7, independent of any
local machine — `.github/workflows/deploy-dev-server.yml` SSHs in and
pulls + restarts it on every push to `main` touching `mobile/**`. Connect
Expo Go to `exp://<that instance's public IP>:8081`; no tunnel/ngrok
needed since the instance already has a public IP. This is purely a
preview tool for testing in-progress code before it's built into a real
app — it plays no part in the OTA update pipeline below.

## Building a real installable app (EAS Build)

Dev-mode (Expo Go) needs your PC's dev server running and the phone on the
same network. To get a real standalone app icon on your phone instead:

### Android — works now, free

```
npx eas-cli build --platform android --profile preview
```

This builds a downloadable `.apk` in the cloud (no Android Studio needed
locally) using the already-linked EAS project (`@parthd/ipo-allotment-checker`).
When it finishes, `eas build:list` or the printed URL gives a download link
— open it on the phone and install (Android will prompt to allow installs
from this source once).

**Important**: `EXPO_PUBLIC_API_BASE_URL` is baked into the build at
build-time from `eas.json`'s `build.preview.env`, and OTA updates instead
read it from the EAS dashboard's per-environment variables (`eas env:list
--environment preview`) — cloud builds and `eas update` don't read your
local `.env`, so both need updating (not just `eas.json`) if the backend
ever moves. It currently points at the production backend (see root
`README.md`), so the installed APK works from any network.

### iOS — needs your own Apple Developer account first

Apple requires code-signing to install on a real device even for personal
use, so this step needs an Apple Developer Program membership ($99/year,
developer.apple.com) — sign up if you haven't, then from this project run:

```
npx eas-cli build --platform ios --profile preview
```

Run it in an interactive terminal (not through an automation session) —
it'll prompt you to log in with your Apple ID and either create a new
distribution certificate or reuse one. Once it finishes, EAS gives you an
install link (or a QR code) that registers your specific iPhone for ad-hoc
distribution and lets you install directly, no TestFlight needed for a
single device.
