import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../queryKeys';
import { createProject, getAllProjects, renameProject, type CreateProjectArgs } from './api';

export function useProjects() {
  return useQuery({
    queryKey: queryKeys.projects,
    queryFn: getAllProjects,
  });
}

/**
 * A single project looked up by id from the projects list (the mock has no
 * get-one endpoint; the list is cached, so this avoids an extra request).
 * `project` is undefined while loading or if the id doesn't exist.
 */
export function useProject(projectId: string) {
  const query = useProjects();
  return {
    ...query,
    project: query.data?.find((p) => p.projectId === projectId),
  };
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: CreateProjectArgs) => createProject(args),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.projects }),
  });
}

export function useRenameProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, newName }: { projectId: string; newName: string }) =>
      renameProject(projectId, newName),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.projects }),
  });
}
