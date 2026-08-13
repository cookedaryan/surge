# Sunday KMZ to 33 kV Network Plan

**Target:** Sunday, 16 August 2026
**Canonical detailed plan:**
[`docs/whats-next.md`](../../docs/whats-next.md)

## Outcome

A user uploads and reviews a KMZ/KML containing WTG coordinates and one
substation. SURGE then uses confirmed project roads, parcels, and restricted
areas to generate several radial collector candidates, electrically screens
them at 33 kV, recommends the best eligible candidate, places preliminary pole
types, and displays the result on the web map.

“Best” means highest ranked among SURGE's bounded, electrically valid
candidates under the disclosed constraints and weights. It is not a global or
construction-ready optimum.

## Input rule

A point-only KMZ is insufficient for road/land avoidance. Roads and land zones
must exist in the same KMZ or a companion reviewed import. Do not invent or
silently download missing layers.

- restricted/no-go land: hard exclusion;
- roads/HT lines/watercourses: buffered soft crossing penalty by default;
- ordinary parcels: soft land-impact penalty; and
- explicitly confirmed no-go feature: hard exclusion.

## Current truth

- Java/web-map KMZ preview, classification, override, commit, and PostGIS
  persistence already exist.
- Python PNC generation, A* routing, 33 kV-compatible Pandapower validation,
  scoring, map-ready output, and pole-placement algorithm already exist.
- Python now accepts avoidance GeoJSON, distinguishes hard exclusions from soft
  penalties, validates endpoints against hard buffers, and returns constraint
  evidence and pole output. V1/V2 coverage is green as part of the full Python
  suite (`460 passed`, with two environment warnings).
- `OptimizationJobService` sends only WTGs/substations to Python.
- Java's legacy response and `RouteService` retain LineStrings but discard rich
  `pnc_pole` Point features.

## Python-owned P0 status

1. **Complete:** hard exclusions and soft road/parcel penalties are distinct.
2. **Complete:** hard-buffer endpoint validation and final route compliance.
3. **Complete:** additive V1/V2 constraint and pole contracts at explicit 33 kV.
4. **Remaining:** deduplicate shared pole endpoints and classify true network
   terminals.
5. **Complete:** stable route and preliminary pole-type GeoJSON.
6. **Complete:** deterministic Python-contract fixture/API tests with the
   provenance limitation documented by SURGE-PY-022.
7. **Complete:** full pytest, Ruff, format, and mypy gates.

## Backend-owner P0 remaining

1. Load project reference lines, parcels, and restrictions when a job runs.
2. Serialize explicit constraint type/mode/buffer/cost and send it to Python.
3. Select/reject ambiguous substations and send the configured 33 kV value.
4. Carry the rich Python result without dropping pole Points.
5. Return or persist the selected route and poles under the same job identity.
6. Capture and verify the exact Python request emitted after a fixed KMZ
   upload, preview, classification, confirmation, commit, and job cycle.

## Frontend-owner P0 remaining

1. Show confirmed feature counts before running optimisation.
2. Render feeders, hard exclusions, soft constraints, and three pole classes.
3. Show preliminary pole popups and recommendation/electrical evidence.
4. Show real failed/no-route states with no successful demo fallback.

## Schedule

- **Thursday:** freeze contract/fixture; stabilize hard/soft Python constraints.
- **Friday:** finish pole/result output; connect Java constraints and rich result.
- **Saturday:** render all layers; run full-stack checks and one cold run.
- **Sunday:** two rehearsals and demo only; no new algorithm or redesign.

## Sunday gate

Upload -> preview -> confirm -> optimise -> display must work without manual
payload or database edits. The selected route must avoid hard zones, disclose
soft crossings/land impacts, be electrically valid at 33 kV, show deterministic
preliminary pole types, survive refresh, and repeat for identical input.

Detailed file-level decisions, tests, fallbacks, and the literal demo procedure
are maintained in the canonical plan.
