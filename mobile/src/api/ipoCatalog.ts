import { apiClient } from './client';
import type {
  IPOCatalogDetail,
  IPOCatalogListResponse,
  IPOCatalogStatus,
  IPOCatalogSummary,
  TrackRecordResponse,
} from '../types/api';

export async function fetchIpoCatalog(status: IPOCatalogStatus): Promise<IPOCatalogSummary[]> {
  const data = await apiClient.get<IPOCatalogListResponse>(`/ipos/catalog?status=${status}`);
  return data.ipos;
}

export async function fetchIpoCatalogDetail(ipoId: string): Promise<IPOCatalogDetail> {
  return apiClient.get<IPOCatalogDetail>(`/ipos/catalog/${ipoId}`);
}

export async function fetchApplySignalTrackRecord(): Promise<TrackRecordResponse> {
  return apiClient.get<TrackRecordResponse>('/ipos/apply-signal/track-record');
}
