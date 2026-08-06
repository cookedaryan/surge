# Python Optimization Engine (FastAPI Microservice)

Source Directory:
`optimisation-python/app/`

## Responsibility Split
The Python service handles **only**:
- GIS processing and dataset validation
- Capacity-constrained WTG clustering and feeder assignment
- Multi-objective pathfinding ($A^*$ / Dijkstra cost surface routing)
- Minimum Spanning Tree (MST) collector topology generation
- Pole placement and variable-span optimization
- Right-of-Way (ROW) corridor analysis & cadastral parcel compensation
- Electrical load flow simulation via `pandapower`
- Machine Learning inference and explainable route ranking
- Standardized GeoJSON result generation

The Java Spring Boot service remains the primary backend responsible for authentication, user management, project workspace persistence, file management, and workflow orchestration.

---

## Technical Architecture & Directory Structure

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
     +--- test_health.py
     \--- test_optimise.py
```

---

## Tech Stack
- **Framework**: FastAPI (`uvicorn`)
- **Config & Schemas**: Pydantic 2, `pydantic-settings`
- **Spatial Processing**: GeoPandas, Shapely, Rasterio, PyPROJ
- **Electrical Simulation**: `pandapower`
- **Graph Optimization**: NetworkX, SciPy, custom A*
- **ML & Validation**: scikit-learn, `mypy`, `ruff`, `pytest`

---

## Related Notes
- [[System Overview]]
- [[FastAPI Microservice Specification]]
- [[ADR-005 Python Service Architecture and Schemas]]
- [[Routing]]
- [[WTG Grouping]]
- [[Cost Model]]
