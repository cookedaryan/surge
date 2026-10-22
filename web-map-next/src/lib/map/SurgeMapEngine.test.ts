import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import L from 'leaflet';
import type { Feature, FeatureCollection, Geometry } from 'geojson';
import { SurgeMapEngine } from './SurgeMapEngine';

/**
 * Popup text comes from imported survey files, and Leaflet writes a string popup straight into
 * innerHTML. A placemark named `<img onerror=…>` therefore ran script in every browser that opened
 * its popup — with the session token in localStorage, that is account takeover.
 *
 * Every popup-producing path is fed a hostile value in every property it reads, and none may
 * surface it as markup.
 */

const HOSTILE = '<img src=x onerror=alert(1)>';

const ALL_PROPS = {
  externalId: HOSTILE,
  id: HOSTILE,
  name: HOSTILE,
  status: HOSTILE,
  towerType: HOSTILE,
  lineSection: HOSTILE,
  lineType: 'ROAD',
  voltageKv: HOSTILE,
  crossingConstraint: true,
  feederName: HOSTILE,
  segmentId: HOSTILE,
  poleId: HOSTILE,
  poleRole: 'terminal',
  recommendedPoleType: HOSTILE,
  parcelId: HOSTILE,
  ownerName: HOSTILE,
  restrictionType: HOSTILE,
  bufferMeters: HOSTILE,
  cableTypeId: HOSTILE,
  cableParallelCount: 2,
  cableRequiredCurrentA: HOSTILE,
  cableEffectiveAmpacityA: HOSTILE,
  conductorCost: HOSTILE,
  costCurrency: HOSTILE,
  poleCount: HOSTILE,
  capacityMw: HOSTILE,
  acquisitionCostPerM2: HOSTILE,
  [HOSTILE]: HOSTILE
};

const point: Geometry = { type: 'Point', coordinates: [69.82, 23.23] };
const line: Geometry = {
  type: 'LineString',
  coordinates: [
    [69.82, 23.23],
    [69.83, 23.24]
  ]
};
const polygon: Geometry = {
  type: 'Polygon',
  coordinates: [
    [
      [69.82, 23.23],
      [69.83, 23.23],
      [69.83, 23.24],
      [69.82, 23.23]
    ]
  ]
};

const collection = (geometry: Geometry, properties: Record<string, unknown> = ALL_PROPS): FeatureCollection => ({
  type: 'FeatureCollection',
  features: [{ type: 'Feature', id: HOSTILE, geometry, properties } as Feature]
});

function popupHtml(layer: L.Layer): string[] {
  if (layer instanceof L.LayerGroup) {
    const out: string[] = [];
    layer.eachLayer((child) => out.push(...popupHtml(child)));
    return out;
  }
  const content = layer.getPopup()?.getContent();
  return typeof content === 'string' ? [content] : [];
}

describe('SurgeMapEngine popups', () => {
  let engine: SurgeMapEngine;

  beforeEach(() => {
    // The engine asks Leaflet for a canvas renderer; jsdom has no 2D context to give it.
    const noopContext = new Proxy({}, { get: () => () => undefined, set: () => true });
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(noopContext as never);
    document.body.innerHTML = '<div id="map" style="width:400px;height:300px"></div>';
    engine = new SurgeMapEngine('map');
  });

  afterEach(() => {
    engine.map.remove();
  });

  const cases: Array<[string, () => string[]]> = [
    ['turbines', () => (engine.renderWtgs(collection(point)), popupHtml(engine.layers.wtgs))],
    ['substations', () => (engine.renderSubstations(collection(point)), popupHtml(engine.layers.substations))],
    ['towers', () => (engine.renderTowers(collection(point)), popupHtml(engine.layers.towers))],
    ['reference lines', () => (engine.renderReferenceLines(collection(line)), popupHtml(engine.layers.referenceLines))],
    ['routes', () => (engine.renderRoutes(collection(line)), popupHtml(engine.layers.routes))],
    [
      'poles',
      () => (
        engine.renderPoles(collection(point)),
        [engine.layers.polesTerminal, engine.layers.polesIntermediate, engine.layers.polesAngle, engine.layers.polesJunction]
          .flatMap(popupHtml)
      )
    ],
    ['parcels', () => (engine.renderParcels(collection(polygon)), popupHtml(engine.layers.parcels))],
    ['restricted areas', () => (engine.renderRestrictedAreas(collection(polygon)), popupHtml(engine.layers.restricted))],
    ['generic imported points', () => (engine.renderImportedGeoJson(collection(point)), popupHtml(engine.layers.imported))],
    [
      // Property *names* are rendered too, and are just as attacker-controlled as values.
      'generic imported polygons',
      () => (
        engine.renderImportedGeoJson(collection(polygon, { [HOSTILE]: HOSTILE })),
        popupHtml(engine.layers.imported)
      )
    ]
  ];

  it.each(cases)('escapes hostile text in %s popups', (_name, render) => {
    const popups = render();

    expect(popups.length, 'the layer produced no popup, so the test proved nothing').toBeGreaterThan(0);
    for (const html of popups) {
      expect(html).not.toContain('<img');
      expect(html).toContain('&lt;img');
    }
  });
});
