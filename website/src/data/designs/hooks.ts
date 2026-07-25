import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../queryKeys';
import {
  deleteDesign,
  getDesignModules,
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

/**
 * Lazily fetches one design's modules. Stays disabled until `enabled` (the row
 * is expanded), so the module payload is only pulled when the user opens the
 * design — then TanStack caches it for subsequent expands.
 */
export function useDesignModules(designId: string, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.designModules(designId),
    queryFn: () => getDesignModules(designId),
    enabled,
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

/**
 * Edit a single module's extracted metadata. Modules live in the per-design
 * lazy cache, so invalidate that key (not the project's design list — a metadata
 * edit doesn't change the list or the module count).
 */
export function useUpdateModule(designId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ moduleId, patch }: { moduleId: string; patch: ModulePatch }) =>
      updateModule(moduleId, patch),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: queryKeys.designModules(designId) }),
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
