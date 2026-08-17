import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { panStore } from '../storage/panStore';

const QUERY_KEY = ['panProfiles'];

export function usePanProfiles() {
  const queryClient = useQueryClient();

  const query = useQuery({
    queryKey: QUERY_KEY,
    queryFn: panStore.getAll,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: QUERY_KEY });

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
