import * as SecureStore from 'expo-secure-store';
import type { PanProfile } from '../types/pan';

// All saved PAN/name entries live under a single SecureStore key as one JSON
// blob. iOS has historically balked at values above ~2KB per key; a personal
// list of PAN entries (a few dozen at most) stays well under that, so a
// single blob is simpler than per-entry keys. If the list ever needs to grow
// large, swap this for expo-sqlite + an encryption layer without touching
// callers of this module.
const STORAGE_KEY = 'pan_profiles_v1';

function generateId(): string {
  return `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
}

async function readAll(): Promise<PanProfile[]> {
  const raw = await SecureStore.getItemAsync(STORAGE_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as PanProfile[];
  } catch {
    return [];
  }
}

async function writeAll(profiles: PanProfile[]): Promise<void> {
  await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(profiles));
}

export const panStore = {
  getAll: (): Promise<PanProfile[]> => readAll(),

  add: async (entry: { name: string; pan: string }): Promise<PanProfile> => {
    const profiles = await readAll();
    const newProfile: PanProfile = { id: generateId(), name: entry.name, pan: entry.pan };
    await writeAll([...profiles, newProfile]);
    return newProfile;
  },

  update: async (id: string, entry: { name: string; pan: string }): Promise<void> => {
    const profiles = await readAll();
    const updated = profiles.map((p) => (p.id === id ? { ...p, ...entry } : p));
    await writeAll(updated);
  },

  remove: async (id: string): Promise<void> => {
    const profiles = await readAll();
    await writeAll(profiles.filter((p) => p.id !== id));
  },
};
