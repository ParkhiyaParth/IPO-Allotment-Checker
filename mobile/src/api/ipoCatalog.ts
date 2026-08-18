import { apiClient } from './client';
import type {
  IPOCatalogDetail,
  IPOCatalogListResponse,
  IPOCatalogStatus,
  IPOCatalogSummary,
} from '../types/api';

export async function fetchIpoCatalog(status: IPOCatalogStatus): Promise<IPOCatalogSummary[]> {
  const data = await apiClient.get<IPOCatalogListResponse>(`/ipos/catalog?status=${status}`);
  return data.ipos;
}

export async function fetchIpoCatalogDetail(ipoId: string): Promise<IPOCatalogDetail> {
  return apiClient.get<IPOCatalogDetail>(`/ipos/catalog/${ipoId}`);
}
