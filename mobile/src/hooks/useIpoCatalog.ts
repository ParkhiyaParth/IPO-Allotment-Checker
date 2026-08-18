import { useQuery } from '@tanstack/react-query';
import { fetchIpoCatalog, fetchIpoCatalogDetail } from '../api/ipoCatalog';
import type { IPOCatalogStatus } from '../types/api';

export function useIpoCatalog(status: IPOCatalogStatus) {
  return useQuery({
    queryKey: ['ipos', 'catalog', status],
    queryFn: () => fetchIpoCatalog(status),
  });
}

export function useIpoCatalogDetail(ipoId: string) {
  return useQuery({
    queryKey: ['ipos', 'catalog', 'detail', ipoId],
    queryFn: () => fetchIpoCatalogDetail(ipoId),
  });
}
