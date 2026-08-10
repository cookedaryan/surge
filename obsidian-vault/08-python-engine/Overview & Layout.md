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
|    |    +--- cost_function.py
|    |    +--- electrical_analysis.py
|    |    +--- route_graph.py
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
     +--- test_crs.py
     +--- test_cost_surface.py
     +--- test_geojson.py
     +--- test_geometry.py
     +--- test_preprocessing.py
     +--- test_health.py
     +--- test_optimise.py
     +--- test_route_graph.py
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
    -> sum per-feeder MST length
    -> OptimisationResponse
```

SURGE-PY-006 is implemented in `app/algorithms/topology.py`. Each feeder subgraph contains its assigned WTGs and the substation. NetworkX minimizes the `weight` attribute and the service reports the sum of selected `distance_m` values.

Selected MST edges are routed via A* over a base cost surface, transformed back to WGS84, and returned as individual LineString Features. `total_length_m` represents the cost-surface-aware routed corridor length.

SURGE-PY-007 adds `app/gis/cost_surface.py` as a standalone uniform raster abstraction. It is now integrated with `OptimisationService` (via SURGE-PY-008) to route the physical LineStrings.

## Related Notes

- [[Python Engine]]
- [[WTG Grouping]]
- [[Per-Feeder MST Topology]]
- [[GIS Cost Surface]]
- [[Feeder Planning]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]
