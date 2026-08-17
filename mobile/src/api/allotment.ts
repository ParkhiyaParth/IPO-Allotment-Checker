import { apiClient } from './client';
import type { CheckAllotmentResponse } from '../types/api';
import type { PanProfile } from '../types/pan';

export async function checkAllotment(
  ipoId: string,
  applicants: PanProfile[],
): Promise<CheckAllotmentResponse> {
  return apiClient.post<CheckAllotmentResponse>(`/ipos/${ipoId}/check-allotment`, {
    applicants: applicants.map((a) => ({ pan: a.pan, label: a.name })),
  });
}
