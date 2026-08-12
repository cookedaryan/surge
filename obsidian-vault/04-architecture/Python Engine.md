# Python Optimization Engine (FastAPI Microservice)

## Responsibility Boundary

`optimisation-python` is a stateless computation service called by Spring Boot. It validates optimization inputs and performs projected spatial calculations. Java remains responsible for projects, persistence, workflow state, public application APIs, and future authentication.

## Implemented Service Pipeline

1. Pydantic validates request IDs, scenario, and electrical parameters.
2. GIS preprocessing validates WTG/substation Point GeoJSON and chooses one UTM CRS.
3. Frozen spatial dataclasses hold projected meter coordinates.
4. NetworkX builds a complete undirected candidate graph.
5. K-Means-assisted MILP creates capacity-constrained WTG groups.
6. [[Per-Feeder MST Topology]] selects one radial minimum-distance tree per feeder.
7. A* routes each selected edge over a uniform projected cost surface.
8. Route refinement removes duplicate/collinear points and applies obstacle-safe visibility shortcuts.
9. Refined routes are transformed back to WGS84 and returned as individual LineString Features.
10. The response reports feeder count and the sum of refined physical-route lengths.

[[GIS Cost Surface]] is implemented as a uniform base raster foundation, and the API-integrated pipeline uses A* to route MST edges over it. [[Pole Placement]], [[ROW Corridor Analysis]], and [[Electrical Feeder Screening]] remain standalone. SURGE-PY-014 through PY-019 now provide PNC assembly, pandapower AC load flow, presentation packaging, deterministic candidate generation, scoring, recommendation, and an internal end-to-end orchestrator. Compatible public API integration remains PY-020. See [[Surge MVP Ticket Plan]] for the frozen sequence.

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
| `app/algorithms/physical_routing.py` | A* translation from topology edges to projected physical routes |
| `app/algorithms/route_refinement.py` | Obstacle-safe simplification and refined route measurements |
| `app/algorithms/pole_placement.py` | Standalone terminal, angle, and intermediate pole placement over refined routes |
| `app/gis/row_analysis.py` | Standalone metric ROW buffers, indexed constraint intersections, and land-impact aggregates |
| `app/electrical` | Standalone radial-feeder current, ampacity, and linear voltage-deviation screening |
| `app/pnc` | Complete PNC assembly and base GeoJSON conversion |
| `app/electrical/load_flow` | Pandapower construction and AC load-flow validation |
| `app/presentation` | Strict summaries and electrically enriched WGS84 GeoJSON |
| `app/optimisation` | Candidate generation, electrical-aware scoring, recommendation, and the internal end-to-end orchestrator |
| `cost_function.py` | Placeholder; not implemented |

## Why the Stages Are Separate

Grouping decides which WTGs share a feeder. MST topology decides which assigned nodes connect. A* replaces each selected straight edge with a cost-surface path, and refinement simplifies that path without crossing blocked cells or increasing its integrated cost. The standalone pole-placement stage can consume those refined paths once service/API integration is defined. Electrical and lifecycle-cost stages will later evaluate the routed alternatives.

This separation keeps each algorithm testable, but intermediate results must eventually be represented in the public contract if Java and the frontend need to inspect or persist them.

## Current Limitations

- MST edges are returned as individual preliminary LineStrings; complete `FeederTopology` models and assignments are not returned.
- Python uses the `feederName` property, which is recognized by the Java route importer. However, because each edge is returned as a separate LineString, Java persists them as separate feeder segments. Aggregation is deferred.
- `total_length_m` is the cost-surface-aware routed line length over the base uniform raster.
- The endpoint is synchronous and CPU-bound work is performed in the request path.
- The cost surface supports blocked cells, but production DEM, restriction, land, and accessibility layers are not yet rasterized.
- Geometry-based pole placement exists, but it is not service-integrated and does not yet use terrain, sag, clearance, crossings, or structural pole selection.
- ROW analysis exists as a projected standalone module, but no constraint layers reach Python through the request contract and no ROW result is returned or persisted.
- Pandapower load flow exists standalone, but it is not API-integrated and does not perform electrical repair, cable resizing, transformer design, protection analysis, or N-1 analysis.
- Candidate generation, recommendation, and internal orchestration are implemented; the richer compatible API response remains PY-020.
- Raw constraint transport/rasterization, Dijkstra, and ML ranking are post-MVP.

## Related Notes

- [[System Overview]]
- [[Overview & Layout]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]
- [[Geospatial Integrity & CRS]]
- [[GIS Cost Surface]]
- [[WTG Grouping]]
- [[Per-Feeder MST Topology]]
- [[Routing]]
- [[Electrical Feeder Screening]]
- [[Surge MVP Ticket Plan]]
- [[ADR-005 Python Service Architecture and Schemas]]
- [[ADR-006 Spatial Models and Unified UTM]]
