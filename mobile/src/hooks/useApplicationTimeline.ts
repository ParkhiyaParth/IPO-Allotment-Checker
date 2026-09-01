import { useMemo } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { appliedMarksStore, type AppliedEntry } from '../storage/appliedMarksStore';
import type { ApplySignal, IpoPotentialLabel } from '../types/api';
import { useIpoCatalog } from './useIpoCatalog';
import { usePanProfiles } from './usePanProfiles';

const APPLIED_MARKS_QUERY_KEY = ['appliedMarks'];

// Blocked-fund release is a bank/UPI-mandate process this app can't observe
// directly -- BoA date + 1 day is a clearly-labeled estimate (allotted
// amounts convert to shares, non-allotted amounts get unblocked, both
// settle within about a day of BoA in practice), not a guarantee.
const FUNDS_FREE_BUFFER_DAYS = 1;

export interface PendingApplication extends AppliedEntry {
  fundsFreeBy: string | null; // ISO date, or null if boaDate isn't known yet
}

export interface ApplyCandidate {
  ipoId: string;
  companyName: string;
  closeDate: string | null;
  boaDate: string | null;
  potentialLabel: IpoPotentialLabel | null;
  applySignal: ApplySignal | null;
  reason: string | null;
  lotSize: number | null;
  issuePrice: number | null;
  fundsStatus: 'ok' | 'conflict' | 'unknown';
  conflictWith: PendingApplication | null;
}

export interface PanTimeline {
  panId: string;
  panName: string;
  pending: PendingApplication[];
  nextAvailableDate: string | null;
  candidates: ApplyCandidate[];
}

function addDays(isoDate: string, days: number): string {
  const [y, m, d] = isoDate.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d + days)).toISOString().slice(0, 10);
}

function todayLocal(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function useApplicationTimeline() {
  const queryClient = useQueryClient();
  const { profiles } = usePanProfiles();
  const openCatalog = useIpoCatalog('open');
  const upcomingCatalog = useIpoCatalog('upcoming');
  const appliedQuery = useQuery({ queryKey: APPLIED_MARKS_QUERY_KEY, queryFn: appliedMarksStore.getAll });

  const isLoading = openCatalog.isLoading || upcomingCatalog.isLoading || appliedQuery.isLoading;
  const isError = openCatalog.isError || upcomingCatalog.isError;

  const openData = openCatalog.data;
  const upcomingData = upcomingCatalog.data;

  const panTimelines: PanTimeline[] = useMemo(() => {
    const allApplied = Object.values(appliedQuery.data ?? {});
    const candidateIpos = [...(openData ?? []), ...(upcomingData ?? [])].filter(
      (ipo) =>
        ipo.linked_registrar_ipo_id != null &&
        (ipo.apply_signal === 'strong_apply' ||
          ipo.ipo_potential_label === 'strong_potential' ||
          ipo.ipo_potential_label === 'promising'),
    );

    const todayIso = todayLocal();

    return profiles.map((profile) => {
      const pendingRaw = allApplied.filter((e) => e.panId === profile.id);
      const pending: PendingApplication[] = pendingRaw
        .map((e) => ({ ...e, fundsFreeBy: e.boaDate ? addDays(e.boaDate, FUNDS_FREE_BUFFER_DAYS) : null }))
        // Once funds are known to be free, this no longer constrains the
        // timeline -- allotted money is now shares, non-allotted is
        // refunded, either way it stops "blocking" a future application.
        .filter((e) => e.fundsFreeBy == null || e.fundsFreeBy >= todayIso);

      const knownFreeDates = pending.map((e) => e.fundsFreeBy).filter((d): d is string => d != null);
      const nextAvailableDate = knownFreeDates.length > 0 ? knownFreeDates.slice().sort().slice(-1)[0] : null;
      const hasUnknownPending = pending.some((e) => e.fundsFreeBy == null);

      const appliedIpoIds = new Set(pendingRaw.map((e) => e.ipoId));

      const candidates: ApplyCandidate[] = candidateIpos
        .filter((ipo) => !appliedIpoIds.has(ipo.linked_registrar_ipo_id as string))
        .map((ipo) => {
          let fundsStatus: ApplyCandidate['fundsStatus'];
          let conflictWith: PendingApplication | null = null;

          if (!ipo.close_date || hasUnknownPending) {
            fundsStatus = 'unknown';
          } else if (!nextAvailableDate || nextAvailableDate <= ipo.close_date) {
            fundsStatus = 'ok';
          } else {
            fundsStatus = 'conflict';
            conflictWith = pending.find((e) => e.fundsFreeBy === nextAvailableDate) ?? null;
          }

          return {
            ipoId: ipo.linked_registrar_ipo_id as string,
            companyName: ipo.company_name,
            closeDate: ipo.close_date,
            boaDate: ipo.boa_date,
            potentialLabel: ipo.ipo_potential_label,
            applySignal: ipo.apply_signal,
            reason: ipo.apply_signal_reason ?? ipo.ipo_potential_reasons?.[0] ?? null,
            lotSize: ipo.lot_size,
            issuePrice: ipo.issue_price,
            fundsStatus,
            conflictWith,
          };
        })
        // Best opportunities first (strong signal ahead of merely
        // "promising"), then soonest-closing as the tiebreak -- this order
        // itself is the prioritization the user's asking for when two good
        // IPOs' windows collide.
        .sort((a, b) => {
          const rank = (c: ApplyCandidate) =>
            c.applySignal === 'strong_apply' || c.potentialLabel === 'strong_potential' ? 0 : 1;
          const byRank = rank(a) - rank(b);
          if (byRank !== 0) return byRank;
          return (a.closeDate ?? '9999-99-99').localeCompare(b.closeDate ?? '9999-99-99');
        });

      return { panId: profile.id, panName: profile.name, pending, nextAvailableDate, candidates };
    });
  }, [appliedQuery.data, openData, upcomingData, profiles]);

  const markApplied = async (candidate: ApplyCandidate, panId: string, panName: string, lots: number) => {
    const amountBlocked =
      candidate.lotSize != null && candidate.issuePrice != null
        ? candidate.lotSize * candidate.issuePrice * lots
        : null;
    await appliedMarksStore.recordApplication({
      ipoId: candidate.ipoId,
      panId,
      panName,
      companyName: candidate.companyName,
      lots,
      amountBlocked,
      boaDate: candidate.boaDate,
      closeDate: candidate.closeDate,
      appliedAt: new Date().toISOString(),
    });
    queryClient.invalidateQueries({ queryKey: APPLIED_MARKS_QUERY_KEY });
  };

  const removeApplication = async (ipoId: string, panId: string) => {
    await appliedMarksStore.remove(ipoId, panId);
    queryClient.invalidateQueries({ queryKey: APPLIED_MARKS_QUERY_KEY });
  };

  return { panTimelines, isLoading, isError, markApplied, removeApplication };
}
