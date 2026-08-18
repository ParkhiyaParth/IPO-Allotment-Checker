import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { syncDevicePans } from '../api/devicePans';
import { getDeviceId } from '../storage/deviceId';
import { devicePanSyncSettings } from '../storage/devicePanSyncSettings';
import { panStore } from '../storage/panStore';

const QUERY_KEY = ['panProfiles'];

// Best-effort, non-blocking: while opted into zero-tap discovery, keep the
// server's copy of the PAN list in sync automatically on every local
// add/edit/remove, rather than requiring a manual "sync now" tap every
// time -- the one-time opt-in disclaimer is the actual consent gate.
async function resyncIfOptedIn(): Promise<void> {
  try {
    const optedIn = await devicePanSyncSettings.isOptedIn();
    if (!optedIn) return;
    const [profiles, deviceId] = await Promise.all([panStore.getAll(), getDeviceId()]);
    await syncDevicePans(deviceId, profiles);
  } catch {
    // Non-fatal -- the next successful sync (or manual toggle) will catch up.
  }
}

export function usePanProfiles() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: panStore.getAll,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    void resyncIfOptedIn();
  };

  const addMutation = useMutation({
    mutationFn: panStore.add,
    onSuccess: invalidate,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, name, pan }: { id: string; name: string; pan: string }) =>
      panStore.update(id, { name, pan }),
    onSuccess: invalidate,
  });

  const removeMutation = useMutation({
    mutationFn: panStore.remove,
    onSuccess: invalidate,
  });

  return {
    profiles: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error,
    addProfile: addMutation.mutateAsync,
    updateProfile: updateMutation.mutateAsync,
    removeProfile: removeMutation.mutateAsync,
  };
}
