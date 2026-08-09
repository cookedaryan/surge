# Python Engine Architecture and GIS Processing

## Current Implementation

The SURGE Python service is a stateless FastAPI computation boundary. It currently validates project Point GeoJSON, transforms coordinates into one UTM CRS, builds a complete NetworkX candidate graph, groups WTGs under feeder-capacity constraints, creates one minimum spanning tree per feeder, and exposes selected edges as preliminary WGS84 LineStrings.

SURGE-PY-007 also provides a standalone uniform projected cost-surface abstraction. It does not yet route topology edges around terrain or restrictions, and the cost surface is not called by the API pipeline.

## Pipeline

```text
Spring Boot POST /api/v1/optimise
    -> Pydantic request validation
    -> WGS84 GeoJSON Point preprocessing
    -> unified UTM projection
    -> complete metric candidate graph
    -> K-Means-assisted MILP feeder grouping
    -> per-feeder minimum spanning trees
    -> WGS84 preliminary edge GeoJSON
    -> feeder count + aggregate preliminary length

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
| `cost_function.py` | Lifecycle-cost evaluation | Placeholder |
| `electrical_analysis.py` | Load flow, voltage drop, and losses | Placeholder |

## SURGE-PY-006: Per-Feeder MST

Grouping determines feeder membership; MST topology determines connections inside each feeder. For every `FeederAssignment`, `build_feeder_mst` selects the project substation and the assigned WTG nodes, creates their induced subgraph, and calls `networkx.minimum_spanning_tree(weight="weight")`.

The result is verified as a connected acyclic tree. Selected edge pairs are normalized and sorted for deterministic output. `total_length_m` is the sum of the selected edges' `distance_m` values.

Because the candidate graph uses straight-line distances in UTM, the MST minimizes preliminary Euclidean topology length. It does not account for terrain, exclusions, parcels, access, junctions, shared trunks, electrical performance, or routed corridor length.

## Service and API Integration

`OptimisationService` builds all feeder trees, sums their lengths into `OptimisationMetrics.total_length_m`, transforms each selected edge back to WGS84, and returns one two-point LineString Feature per edge.

The current response property `feeder_id` does not match any feeder-name key recognized by Java's `RouteService`, so Java assigns generated names and persists each edge as a separate route record. Before these preliminary features are treated as feeder routes, the cross-service contract must define feeder identity and whether one Feature represents an edge, segment, or complete feeder.

## SURGE-PY-007: Uniform Cost Surface

`build_project_cost_surface` calculates a padded bounding box around projected WTGs and the substation, derives raster dimensions from `resolution_m`, creates a north-up affine transform, and fills a NumPy `float32` array with base cost `1.0`.

`world_to_grid` inverts the affine transform and floors the result. `grid_to_world` returns the projected center of a raster cell. Positive infinity is reserved for future hard exclusions, while larger finite values can represent soft penalties.

The current implementation does not validate padding, enforce coordinate/index bounds, cap allocation size, or rasterize GIS layers. With zero padding, points on the maximum-x or minimum-y extent map one index beyond the array.

## Input Assumptions

The topology function is designed for outputs from `build_project_graph` and `group_wtgs`. It now rejects zero/multiple substations, feeder-count mismatch, duplicate assignments, missing assigned nodes, count-based incomplete coverage, and disconnected results. Coverage compares counts rather than exact node sets; the normal graph builder keeps those equivalent, but direct callers should still supply correctly typed nodes and finite `weight`/`distance_m` attributes.

## Verification

Focused topology tests cover membership, substation inclusion, connectivity, acyclicity, edge count, minimum-weight selection, length aggregation, multiple feeders, single-WTG feeders, and unknown turbine rejection.

Twelve cost-surface tests cover its current successful-path behavior, and the endpoint fixture now includes WTG capacity. Cross-service persistence and zero-padding boundary behavior are not covered.
