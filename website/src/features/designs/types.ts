export type ProcessingStatus = 'NONE' | 'IN_PROGRESS' | 'COMPLETE';

/**
 * A "design" = a user-given name + an uploaded design file (IFC).
 * The file itself is not rendered in this web UI; we surface its metadata.
 */
export interface Design {
  designId: string;
  projectName: string;
  /** User-supplied name from the upload modal. */
  name: string;
  /** Original uploaded file name, e.g. "hospital-headwall.ifc". */
  fileName: string;
  /** Size in bytes. */
  fileSize: number;
  status: ProcessingStatus;
  /** ISO timestamp. */
  uploadTime: string;

  // ---- Metadata extracted by the backend once status === COMPLETE ----
  moduleType?: string;
  dimensions?: { x: number; y: number; z: number };
  anchorCount?: number;
  roomId?: string;
  unitScale?: string;
}
