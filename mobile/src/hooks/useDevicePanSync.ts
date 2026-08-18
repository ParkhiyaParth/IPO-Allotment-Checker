import { useQuery, useQueryClient } from '@tanstack/react-query';
import { deleteDevicePans, syncDevicePans } from '../api/devicePans';
import { getDeviceId } from '../storage/deviceId';
import { devicePanSyncSettings } from '../storage/devicePanSyncSettings';
import { usePanProfiles } from './usePanProfiles';

const QUERY_KEY = ['devicePanSync', 'optedIn'];

export function useDevicePanSync() {
  const queryClient = useQueryClient();
  const { profiles } = usePanProfiles();
  const query = useQuery({ queryKey: QUERY_KEY, queryFn: devicePanSyncSettings.isOptedIn });

  const enableSync = async () => {
    const deviceId = await getDeviceId();
    await syncDevicePans(deviceId, profiles);
    await devicePanSyncSettings.setOptedIn(true);
    queryClient.invalidateQueries({ queryKey: QUERY_KEY });
  };

  const disableSync = async () => {
    const deviceId = await getDeviceId();
    await deleteDevicePans(deviceId);
    await devicePanSyncSettings.setOptedIn(false);
    queryClient.invalidateQueries({ queryKey: QUERY_KEY });
  };

  return {
    isOptedIn: query.data ?? false,
    isLoading: query.isLoading,
    enableSync,
    disableSync,
  };
}
