import { http, HttpResponse, delay } from 'msw';
import { db } from './db';
import type { DesignPatch, ModulePatch } from '../designs/types';

const BASE = '*/api'; // matches whatever origin/baseURL the client uses

/** Simulated network latency for realism. */
const LATENCY = 400;

export const handlers = [
  // ---- Projects ----
  http.get(`${BASE}/projects/all_projects`, async () => {
    await delay(LATENCY);
    return HttpResponse.json(db.listProjects());
  }),

  http.post(`${BASE}/projects`, async ({ request }) => {
    await delay(LATENCY);
    const body = (await request.json()) as { name?: string; location?: string };
    const name = body.name?.trim();
    const location = body.location?.trim();
    if (!name) {
      return HttpResponse.json({ message: 'Project name is required.' }, { status: 400 });
    }
    if (!location) {
      return HttpResponse.json({ message: 'Project location is required.' }, { status: 400 });
    }
    if (db.projectNameExists(name)) {
      return HttpResponse.json({ message: 'A project with that name already exists.' }, { status: 409 });
    }
    return HttpResponse.json(db.createProject(name, location), { status: 201 });
  }),

  http.patch(`${BASE}/projects/:projectId`, async ({ request, params }) => {
    await delay(LATENCY);
    const body = (await request.json()) as { new_name?: string };
    const newName = body.new_name?.trim();
    if (!newName) {
      return HttpResponse.json({ message: 'new_name is required.' }, { status: 400 });
    }
    const updated = db.renameProject(String(params.projectId), newName);
    if (!updated) return HttpResponse.json({ message: 'Project not found.' }, { status: 404 });
    return HttpResponse.json(updated);
  }),

  // ---- Designs ----
  http.get(`${BASE}/designs/project_designs/:projectId`, async ({ params }) => {
    await delay(LATENCY);
    return HttpResponse.json(db.listDesigns(String(params.projectId)));
  }),

  http.post(`${BASE}/designs/:projectId`, async ({ request, params }) => {
    await delay(LATENCY);
    const form = await request.formData();
    const file = form.get('file');
    const name = String(form.get('name') ?? '').trim();

    if (!(file instanceof File)) {
      return HttpResponse.json({ message: 'A file is required.' }, { status: 400 });
    }
    if (!file.name.toLowerCase().endsWith('.ifc')) {
      return HttpResponse.json({ message: 'Only .ifc files are accepted.' }, { status: 400 });
    }
    if (file.size > 1024 ** 3) {
      return HttpResponse.json({ message: 'File exceeds the 1 GB limit.' }, { status: 400 });
    }
    const design = db.createDesign(String(params.projectId), name || file.name, {
      name: file.name,
      size: file.size,
    });
    if (!design) {
      return HttpResponse.json({ message: 'Project not found.' }, { status: 404 });
    }
    return HttpResponse.json(design, { status: 201 });
  }),

  http.get(`${BASE}/designs/:designId/status`, async ({ params }) => {
    const status = db.getStatus(String(params.designId));
    if (!status) return HttpResponse.json({ message: 'Design not found.' }, { status: 404 });
    return HttpResponse.json({ status });
  }),

  http.get(`${BASE}/designs/:designId`, async ({ params }) => {
    await delay(LATENCY);
    const design = db.getDesign(String(params.designId));
    if (!design) return HttpResponse.json({ message: 'Design not found.' }, { status: 404 });
    return HttpResponse.json(design);
  }),

  http.patch(`${BASE}/designs/:designId`, async ({ request, params }) => {
    await delay(LATENCY);
    const patch = (await request.json()) as DesignPatch;
    if (patch.name !== undefined && patch.name.trim().length === 0) {
      return HttpResponse.json({ message: 'Design name is required.' }, { status: 400 });
    }
    const updated = db.updateDesign(String(params.designId), patch);
    if (!updated) return HttpResponse.json({ message: 'Design not found.' }, { status: 404 });
    return HttpResponse.json(updated);
  }),

  http.delete(`${BASE}/designs/:designId`, async ({ params }) => {
    await delay(LATENCY);
    const ok = db.deleteDesign(String(params.designId));
    if (!ok) return HttpResponse.json({ message: 'Design not found.' }, { status: 404 });
    return new HttpResponse(null, { status: 204 });
  }),

  // ---- Modules ----
  http.patch(`${BASE}/modules/:moduleId`, async ({ request, params }) => {
    await delay(LATENCY);
    const patch = (await request.json()) as ModulePatch;
    const updated = db.updateModule(String(params.moduleId), patch);
    if (!updated) return HttpResponse.json({ message: 'Module not found.' }, { status: 404 });
    return HttpResponse.json(updated);
  }),
];
