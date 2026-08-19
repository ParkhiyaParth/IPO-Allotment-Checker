import * as SecureStore from 'expo-secure-store';

// Local "did I apply for this IPO with this PAN, and with how much money"
// ledger -- there's no server-side signal for this (only post-BoA "checked"
// status exists), so both the family-portfolio nudge list and the
// application-timeline fund planner need their own local record.
const STORAGE_KEY = 'applied_marks_v1';

export interface AppliedEntry {
  ipoId: string; // linked_registrar_ipo_id -- matches checkResultsCache's keying
  panId: string;
  panName: string;
  companyName: string;
  lots: number;
  amountBlocked: number | null; // lots * lot_size * issue_price, snapshotted at apply time
  boaDate: string | null; // snapshotted catalog boa_date (ISO) at apply time
  closeDate: string | null; // snapshotted catalog close_date (ISO), for display context
  appliedAt: string; // ISO, when this was recorded
}

function keyFor(ipoId: string, panId: string): string {
  return `${ipoId}:${panId}`;
}

async function readAll(): Promise<Record<string, AppliedEntry>> {
  const raw = await SecureStore.getItemAsync(STORAGE_KEY);
  if (!raw) return {};
  try {
    return JSON.parse(raw) as Record<string, AppliedEntry>;
  } catch {
    return {};
  }
}

async function writeAll(entries: Record<string, AppliedEntry>): Promise<void> {
  await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(entries));
}

export const appliedMarksStore = {
  getAll: (): Promise<Record<string, AppliedEntry>> => readAll(),

  recordApplication: async (entry: AppliedEntry): Promise<void> => {
    const all = await readAll();
    all[keyFor(entry.ipoId, entry.panId)] = entry;
    await writeAll(all);
  },

  remove: async (ipoId: string, panId: string): Promise<void> => {
    const all = await readAll();
    delete all[keyFor(ipoId, panId)];
    await writeAll(all);
  },

  key: keyFor,
};
