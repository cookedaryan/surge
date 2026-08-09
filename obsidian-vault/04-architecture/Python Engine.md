# Python Optimization Engine (FastAPI Microservice)

## Responsibility Boundary

`optimisation-python` is a stateless computation service called by Spring Boot. It validates optimization inputs and performs projected spatial calculations. Java remains responsible for projects, persistence, workflow state, public application APIs, and future authentication.

## Implemented Pipeline

1. Pydantic validates request IDs, scenario, and electrical parameters.
2. GIS preprocessing validates WTG/substation Point GeoJSON and chooses one UTM CRS.
3. Frozen spatial dataclasses hold projected meter coordinates.
4. NetworkX builds a complete undirected candidate graph.
5. K-Means-assisted MILP creates capacity-constrained WTG groups.
6. [[Per-Feeder MST Topology]] selects one radial minimum-distance tree per feeder.
7. Selected MST edges are transformed back to WGS84 and returned as two-point LineString Features.
8. The response reports feeder count and the sum of preliminary MST lengths.

[[GIS Cost Surface]] is implemented as a standalone uniform raster foundation but is not called by this request pipeline. A successful response does not mean A*, terrain routing, pole placement, ROW analysis, electrical simulation, lifecycle cost, or ML ranking has run.

## Package Responsibilities

| Package | Responsibility |
| --- | --- |
| `app/api/v1` | FastAPI endpoints and error translation |
| `app/schemas` | Pydantic request, response, and metric contracts |
| `app/services` | Ordered pipeline orchestration |
| `app/gis` | GeoJSON parsing, validation, CRS selection, and transforms |
| `app/gis/cost_surface.py` | Uniform projected raster and world/grid coordinate helpers |
| `app/models` | Immutable projected WTG/substation/project models |
| `app/algorithms/route_graph.py` | Complete metric candidate graph |
| `app/algorithms/wtg_grouping.py` | Capacity-constrained feeder assignments |
| `app/algorithms/topology.py` | Per-feeder MSTs and preliminary length |
| `cost_function.py` | Placeholder; not implemented |
| `electrical_analysis.py` | Placeholder; not implemented |

## Why the Stages Are Separate

Grouping decides which WTGs share a feeder. MST topology decides which assigned nodes connect. Future routing will replace each selected straight edge with a feasible geographic path. Electrical and lifecycle-cost stages will then evaluate those routed alternatives.

This separation keeps each algorithm testable, but intermediate results must eventually be represented in the public contract if Java and the frontend need to inspect or persist them.

## Current Limitations

- MST edges are returned as individual preliminary LineStrings; complete `FeederTopology` models and assignments are not returned.
- Python's `feeder_id` property is not recognized by the current Java route importer, which falls back to generated feeder names.
- `total_length_m` is projected straight-line MST length, not routed line length.
- The cost surface is not integrated into `OptimisationService`.
- The endpoint is synchronous and CPU-bound work is performed in the request path.
- A*, Dijkstra, DEM processing, obstacles, poles, ROW, pandapower, and ML are not implemented.

## Related Notes

- [[System Overview]]
- [[Overview & Layout]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]
- [[Geospatial Integrity & CRS]]
- [[GIS Cost Surface]]
- [[WTG Grouping]]
- [[Per-Feeder MST Topology]]
- [[Routing]]
- [[ADR-005 Python Service Architecture and Schemas]]
- [[ADR-006 Spatial Models and Unified UTM]]
