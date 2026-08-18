import * as SecureStore from 'expo-secure-store';
import type { AllotmentResultItem, AllotmentStatus } from '../types/api';

// Same single-blob pattern as panStore.ts. Caps at MAX_ENTRIES (pruned by
// most-recent checkedAt) so this can't grow unbounded across a long-lived
// install -- a personal app's realistic history stays well under this.
const STORAGE_KEY = 'check_results_cache_v1';
const MAX_ENTRIES = 200;

export interface CachedCheckResult {
  ipoId: string;
  pan: string;
  companyName: string;
  status: AllotmentStatus;
  sharesAllotted: number | null;
  checkedAt: string;
}

function keyFor(ipoId: string, pan: string): string {
  return `${ipoId}:${pan}`;
}

async function readAll(): Promise<CachedCheckResult[]> {
  const raw = await SecureStore.getItemAsync(STORAGE_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as CachedCheckResult[];
  } catch {
    return [];
  }
}

async function writeAll(entries: CachedCheckResult[]): Promise<void> {
  await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(entries));
}

export const checkResultsCache = {
  getAll: (): Promise<CachedCheckResult[]> => readAll(),

  saveMany: async (ipoId: string, companyName: string, results: AllotmentResultItem[]): Promise<void> => {
    const existing = await readAll();
    const now = new Date().toISOString();
    const byKey = new Map(existing.map((e) => [keyFor(e.ipoId, e.pan), e]));

    for (const r of results) {
      byKey.set(keyFor(ipoId, r.pan), {
        ipoId,
        pan: r.pan,
        companyName,
        status: r.status,
        sharesAllotted: r.shares_allotted,
        checkedAt: now,
      });
    }

    const merged = Array.from(byKey.values()).sort(
      (a, b) => new Date(b.checkedAt).getTime() - new Date(a.checkedAt).getTime(),
    );
    await writeAll(merged.slice(0, MAX_ENTRIES));
  },
};
