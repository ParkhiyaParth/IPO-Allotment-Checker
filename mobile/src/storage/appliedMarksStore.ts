import * as SecureStore from 'expo-secure-store';

// Purely local "did I apply for this IPO with this PAN" flag -- there's no
// server-side signal for this (only post-BoA "checked" status exists), so
// the family-portfolio nudge list needs its own lightweight local marker.
const STORAGE_KEY = 'applied_marks_v1';

function keyFor(ipoId: string, panId: string): string {
  return `${ipoId}:${panId}`;
}

async function readAll(): Promise<Record<string, boolean>> {
  const raw = await SecureStore.getItemAsync(STORAGE_KEY);
  if (!raw) return {};
  try {
    return JSON.parse(raw) as Record<string, boolean>;
  } catch {
    return {};
  }
}

async function writeAll(marks: Record<string, boolean>): Promise<void> {
  await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(marks));
}

export const appliedMarksStore = {
  getAll: (): Promise<Record<string, boolean>> => readAll(),

  setApplied: async (ipoId: string, panId: string, applied: boolean): Promise<void> => {
    const marks = await readAll();
    const key = keyFor(ipoId, panId);
    if (applied) {
      marks[key] = true;
    } else {
      delete marks[key];
    }
    await writeAll(marks);
  },

  key: keyFor,
};
