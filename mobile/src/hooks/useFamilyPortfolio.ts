import { useQuery, useQueryClient } from '@tanstack/react-query';
import { appliedMarksStore } from '../storage/appliedMarksStore';
import { checkResultsCache } from '../storage/checkResultsCache';
import type { IPOCatalogSummary } from '../types/api';
import { useIpoCatalog } from './useIpoCatalog';
import { usePanProfiles } from './usePanProfiles';

const CACHED_RESULTS_QUERY_KEY = ['checkResultsCache'];
const APPLIED_MARKS_QUERY_KEY = ['appliedMarks'];

export interface FamilyPortfolioNudge {
  panId: string;
  panName: string;
  ipoId: string;
  companyName: string;
  closeDate: string | null;
  reason: string | null;
}

export function useFamilyPortfolio() {
  const queryClient = useQueryClient();
  const { profiles } = usePanProfiles();
  const openCatalog = useIpoCatalog('open');
  const upcomingCatalog = useIpoCatalog('upcoming');
  const cachedResultsQuery = useQuery({ queryKey: CACHED_RESULTS_QUERY_KEY, queryFn: checkResultsCache.getAll });
  const appliedMarksQuery = useQuery({ queryKey: APPLIED_MARKS_QUERY_KEY, queryFn: appliedMarksStore.getAll });

  const isLoading =
    openCatalog.isLoading || upcomingCatalog.isLoading || cachedResultsQuery.isLoading || appliedMarksQuery.isLoading;
  const isError = openCatalog.isError || upcomingCatalog.isError;

  const cachedResults = cachedResultsQuery.data ?? [];
  const appliedMarks = appliedMarksQuery.data ?? {};

  // Cached check results are keyed by the registrar-based ipo id (what
  // AllotmentCheckScreen passes as ipoId), not the catalog's own id -- the
  // catalog links back to that same id via linked_registrar_ipo_id.
  const catalogByRegistrarId = new Map<string, IPOCatalogSummary>();
  for (const ipo of [...(openCatalog.data ?? []), ...(upcomingCatalog.data ?? [])]) {
    if (ipo.linked_registrar_ipo_id) catalogByRegistrarId.set(ipo.linked_registrar_ipo_id, ipo);
  }

  let actualProfit = 0;
  let estimatedProfit = 0;
  for (const result of cachedResults) {
    if (result.status !== 'ALLOTTED') continue;
    const catalog = catalogByRegistrarId.get(result.ipoId);
    if (catalog?.profit_per_lot == null) continue;
    // Approximation: scales the per-lot figure by shares-allotted / lot_size
    // when both are known, otherwise assumes exactly 1 lot.
    const lots =
      result.sharesAllotted != null && catalog.lot_size ? result.sharesAllotted / catalog.lot_size : 1;
    const profit = catalog.profit_per_lot * lots;
    if (catalog.profit_basis === 'actual') actualProfit += profit;
    else estimatedProfit += profit;
  }

  const nudges: FamilyPortfolioNudge[] = [];
  for (const ipo of [...(openCatalog.data ?? []), ...(upcomingCatalog.data ?? [])]) {
    if (ipo.apply_signal !== 'strong_apply' || !ipo.linked_registrar_ipo_id) continue;
    for (const profile of profiles) {
      const key = appliedMarksStore.key(ipo.linked_registrar_ipo_id, profile.id);
      if (appliedMarks[key]) continue;
      nudges.push({
        panId: profile.id,
        panName: profile.name,
        ipoId: ipo.linked_registrar_ipo_id,
        companyName: ipo.company_name,
        closeDate: ipo.close_date,
        reason: ipo.apply_signal_reason,
      });
    }
  }

  const markApplied = async (ipoId: string, panId: string) => {
    await appliedMarksStore.setApplied(ipoId, panId, true);
    queryClient.invalidateQueries({ queryKey: APPLIED_MARKS_QUERY_KEY });
  };

  return { actualProfit, estimatedProfit, nudges, isLoading, isError, markApplied };
}
