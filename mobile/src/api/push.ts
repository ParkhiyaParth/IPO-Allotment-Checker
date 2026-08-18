import { apiClient } from './client';

export async function registerPushToken(token: string, deviceId: string): Promise<void> {
  await apiClient.post<void>('/push-tokens', { token, device_id: deviceId });
}
