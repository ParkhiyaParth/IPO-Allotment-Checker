import { apiClient } from './client';
import type {
  HistoricalOutcomeSummary,
  IPOCatalogDetail,
  IPOCatalogListResponse,
  IPOCatalogStatus,
  IPOCatalogSummary,
  NewsHeadline,
  NewsHeadlinesResponse,
  SimilarOutcomesResponse,
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

export async function fetchIpoHeadlines(ipoId: string): Promise<NewsHeadline[]> {
  const data = await apiClient.get<NewsHeadlinesResponse>(`/ipos/catalog/${ipoId}/headlines`);
  return data.headlines;
}

export async function fetchSimilarOutcomes(ipoId: string): Promise<HistoricalOutcomeSummary[]> {
  const data = await apiClient.get<SimilarOutcomesResponse>(`/ipos/catalog/${ipoId}/similar-outcomes`);
  return data.outcomes;
}
