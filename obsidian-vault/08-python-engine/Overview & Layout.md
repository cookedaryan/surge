# Python Microservice Overview & Layout

The **SURGE Python GIS & Optimization Service** provides high-performance spatial algorithms and electrical calculations for the SURGE platform.

## Directory Layout

```text
optimisation-python/
+--- .dockerignore
+--- .env.example
+--- .gitignore
+--- AGENTS.md
+--- CONTEXT.md
+--- Dockerfile
+--- README.md
+--- app
|    +--- __init__.py
|    +--- algorithms
|    |    +--- __init__.py
|    |    +--- cost_function.py
|    |    +--- electrical_analysis.py
|    |    \--- route_graph.py
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
     \--- test_optimise.py
```

## Key Architectural Principles

1. **Decoupled Service Layer**: Endpoint functions in `app/api/v1/endpoints/optimise.py` delegate execution to `OptimisationService` in `app/services/optimisation_service.py`. Algorithms reside in `app/algorithms/`.
2. **GIS & Preprocessing**: The `app/gis/preprocessing.py` layer converts incoming WGS84 GeoJSON API objects into strictly-validated metric point entities (`app/models/spatial.py`), completely decoupling the algorithm logic from standard HTTP GeoJSON structures.
3. **Pydantic 2 Validation**: Model configuration uses `SettingsConfigDict` and typed models (`OptimisationMetrics`, `ElectricalParams`, `OptimisationRequest`, `OptimisationResponse`).
4. **Correlation ID (`request_id`)**: Every request carries a `request_id` passed from Spring Boot to enable end-to-end tracing across service logs.
5. **Reproducible Environment**: Dependencies are locked via `requirements.lock.txt`.
