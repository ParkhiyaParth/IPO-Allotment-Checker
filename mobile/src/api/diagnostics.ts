import { apiClient } from './client';

export async function reportDiagnostic(message: string): Promise<void> {
  try {
    await apiClient.post<void>('/diagnostics', { message });
  } catch {
    // If the diagnostic report itself can't reach the server, there's
    // nowhere else useful to surface this — just drop it.
  }
}
