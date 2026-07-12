import type { Design, DesignPatch, ProcessingStatus } from '../designs/types';
import type { Project } from '../projects/types';

/**
 * In-memory store backing the MSW mock. Resets on page reload. This exists only
 * to stand in for the real backend; components never import it directly.
 */

let designSeq = 100;
const nextDesignId = () => `dsn_${++designSeq}`;

interface StoredDesign extends Design {
  /** Epoch ms when the upload started, used to derive processing status. */
  startedAt: number;
}

const projects = new Map<string, Project>();
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

/** Metadata revealed only once processing completes. */
function completedMetadata(seed: number): Partial<Design> {
  return {
    moduleType: MODULE_TYPES[seed % MODULE_TYPES.length],
    dimensions: {
      x: 2 + (seed % 3),
      y: 2.4,
      z: 0.15 + (seed % 2) * 0.1,
    },
    anchorCount: 4 + (seed % 5),
    roomId: `IfcSpace_${1000 + seed}`,
    unitScale: 'METRE',
  };
}

/** Project as returned to clients, with a live design count. */
function projectView(p: Project): Project {
  const count = [...designs.values()].filter(
    (d) => d.projectName === p.name,
  ).length;
  return { ...p, designCount: count };
}

/**
 * Design as returned to clients. Status is derived from elapsed time. Metadata
 * defaults to the generated values once COMPLETE, but any field the user has
 * edited (stored on the record) overrides the generated default.
 */
function designView(d: StoredDesign): Design {
  // A stored ERROR is terminal; otherwise status is derived from elapsed time.
  const status = d.status === 'ERROR' ? 'ERROR' : statusFor(d.startedAt);
  const base = status === 'COMPLETE' ? completedMetadata(d.fileSize) : {};
  return {
    designId: d.designId,
    projectName: d.projectName,
    name: d.name,
    fileName: d.fileName,
    fileSize: d.fileSize,
    status,
    uploadTime: d.uploadTime,
    moduleType: d.moduleType ?? base.moduleType,
    dimensions: d.dimensions ?? base.dimensions,
    anchorCount: d.anchorCount ?? base.anchorCount,
    roomId: d.roomId ?? base.roomId,
    unitScale: d.unitScale ?? base.unitScale,
  };
}

export const db = {
  listProjects(): Project[] {
    return [...projects.values()]
      .map(projectView)
      .sort((a, b) => b.createdTime.localeCompare(a.createdTime));
  },

  hasProject(name: string): boolean {
    return projects.has(name);
  },

  createProject(name: string): Project {
    const project: Project = {
      name,
      designCount: 0,
      createdTime: new Date().toISOString(),
    };
    projects.set(name, project);
    return projectView(project);
  },

  renameProject(name: string, newName: string): Project | undefined {
    const existing = projects.get(name);
    if (!existing) return undefined;
    projects.delete(name);
    const renamed: Project = { ...existing, name: newName };
    projects.set(newName, renamed);
    // Re-point child designs at the new project name.
    for (const d of designs.values()) {
      if (d.projectName === name) d.projectName = newName;
    }
    return projectView(renamed);
  },

  listDesigns(projectName: string): Design[] {
    return [...designs.values()]
      .filter((d) => d.projectName === projectName)
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

  createDesign(projectName: string, name: string, file: { name: string; size: number }): Design {
    const stored: StoredDesign = {
      designId: nextDesignId(),
      projectName,
      name,
      fileName: file.name,
      fileSize: file.size,
      status: 'PROCESSING',
      uploadTime: new Date().toISOString(),
      startedAt: Date.now(),
    };
    designs.set(stored.designId, stored);
    return designView(stored);
  },

  updateDesign(designId: string, patch: DesignPatch): Design | undefined {
    const d = designs.get(designId);
    if (!d) return undefined;
    if (patch.name !== undefined) d.name = patch.name;
    if (patch.moduleType !== undefined) d.moduleType = patch.moduleType;
    if (patch.dimensions !== undefined) d.dimensions = patch.dimensions;
    if (patch.anchorCount !== undefined) d.anchorCount = patch.anchorCount;
    if (patch.roomId !== undefined) d.roomId = patch.roomId;
    if (patch.unitScale !== undefined) d.unitScale = patch.unitScale;
    return designView(d);
  },

  deleteDesign(designId: string): boolean {
    return designs.delete(designId);
  },
};

// ---- Seed data so the dashboard isn't empty on first load ----
function seed() {
  db.createProject('Riverside Modular Clinic');
  db.createProject('Bay St. Office Retrofit');
  // Backdate an existing design so it shows as COMPLETE immediately.
  const past = Date.now() - 60_000;
  designSeq++;
  designs.set('dsn_seed1', {
    designId: 'dsn_seed1',
    projectName: 'Riverside Modular Clinic',
    name: 'Ward A Headwall',
    fileName: 'ward-a-headwall.ifc',
    fileSize: 42_500_000,
    status: 'COMPLETE',
    uploadTime: new Date(past).toISOString(),
    startedAt: past,
  });
  // Future startedAt keeps this one in PROCESSING for the whole session (demo).
  const future = Date.now() + 60 * 60_000;
  designs.set('dsn_seed2', {
    designId: 'dsn_seed2',
    projectName: 'Riverside Modular Clinic',
    name: 'Corridor Utility Panel',
    fileName: 'corridor-utility.ifc',
    fileSize: 18_900_000,
    status: 'PROCESSING',
    uploadTime: new Date().toISOString(),
    startedAt: future,
  });
  // An upload that failed processing, to exercise the error state.
  designs.set('dsn_seed3', {
    designId: 'dsn_seed3',
    projectName: 'Riverside Modular Clinic',
    name: 'Nurse Station Wall',
    fileName: 'nurse-station.ifc',
    fileSize: 27_300_000,
    status: 'ERROR',
    uploadTime: new Date(past - 10_000).toISOString(),
    startedAt: past - 10_000,
  });
}
seed();
