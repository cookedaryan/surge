/**
 * Asset classification rules, mirroring com.power.surge.service.classification.AssetClassifier.
 *
 * The browser needs the same rules as the backend so that locally rendered drag-and-drop imports
 * agree with what the server persists. Keep the two in sync: if a pattern changes here it must
 * change in AssetClassificationRules.java, and vice versa.
 */

export const ASSET_TYPES = {
  WTG: 'WTG',
  SUBSTATION: 'SUBSTATION',
  EVACUATION_TOWER: 'EVACUATION_TOWER',
  SURVEY_POINT: 'SURVEY_POINT',
  PARCEL: 'PARCEL',
  RESTRICTED_AREA: 'RESTRICTED_AREA',
  REFERENCE_LINE: 'REFERENCE_LINE',
  UNKNOWN: 'UNKNOWN'
};

export const ASSET_TYPE_LABELS = {
  WTG: 'Wind Turbine',
  SUBSTATION: 'Substation',
  EVACUATION_TOWER: 'Evacuation Tower',
  SURVEY_POINT: 'Survey Point',
  PARCEL: 'Land Parcel',
  RESTRICTED_AREA: 'Restricted Area',
  REFERENCE_LINE: 'Reference Line',
  UNKNOWN: 'Unclassified'
};

const FOLDER_KEYWORDS = {
  SURVEY_POINT: ['borehole', 'geotech', 'soil investigation', 'survey point'],
  EVACUATION_TOWER: ['gantry', 'tower', 'angle point', 'evacuation', 'transmission', 'ht line', 'ehv'],
  SUBSTATION: ['pss', 'substation', 's/s', 'switchyard', 'pgcil', 'ctu'],
  WTG: ['turbine', 'wtg', 'wec', 'approved', 'proposed', 'registration',
        'low aep', 'cancel', 'shifting', 'micrositing', 'micro siting']
};

// Evaluated in this order; survey before substation so "Anantapur PSS_Borehole.kmz" is a survey folder.
const TYPE_ORDER = ['SURVEY_POINT', 'EVACUATION_TOWER', 'SUBSTATION', 'WTG'];

const ID_PATTERNS = {
  WTG: /^(KS|SUR|VAJ)[\s_-]*\d+/i,
  EVACUATION_TOWER: /^(\d+\s*\/\s*\d+|AP[\s_-]*\d+|GANTRY|TOWER[\s_-]*\d+)$/i,
  SUBSTATION: /(\bPSS\b|SUBSTATION|\bS\/S\b|SWITCHYARD|\d+\s*\/\s*\d+\s*KV)/i,
  SURVEY_POINT: /^(BH|CBR|ERT|PLT|TP|TRT)[\s_-]*\d+$/i
};

const STATUS_RULES = [
  ['cancel location', 'CANCELLED'],
  ['to be shifting', 'TO_BE_SHIFTED'],
  ['low aep', 'LOW_AEP'],
  ['registration', 'REGISTRATION'],
  ['approved', 'APPROVED'],
  ['proposed', 'PROPOSED'],
  ['shifting', 'TO_BE_SHIFTED'],
  ['cancel', 'CANCELLED']
];

export const OPTIMISABLE_STATUSES = ['APPROVED', 'REGISTRATION', 'PROPOSED'];

const IGNORED_SEGMENTS = new Set([
  'nom du document', 'sheet1', 'document', 'folder', 'line features', 'untitled'
]);

// "My Places" marks an embedded copy of another document. Folders above it belong to a different
// tree and must not classify anything below it.
const NESTING_BOUNDARIES = new Set(['my places']);

/** Splits "A / B / C" leaf-first. A bare slash inside a name ("220/11KV") is not a separator. */
function folderSegmentsLeafFirst(folderPath) {
  if (!folderPath) return [];
  const out = [];
  const parts = folderPath.split(/\s+\/\s+/).map(s => s.trim()).reverse();
  for (const segment of parts) {
    if (!segment) continue;
    const lower = segment.toLowerCase();
    if (NESTING_BOUNDARIES.has(lower)) break;
    if (IGNORED_SEGMENTS.has(lower)) continue;
    out.push(segment);
  }
  return out;
}

function statusFor(assetType, segments) {
  if (assetType !== ASSET_TYPES.WTG) return 'UNKNOWN';
  for (const segment of segments) {
    const lower = segment.toLowerCase();
    for (const [keyword, status] of STATUS_RULES) {
      if (lower.includes(keyword)) return status;
    }
  }
  return 'UNKNOWN';
}

/**
 * Resolves an asset type using the same ordered chain as the backend:
 * explicit property -> KML folder (leaf first) -> ID pattern -> UNKNOWN.
 *
 * Never falls back to WTG. Defaulting unmatched placemarks to turbines is what caused
 * evacuation towers to be imported as 3 MW generators.
 */
export function classifyFeature(properties = {}) {
  const externalId = (properties.externalId || properties.name || properties.id || '').toString().trim();
  const folderPath = properties.kmlFolderPath || properties.kmlFolder || '';
  const segments = folderSegmentsLeafFirst(folderPath);

  const explicit = normaliseType(properties.assetType || properties.type || properties.layer);
  if (explicit !== ASSET_TYPES.UNKNOWN) {
    return { assetType: explicit, status: statusFor(explicit, segments), matchedRule: 'EXPLICIT_PROPERTY', evidence: explicit };
  }

  for (const segment of segments) {
    const lower = segment.toLowerCase();
    for (const type of TYPE_ORDER) {
      if (FOLDER_KEYWORDS[type].some(keyword => lower.includes(keyword))) {
        return { assetType: type, status: statusFor(type, segments), matchedRule: 'KML_FOLDER', evidence: segment };
      }
    }
  }

  if (externalId) {
    for (const type of TYPE_ORDER) {
      if (ID_PATTERNS[type].test(externalId)) {
        return { assetType: type, status: statusFor(type, segments), matchedRule: 'ID_PATTERN', evidence: externalId };
      }
    }
  }

  return { assetType: ASSET_TYPES.UNKNOWN, status: 'UNKNOWN', matchedRule: 'UNRESOLVED', evidence: externalId };
}

export function normaliseType(value) {
  if (!value) return ASSET_TYPES.UNKNOWN;
  const upper = value.toString().trim().toUpperCase().replace(/[\s-]/g, '_');
  if (ASSET_TYPES[upper]) return upper;
  const aliases = {
    TOWER: 'EVACUATION_TOWER', TOWERS: 'EVACUATION_TOWER', EVACUATION_TOWERS: 'EVACUATION_TOWER',
    TRANSMISSION_TOWER: 'EVACUATION_TOWER', GANTRY: 'EVACUATION_TOWER',
    TURBINE: 'WTG', WIND_TURBINE: 'WTG', WEC: 'WTG',
    SUB: 'SUBSTATION', PSS: 'SUBSTATION', SUBSTATIONS: 'SUBSTATION',
    BOREHOLE: 'SURVEY_POINT', GEOTECH: 'SURVEY_POINT', SURVEY: 'SURVEY_POINT'
  };
  return aliases[upper] || ASSET_TYPES.UNKNOWN;
}

export function isOptimisable(status) {
  return OPTIMISABLE_STATUSES.includes(status);
}

/* ==========================================================================
   Linear and area features — mirrors AssetClassifier.classifyLine/classifyPolygon
   ========================================================================== */

export const LINE_TYPES = {
  ROAD: 'ROAD',
  HT_LINE: 'HT_LINE',
  EVACUATION_ROUTE: 'EVACUATION_ROUTE',
  WATERCOURSE: 'WATERCOURSE',
  MEASUREMENT: 'MEASUREMENT',
  UNKNOWN: 'UNKNOWN'
};

export const LINE_TYPE_LABELS = {
  ROAD: 'Road',
  HT_LINE: 'HT / EHV line',
  EVACUATION_ROUTE: 'Evacuation route',
  WATERCOURSE: 'Watercourse',
  MEASUREMENT: 'Measurement artifact',
  UNKNOWN: 'Unclassified line'
};

const LINE_FOLDER_KEYWORDS = {
  WATERCOURSE: ['river', 'canal', 'reservoir', 'water', 'stream'],
  ROAD: ['road', 'highway', 'b.t.road', 'bt road', 'track'],
  EVACUATION_ROUTE: ['pcn', 'evacuation', 'collector', 'feeder'],
  HT_LINE: ['ht line', 'ehv', 'gantry', 'transmission', 'power line']
};
const LINE_FOLDER_ORDER = ['WATERCOURSE', 'ROAD', 'EVACUATION_ROUTE', 'HT_LINE'];

const LINE_NAME_PATTERNS = [
  ['ROAD', /(^\s*(NH|SH)[\s-]*\d+|\bROAD\b|HIGHWAY|\bB\.?T\.?\s*ROAD)/i],
  ['HT_LINE', /(\bHT\s*LINE\b|\d+\s*KV\b|TRANSMISSION)/i],
  ['WATERCOURSE', /(RIVER|CANAL|STREAM|RESERVOIR)/i]
];
// Google Earth measuring-tool leftovers. Only consulted when the folders say nothing — most of the
// PCN route was drawn with that tool, so the name alone is not evidence of noise.
const MEASUREMENT_NAME = /^(PATH\s*MEASURE|POLYLINE|UNTITLED\s*(PATH|LINE|POLYGON))\s*\d*$/i;

const AREA_FOLDER_KEYWORDS = {
  RESTRICTED_AREA: ['river', 'reservoir', 'canal', 'lake', 'tank', 'water', 'forest', 'sanctuary',
                    'reserve', 'wildlife', 'village', 'settlement', 'radar', 'restricted',
                    'exclusion', 'buffer'],
  PARCEL: ['parcel', 'cadastral', 'land', 'acquisition', 'plot', 'survey no']
};
const AREA_NAME_PATTERNS = [
  ['RESTRICTED_AREA', /(RIVER|RESERVOIR|CANAL|\bLAKE\b|\bTANK\b|\bNALA\b|FOREST|SANCTUARY|WILDLIFE|RESERVE|SETTLEMENT|RADAR|BUFFER|SETBACK)/i],
  ['PARCEL', /(\bLAND\b|PARCEL|\bPLOT\b|ACRES?\b|SURVEY\s*NO)/i]
];

export function classifyLine(properties = {}) {
  const name = (properties.externalId || properties.name || '').toString().trim();
  const segments = folderSegmentsLeafFirst(properties.kmlFolderPath || properties.kmlFolder || '');

  const explicit = (properties.lineType || '').toString().toUpperCase();
  if (LINE_TYPES[explicit]) return { lineType: explicit, matchedRule: 'EXPLICIT_PROPERTY' };

  for (const segment of segments) {
    const lower = segment.toLowerCase();
    for (const type of LINE_FOLDER_ORDER) {
      if (LINE_FOLDER_KEYWORDS[type].some(k => lower.includes(k))) {
        return { lineType: type, matchedRule: 'KML_FOLDER', evidence: segment };
      }
    }
  }
  for (const [type, pattern] of LINE_NAME_PATTERNS) {
    if (name && pattern.test(name)) return { lineType: type, matchedRule: 'ID_PATTERN', evidence: name };
  }
  if (name && MEASUREMENT_NAME.test(name)) {
    return { lineType: LINE_TYPES.MEASUREMENT, matchedRule: 'ID_PATTERN', evidence: name };
  }
  return { lineType: LINE_TYPES.UNKNOWN, matchedRule: 'UNRESOLVED', evidence: name };
}

export function classifyPolygon(properties = {}) {
  const name = (properties.externalId || properties.name || '').toString().trim();
  const segments = folderSegmentsLeafFirst(properties.kmlFolderPath || properties.kmlFolder || '');

  const explicit = normaliseType(properties.assetType);
  if (explicit === ASSET_TYPES.PARCEL || explicit === ASSET_TYPES.RESTRICTED_AREA) {
    return { assetType: explicit, matchedRule: 'EXPLICIT_PROPERTY' };
  }

  for (const segment of segments) {
    const lower = segment.toLowerCase();
    for (const type of ['RESTRICTED_AREA', 'PARCEL']) {
      if (AREA_FOLDER_KEYWORDS[type].some(k => lower.includes(k))) {
        return { assetType: type, matchedRule: 'KML_FOLDER', evidence: segment };
      }
    }
  }
  for (const [type, pattern] of AREA_NAME_PATTERNS) {
    if (name && pattern.test(name)) return { assetType: type, matchedRule: 'ID_PATTERN', evidence: name };
  }
  return { assetType: ASSET_TYPES.UNKNOWN, matchedRule: 'UNRESOLVED', evidence: name };
}

/** Dispatches on GeoJSON geometry type. */
export function classifyGeoJsonFeature(feature) {
  const type = feature?.geometry?.type || '';
  const props = feature?.properties || {};
  if (type.includes('Polygon')) return classifyPolygon(props);
  if (type.includes('LineString')) {
    const line = classifyLine(props);
    return {
      assetType: line.lineType === LINE_TYPES.UNKNOWN ? ASSET_TYPES.UNKNOWN : ASSET_TYPES.REFERENCE_LINE,
      lineType: line.lineType,
      matchedRule: line.matchedRule,
      evidence: line.evidence
    };
  }
  return classifyFeature(props);
}
