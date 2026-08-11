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
|    |    +--- topology.py
|    |    \--- wtg_grouping.py
|    +--- gis
|    |    +--- __init__.py
|    |    +--- crs.py
|    |    +--- cost_surface.py
|    |    +--- geojson.py
|    |    +--- geometry.py
|    |    \--- preprocessing.py
|    +--- models
|    |    +--- __init__.py
|    |    \--- spatial.py
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
     +--- test_geojson.py
     +--- test_geometry.py
     +--- test_health.py
     +--- test_optimise.py
     +--- test_physical_routing.py
     +--- test_pole_placement.py
     +--- test_preprocessing.py
     +--- test_route_graph.py
     +--- test_route_refinement.py
     +--- test_topology.py
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
    -> place_poles_on_routes
    -> sum refined route length
    -> OptimisationResponse
```

SURGE-PY-006 is implemented in `app/algorithms/topology.py`. Each feeder subgraph contains its assigned WTGs and the substation. NetworkX minimizes the `weight` attribute and the service reports the sum of selected `distance_m` values.

Selected MST edges are routed via A* over a base cost surface, transformed back to WGS84, and returned as individual LineString Features. `total_length_m` represents the cost-surface-aware routed corridor length.

SURGE-PY-007 adds `app/gis/cost_surface.py` as a standalone uniform raster abstraction. It is now integrated with `OptimisationService` (via SURGE-PY-008) to route the physical LineStrings.

SURGE-PY-009 adds `app/algorithms/route_refinement.py`. It removes duplicate and collinear grid points, then applies deterministic farthest-visible shortcutting. A continuous supercover check validates every touched raster cell, including corner-touching cells, and the shortcut must not cost more than the subpath it replaces. Exact endpoints and feeder/node metadata remain unchanged.

The API emits refined geometry and uses refined length for aggregate metrics. Route features retain both original and refined length/cost properties so the A* result remains auditable.

SURGE-PY-010 adds `app/algorithms/pole_placement.py`. It converts each `RefinedPhysicalRoute` into an ordered sequence of physical `Pole` structures connected by `PoleSpan` objects. Poles are placed using section-based, evenly-distributed span allocation: mandatory structures are first identified at route endpoints and at LineString vertices whose deflection angle meets or exceeds the configurable `angle_pole_threshold_deg`. The route is then divided into sections between mandatory positions, and each section is filled with intermediate poles whose spans are kept within `[min_span_m, max_span_m]`. The `max_span_m` limit is hard; `min_span_m` is a soft lower bound (routes shorter than `min_span_m` produce only two terminal poles). Pole IDs are deterministic (`{feeder_id}-P{sequence:03d}`). `PoleRouteResult` carries `start_node_id` / `end_node_id` for future network-level deduplication of shared topology endpoints.

## Related Notes

- [[Python Engine]]
- [[WTG Grouping]]
- [[Per-Feeder MST Topology]]
- [[GIS Cost Surface]]
- [[Feeder Planning]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]
