/** Unit-scale helpers shared by the module metadata display and its editor. */

/** The unit scales the backend reports for extracted module dimensions. */
export const UNIT_SCALE_OPTIONS = [
  'METRE',
  'MILLIMETRE',
  'CENTIMETRE',
  'FOOT',
  'INCH',
];

/** Metres per 1 of each unit — the basis for converting dimensions between units. */
export const METRES_PER_UNIT: Record<string, number> = {
  METRE: 1,
  MILLIMETRE: 0.001,
  CENTIMETRE: 0.01,
  FOOT: 0.3048,
  INCH: 0.0254,
};

/** Short label for a unit, e.g. "cm" — falls back to the raw value if unknown. */
export const UNIT_ABBR: Record<string, string> = {
  METRE: 'm',
  MILLIMETRE: 'mm',
  CENTIMETRE: 'cm',
  FOOT: 'ft',
  INCH: 'in',
};

/** Abbreviation for a unit scale, or '' if none is set. */
export function unitAbbr(unit: string | undefined): string {
  if (!unit) return '';
  return UNIT_ABBR[unit] ?? unit.toLowerCase();
}

/**
 * A module's bounding dimensions as one display string, e.g. "2 × 2.4 × 0.15 m",
 * or null when the module has none. Takes the parts rather than a Module so the
 * unit helpers stay independent of the API types.
 */
export function formatDimensions(
  dimensions: { x: number; y: number; z: number } | undefined,
  unitScale: string | undefined,
): string | null {
  if (!dimensions) return null;
  const { x, y, z } = dimensions;
  const unit = unitAbbr(unitScale);
  return `${x} × ${y} × ${z}${unit ? ` ${unit}` : ''}`;
}

/** Convert a length from one unit to another; trims float noise to 4 decimals. */
export function convertLength(value: number, from: string, to: string): number {
  const f = METRES_PER_UNIT[from];
  const t = METRES_PER_UNIT[to];
  if (!f || !t) return value;
  return Math.round((value * f) / t * 1e4) / 1e4;
}
