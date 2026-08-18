import * as SecureStore from 'expo-secure-store';

// Local opt-in flag for zero-tap allotment discovery -- same single-blob
// pattern as panStore.ts. Opting in means the device's PAN list gets synced
// (encrypted in transit and at rest) to the server so it can auto-check
// allotment on your behalf and push you the result.
const STORAGE_KEY = 'device_pan_sync_v1';

async function readState(): Promise<{ optedIn: boolean }> {
  const raw = await SecureStore.getItemAsync(STORAGE_KEY);
  if (!raw) return { optedIn: false };
  try {
    return JSON.parse(raw) as { optedIn: boolean };
  } catch {
    return { optedIn: false };
  }
}

async function writeState(state: { optedIn: boolean }): Promise<void> {
  await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(state));
}

export const devicePanSyncSettings = {
  isOptedIn: async (): Promise<boolean> => (await readState()).optedIn,
  setOptedIn: (optedIn: boolean): Promise<void> => writeState({ optedIn }),
};
