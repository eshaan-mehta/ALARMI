import { http } from '../http';
import type { Project } from './types';

/** GET /api/projects/all_projects */
export async function getAllProjects(): Promise<Project[]> {
  const { data } = await http.get<Project[]>('/projects/all_projects');
  // Guard against a non-JSON body (e.g. the dev server's index.html when the
  // mock worker isn't yet controlling the page) so the UI shows its error
  // state and retries, instead of crashing on `projects.map`.
  if (!Array.isArray(data)) {
    throw new Error('Expected an array of projects from /projects/all_projects');
  }
  return data;
}

/** POST /api/projects */
export async function createProject(name: string): Promise<Project> {
  const { data } = await http.post<Project>('/projects', { name });
  return data;
}

/** PATCH /api/projects/{project_name} */
export async function renameProject(name: string, newName: string): Promise<Project> {
  const { data } = await http.patch<Project>(
    `/projects/${encodeURIComponent(name)}`,
    { new_name: newName },
  );
  return data;
}
