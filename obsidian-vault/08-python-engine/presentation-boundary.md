# Python Presentation Boundary

## Purpose and boundary

SURGE-PY-016 adds `app.presentation`, the adapter between the internal engineering models and a future public API response. `build_project_result()` combines:

- `ProjectPNCNetwork`, the authoritative projected physical network produced by PNC assembly; and
- `LoadFlowNetworkResult`, the pandapower analysis result for that exact network.

It returns `ProjectOptimizationResult`, which contains network and feeder summaries, electrical violations, and a map-ready GeoJSON `FeatureCollection`. The module does not generate topology, route cables, or run load flow. Its calculations are limited to presentation concerns such as rounding, ordering, grouping violations, and calculating a WGS-84 bounding box.

The `/api/v1/optimise` response correctly uses this presentation model by filtering it to match the legacy Java DTO schema. V2 endpoints expose the full `ProjectOptimizationResult`.

## How the pieces work together

`app/presentation/result_builder.py` is the orchestration entry point. It first validates each source result and their shared identifiers, builds the summary models, associates node and segment violations with their owning feeder, and delegates geometry conversion to `build_enriched_geojson()`.

`app/presentation/geojson.py` calls the existing `app.pnc.geojson.network_to_feature_collection()` converter. That converter creates a new collection and reprojects the PNC's metric geometry to EPSG:4326. The presentation layer enriches that new object in place, avoiding a redundant deep copy of the complete coordinate tree. The internal `ProjectPNCNetwork` is not mutated.

`app/presentation/models.py` defines strict Pydantic response structures. Unknown model fields are rejected, assignments to model fields are frozen, and non-finite floats are forbidden. The nested feeder lists and raw GeoJSON dictionary remain ordinary mutable Python collections, so the contract is assignment-frozen rather than deeply immutable.

## Reconciliation rules

A converged electrical result must provide:

- exactly one bus result for every PNC substation and WTG;
- exactly one segment result for every PNC segment;
- exactly one feeder result for every PNC feeder;
- complete finite network, bus, segment, and feeder metrics; and
- segment-to-feeder and WTG-count values that agree with the PNC.

Duplicate or unknown identifiers, invalid node types, mismatched associations, non-finite electrical values, and contradictory validity state raise `PresentationDataMismatchError`. PNC feeder, WTG-membership, segment, endpoint, and substation references are also checked before packaging. A converged result is valid exactly when it has no violations.

Violations are ordered deterministically. A violation with a WTG or segment reference is included in the owning `FeederResult.violations` even if the load-flow record omits the redundant `feeder_id`. Explicit feeder references must agree with the owning PNC feeder.

## GeoJSON contract

The returned RFC 7946-style `FeatureCollection` contains features in this stable order:

1. the substation Point;
2. WTG Points sorted by WTG ID;
3. segment LineStrings sorted by segment ID; and
4. deduplicated physical pole Points sorted canonically by topology node, pole ID, then route IDs (if pole placement is configured).

Every feature receives a stable top-level ID: `substation-{id}`, `wtg-{id}`, `segment-{id}`, or `pole-{id}`. Coordinates contain exactly longitude and latitude, must be finite, and are checked against WGS-84 longitude and latitude bounds. The collection includes `[west, south, east, north]` in `bbox`. `ProjectOptimizationResult.source_crs` records the original PNC CRS; all feature geometry is EPSG:4326.

Node properties include voltage, voltage angle, and net active/reactive demand. Segment properties include terminal currents, maximum current, loading, losses, endpoint voltages, and physical PNC identifiers. `has_voltage_violation` is set only for under- or over-voltage codes; `has_cable_overload` is set only for a cable-overload code.

Pole features represent deduplicated physical structures rather than logical route endpoints. Coincident topology endpoints are merged into a single `junction` pole, while keeping their contributor references (`connected_feeder_ids`, `connected_route_ids`) and `connected_node_ids`. Pole summary semantics (`total_poles`, `terminal_poles`, `angle_poles`, `intermediate_poles`, `junction_poles`) are strictly calculated from these unique physical structures rather than raw route-local pole counts.

## Non-convergence

A non-converged result is a valid analytical outcome, not a presentation failure. It must be marked invalid, contain no bus/segment/feeder detail rows, and include `LOAD_FLOW_NOT_CONVERGED`. Physical features, stable feature IDs, and the bounding box are still returned. Electrical summary and feature telemetry values are `null`, while violation flags default to `false`. This keeps the map schema stable for clients regardless of solver convergence.

## Deliberate decisions

- **Reuse PNC GeoJSON conversion:** CRS conversion and base feature construction have one implementation instead of two drifting copies.
- **Fail on reconciliation errors:** silently joining partial electrical data to the wrong physical asset would produce a credible-looking but unsafe engineering result.
- **Permit topology-only output after solver failure:** users can still inspect the proposed physical network and the explicit convergence violation.
- **Keep presentation separate from computation:** rounding and JSON naming cannot affect the engineering models used for validation.
- **Use nullable telemetry keys:** clients can render one stable feature schema without probing whether properties exist.

## Verification scope

`tests/test_presentation.py` covers successful packaging, strict JSON serialization, deterministic feature order and IDs, WGS-84 bounding-box output, non-converged defaults, exact violation flags, feeder violation ownership, identifier mismatches, PNC membership errors, and rejection of non-finite or contradictory electrical results.
