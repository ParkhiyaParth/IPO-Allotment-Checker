import * as SecureStore from 'expo-secure-store';

// A random per-install string (same lightweight scheme panStore.ts already
// uses for profile ids), NOT a hardware/installation identifier from
// expo-application -- those APIs pull in a native module, which would force
// an `eas build` (new APK) instead of an OTA `eas update` for this feature.
// Good enough for "device-scoped, opt-in": stable across app restarts,
// regenerated only on reinstall/SecureStore clear.
const DEVICE_ID_KEY = 'device_id_v1';

let cached: string | null = null;

function generateDeviceId(): string {
  return `dev-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`;
}

export async function getDeviceId(): Promise<string> {
  if (cached) return cached;

  let id = await SecureStore.getItemAsync(DEVICE_ID_KEY);
  if (!id) {
    id = generateDeviceId();
    await SecureStore.setItemAsync(DEVICE_ID_KEY, id);
  }
  cached = id;
  return id;
}
