export interface Project {
  /** Stable unique identifier (survives renames). */
  projectId: string;
  /** Display name; must be unique. Used for routing. */
  name: string;
  /** Physical site/location of the project. */
  location: string;
  /** Number of designs contained in the project. */
  designCount: number;
  /** ISO timestamp. */
  createdTime: string;
}
