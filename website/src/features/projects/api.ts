import { http } from '../../lib/api/http';
import type { Project } from './types';

/** GET /api/projects/all_projects */
export async function getAllProjects(): Promise<Project[]> {
  const { data } = await http.get<Project[]>('/projects/all_projects');
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
