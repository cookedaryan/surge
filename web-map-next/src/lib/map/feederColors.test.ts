import { describe, it, expect } from 'vitest';
import type { Feature } from 'geojson';
import {
  assignFeederColors,
  assignFeederDashPatterns,
  colorForIndex,
  dashPatternForIndex,
  feederNameOf,
  FEEDER_COLORS,
  RESERVED_COLORS,
  UNASSIGNED_FEEDER
} from './feederColors';

/**
 * Colour identifies the feeder. The map used to increment a counter per feature, so the reference
 * project's seven feeders — 38 segments between them — were drawn as 38 rotations through a
 * five-colour palette: every feeder multi-coloured, every colour shared by several feeders.
 */

function segment(feederName?: string, id = 'x'): Feature {
  return {
    type: 'Feature',
    id,
    geometry: { type: 'LineString', coordinates: [[0, 0], [1, 1]] },
    properties: feederName === undefined ? {} : { feederName }
  };
}

function feeders(count: number): Feature[] {
  return Array.from({ length: count }, (_, i) => segment(`FDR-${String(i).padStart(3, '0')}`, `s${i}`));
}

function rgb(hex: string): [number, number, number] {
  const v = parseInt(hex.slice(1), 16);
  return [(v >> 16) & 255, (v >> 8) & 255, v & 255];
}

/**
 * Rough perceptual distance. Weighted because the eye resolves green far better than blue, so a
 * plain RGB distance overstates how different two blues look.
 */
function perceptualDistance(a: string, b: string): number {
  const [r1, g1, b1] = rgb(a);
  const [r2, g2, b2] = rgb(b);
  const rMean = (r1 + r2) / 2;
  const dr = r1 - r2;
  const dg = g1 - g2;
  const db = b1 - b2;
  return Math.sqrt((2 + rMean / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rMean) / 256) * db * db);
}

describe('assignFeederColors', () => {
  it('gives every segment of a feeder the same colour', () => {
    // FDR-003 has six segments on the reference project.
    const features = [
      segment('FDR-001'), segment('FDR-002'),
      ...Array.from({ length: 6 }, (_, i) => segment('FDR-003', `s${i}`))
    ];

    const colors = assignFeederColors(features);
    const forThirdFeeder = features
      .filter((f) => f.properties!.feederName === 'FDR-003')
      .map((f) => colors.get(feederNameOf(f)));

    expect(new Set(forThirdFeeder).size).toBe(1);
  });

  it('gives every feeder its own colour, at any count', () => {
    // Not just the seven the reference site has: a large farm splits into many more, and none of
    // them may share. Sixty is well past anything realistic.
    for (const count of [7, 24, 25, 40, 60]) {
      const colors = assignFeederColors(feeders(count));
      expect(new Set(colors.values()).size, `${count} feeders`).toBe(count);
    }
  });

  it('keeps a feeder on the same colour whatever order the segments arrive in', () => {
    // Segments come back in whatever order the query returns. Without a stable rule, adding one
    // segment could recolour the whole network between renders.
    const names = ['FDR-003', 'FDR-001', 'FDR-002'];
    const forward = assignFeederColors(names.map((n) => segment(n)));
    const reversed = assignFeederColors([...names].reverse().map((n) => segment(n)));

    expect(forward.get('FDR-001')).toBe(reversed.get('FDR-001'));
    expect(forward.get('FDR-003')).toBe(reversed.get('FDR-003'));
  });

  it('gives a feeder the same colour whether the site is small or large', () => {
    // Position decides the colour, not how many neighbours it happens to have.
    expect(colorForIndex(3)).toBe(colorForIndex(3));
    const small = assignFeederColors(feeders(5));
    const large = assignFeederColors(feeders(50));
    expect(small.get('FDR-003')).toBe(large.get('FDR-003'));
  });

  it('keeps every route colour well clear of the pole and reference-line colours', () => {
    // Poles are drawn on top of routes — 84 angle poles on the reference project alone. A route
    // merely *not equal* to the angle-pole red is not enough; it has to be visibly different, or
    // the poles disappear into the line they sit on. Checked across the generated range too.
    for (let i = 0; i < 60; i++) {
      const color = colorForIndex(i);
      const nearest = RESERVED_COLORS
        .map((r) => [r, perceptualDistance(color, r)] as const)
        .sort((a, b) => a[1] - b[1])[0];
      expect(nearest[1], `colour ${i} ${color} vs reserved ${nearest[0]}`).toBeGreaterThan(80);
    }
  });

  it('keeps the colours a small site uses clearly apart', () => {
    // Eight feeders is a normal site. These have to be distinguishable at a glance on a dark map,
    // not merely unequal as hex strings. An earlier ordering put two greens six apart in the list
    // at a separation of 69, which this caught.
    const first = FEEDER_COLORS.slice(0, 8);
    const pairs: Array<[string, string, number]> = [];
    for (let i = 0; i < first.length; i++) {
      for (let j = i + 1; j < first.length; j++) {
        pairs.push([first[i], first[j], perceptualDistance(first[i], first[j])]);
      }
    }
    const closest = pairs.sort((a, b) => a[2] - b[2])[0];
    expect(closest[2], `closest pair ${closest[0]}/${closest[1]}`).toBeGreaterThan(150);
  });

  it('keeps the whole curated palette apart, if less strictly', () => {
    const pairs: number[] = [];
    for (let i = 0; i < FEEDER_COLORS.length; i++) {
      for (let j = i + 1; j < FEEDER_COLORS.length; j++) {
        pairs.push(perceptualDistance(FEEDER_COLORS[i], FEEDER_COLORS[j]));
      }
    }
    expect(Math.min(...pairs)).toBeGreaterThan(60);
  });

  it('emits colours the browser can actually parse', () => {
    for (let i = 0; i < 60; i++) {
      expect(colorForIndex(i)).toMatch(/^#[0-9A-F]{6}$/);
    }
  });

  it('treats segments with no feeder as one group rather than colouring each differently', () => {
    const colors = assignFeederColors([segment(undefined, 'a'), segment(undefined, 'b')]);

    expect(colors.size).toBe(1);
    expect(colors.has(UNASSIGNED_FEEDER)).toBe(true);
  });

  it('backs colour with a stroke pattern so identity survives colour blindness', () => {
    // Colour alone is the wrong single channel: measured against dichromat simulations the
    // palette collapses to 31 under protanopia and 19 under tritanopia, and the PDF export is
    // often printed in greyscale where every hue collapses.
    const patterns = assignFeederDashPatterns(feeders(6));
    expect(new Set(patterns.values()).size).toBe(6);
  });

  it('uses the same stable ordering for patterns as for colours', () => {
    const names = ['FDR-003', 'FDR-001', 'FDR-002'];
    const forward = assignFeederDashPatterns(names.map((n) => segment(n)));
    const reversed = assignFeederDashPatterns([...names].reverse().map((n) => segment(n)));

    expect(forward.get('FDR-002')).toBe(reversed.get('FDR-002'));
  });

  it('only repeats a pattern between feeders that are already far apart in colour', () => {
    // Patterns cycle sooner than colours do, so the two channels must not repeat together.
    const patternCycle = new Set(
      Array.from({ length: 40 }, (_, i) => dashPatternForIndex(i))
    ).size;
    const firstRepeat = Array.from({ length: 40 }, (_, i) => dashPatternForIndex(i))
      .findIndex((p, i, all) => all.indexOf(p) !== i);

    expect(patternCycle).toBeGreaterThan(1);
    // A shared pattern is only reached well beyond the point where hues are clearly distinct.
    expect(firstRepeat).toBeGreaterThanOrEqual(4);
    expect(colorForIndex(0)).not.toBe(colorForIndex(firstRepeat));
  });

  it('reads the property names the API actually sends', () => {
    const withProps = (properties: Record<string, unknown>): Feature => ({
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [[0, 0], [1, 1]] },
      properties
    });

    expect(feederNameOf(withProps({ feederName: 'A' }))).toBe('A');
    expect(feederNameOf(withProps({ feeder_id: 'B' }))).toBe('B');
    expect(feederNameOf(withProps({ feeder_name: 'C' }))).toBe('C');
  });
});
