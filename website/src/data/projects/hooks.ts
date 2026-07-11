import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../queryKeys';
import { createProject, getAllProjects, renameProject } from './api';

export function useProjects() {
  return useQuery({
    queryKey: queryKeys.projects,
    queryFn: getAllProjects,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) => createProject(name),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.projects }),
  });
}

export function useRenameProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, newName }: { name: string; newName: string }) =>
      renameProject(name, newName),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.projects }),
  });
}
