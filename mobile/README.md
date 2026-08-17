# IPO Allotment Checker — Mobile App

React Native (Expo) app for iOS + Android. Talks to the Python backend in
`../backend`.

## Dev run (Expo Go)

```
npm install
npx expo start
```

Set `EXPO_PUBLIC_API_BASE_URL` in `.env` to your PC's LAN IP (e.g.
`http://192.168.3.149:8000`) so a phone on the same Wi-Fi can reach the
backend. Scan the QR code with Expo Go.

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
build-time from `eas.json`'s `build.preview.env` (cloud builds don't read
your local `.env`). It's currently set to this dev PC's LAN IP. That means
the installed APK will only work when: the backend is running on this PC,
and the phone is on the same Wi-Fi network as it. There's no public
deployment yet — see "Going further" below if you want the app usable from
anywhere.

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

## Going further: using the app off your home network

Right now the backend only runs on this dev PC and the app is hardcoded to
its LAN IP. To use the app away from home, the backend needs to run
somewhere always-reachable (a small cloud VM, Railway/Render/Fly.io, etc.),
and `EXPO_PUBLIC_API_BASE_URL` (in `eas.json`) would need to point at that
public address instead. Not set up yet — ask if you want this next.
