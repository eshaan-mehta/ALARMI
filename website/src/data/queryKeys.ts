/** Central registry of TanStack Query keys so invalidation stays consistent. */
export const queryKeys = {
  projects: ['projects'] as const,
  projectDesigns: (projectId: string) =>
    ['designs', 'project', projectId] as const,
  designModules: (designId: string) =>
    ['designs', designId, 'modules'] as const,
};
