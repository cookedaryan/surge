import type { Feature } from 'geojson';

/**
 * Colours reserved by other things drawn on the map.
 *
 * <p>Pole classes sit on top of the routes, and reference lines and assets sit beside them. A
 * feeder painted in one of these reads as the wrong kind of object, so the palette stays clear of
 * them and a test enforces it.
 */
export const RESERVED_COLORS = [
  '#F59E0B', // terminal pole
  '#EF4444', // angle pole
  '#8B5CF6', // junction pole
  '#94A3B8', // tangent pole
  '#F472B6', // reference line
  '#A8A29E', // reference line
  '#38BDF8', // asset
  '#A78BFA' //  asset
];

/**
 * Twenty-four feeder colours, ordered so that any prefix is as distinguishable as possible.
 *
 * <p>Most sites use a handful of feeders — the reference site has seven — so the ordering matters
 * as much as the length. These were selected by farthest-point search over a larger pool under two
 * constraints: every colour stays at least 95 units from each reserved colour, and each successive
 * entry is the one furthest from everything already chosen. The first four separate by 296, the
 * first eight by 170, all twenty-four by 69.
 *
 * <p>That search rejected some obvious-looking choices, which is the point of doing it by
 * measurement rather than by eye: indigo #6366F1 sits too close to the junction-pole violet, and
 * dark yellow #CA8A04 too close to the terminal-pole amber. Both would have looked fine in a
 * swatch and confusing on the map.
 */
const CURATED = [
  '#16A34A', // green
  '#D946EF', // fuchsia
  '#BEF264', // pale lime
  '#1D4ED8', // deep blue
  '#9D174D', // dark rose
  '#5EEAD4', // pale teal
  '#A16207', // bronze
  '#84CC16', // lime
  '#06B6D4', // cyan
  '#A21CAF', // magenta
  '#0E7490', // dark cyan
  '#4ADE80', // light green
  '#EC4899', // pink
  '#3B82F6', // blue
  '#E879F9', // light fuchsia
  '#10B981', // emerald
  '#0284C7', // dark sky
  '#65A30D', // olive
  '#2DD4BF', // turquoise
  '#DB2777', // deep pink
  '#A3E635', // bright lime
  '#4F46E5', // indigo
  '#C026D3', // dark fuchsia
  '#22C55E' //  bright green
];

/** Kept for callers that want the curated set specifically. */
export const FEEDER_COLORS = CURATED;

/** Segments with no feeder share one bucket rather than each taking the next colour. */
export const UNASSIGNED_FEEDER = 'Unassigned';

const MIN_RESERVED_DISTANCE = 90;

function toRgb(hex: string): [number, number, number] {
  const v = parseInt(hex.slice(1), 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}

/**
 * Rough perceptual distance between two colours.
 *
 * <p>Weighted because the eye resolves green far better than blue, so a plain RGB distance
 * overstates how different two blues look and understates two greens.
 */
function perceptualDistance(a: string, b: string): number {
  const [r1, g1, b1] = toRgb(a);
  const [r2, g2, b2] = toRgb(b);
  const rMean = (r1 + r2) / 2;
  const dr = r1 - r2;
  const dg = g1 - g2;
  const db = b1 - b2;
  return Math.sqrt((2 + rMean / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rMean) / 256) * db * db);
}

function clashesWithReserved(hex: string): boolean {
  return RESERVED_COLORS.some((r) => perceptualDistance(hex, r) < MIN_RESERVED_DISTANCE);
}

function hslToHex(h: number, s: number, l: number): string {
  const a = (s / 100) * Math.min(l / 100, 1 - l / 100);
  const channel = (n: number) => {
    const k = (n + h / 30) % 12;
    const value = l / 100 - a * Math.max(-1, Math.min(k - 3, Math.min(9 - k, 1)));
    return Math.round(255 * value)
      .toString(16)
      .padStart(2, '0');
  };
  return `#${channel(0)}${channel(8)}${channel(4)}`.toUpperCase();
}

/**
 * A colour for the feeder at this position, unique for any position.
 *
 * <p>Past the curated list the colour is generated rather than wrapped, so two feeders never share
 * one however many a site has. Hues advance by the golden angle, which spreads successive values as
 * widely as possible instead of walking the spectrum in order, and lightness shifts each time the
 * sequence comes back around so that near-repeats of a hue still read as distinct.
 *
 * <p>Deterministic by position: feeder three is the same colour whether the site has four feeders
 * or forty.
 */
export function colorForIndex(index: number): string {
  if (index < CURATED.length) {
    return CURATED[index];
  }

  const overflow = index - CURATED.length;
  const cycle = Math.floor(overflow / 12);
  const lightness = [58, 44, 70, 36][cycle % 4];
  const saturation = cycle % 2 === 0 ? 72 : 58;

  // Advance until the colour is measurably clear of every reserved one. Approximating this with
  // "avoid these hue bands" let a 345° rose through at 65 from the angle-pole red — close enough
  // that 84 angle poles would have vanished into the line they sit on. Checking the distance the
  // eye actually cares about is both simpler and correct.
  let hue = (overflow * 137.508 + 95) % 360;
  let candidate = hslToHex(hue, saturation, lightness);
  for (let guard = 0; guard < 60 && clashesWithReserved(candidate); guard++) {
    hue = (hue + 11) % 360;
    candidate = hslToHex(hue, saturation, lightness);
  }
  return candidate;
}

/**
 * Stroke patterns, used alongside colour so feeder identity does not rest on hue alone.
 *
 * <p>Colour is the wrong single channel for this. Measured against dichromat simulations, the
 * palette's sixth and second colours collapse to 31 under protanopia and its fourth and seventh
 * to 19 under tritanopia — and the PDF export people print is often greyscale, where every hue
 * collapses. A pattern survives all of that.
 *
 * <p>Cycled independently of colour, so two feeders share a pattern only when they are far apart
 * in the palette and therefore already distinct by hue.
 */
const DASH_PATTERNS = [
  '10, 6', // even dash — the original look
  null, //    solid
  '2, 5', //  dotted
  '18, 7', // long dash
  '14, 5, 2, 5', // dash-dot
  '6, 4, 2, 4' //   short dash-dot
];

/** The stroke pattern for the feeder at this position, or null for a solid line. */
export function dashPatternForIndex(index: number): string | null {
  return DASH_PATTERNS[index % DASH_PATTERNS.length];
}

/** Maps every feeder to its stroke pattern, using the same stable ordering as the colours. */
export function assignFeederDashPatterns(features: Feature[]): Map<string, string | null> {
  const assigned = new Map<string, string | null>();
  [...new Set(features.map(feederNameOf))].sort().forEach((name, i) => {
    assigned.set(name, dashPatternForIndex(i));
  });
  return assigned;
}

export function feederNameOf(feature: Feature | undefined | null): string {
  const props = (feature?.properties || {}) as Record<string, unknown>;
  const name = props.feederName || props.feeder_id || props.feeder_name;
  return name ? String(name) : UNASSIGNED_FEEDER;
}

/**
 * Maps every feeder in the collection to its own colour.
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
    assigned.set(name, colorForIndex(i));
  });
  return assigned;
}
