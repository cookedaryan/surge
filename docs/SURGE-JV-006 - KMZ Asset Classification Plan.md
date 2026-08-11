# SURGE-JV-006 — KMZ Asset Classification

**Problem:** every placemark in an imported KMZ was persisted as a WTG, including evacuation towers.
**Status:** implemented. Java backend, PostGIS schema, web-map frontend. No Python engine changes.
**Reference file:** `Uravakonda Estimated PCN route -1.kmz`

---

## 1. Root cause

Three separate defects compounded into the observed behaviour.

### 1.1 The converter threw away the classification signal

`KmzGeoJsonConverter.extractPointFeatures()` wrote the placemark `<name>` into `properties.externalId`
and copied `ExtendedData` verbatim. It never emitted an `assetType`, and it used a flat
`getElementsByTagName("Placemark")` scan that discarded the enclosing `<Folder>` names entirely — the
single most reliable signal in a survey export.

### 1.2 The importer defaulted everything to WTG

`AssetService.importGeoJson()`:

```java
boolean isSubstation = assetType != null && assetType.toLowerCase().contains("substation");
if (isSubstation) { ... } else { /* WTG */ }
```

A binary test with an `else` fallback. Since the converter never set `assetType`, `isSubstation` was
always false and **100% of KMZ placemarks took the WTG branch**, each picking up a fabricated
`capacityMw = 3.000` that made the bad data look plausible downstream.

### 1.3 There was nowhere for a tower to go

The schema had `wtg_locations` and `substations` only. No entity, no table, no DTO, no map layer, no
`AssetType` concept anywhere in the codebase.

### Blast radius

`OptimizationJobService.buildWtgGeoJson()` reads `wtgLocationRepository` and ships the result to the
Python engine. Towers arrived as 3.0 MW turbines, inflating `feeder_count` in `group_wtgs()` and
corrupting the MST in `build_feeder_mst()`. The optimiser output was silently wrong, not just the map.

The frontend had the same defect independently: `app.js` auto-detect also ended in
`else { allWtgs.push(feat) }`.

---

## 2. What the reference file actually contains

Measured, not assumed:

| Metric | Value |
|---|---|
| Placemarks | 1064 |
| Point placemarks | 903 |
| **Distinct assets** | **303** |
| Duplicates | 600 |
| Non-point skipped | 134 LineString, 27 Polygon |
| ExtendedData entries | **0** |

Three findings changed the design:

**The file nests a copy of its own tree inside itself, three times over.** Subtrees appear under
`PSS Land final / My Places / …` and `Cancel Location / My Places / …`. Without deduplication each
asset is persisted three times under suffixed IDs (`KS67_S1`, `KS67_S1-1`, `KS67_S1-2`).

**There is no ExtendedData at all.** Capacity, height and tower type cannot be read from the file.
The folder name and the placemark name are the *only* signals available, which is why folder-aware
parsing was mandatory rather than a nice-to-have.

**Turbine status lives in the folder name.** `Approved`, `Cancel Location`, `Low AEP`, `Registration`,
`proposed`, `To be Shifting`. Only 38 of 99 turbine locations are eligible for optimisation — the
other 61 are cancelled, low-AEP or awaiting relocation.

Observed naming:

| Asset | Pattern | Examples |
|---|---|---|
| Turbines | `KS` / `SUR` / `VAJ` + digits, messy separators | `KS67_S1`, `KS-38_S3`, `KS 24 S2`, `KS42P_S2`, `SUR0001_S2`, `VAJ051_S1` |
| Towers | `<section>/<index>`, angle points, gantry | `2/1`, `15/11`, `20/12`, `AP1`, `AP34`, `GANTRY` |
| Substations | PSS / voltage class | `Mopidi PSS`, `Ragulapadu 220/11KV Substation` |
| Geotechnical | BH / CBR / ERT / PLT / TP / TRT | `BH-1`, `CBR-2`, `ERT-5` |

---

## 3. Decisions taken

| Decision | Choice |
|---|---|
| Storage | Dedicated `evacuation_towers` table + entity |
| Classification | Ordered rule chain + UI confirm step before persist |
| Optimiser role | Fixed existing assets — stored and rendered, excluded from grouping/MST |

---

## 4. Implementation

### 4.1 Classification core

- `domain/AssetType` — `WTG`, `SUBSTATION`, `EVACUATION_TOWER`, `SURVEY_POINT`, `UNKNOWN`, with alias
  handling (`TOWER`, `PSS`, `TURBINE`, …).
- `domain/WtgStatus` — six lifecycle states, each carrying `isOptimisable()`. `APPROVED`,
  `REGISTRATION` and `PROPOSED` feed the optimiser; `CANCELLED`, `LOW_AEP`, `TO_BE_SHIFTED` and
  `UNKNOWN` do not.
- `service/classification/AssetClassificationRules` — folder keywords, ID regexes and status keywords
  in one configurable record, defaults derived from the reference file.
- `service/classification/AssetClassifier` — ordered chain, first match wins:
  1. explicit `assetType` / `type` / `layer` property;
  2. KML folder, **evaluated one path segment at a time from the leaf upward** (this is what makes the
     self-nesting harmless — the nearest enclosing folder wins);
  3. ID pattern;
  4. `UNKNOWN`. **Never WTG.**

  Within the folder and ID passes, survey is tested before substation so
  `Anantapur PSS_Borehole.kmz` resolves to a survey folder rather than a substation.
- `normaliseId()` collapses separator noise so `KS-38_S3`, `KS 38 S3` and `ks38s3` dedupe as one asset.
- Every result carries the rule that fired and the evidence that matched, for display in the preview.

### 4.2 Converter

`KmzGeoJsonConverter.convert()` replaces the flat scan with a depth-first walk that keeps folder names
on a stack, emitting `kmlFolder` (leaf) and `kmlFolderPath` (full path, joined with `" / "` so a bare
slash in `220/11KV` is not read as a separator). Placemarks are deduplicated on normalised name plus
coordinates to 7 decimal places. Returns a `KmzConversionResult` with placemark, duplicate and
skipped-geometry counts. `convertToFeatureCollection()` is retained as a delegating shim.

### 4.3 Schema — `V4__create_evacuation_towers_and_asset_metadata.sql`

- `evacuation_towers` — `tower_type`, `height_m`, `line_section`, `source_folder`, WGS84 point, GIST
  index, unique `(project_id, external_id)`. No `capacity_mw NOT NULL`, which is exactly why towers
  could not be shoehorned into `wtg_locations`.
- `wtg_locations.status` — backfilled `APPROVED` so existing projects keep working, then the column
  default flips to `UNKNOWN` so anything imported from here on must be classified explicitly.
- `wtg_locations.source_folder`, `substations.source_folder` — provenance for audit and
  re-classification.

### 4.4 Import — preview then commit

| Endpoint | Behaviour |
|---|---|
| `POST /assets/kmz/preview` | Classifies and stages; **persists nothing**. Returns per-feature type, status, matched rule and evidence, plus counts and duplicate/skip statistics. |
| `POST /assets/import/commit` | Persists a staged import, applying `overrides`, `statusOverrides` and `defaultCapacityMw`. |
| `POST /assets/kmz` | Retained. Now **rejects** unclassifiable features with a 400 listing offending IDs instead of defaulting them to turbines. |
| `GET /towers` | Lists evacuation towers. |

`AssetImportStagingService` holds staged imports for 30 minutes, keyed by `importId` and pinned to the
project so a handle cannot be replayed elsewhere.

### 4.5 Optimiser isolation

`OptimizationJobService` filters on `status.isOptimisable()` before building the Python payload, and
fails with a distinct message when a project has turbines but none eligible. Towers are structurally
excluded — they no longer live in the table that service reads.

### 4.6 Frontend

- `src/classify.js` — the same rule chain in the browser, so drag-and-drop rendering and server
  persistence cannot disagree. The `else → WTG` fallback in `app.js` auto-detect is gone; unmatched
  features are surfaced in a toast instead.
- Tower layer, lattice-tower icon, `chkShowTowers` toggle, tower count card.
- Turbines excluded by status render dimmed with a dashed border, and the WTG count shows
  `optimisable / total` when they differ — the gap between "on the map" and "in the model" is visible.
- Import preview modal: per-feature type dropdown, bulk apply, default-capacity input, warning banner
  for unclassified features, Confirm → commit.

---

## 5. Verification

The rule table was ported to a harness and run against the real file
(`outputs/verify_rules.py`), then cross-checked against the browser module:

```
Placemarks 1064 → 903 points → 600 duplicates removed → 303 distinct assets

EVACUATION_TOWER  174        Turbine status:  CANCELLED     48   excluded
WTG                99                         APPROVED      23   → optimiser
SURVEY_POINT       15                         REGISTRATION  10   → optimiser
SUBSTATION         10                         LOW_AEP        8   excluded
UNKNOWN             5                         PROPOSED       5   → optimiser
                                              TO_BE_SHIFTED  5   excluded
                                              optimisable   38
PASS — no turbine/tower/borehole cross-contamination
PASS — browser rules agree with backend rules exactly
```

The 5 unresolved features are `Penna River`, `P.A.B.R Reservoir` and three `Feeder 4` labels — map
annotations, not assets. They surface in the preview for a human decision rather than becoming
turbines.

### Java test coverage added

- `AssetClassifierTest` — 40+ cases from the real file: ID patterns per asset class, folder precedence
  over ID, survey-before-substation ordering, leaf-folder-wins under self-nesting, explicit-property
  override, status derivation, ID normalisation, and a regression guard asserting unmatched
  placemarks resolve to `UNKNOWN` and never `WTG`.
- `KmzGeoJsonConverterTest` — folder path propagation, deduplication across nested copies including
  separator-noise variants, non-point geometry reporting.
- `AssetServiceTest` — three-way split with tower metadata, status derivation and optimisable flags,
  rejection of unclassifiable features, preview-persists-nothing plus commit-applies-overrides.
- `OptimizationJobServiceTest` — only optimisable turbines reach the Python client; a project whose
  turbines are all excluded fails with a distinct message.

### Not yet run

The Java build could not be executed in this environment (JDK 11 available, project targets 21).
Run before merging:

```powershell
cd backend-java
.\mvnw.cmd test
cd ..\web-map
npm run build
```

---

## 6. Data cleanup

Existing projects hold towers in `wtg_locations` with a fabricated 3.0 MW capacity. Options, cheapest
first:

1. **Re-import into a fresh project** — data is early-stage; simplest and safest.
2. One-off SQL migrating rows whose `external_id !~* '^(KS|SUR|VAJ)'` into `evacuation_towers` and
   dropping the fake capacity. Ship as a repeatable Flyway script only if production data must be kept.

Note that V4 backfills existing turbine rows as `APPROVED`, so previously working projects continue to
optimise unchanged.

---

## 7. Follow-ups

- **Turbine capacity is still a default.** The file carries none; the preview lets the user set one
  value for the whole import. Per-turbine capacity needs a separate source (a spreadsheet or the
  supplier's layout sheet).
- **A/B/C/D in the `ATP-II PGCIL` folder classify as substations.** They are most likely land-parcel
  corner markers. The preview allows reclassification; if this recurs, add a rule.
- **134 LineStrings and 27 Polygons are skipped.** The HT lines, PCN route, roads, river and PSS land
  boundary are real data that currently import nowhere. Routing them to the parcels and
  restricted-areas importers is a natural next task.
- **Tower height and type are null.** Derivable from the section/index pattern only for structure
  type; heights need a source.
- Commit a small redacted KMZ fixture to `backend-java/src/test/resources/kmz/` — the reference file
  is customer data and 677 KB.
