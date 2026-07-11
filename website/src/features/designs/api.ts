import type { AxiosProgressEvent } from 'axios';
import { http } from '../../lib/api/http';
import type { Design, ProcessingStatus } from './types';

/** GET /api/designs/project_designs/{project_name} */
export async function getProjectDesigns(projectName: string): Promise<Design[]> {
  const { data } = await http.get<Design[]>(
    `/designs/project_designs/${encodeURIComponent(projectName)}`,
  );
  return data;
}

/** GET /api/designs/{designId} */
export async function getDesign(designId: string): Promise<Design> {
  const { data } = await http.get<Design>(`/designs/${designId}`);
  return data;
}

/** GET /api/designs/{designId}/status */
export async function getDesignStatus(designId: string): Promise<ProcessingStatus> {
  const { data } = await http.get<{ status: ProcessingStatus }>(
    `/designs/${designId}/status`,
  );
  return data.status;
}

export interface UploadDesignArgs {
  projectName: string;
  /** User-supplied design name. */
  name: string;
  file: File;
  onProgress?: (percent: number) => void;
}

/** POST /api/designs/{project_name} — multipart { name, file } */
export async function uploadDesign({
  projectName,
  name,
  file,
  onProgress,
}: UploadDesignArgs): Promise<Design> {
  const form = new FormData();
  form.append('name', name);
  form.append('file', file);

  const { data } = await http.post<Design>(
    `/designs/${encodeURIComponent(projectName)}`,
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

/** DELETE /api/designs/{designId} */
export async function deleteDesign(designId: string): Promise<void> {
  await http.delete(`/designs/${designId}`);
}
