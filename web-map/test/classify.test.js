import test from 'node:test';
import assert from 'node:assert/strict';

import {
  ASSET_TYPES,
  LINE_TYPES,
  classifyGeoJsonFeature,
} from '../src/classify.js';

test('classifies a turbine point from its identifier', () => {
  const result = classifyGeoJsonFeature({
    geometry: { type: 'Point' },
    properties: { externalId: 'KS-101' },
  });

  assert.equal(result.assetType, ASSET_TYPES.WTG);
  assert.equal(result.matchedRule, 'ID_PATTERN');
});

test('does not classify an unrecognised point as a turbine', () => {
  const result = classifyGeoJsonFeature({
    geometry: { type: 'Point' },
    properties: { externalId: 'marker-01' },
  });

  assert.equal(result.assetType, ASSET_TYPES.UNKNOWN);
});

test('classifies a road line and preserves its line type', () => {
  const result = classifyGeoJsonFeature({
    geometry: { type: 'LineString' },
    properties: { externalId: 'NH-27 Road' },
  });

  assert.equal(result.lineType, LINE_TYPES.ROAD);
  assert.equal(result.assetType, ASSET_TYPES.REFERENCE_LINE);
});
