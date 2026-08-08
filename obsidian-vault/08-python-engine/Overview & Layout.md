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
|    |    \--- wtg_grouping.py
|    +--- gis
|    |    +--- __init__.py
|    |    +--- crs.py
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
     +--- test_geojson.py
     +--- test_geometry.py
     +--- test_preprocessing.py
     +--- test_health.py
     +--- test_optimise.py
     +--- test_route_graph.py
     \--- test_wtg_grouping.py
```

## Key Architectural Principles

1. **Decoupled Service Layer**: The optimize endpoint delegates to `OptimisationService`. HTTP handling, pipeline orchestration, spatial translation, and algorithms therefore have separate testable boundaries.
2. **GIS Translation Boundary**: `app/gis/preprocessing.py` converts WGS84 GeoJSON into validated, projected domain objects. Algorithms receive meter-based Points rather than untyped API dictionaries.
3. **External and Internal Models**: Pydantic models define the HTTP contract; frozen dataclasses define internal spatial state. The distinction prevents transport concerns from leaking into algorithms.
4. **Correlation ID (`request_id`)**: Each optimization request carries the Java job-derived identifier and echoes it in the response. The health endpoint has no correlation ID.
5. **Reproducible Environment**: Runtime and tooling versions are pinned in `requirements.txt` and `requirements.lock.txt`; Python behavior targets 3.11 in `pyproject.toml`.

## How the Packages Work Together

```text
FastAPI endpoint
    -> Pydantic OptimisationRequest
    -> OptimisationService
       -> GIS preprocessing
          -> Shapely parsing and validation
          -> pyproj UTM transformation
          -> frozen spatial dataclasses
       -> NetworkX candidate graph
       -> K-Means + SciPy MILP feeder grouping
    -> Pydantic OptimisationResponse
```

The graph and grouping results remain internal. The current response exposes only the feeder count and an empty route FeatureCollection; feeder assignments and graph edges are not yet part of the public contract.

## Implemented and Planned Boundaries

| Package or file | Current behavior |
| --- | --- |
| `app/gis/` | Implemented parsing, geometry repair helper, input validation, UTM selection, and transforms |
| `app/models/spatial.py` | Implemented immutable WTG, substation, and project objects |
| `app/algorithms/route_graph.py` | Implemented complete straight-line candidate graph |
| `app/algorithms/wtg_grouping.py` | Implemented capacity-constrained K-Means/MILP grouping |
| `app/algorithms/cost_function.py` | Planned placeholder only |
| `app/algorithms/electrical_analysis.py` | Planned placeholder only |
| MST, A*, terrain, poles, ROW, ML | Not yet implemented |

## Design Trade-offs

- A complete graph is simple and preserves every direct connection candidate, but grows as `N(N-1)/2` edges and will not scale indefinitely.
- One UTM CRS makes all internal coordinates comparable, but large cross-zone projects need a different projection policy.
- A synchronous endpoint is easy to integrate, but CPU-heavy future solvers should move behind a worker/job boundary.
