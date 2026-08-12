# Python Microservice Overview & Layout

The **SURGE Python GIS & Optimization Service** provides high-performance spatial algorithms and electrical calculations for the SURGE platform.

## Directory Layout

```text
optimisation-python/
+--- .dockerignore
+--- .env.example
+--- .gitignore
+--- Dockerfile
+--- README.md
+--- app
|    +--- __init__.py
|    +--- algorithms
|    |    +--- __init__.py
|    |    +--- a_star.py
|    |    +--- cost_function.py
|    |    +--- electrical_analysis.py
|    |    +--- physical_routing.py
|    |    +--- pole_placement.py
|    |    +--- route_graph.py
|    |    +--- route_refinement.py
|    |    +--- route_scoring.py
|    |    +--- topology.py
|    |    \--- wtg_grouping.py
|    +--- electrical
|    |    +--- __init__.py
|    |    +--- feeder_validation.py
|    |    +--- load_flow
|    |    |    +--- analysis.py
|    |    |    +--- builder.py
|    |    |    +--- config.py
|    |    |    \--- models.py
|    |    +--- models.py
|    |    \--- voltage_drop.py
|    +--- gis
|    |    +--- __init__.py
|    |    +--- crs.py
|    |    +--- cost_surface.py
|    |    +--- geojson.py
|    |    +--- geometry.py
|    |    +--- row_analysis.py
|    |    \--- preprocessing.py
|    +--- models
|    |    +--- __init__.py
|    |    \--- spatial.py
|    +--- pnc
|    |    +--- assembly.py
|    |    +--- errors.py
|    |    +--- geojson.py
|    |    \--- models.py
|    +--- presentation
|    |    +--- exceptions.py
|    |    +--- geojson.py
|    |    +--- models.py
|    |    \--- result_builder.py
|    +--- api
|    |    +--- __init__.py
|    |    \--- v1
|    |         +--- __init__.py
|    |         +--- endpoints
|    |         |    +--- __init__.py
|    |         |    +--- health.py
|    |         |    \--- optimise.py
|    |         \--- router.py
|    +--- core
|    |    +--- __init__.py
|    |    \--- config.py
|    +--- main.py
|    +--- schemas
|    |    +--- __init__.py
|    |    \--- optimise.py
|    +--- services
|    |    +--- __init__.py
|    |    \--- optimisation_service.py
|    \--- utils
|         +--- __init__.py
|         \--- coordinate_transform.py
+--- notebooks
|    \--- .gitkeep
+--- pyproject.toml
+--- requirements.lock.txt
+--- requirements.txt
\--- tests
     +--- .gitkeep
     +--- __init__.py
     +--- test_a_star.py
     +--- test_crs.py
     +--- test_cost_surface.py
     +--- test_feeder_validation.py
     +--- test_geojson.py
     +--- test_geometry.py
     +--- test_health.py
     +--- test_optimise.py
     +--- test_physical_routing.py
     +--- test_pole_placement.py
     +--- test_preprocessing.py
     +--- test_route_graph.py
     +--- test_route_refinement.py
     +--- test_route_scoring.py
     +--- test_row_analysis.py
     +--- test_topology.py
     +--- test_voltage_drop.py
     \--- test_wtg_grouping.py
```

## Key Architectural Principles

1. **Decoupled Service Layer**: The optimize endpoint delegates execution to `OptimisationService`. HTTP, preprocessing, graph, grouping, and topology code remain independently testable.
2. **GIS Translation Boundary**: `app/gis/preprocessing.py` converts WGS84 GeoJSON into validated projected domain objects before algorithms run.
3. **Separated Algorithm Stages**: `route_graph.py` creates candidates, `wtg_grouping.py` creates capacity-safe feeder membership, and `topology.py` selects a radial MST for each feeder.
4. **Pydantic 2 Validation**: Typed models define external requests, responses, electrical parameters, and aggregate metrics.
5. **Correlation ID (`request_id`)**: Each optimization request echoes the Java-supplied correlation ID in its response.
6. **Reproducible Environment**: Dependencies are pinned in `requirements.txt` and `requirements.lock.txt`.

## Current Execution Flow

```text
OptimisationRequest
    -> process_project_data
    -> build_project_graph
    -> group_wtgs
    -> build_feeder_mst
    -> route_collector_topology
    -> refine_routing_result
    -> sum refined route length
    -> OptimisationResponse
```

SURGE-PY-006 is implemented in `app/algorithms/topology.py`. Each feeder subgraph contains its assigned WTGs and the substation. NetworkX minimizes the `weight` attribute and the service reports the sum of selected `distance_m` values.

Selected MST edges are routed via A* over a base cost surface, transformed back to WGS84, and returned as individual LineString Features. `total_length_m` represents the cost-surface-aware routed corridor length.

SURGE-PY-007 adds `app/gis/cost_surface.py` as a standalone uniform raster abstraction. It is now integrated with `OptimisationService` (via SURGE-PY-008) to route the physical LineStrings.

SURGE-PY-009 adds `app/algorithms/route_refinement.py`. It removes duplicate and collinear grid points, then applies deterministic farthest-visible shortcutting. A continuous supercover check validates every touched raster cell, including corner-touching cells, and the shortcut must not cost more than the subpath it replaces. Exact endpoints and feeder/node metadata remain unchanged.

The API emits refined geometry and uses refined length for aggregate metrics. Route features retain both original and refined length/cost properties so the A* result remains auditable.

SURGE-PY-010 adds the standalone `app/algorithms/pole_placement.py` module. It converts each projected `RefinedPhysicalRoute` into ordered `Pole` structures connected by `PoleSpan` objects, but `OptimisationService` does not yet invoke it and the API does not return pole results.

The module first makes route endpoints and qualifying deflection vertices mandatory, then treats the geometry between consecutive mandatory positions as independent sections. Sections longer than `min_span_m` receive evenly spaced fill poles based on `round(section_length / target_span_m)`; the count increases until the arc-length interval satisfies the hard `max_span_m` limit. The minimum is a soft subdivision threshold, not a guaranteed lower bound. `PoleSpan.span_length_m` records the Euclidean chord between pole Points, while each pole's `distance_along_route_m` records LineString arc length. Batch placement maintains continuous, non-colliding sequences per feeder. Shared endpoint deduplication, terrain/clearance rules, and service/API integration remain future work. See [[Pole Placement]].

SURGE-PY-011 adds standalone `app/gis/row_analysis.py`. It buffers projected refined route segments into flat-ended metric corridors, validates and repairs projected constraint geometries, uses one STRtree for candidate filtering, and returns deterministic route/constraint intersection events. Results distinguish summed segment area from the dissolved unique ROW footprint and retain route-edge identity, overlap area, centreline exposure length, road crossings, restricted events, and hard violations. CRS provenance is supplied explicitly with `pyproj.CRS`; route and constraint CRS values must be equivalent projected systems measured in metres. The service does not yet receive constraint layers or expose ROW results. See [[ROW Corridor Analysis]].

SURGE-PY-012 (formerly PY-015) adds standalone `app/algorithms/route_scoring.py`. It is a preliminary multi-criteria spatial and constructability scoring engine designed to evaluate complete network alternatives. It computes deterministic min-max normalization exclusively on feasible candidates, preserves raw metrics and exact normalization ranges for explainability, and handles hard constraint violations by marking candidates infeasible. Financial and electrical criteria are currently omitted. `OptimisationService` does not yet invoke it as the pipeline currently produces only a single network alternative. See [[Route Scoring Architecture]].

SURGE-PY-013 adds standalone `app/electrical/models.py`, `app/electrical/voltage_drop.py`, and `app/electrical/feeder_validation.py`. It reconciles a complete projected project, radial topology, and refined-route set before calculating a deterministic balanced three-phase screening result. Post-order traversal aggregates operating WTG power on each edge; nominal-voltage current is checked against conductor ampacity; and linear segment voltage changes are accumulated to every turbine. Malformed or incomplete inputs raise `ValueError`, while valid networks that exceed ampacity, cumulative voltage-deviation, or substation-capacity limits return explicit `ElectricalViolation` records. This is a standalone linear proxy—not pandapower or final design validation—and `OptimisationService` does not invoke it. See [[Electrical Feeder Screening]].

SURGE-PY-014 adds `app/pnc`, which can run the grouping-to-routing pipeline and assemble a validated `ProjectPNCNetwork`, or assemble from compatible precomputed topology and refined routes without rerunning them.

SURGE-PY-015 adds standalone `app/electrical/load_flow`. It builds a deterministic pandapower network from a PNC and returns convergence, bus, segment, feeder, loss, loading, voltage, and violation results without modifying the proposed network. See [[AC Load Flow Validation]].

SURGE-PY-016 adds standalone `app/presentation`. It reconciles the canonical projected `ProjectPNCNetwork` with its pandapower `LoadFlowNetworkResult`, rejects missing, duplicate, mismatched, or non-finite electrical references, and returns strict summary models plus WGS-84 GeoJSON. Features receive stable IDs, nullable electrical telemetry, exact voltage/overload flags, and a collection bounding box. A non-converged solver result still produces a topology-only map with an explicit violation. This result is not yet returned by `/api/v1/optimise` or imported by Java. See [[presentation-boundary|Python Presentation Boundary]].

SURGE-PY-017 candidate PNC scenario generation is in progress under `app/optimisation`. Its boundary is deterministic generation of 1-5 distinct, structurally valid `ProjectPNCNetwork` candidates from prepared project data and a prepared cost surface. Electrical evaluation, scoring, recommendation, orchestration, and API integration remain PY-018 through PY-020. See [[Candidate PNC Scenario Generation]] and [[Surge MVP Ticket Plan]].

## Related Notes

- [[Python Engine]]
- [[WTG Grouping]]
- [[Per-Feeder MST Topology]]
- [[GIS Cost Surface]]
- [[Feeder Planning]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]
- [[presentation-boundary|Python Presentation Boundary]]
- [[Surge MVP Ticket Plan]]
- [[Candidate PNC Scenario Generation]]
