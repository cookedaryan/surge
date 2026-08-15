import type { Feature } from 'geojson';

/**
 * One colour per feeder.
 *
 * <p>None of these collide with a pole class (#F59E0B terminal, #EF4444 angle, #8B5CF6 junction,
 * #94A3B8 tangent) or with the reference-line and asset colours (#F472B6, #A8A29E, #38BDF8,
 * #A78BFA), so a route is never mistaken for something drawn on top of it. Ten entries covers
 * realistic feeder counts — the reference project has seven.
 */
export const FEEDER_COLORS = [
  '#10B981', // emerald
  '#3B82F6', // blue
  '#06B6D4', // cyan
  '#84CC16', // lime
  '#6366F1', // indigo
  '#14B8A6', // teal
  '#D946EF', // fuchsia
  '#0891B2', // dark cyan
  '#65A30D', // dark lime
  '#4F46E5' //  dark indigo
];

/** Segments with no feeder share one bucket rather than each taking the next colour. */
export const UNASSIGNED_FEEDER = 'Unassigned';

export function feederNameOf(feature: Feature | undefined | null): string {
  const props = (feature?.properties || {}) as Record<string, unknown>;
  const name = props.feederName || props.feeder_id || props.feeder_name;
  return name ? String(name) : UNASSIGNED_FEEDER;
}

/**
 * Maps every feeder in the collection to exactly one colour.
 *
 * <p>Colour belongs to the feeder, not the segment. The map used to increment a counter per
 * feature, so a feeder built from six segments was drawn in six different colours while unrelated
 * feeders shared one — the palette carried no information about the network.
 *
 * <p>Names are sorted before assignment so a feeder keeps its colour across re-renders, across
 * runs, and regardless of the order features arrive in. Without that, adding one segment could
 * recolour the entire network.
 */
export function assignFeederColors(features: Feature[]): Map<string, string> {
  const assigned = new Map<string, string>();
  [...new Set(features.map(feederNameOf))].sort().forEach((name, i) => {
    assigned.set(name, FEEDER_COLORS[i % FEEDER_COLORS.length]);
  });
  return assigned;
}
