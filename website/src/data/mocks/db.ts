import type {
  Design,
  DesignPatch,
  Module,
  ModulePatch,
  ProcessingStatus,
} from '../designs/types';
import type { Project } from '../projects/types';

/**
 * In-memory store backing the MSW mock. Resets on page reload. This exists only
 * to stand in for the real backend; components never import it directly.
 *
 * Identity is by **id**, never name: projects are keyed by `projectId` and
 * designs reference their parent by `projectId`. Names are display-only, so a
 * rename touches a single field and never re-keys anything.
 */

let projectSeq = 10;
const nextProjectId = () => `prj_${++projectSeq}`;

let designSeq = 100;
const nextDesignId = () => `dsn_${++designSeq}`;

let moduleSeq = 1000;
const nextModuleId = () => `mod_${++moduleSeq}`;

// moduleCount is derived (from modules.length) in designView, so it isn't stored.
interface StoredDesign extends Omit<Design, 'moduleCount'> {
  /** Epoch ms when the upload started, used to derive processing status. */
  startedAt: number;
}

/** Keyed by projectId. */
const projects = new Map<string, Project>();
/** Keyed by designId. */
const designs = new Map<string, StoredDesign>();

// Status timeline (ms since upload): PROCESSING -> COMPLETE.
const COMPLETE_AFTER = 5000;

function statusFor(startedAt: number): ProcessingStatus {
  return Date.now() - startedAt < COMPLETE_AFTER ? 'PROCESSING' : 'COMPLETE';
}

const MODULE_TYPES = [
  'Wall Panel',
  'Bathroom Service Wall',
  'Hospital Headwall',
  'Utility Panel',
];

/**
 * A single uploaded IFC yields one or more marked modules (1:N). Generated once
 * at upload time and stored on the design so later metadata edits persist; the
 * modules are only exposed to clients once the design is COMPLETE.
 */
function generateModules(seed: number): Module[] {
  const count = 1 + (seed % 3); // 1..3 modules per design
  return Array.from({ length: count }, (_, i) => {
    const s = seed + i * 7;
    return {
      moduleId: nextModuleId(),
      type: MODULE_TYPES[s % MODULE_TYPES.length],
      dimensions: {
        x: 2 + (s % 3),
        y: 2.4,
        z: 0.15 + (s % 2) * 0.1,
      },
      roomId: `IfcSpace_${1000 + s}`,
      unitScale: 'METRE',
    };
  });
}

/** Project as returned to clients, with a live design count. */
function projectView(p: Project): Project {
  const count = [...designs.values()].filter(
    (d) => d.projectId === p.projectId,
  ).length;
  return { ...p, designCount: count };
}

/**
 * Design as returned to clients. Status is derived from elapsed time. The
 * extracted modules are surfaced only once processing is COMPLETE.
 */
function designView(d: StoredDesign): Design {
  // A stored ERROR is terminal; otherwise status is derived from elapsed time.
  const status = d.status === 'ERROR' ? 'ERROR' : statusFor(d.startedAt);
  return {
    designId: d.designId,
    projectId: d.projectId,
    name: d.name,
    fileName: d.fileName,
    fileSize: d.fileSize,
    status,
    uploadTime: d.uploadTime,
    // Count reflects only what's exposed: modules appear once COMPLETE. Eager
    // mode ships the array too; a future lazy variant could drop it and keep this.
    moduleCount: status === 'COMPLETE' ? d.modules.length : 0,
    modules: status === 'COMPLETE' ? d.modules : [],
  };
}

export const db = {
  listProjects(): Project[] {
    return [...projects.values()]
      .map(projectView)
      .sort((a, b) => b.createdTime.localeCompare(a.createdTime));
  },

  getProject(projectId: string): Project | undefined {
    const p = projects.get(projectId);
    return p ? projectView(p) : undefined;
  },

  /** Name uniqueness check for create (names are display-only but kept unique). */
  projectNameExists(name: string): boolean {
    return [...projects.values()].some((p) => p.name === name);
  },

  createProject(name: string, location: string): Project {
    const project: Project = {
      projectId: nextProjectId(),
      name,
      location,
      designCount: 0,
      createdTime: new Date().toISOString(),
    };
    projects.set(project.projectId, project);
    return projectView(project);
  },

  renameProject(projectId: string, newName: string): Project | undefined {
    const existing = projects.get(projectId);
    if (!existing) return undefined;
    // Identity is the id, so a rename is just a field update — no re-keying and
    // no child designs to re-point (they reference projectId).
    existing.name = newName;
    return projectView(existing);
  },

  listDesigns(projectId: string): Design[] {
    return [...designs.values()]
      .filter((d) => d.projectId === projectId)
      .map(designView)
      .sort((a, b) => b.uploadTime.localeCompare(a.uploadTime));
  },

  getDesign(designId: string): Design | undefined {
    const d = designs.get(designId);
    return d ? designView(d) : undefined;
  },

  getStatus(designId: string): ProcessingStatus | undefined {
    const d = designs.get(designId);
    if (!d) return undefined;
    return d.status === 'ERROR' ? 'ERROR' : statusFor(d.startedAt);
  },

  createDesign(
    projectId: string,
    name: string,
    file: { name: string; size: number },
  ): Design | undefined {
    if (!projects.has(projectId)) return undefined;
    const stored: StoredDesign = {
      designId: nextDesignId(),
      projectId,
      name,
      fileName: file.name,
      fileSize: file.size,
      status: 'PROCESSING',
      uploadTime: new Date().toISOString(),
      startedAt: Date.now(),
      modules: generateModules(file.size),
    };
    designs.set(stored.designId, stored);
    return designView(stored);
  },

  updateDesign(designId: string, patch: DesignPatch): Design | undefined {
    const d = designs.get(designId);
    if (!d) return undefined;
    if (patch.name !== undefined) d.name = patch.name;
    return designView(d);
  },

  updateModule(moduleId: string, patch: ModulePatch): Module | undefined {
    for (const d of designs.values()) {
      const m = d.modules.find((x) => x.moduleId === moduleId);
      if (!m) continue;
      if (patch.type !== undefined) m.type = patch.type;
      if (patch.dimensions !== undefined) m.dimensions = patch.dimensions;
      if (patch.roomId !== undefined) m.roomId = patch.roomId;
      if (patch.unitScale !== undefined) m.unitScale = patch.unitScale;
      return m;
    }
    return undefined;
  },

  deleteDesign(designId: string): boolean {
    return designs.delete(designId);
  },
};

// ---- Seed data so the dashboard isn't empty on first load ----
// Hand-authored to exercise the Project -> Design -> Module[] model: two
// projects, designs across all three statuses, and realistic per-module
// metadata (type, dimensions, room, unit scale) that COMPLETE designs surface.
function seed() {
  const clinic = db.createProject('Riverside Modular Clinic', 'Portland, OR');
  const office = db.createProject('Bay St. Office Retrofit', 'San Francisco, CA');

  const hourAgo = Date.now() - 60 * 60_000;
  const dayAgo = Date.now() - 24 * 60 * 60_000;

  const seedDesign = (d: StoredDesign) => designs.set(d.designId, d);

  // --- Riverside Modular Clinic ---
  seedDesign({
    designId: 'dsn_seed1',
    projectId: clinic.projectId,
    name: 'Ward A Headwall',
    fileName: 'ward-a-headwall.ifc',
    fileSize: 42_500_000,
    status: 'COMPLETE',
    uploadTime: new Date(dayAgo).toISOString(),
    startedAt: dayAgo,
    modules: [
      {
        moduleId: 'mod_seed_wardA_1',
        type: 'Hospital Headwall',
        dimensions: { x: 3.6, y: 1.4, z: 0.2 },
        roomId: 'IfcSpace_WardA_Bed01',
        unitScale: 'METRE',
      },
      {
        moduleId: 'mod_seed_wardA_2',
        type: 'Hospital Headwall',
        dimensions: { x: 3.6, y: 1.4, z: 0.2 },
        roomId: 'IfcSpace_WardA_Bed02',
        unitScale: 'METRE',
      },
      {
        moduleId: 'mod_seed_wardA_3',
        type: 'Bathroom Service Wall',
        dimensions: { x: 2.4, y: 2.7, z: 0.15 },
        roomId: 'IfcSpace_WardA_WC',
        unitScale: 'METRE',
      },
    ],
  });

  seedDesign({
    designId: 'dsn_seed2',
    projectId: clinic.projectId,
    name: 'Corridor Utility Panel',
    fileName: 'corridor-utility.ifc',
    fileSize: 18_900_000,
    status: 'COMPLETE',
    uploadTime: new Date(hourAgo).toISOString(),
    startedAt: hourAgo,
    modules: [
      {
        moduleId: 'mod_seed_corridor_1',
        type: 'Utility Panel',
        dimensions: { x: 1.2, y: 2.7, z: 0.25 },
        roomId: 'IfcSpace_Corridor_L1',
        unitScale: 'METRE',
      },
      {
        moduleId: 'mod_seed_corridor_2',
        type: 'Utility Panel',
        dimensions: { x: 1.2, y: 2.7, z: 0.25 },
        roomId: 'IfcSpace_Corridor_L1',
        unitScale: 'METRE',
      },
    ],
  });

  seedDesign({
    designId: 'dsn_seed3',
    projectId: clinic.projectId,
    name: 'Nurse Station Wall',
    fileName: 'nurse-station.ifc',
    fileSize: 27_300_000,
    status: 'COMPLETE',
    uploadTime: new Date(dayAgo - 10_000).toISOString(),
    startedAt: dayAgo - 10_000,
    modules: [
      {
        moduleId: 'mod_seed_nurse_1',
        type: 'Utility Panel',
        dimensions: { x: 2.8, y: 2.7, z: 0.2 },
        roomId: 'IfcSpace_NurseStn_L1',
        unitScale: 'METRE',
      },
      {
        moduleId: 'mod_seed_nurse_2',
        type: 'Wall Panel',
        dimensions: { x: 1.6, y: 2.7, z: 0.1 },
        roomId: 'IfcSpace_NurseStn_L1',
        unitScale: 'METRE',
      },
    ],
  });

  // --- Bay St. Office Retrofit ---
  seedDesign({
    designId: 'dsn_seed4',
    projectId: office.projectId,
    name: 'Level 3 Partition Set',
    fileName: 'level-3-partitions.ifc',
    fileSize: 33_100_000,
    status: 'COMPLETE',
    uploadTime: new Date(hourAgo).toISOString(),
    startedAt: hourAgo,
    modules: [
      {
        moduleId: 'mod_seed_l3_1',
        type: 'Wall Panel',
        dimensions: { x: 2.4, y: 3.0, z: 0.1 },
        roomId: 'IfcSpace_L3_OpenPlan',
        unitScale: 'METRE',
      },
      {
        moduleId: 'mod_seed_l3_2',
        type: 'Wall Panel',
        dimensions: { x: 2.4, y: 3.0, z: 0.1 },
        roomId: 'IfcSpace_L3_OpenPlan',
        unitScale: 'METRE',
      },
      {
        moduleId: 'mod_seed_l3_3',
        type: 'Wall Panel',
        dimensions: { x: 1.8, y: 3.0, z: 0.1 },
        roomId: 'IfcSpace_L3_MeetingRm',
        unitScale: 'METRE',
      },
    ],
  });

  seedDesign({
    designId: 'dsn_seed5',
    projectId: office.projectId,
    name: 'Server Room Service Wall',
    fileName: 'server-room-service-wall.ifc',
    fileSize: 21_700_000,
    status: 'COMPLETE',
    uploadTime: new Date(dayAgo).toISOString(),
    startedAt: dayAgo,
    modules: [
      {
        moduleId: 'mod_seed_srv_1',
        type: 'Utility Panel',
        dimensions: { x: 2.0, y: 2.7, z: 0.3 },
        roomId: 'IfcSpace_L3_ServerRm',
        unitScale: 'METRE',
      },
      {
        moduleId: 'mod_seed_srv_2',
        type: 'Bathroom Service Wall',
        dimensions: { x: 1.6, y: 2.7, z: 0.15 },
        roomId: 'IfcSpace_L3_WC',
        unitScale: 'METRE',
      },
    ],
  });
}
seed();
