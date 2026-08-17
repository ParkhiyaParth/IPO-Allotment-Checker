import { useQuery } from '@tanstack/react-query';
import { fetchRecentIpos } from '../api/ipos';

export function useRecentIpos() {
  return useQuery({
    queryKey: ['ipos', 'recent'],
    queryFn: fetchRecentIpos,
  });
}
