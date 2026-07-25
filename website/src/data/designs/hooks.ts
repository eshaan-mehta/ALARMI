import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../queryKeys';
import {
  deleteDesign,
  getProjectDesigns,
  updateDesign,
  updateModule,
  uploadDesign,
  type UploadDesignArgs,
} from './api';
import type { DesignPatch, ModulePatch } from './types';

/**
 * Lists a project's designs and auto-polls every 2s while any design is still
 * processing, so cards flip to COMPLETE (or ERROR) on their own. Polling stops
 * once no design is processing.
 */
export function useProjectDesigns(projectId: string) {
  return useQuery({
    queryKey: queryKeys.projectDesigns(projectId),
    queryFn: () => getProjectDesigns(projectId),
    refetchInterval: (query) => {
      const data = query.state.data;
      const pending = data?.some((d) => d.status === 'PROCESSING');
      return pending ? 2000 : false;
    },
  });
}

export function useUploadDesign(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: Omit<UploadDesignArgs, 'projectId'>) =>
      uploadDesign({ ...args, projectId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.projectDesigns(projectId) });
      qc.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}

/** Rename a design. */
export function useUpdateDesign(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ designId, patch }: { designId: string; patch: DesignPatch }) =>
      updateDesign(designId, patch),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.projectDesigns(projectId) }),
  });
}

/** Edit a single module's extracted metadata. */
export function useUpdateModule(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ moduleId, patch }: { moduleId: string; patch: ModulePatch }) =>
      updateModule(moduleId, patch),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.projectDesigns(projectId) }),
  });
}

export function useDeleteDesign(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (designId: string) => deleteDesign(designId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.projectDesigns(projectId) });
      qc.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}
