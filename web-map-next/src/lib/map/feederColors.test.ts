import { describe, it, expect } from 'vitest';
import type { Feature } from 'geojson';
import { assignFeederColors, feederNameOf, FEEDER_COLORS, UNASSIGNED_FEEDER } from './feederColors';

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

describe('assignFeederColors', () => {
  it('gives every segment of a feeder the same colour', () => {
    // FDR-003 has six segments on the reference project.
    const features = [
      segment('FDR-001'), segment('FDR-002'),
      ...Array.from({ length: 6 }, (_, i) => segment('FDR-003', `s${i}`))
    ];

    const colors = assignFeederColors(features);
    const forThirdFeeder = features.filter((f) => f.properties!.feederName === 'FDR-003')
      .map((f) => colors.get(feederNameOf(f)));

    expect(new Set(forThirdFeeder).size).toBe(1);
  });

  it('gives different feeders different colours', () => {
    const names = ['FDR-001', 'FDR-002', 'FDR-003', 'FDR-004', 'FDR-005', 'FDR-006', 'FDR-007'];
    const colors = assignFeederColors(names.map((n) => segment(n)));

    expect(new Set(colors.values()).size).toBe(names.length);
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

  it('never paints a route in a pole or reference-line colour', () => {
    // Poles are drawn over routes. Sharing a colour would make a junction pole look like the
    // route beneath it.
    const reserved = ['#F59E0B', '#EF4444', '#8B5CF6', '#94A3B8', '#F472B6', '#A8A29E', '#38BDF8', '#A78BFA'];
    expect(FEEDER_COLORS.filter((c) => reserved.includes(c))).toEqual([]);
  });

  it('treats segments with no feeder as one group rather than colouring each differently', () => {
    const colors = assignFeederColors([segment(undefined, 'a'), segment(undefined, 'b')]);

    expect(colors.size).toBe(1);
    expect(colors.has(UNASSIGNED_FEEDER)).toBe(true);
  });

  it('wraps predictably when there are more feeders than colours', () => {
    const many = Array.from({ length: FEEDER_COLORS.length + 2 }, (_, i) =>
      segment(`FDR-${String(i).padStart(3, '0')}`));
    const colors = assignFeederColors(many);

    expect(colors.get('FDR-000')).toBe(FEEDER_COLORS[0]);
    expect(colors.get(`FDR-${String(FEEDER_COLORS.length).padStart(3, '0')}`)).toBe(FEEDER_COLORS[0]);
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
