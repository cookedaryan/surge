# Python Microservice Overview & Layout

The **SURGE Python GIS & Optimization Service** provides high-performance spatial algorithms and electrical calculations for the SURGE platform.

## Directory Layout

```text
optimisation-python/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Application factory (FastAPI)
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py               # Pydantic 2 BaseSettings configuration
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py           # Includes health and optimise routers
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── health.py       # GET /api/v1/health
│   │           └── optimise.py     # POST /api/v1/optimise
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── optimise.py             # Request, Response, Metrics & Electrical Pydantic 2 models
│   ├── services/
│   │   ├── __init__.py
│   │   └── optimisation_service.py # Core service orchestration layer
│   ├── algorithms/
│   │   ├── __init__.py
│   │   ├── route_graph.py          # A* / Dijkstra pathfinding & MST graphs
│   │   ├── cost_function.py        # Geospatial cost surface calculations
│   │   └── electrical_analysis.py  # Pandapower load flow & voltage drop solvers
│   └── utils/
│       ├── __init__.py
│       └── coordinate_transform.py # WGS84 GeoJSON <-> Projected meter CRS
├── tests/
│   ├── __init__.py
│   ├── test_health.py
│   └── test_optimise.py
├── .env.example
├── .dockerignore
├── .gitignore
├── AGENTS.md                       # Directive & constraint rules for LLM agents
├── Dockerfile                      # Non-root slim Docker image
├── pyproject.toml                  # Ruff, mypy & pytest settings
├── requirements.txt                # Abstract editable requirements
├── requirements.lock.txt            # Concrete locked environment dependencies
└── README.md
```

## Key Architectural Principles

1. **Decoupled Service Layer**: Endpoint functions in `app/api/v1/endpoints/optimise.py` delegate execution to `OptimisationService` in `app/services/optimisation_service.py`. Algorithms reside in `app/algorithms/`.
2. **Pydantic 2 Validation**: Model configuration uses `SettingsConfigDict` and typed models (`OptimisationMetrics`, `ElectricalParams`, `OptimisationRequest`, `OptimisationResponse`).
3. **Correlation ID (`request_id`)**: Every request carries a `request_id` passed from Spring Boot to enable end-to-end tracing across service logs.
4. **Reproducible Environment**: Dependencies are locked via `requirements.lock.txt`.
