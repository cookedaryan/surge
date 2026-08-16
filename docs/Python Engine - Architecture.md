# Python Engine Architecture and GIS Processing

## Current Implementation

The SURGE Python service is a stateless FastAPI computation boundary. It currently validates project Point GeoJSON, transforms coordinates into one UTM CRS, builds a complete NetworkX candidate graph, groups WTGs under feeder-capacity constraints, creates one minimum spanning tree per feeder, routes each selected edge across a raster cost surface, and exposes refined WGS84 LineStrings.

SURGE-PY-007 through SURGE-PY-009 provide a uniform projected cost-surface abstraction, A* physical routing, and obstacle-safe route refinement. The cost surface currently defaults to 1.0 everywhere, meaning routes optimize for distance until terrain and exclusion layers are rasterized. SURGE-PY-010 provides pole placement over refined routes, PY-023 adds project-wide endpoint deduplication, and PY-024 runs both stages once for the recommended PNC and returns the canonical pole network from the optimisation workflow. SURGE-PY-011 provides right-of-way corridor and constraint-intersection analysis.

## Pipeline

```text
Spring Boot POST /api/v1/optimise
    -> Pydantic request validation
    -> WGS84 GeoJSON Point preprocessing
    -> unified UTM projection
    -> complete metric candidate graph
    -> K-Means-assisted MILP feeder grouping
    -> per-feeder minimum spanning trees
    -> A* physical routes over the projected cost surface
    -> collinear removal + obstacle-safe visibility shortcutting
    -> WGS84 refined route GeoJSON
    -> feeder count + aggregate refined length

Standalone SURGE-PY-007:
ProjectSpatialData -> uniform CostSurface + Affine transform
```

## Package Responsibilities

| Package or module | Responsibility | Status |
| --- | --- | --- |
| `app/api/v1` | Java-compatible additive workflow API and expected-error translation | Implemented through PY-020 |
| `app/api/v2` | Explicit cable/configuration workflow API | Implemented through PY-020 |
| `app/schemas` | Pydantic request/response contract | Implemented |
| `app/gis` | GeoJSON parsing, validation, UTM selection, transforms | Implemented for WTG/substation Points |
| `app/gis/cost_surface.py` | Uniform raster, affine transform, and coordinate helpers | Implemented and service-integrated |
| `app/models` | Frozen projected spatial domain objects | Implemented |
| `route_graph.py` | Complete undirected graph with Euclidean metric edges | Implemented |
| `wtg_grouping.py` | Capacity-constrained feeder assignment | Implemented |
| `topology.py` | SURGE-PY-006 per-feeder MST topology | Implemented internally |
| `physical_routing.py` | SURGE-PY-008 A* translation from topology edges to projected physical routes | Implemented |
| `route_refinement.py` | SURGE-PY-009 duplicate/collinear removal and supercover-validated visibility shortcuts | Implemented |
| `pole_placement.py` | SURGE-PY-010/PY-023 route placement plus network endpoint deduplication | Implemented and integrated for the recommended PNC by PY-024 |
| `app/gis/row_analysis.py` | SURGE-PY-011 projected ROW buffers, indexed constraint intersections, and impact aggregates | Implemented standalone; no constraint API input yet |
| `app/land` | PY-034 parcel availability, owner interaction, transaction NPV selection, and economic-context fingerprints | Implemented and integrated with V2 optimisation |
| `cost_function.py` | Lifecycle-cost evaluation | Placeholder |
| `app/electrical` | SURGE-PY-013 deterministic electrical screening proxy (ampacity & voltage drop) | Implemented standalone; not service-integrated |
| `app/pnc` | Canonical projected physical network assembly and base GeoJSON conversion | Implemented standalone; not service-integrated |
| `app/electrical/load_flow` | Pandapower network construction and AC load-flow analysis | Implemented standalone; not service-integrated |
| `app/presentation` | Reconciles PNC and load-flow results into strict summaries and enriched WGS-84 GeoJSON | Implemented and exposed for the recommendation |
| `app/optimisation` | SURGE-PY-017 deterministic candidate PNC scenario generation | Implemented standalone; not service-integrated |

## SURGE-PY-006: Per-Feeder MST

Grouping determines feeder membership; MST topology determines connections inside each feeder. For every `FeederAssignment`, `build_feeder_mst` selects the project substation and the assigned WTG nodes, creates their induced subgraph, and calls `networkx.minimum_spanning_tree(weight="weight")`.

The result is verified as a connected acyclic tree. Selected edge pairs are normalized and sorted for deterministic output. `total_length_m` is the sum of the selected edges' `distance_m` values.

Because the candidate graph uses straight-line distances in UTM, the MST minimizes preliminary Euclidean topology length. The edges are then routed by A* over a uniform base cost surface. True terrain-aware routing, exclusions, parcels, access, junctions, shared trunks, and electrical performance are future extensions.

## Service and API Integration

`OptimisationService` builds all feeder trees, routes them via A* over the base cost surface, refines those routes, sums the refined lengths into `OptimisationMetrics.total_length_m`, transforms each refined path back to WGS84, and returns one LineString Feature per edge. Existing `length_m` and `traversal_cost` properties describe the refined route; additive `original_*` and `refined_*` properties retain both measurements.

The current response property `feederName` matches the key recognized by Java's `RouteService`. Java persists each generated route feature independently as a distinct route record. Consequently, one feeder appears as multiple feeder-summary segment rows in downstream reports. These records represent feeder segments, and the deferral of Java-level aggregation is intentional.

## SURGE-PY-007: Uniform Cost Surface

`build_project_cost_surface` calculates a padded bounding box around projected WTGs and the substation, derives raster dimensions from `resolution_m`, creates a north-up affine transform, and fills a NumPy `float32` array with base cost `1.0`.

`world_to_grid` inverts the affine transform and floors the result. `grid_to_world` returns the projected center of a raster cell. Positive infinity is reserved for future hard exclusions, while larger finite values can represent soft penalties.

The current implementation does not validate padding, enforce coordinate/index bounds, cap allocation size, or rasterize GIS layers. With zero padding, points on the maximum-x or minimum-y extent map one index beyond the array.

## SURGE-PY-009: Route Geometry Refinement

`refine_routing_result` processes each immutable `PhysicalRoute` independently. It removes consecutive duplicates and forward-moving collinear points, then greedily connects each retained point to the farthest later point that remains visible across the cost surface without increasing the continuously integrated cost of the replaced subpath. Exact route endpoints and feeder/node metadata are preserved.

Visibility uses a continuous grid-coordinate supercover. Every existing raster cell touched by a candidate segment is checked, including both side cells when the segment touches an internal grid corner or follows an internal cell boundary. Coordinates outside the closed raster extent and non-finite cells make the segment non-traversable. A segment on the outer raster boundary checks only the existing interior side.

Each `RefinedPhysicalRoute` retains original and refined length and traversal cost. Refined cost integrates segment length through the raster cells it crosses; when a segment lies on an internal cell boundary, the higher adjacent finite cost is used conservatively. Shortcut decisions compare candidate and replaced-subpath costs using this same integration model, preventing refinement from undoing A* avoidance of finite high-cost cells.

Coincident endpoints are rejected during refinement because they collapse to fewer than two distinct coordinates and cannot produce a non-degenerate engineering route. The API maps this spatial infeasibility to HTTP 422.

## SURGE-PY-010: Pole Placement

`place_poles_on_route` consumes one projected `RefinedPhysicalRoute`. It always creates terminal poles at the route endpoints and makes an interior LineString vertex mandatory when its deflection angle meets or exceeds `angle_pole_threshold_deg`. Deflection is measured between consecutive forward segment vectors: 0° is straight, 90° is a right-angle turn, and 180° is a reversal. At a threshold of 180°, exact reversals remain mandatory.

Mandatory positions split the route into independent sections. A section at or below `min_span_m` receives no intermediate fill pole. For a longer section, the initial span count is `round(section_length / target_span_m)` using Python's ties-to-even rule and is increased as necessary to keep the arc-length interval at or below `max_span_m`. Consequently, `max_span_m` is hard while `min_span_m` is a soft subdivision threshold; the implementation does not promise that every resulting span is at least the minimum.

`Pole.distance_along_route_m` stores arc length along the LineString, while `PoleSpan.span_length_m` stores the Euclidean chord between consecutive pole Points. Batch placement maintains a continuous sequence per `feeder_id`, preventing ID collisions between multiple routes from the same feeder. SURGE-PY-023 adds an explicit network post-pass: terminal records from different routes merge only when they declare the same topology node and fall within a strict-pairwise coordinate tolerance. The resulting `PhysicalPole` is classified as a junction with stable identity and sorted feeder, source-pole, and route/segment references, while route-local pole and span records remain unchanged. When the input comes from a `ProjectPNCNetwork`, the canonical `PNCSegment.segment_id` is preserved as that route reference.

The module does not yet use DEM profiles, calculate sag or clearance, select structural pole classes, insert crossing structures, or create ROW geometry. `place_poles_on_network()` adapts the recommended `ProjectPNCNetwork` without reconstructing routes, applies PY-023 deduplication, and preserves canonical segment IDs. `OptimisationWorkflowResult.pole_network` owns that domain result; pole generation runs after recommendation and does not affect PY-018 scoring. Formal public presentation remains the PY-025 boundary.

## SURGE-PY-011: ROW Corridor and Constraint Analysis

`analyse_row_corridors` consumes projected `RefinedPhysicalRoute` objects, explicit route CRS provenance, projected project constraints, and a `RowConfig`. CRS is intentionally separate from corridor configuration: Shapely geometries do not carry CRS metadata, so the caller supplies the route CRS while `ProjectConstraintLayers` carries the constraint CRS. The analysis requires equivalent projected CRS definitions whose axes are measured in metres.

Each route segment is buffered by half the configured total corridor width. The implementation uses flat end caps by default so the ROW stops at the exact route endpoints, and it records both the sum of segment-level corridor areas and the unique union footprint. The distinction matters where feeder segments overlap at substations, junctions, or shared alignments.

Constraint geometries are validated and repaired before one Shapely `STRtree` is built and reused for all corridors. Areal layers such as parcels, forests, restricted zones, and environmental areas require Polygon or MultiPolygon geometry. Roads and water may be linear or areal. Empty non-critical features are reported as skipped; empty critical features and invalid or incompatible geometries fail the analysis rather than silently weakening compliance checks.

Every `RowIntersection` retains feeder and route-edge identity. It distinguishes corridor overlap area, route-centreline overlap length, linear-constraint length inside the corridor, and boundary-only contact. Aggregates report unique parcels, road crossing events, restricted route-feature events, unique restricted features, and whether any included intersection has `severity="hard"`. Linear road crossings count transverse point events, while areal roads count positive-length route passages.

This is currently a standalone spatial algorithm. `OptimisationRequest` does not carry parcel, road, forest, water, environmental, or restricted-zone layers; `OptimisationService` does not invoke ROW analysis; and the API does not serialize or persist its result. An integration ticket must define constraint transport, projected conversion, response GeoJSON, and Java persistence before callers can use these outputs end to end.

## SURGE-PY-013: Electrical Feasibility Validation

`validate_collector_network` consumes a complete collector topology, its refined physical routes, projected project nodes, and an `ElectricalDesignConfig`. It acts as a fast, deterministic screening proxy for a full nonlinear load flow. It is deliberately standalone: `OptimisationService` does not invoke it and the API does not expose its results.

Before calculation, the module verifies that the project uses a projected metre-based CRS; every project WTG appears exactly once across the feeder trees; graph nodes, declared MST edges, route identities, route lengths, route endpoints, and aggregate refined length agree; and all capacities and electrical parameters are positive finite values where required. Structural inconsistencies raise `ValueError` because they make the electrical result undefined.

Downstream active power is calculated by post-order traversal of each substation-rooted tree. Installed WTG capacities are multiplied by `operating_factor`; the resulting operating power is used consistently for feeder/turbine reporting, substation-capacity screening, current, ampacity loading, and voltage change. Current assumes balanced three-phase power at nominal line voltage and a fixed feeder-wide power factor.

For each route segment, impedance is proportional to its refined metric length. Voltage change uses the linear approximation $\Delta V \approx \sqrt{3} I(R\cos\phi \pm X\sin\phi)$, with `+` for lagging and `−` for leading power factor, and is accumulated from the nominal-voltage substation to every WTG. Positive values represent drop and negative values represent rise; voltage compliance uses the absolute cumulative deviation.

Well-formed networks that exceed limits return deterministic `AMPACITY_EXCEEDED`, `VOLTAGE_LIMIT_EXCEEDED`, or `SUBSTATION_CAPACITY_EXCEEDED` records rather than exceptions. The result exposes per-segment loading and voltage change, per-turbine cumulative voltage deviation, feeder maxima, network maxima, and validity flags.

This is not pandapower validation. It ignores conductor losses when calculating downstream power, shunt admittance, transformers, tap changers, phase imbalance, voltage-dependent loads, reactive-power variation, fault levels, protection coordination, thermal/environmental derating, and iterative voltage/current coupling. These results are preliminary screening values and must not be presented as final electrical design approval.

## SURGE-PY-016: Presentation Boundary

`build_project_result` reconciles an assembled `ProjectPNCNetwork` with the `LoadFlowNetworkResult` calculated for that network. Converged results require exact bus, segment, and feeder coverage plus consistent ownership and finite electrical metrics. Non-converged results retain the physical map but require empty electrical detail collections and an explicit `LOAD_FLOW_NOT_CONVERGED` violation.

The boundary returns strict Pydantic summaries and enriched GeoJSON. The existing PNC converter performs projected-CRS to WGS-84 transformation; presentation enrichment adds stable feature IDs, nullable electrical telemetry, exact violation flags, and a collection bounding box. It also records the source projected CRS and groups WTG/segment violations under their owning feeder. The recommended presentation is exposed by both optimisation API versions; V1 additionally derives a segment-only `feeder_routes_geojson` collection for the existing Java importer. See [Python Presentation Boundary](presentation-boundary.md).

## PY-034: Land Parcel and Landowner Decision Intelligence

The V2 optimisation request accepts an optional `land_context` containing dated
parcel profiles, availability, owner IDs, and purchase, lease, or easement
terms. The land decision module values recurring payments with the lifecycle
discount rate and analysis horizon, selects the lowest-present-value feasible
option deterministically, counts unique confirmed owners (or uses a parcel
proxy when ownership is incomplete), and rejects candidates that intersect an
`UNAVAILABLE` parcel.

Before A* generation, matching parcel constraint layers are replaced with an
effective land policy. Unavailable parcels become hard exclusions. Other
profiled parcels retain their original soft cost and receive an additive owner
interaction and present-value penalty. The adjustment is burned into the
prepared cost surface before scenario generation; layer IDs remain unique so
ROW extraction continues to report the original parcel identity.

Lifecycle costing publishes `land_purchase_capex`,
`land_recurring_cost_pv`, and `land_access_present_value`. A selected quoted or
estimated commercial option takes precedence. Affected parcels without a
selectable commercial price use the existing catalogue policy (fixed cost plus
the configured route-length or ROW-area rate). The legacy V2 `land_capex`
response field remains as an alias for upfront land cost.

## Frozen MVP sequence

SURGE-PY-017 owns deterministic candidate PNC generation, SURGE-PY-018 adds
electrical-aware deterministic scoring and recommendation, and SURGE-PY-019
connects the existing modules behind one internal orchestrator. These stages
and PY-020 connects them to compatible V1 and explicit V2 API boundaries. The
golden demo validates three distinct candidates and deterministic repeated
output. The numbering freezes at SURGE-PY-020 for the MVP.

Raw boundary/restriction transport and rasterization are not part of this MVP.
Internal routing and scenario generation continue to respect blocked or
penalized cells already present in a prepared `CostSurface`. See
[Surge MVP Ticket Plan](Surge%20MVP%20Ticket%20Plan.md) for the authoritative
boundaries and compatibility rules.

## Input Assumptions

The topology function is designed for outputs from `build_project_graph` and `group_wtgs`. It now rejects zero/multiple substations, feeder-count mismatch, duplicate assignments, missing assigned nodes, count-based incomplete coverage, and disconnected results. Coverage compares counts rather than exact node sets; the normal graph builder keeps those equivalent, but direct callers should still supply correctly typed nodes and finite `weight`/`distance_m` attributes.

## Verification

Focused topology tests cover membership, substation inclusion, connectivity, acyclicity, edge count, minimum-weight selection, length aggregation, multiple feeders, single-WTG feeders, and unknown turbine rejection.

Route-refinement tests cover duplicate and collinear removal, exact endpoints, cost-preserving shortcuts, obstacle and finite-penalty detours, corner and outer-boundary supercover behavior, metadata, determinism, cost recomputation, and batch totals. Pole-placement tests cover terminal, angle, and intermediate structures; span allocation; feeder-wide IDs; chord lengths; input validation; and aggregate counts. ROW-analysis tests cover metric CRS enforcement, explicit buffer behavior, repaired and empty constraints, indexed intersections, route-edge traceability, line and polygon roads, hard violations, overlap thresholds, deterministic ordering, and summed versus unique ROW area. Electrical tests cover primitive formulas and invalid numeric inputs, radial downstream aggregation, complete topology/route/project reconciliation, endpoint continuity, operating-factor consistency, ampacity, voltage, and substation-capacity violations. API coverage includes refined response properties and coincident-endpoint rejection. Pole/ROW/electrical API integration, cross-service persistence, nonlinear load flow, and zero-padding cost-surface construction remain outside this test boundary.
