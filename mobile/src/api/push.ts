import { apiClient } from './client';

export async function registerPushToken(token: string): Promise<void> {
  await apiClient.post<void>('/push-tokens', { token });
}
