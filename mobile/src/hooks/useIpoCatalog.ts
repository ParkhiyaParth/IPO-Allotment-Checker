import { useQuery } from '@tanstack/react-query';
import { fetchApplySignalTrackRecord, fetchIpoCatalog, fetchIpoCatalogDetail } from '../api/ipoCatalog';
import type { IPOCatalogStatus } from '../types/api';

// The backend itself only re-scrapes every 5min (market hours) / 2h
// (off-hours) -- see main.py -- but without this the app would only ever
// show fresh GMP/subscription data right after a manual pull-to-refresh —
// auto-refetching while the screen is open keeps it visibly live without
// over-polling the backend.
const LIVE_REFETCH_INTERVAL_MS = 60_000;

export function useIpoCatalog(status: IPOCatalogStatus) {
  return useQuery({
    queryKey: ['ipos', 'catalog', status],
    queryFn: () => fetchIpoCatalog(status),
    refetchInterval: LIVE_REFETCH_INTERVAL_MS,
  });
}

export function useIpoCatalogDetail(ipoId: string) {
  return useQuery({
    queryKey: ['ipos', 'catalog', 'detail', ipoId],
    queryFn: () => fetchIpoCatalogDetail(ipoId),
    refetchInterval: LIVE_REFETCH_INTERVAL_MS,
  });
}

export function useApplySignalTrackRecord() {
  return useQuery({
    queryKey: ['ipos', 'applySignal', 'trackRecord'],
    queryFn: fetchApplySignalTrackRecord,
  });
}
