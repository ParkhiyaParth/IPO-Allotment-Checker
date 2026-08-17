import { useMutation } from '@tanstack/react-query';
import { checkAllotment } from '../api/allotment';
import type { PanProfile } from '../types/pan';

export function useCheckAllotment() {
  return useMutation({
    mutationFn: ({ ipoId, applicants }: { ipoId: string; applicants: PanProfile[] }) =>
      checkAllotment(ipoId, applicants),
  });
}
