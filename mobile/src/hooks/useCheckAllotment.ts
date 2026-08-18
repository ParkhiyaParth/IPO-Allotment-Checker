import { useMutation } from '@tanstack/react-query';
import { checkAllotment } from '../api/allotment';
import { checkResultsCache } from '../storage/checkResultsCache';
import type { PanProfile } from '../types/pan';

type Variables = { ipoId: string; companyName: string; applicants: PanProfile[] };

export function useCheckAllotment() {
  return useMutation({
    mutationFn: ({ ipoId, applicants }: Variables) => checkAllotment(ipoId, applicants),
    onSuccess: (data, variables) => {
      checkResultsCache.saveMany(variables.ipoId, variables.companyName, data.results).catch(() => {});
    },
  });
}
