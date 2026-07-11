/** Central registry of TanStack Query keys so invalidation stays consistent. */
export const queryKeys = {
  projects: ['projects'] as const,
  projectDesigns: (projectName: string) =>
    ['designs', 'project', projectName] as const,
  design: (designId: string) => ['designs', designId] as const,
  designStatus: (designId: string) => ['designs', designId, 'status'] as const,
};
