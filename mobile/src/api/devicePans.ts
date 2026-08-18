import { apiClient } from './client';
import type { PanProfile } from '../types/pan';

export async function syncDevicePans(deviceId: string, profiles: PanProfile[]): Promise<void> {
  await apiClient.put<void>(`/device-pans/${deviceId}`, {
    pans: profiles.map((p) => ({ id: p.id, label: p.name, pan: p.pan })),
  });
}

export async function deleteDevicePans(deviceId: string): Promise<void> {
  await apiClient.delete<void>(`/device-pans/${deviceId}`);
}
