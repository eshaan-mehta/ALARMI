export type ProcessingStatus = 'PROCESSING' | 'COMPLETE' | 'ERROR';

/**
 * A module = one marked modular component the backend extracts from an uploaded
 * IFC design. A single design (one IFC file) can yield many modules (1:N), each
 * carrying its own BIM metadata. See design doc §3.2.3 / Table 5.
 */
export interface Module {
  moduleId: string;
  /** Component type, e.g. "Hospital Headwall". */
  type?: string;
  /** Bounding dimensions in the design's unit scale. */
  dimensions?: { x: number; y: number; z: number };
  /** ID of the room (IfcSpace) the module belongs to. */
  roomId?: string;
  unitScale?: string;
}

/**
 * A "design" = a user-given name + an uploaded IFC file. Once processing
 * completes, the backend attaches the modules extracted from that file.
 */
export interface Design {
  designId: string;
  /** Stable FK to the parent project (identity — the project's name is display-only). */
  projectId: string;
  /** User-supplied name from the upload modal. */
  name: string;
  /** Original uploaded file name, e.g. "hospital-headwall.ifc". */
  fileName: string;
  /** Size in bytes. */
  fileSize: number;
  status: ProcessingStatus;
  /** ISO timestamp. */
  uploadTime: string;
  /** Modules extracted from the file. Empty until status === COMPLETE. */
  modules: Module[];
}

/** Design-level edits (rename). */
export type DesignPatch = Partial<Pick<Design, 'name'>>;

/** Per-module metadata edits. */
export type ModulePatch = Partial<
  Pick<Module, 'type' | 'dimensions' | 'roomId' | 'unitScale'>
>;
