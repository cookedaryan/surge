# SURGE GIS Optimization Service (Python Microservice)

FastAPI microservice dedicated to GIS processing, route optimisation, electrical analysis, ML inference, and GeoJSON result generation for the SURGE project.

## Project Structure

```text
optimisation-python/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── health.py
│   │           └── optimise.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── optimise.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── optimisation_service.py
│   ├── gis/
│   │   ├── __init__.py
│   │   ├── crs.py
│   │   ├── geojson.py
│   │   ├── geometry.py
│   │   └── preprocessing.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── spatial.py
│   ├── algorithms/
│   │   ├── __init__.py
│   │   ├── route_graph.py
│   │   ├── cost_function.py
│   │   └── electrical_analysis.py
│   └── utils/
│       ├── __init__.py
│       └── coordinate_transform.py
├── tests/
│   ├── __init__.py
│   ├── test_health.py
│   └── test_optimise.py
├── .env.example
├── .dockerignore
├── .gitignore
├── AGENTS.md
├── Dockerfile
├── pyproject.toml
├── requirements.txt
├── requirements.lock.txt
└── README.md
```

## Running Locally

```bash
uvicorn app.main:app --reload --port 8000
```

## Running Tests

```bash
pytest
```

## Route Refinement

`app/algorithms/route_refinement.py` converts raw A* grid paths into cleaner projected LineStrings. It removes duplicate and collinear coordinates and accepts a visibility shortcut only when its raster supercover contains no blocked cell and its integrated cost does not exceed the subpath it replaces. Exact endpoints and original/refined length and traversal-cost measurements are preserved. Coincident endpoints are rejected as spatially infeasible because they cannot form a non-degenerate refined route.
