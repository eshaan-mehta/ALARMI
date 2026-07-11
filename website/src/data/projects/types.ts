export interface Project {
  /** Unique identifier and display name. */
  name: string;
  /** Number of designs contained in the project. */
  designCount: number;
  /** ISO timestamp. */
  createdTime: string;
}
