import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../../lib/api/queryKeys';
import {
  deleteDesign,
  getProjectDesigns,
  uploadDesign,
  type UploadDesignArgs,
} from './api';

/**
 * Lists a project's designs and auto-polls every 2s while any design is still
 * processing, so cards flip to COMPLETE on their own. Polling stops once all
 * designs are done.
 */
export function useProjectDesigns(projectName: string) {
  return useQuery({
    queryKey: queryKeys.projectDesigns(projectName),
    queryFn: () => getProjectDesigns(projectName),
    refetchInterval: (query) => {
      const data = query.state.data;
      const pending = data?.some((d) => d.status !== 'COMPLETE');
      return pending ? 2000 : false;
    },
  });
}

export function useUploadDesign(projectName: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: Omit<UploadDesignArgs, 'projectName'>) =>
      uploadDesign({ ...args, projectName }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.projectDesigns(projectName) });
      qc.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}

export function useDeleteDesign(projectName: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (designId: string) => deleteDesign(designId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.projectDesigns(projectName) });
      qc.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}
