# Python Engine Architecture and GIS Processing

## Current Implementation

The SURGE Python service is a stateless FastAPI computation boundary. It currently validates project Point GeoJSON, transforms coordinates into one UTM CRS, builds a complete NetworkX candidate graph, groups WTGs under feeder-capacity constraints, creates one minimum spanning tree per feeder, routes each selected edge across a raster cost surface, and exposes refined WGS84 LineStrings.

SURGE-PY-007 through SURGE-PY-009 provide a uniform projected cost-surface abstraction, A* physical routing, and obstacle-safe route refinement. The cost surface currently defaults to 1.0 everywhere, meaning routes optimize for distance until terrain and exclusion layers are rasterized.

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
| `app/api/v1` | FastAPI routes and expected-error translation | Implemented |
| `app/schemas` | Pydantic request/response contract | Implemented |
| `app/gis` | GeoJSON parsing, validation, UTM selection, transforms | Implemented for WTG/substation Points |
| `app/gis/cost_surface.py` | Uniform raster, affine transform, and coordinate helpers | Implemented standalone |
| `app/models` | Frozen projected spatial domain objects | Implemented |
| `route_graph.py` | Complete undirected graph with Euclidean metric edges | Implemented |
| `wtg_grouping.py` | Capacity-constrained feeder assignment | Implemented |
| `topology.py` | SURGE-PY-006 per-feeder MST topology | Implemented internally |
| `physical_routing.py` | SURGE-PY-008 A* translation from topology edges to projected physical routes | Implemented |
| `route_refinement.py` | SURGE-PY-009 duplicate/collinear removal and supercover-validated visibility shortcuts | Implemented |
| `cost_function.py` | Lifecycle-cost evaluation | Placeholder |
| `electrical_analysis.py` | Load flow, voltage drop, and losses | Placeholder |

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

## Input Assumptions

The topology function is designed for outputs from `build_project_graph` and `group_wtgs`. It now rejects zero/multiple substations, feeder-count mismatch, duplicate assignments, missing assigned nodes, count-based incomplete coverage, and disconnected results. Coverage compares counts rather than exact node sets; the normal graph builder keeps those equivalent, but direct callers should still supply correctly typed nodes and finite `weight`/`distance_m` attributes.

## Verification

Focused topology tests cover membership, substation inclusion, connectivity, acyclicity, edge count, minimum-weight selection, length aggregation, multiple feeders, single-WTG feeders, and unknown turbine rejection.

Route-refinement tests cover duplicate and collinear removal, exact endpoints, cost-preserving shortcuts, obstacle and finite-penalty detours, corner and outer-boundary supercover behavior, metadata, determinism, cost recomputation, and batch totals. API coverage includes refined response properties and coincident-endpoint rejection. Cross-service persistence and zero-padding cost-surface construction remain outside this test boundary.
