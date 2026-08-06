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
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application factory
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py               # Pydantic 2 Settings (BaseSettings)
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py           # APIRouter combining endpoints
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── health.py       # Health check endpoint (/api/v1/health)
│   │           └── optimise.py     # Optimisation endpoint (/api/v1/optimise)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── optimise.py             # Pydantic 2 request/response models & validation
│   ├── services/
│   │   ├── __init__.py
│   │   └── optimisation_service.py # Optimisation business logic layer
│   ├── algorithms/
│   │   ├── __init__.py
│   │   ├── route_graph.py          # Route graph & A* pathfinding
│   │   ├── cost_function.py        # Terrain & cost surface logic
│   │   └── electrical_analysis.py  # Electrical load-flow solvers
│   └── utils/
│       ├── __init__.py
│       └── coordinate_transform.py # WGS84 GeoJSON <-> Meter Projected CRS
├── tests/
│   ├── __init__.py
│   ├── test_health.py
│   └── test_optimise.py
├── .env.example
├── .dockerignore
├── .gitignore
├── AGENTS.md                       # LLM agent instructions & constraints
├── Dockerfile                      # Python 3.11 slim non-root container
├── pyproject.toml
├── requirements.txt
├── requirements.lock.txt            # Pin-locked reproducible environment
└── README.md
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
