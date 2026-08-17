import { apiClient } from './client';
import type { IPOSummary, RecentIposResponse } from '../types/api';

export async function fetchRecentIpos(): Promise<IPOSummary[]> {
  const data = await apiClient.get<RecentIposResponse>('/ipos/recent');
  return data.ipos;
}
