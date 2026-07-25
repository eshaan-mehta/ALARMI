import type { AxiosProgressEvent } from 'axios';
import { http } from '../http';
import type { Design, DesignPatch, Module, ModulePatch } from './types';

/** GET /api/projects/{projectId}/designs */
export async function getProjectDesigns(projectId: string): Promise<Design[]> {
  const { data } = await http.get<Design[]>(
    `/projects/${projectId}/designs`,
  );
  // Same guard as getAllProjects: a non-array body means the request didn't
  // reach the mock/backend, so fail loudly rather than crashing on `.map`.
  if (!Array.isArray(data)) {
    throw new Error('Expected an array of designs from /projects/{projectId}/designs');
  }
  return data;
}

export interface UploadDesignArgs {
  projectId: string;
  /** User-supplied design name. */
  name: string;
  file: File;
  onProgress?: (percent: number) => void;
}

/** POST /api/projects/{projectId}/designs — multipart { name, file } */
export async function uploadDesign({
  projectId,
  name,
  file,
  onProgress,
}: UploadDesignArgs): Promise<Design> {
  const form = new FormData();
  form.append('name', name);
  form.append('file', file);

  const { data } = await http.post<Design>(
    `/projects/${projectId}/designs`,
    form,
    {
      onUploadProgress: (e: AxiosProgressEvent) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      },
    },
  );
  return data;
}

/** GET /api/designs/{designId}/modules — a design's modules, fetched lazily. */
export async function getDesignModules(designId: string): Promise<Module[]> {
  const { data } = await http.get<Module[]>(`/designs/${designId}/modules`);
  if (!Array.isArray(data)) {
    throw new Error('Expected an array of modules from /designs/{designId}/modules');
  }
  return data;
}

/** PATCH /api/designs/{designId} — rename a design. */
export async function updateDesign(
  designId: string,
  patch: DesignPatch,
): Promise<Design> {
  const { data } = await http.patch<Design>(`/designs/${designId}`, patch);
  return data;
}

/** PATCH /api/modules/{moduleId} — edit a module's extracted metadata. */
export async function updateModule(
  moduleId: string,
  patch: ModulePatch,
): Promise<Module> {
  const { data } = await http.patch<Module>(`/modules/${moduleId}`, patch);
  return data;
}

/** DELETE /api/designs/{designId} */
export async function deleteDesign(designId: string): Promise<void> {
  await http.delete(`/designs/${designId}`);
}
