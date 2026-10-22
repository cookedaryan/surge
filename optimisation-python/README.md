# SURGE GIS Optimization Service (Python Microservice)

FastAPI microservice that does the computation for SURGE: capacity-constrained feeder grouping, MST
topology, A\* routing over a terrain and constraint cost surface, pole placement, pandapower AC load
flow, cable sizing, lifecycle costing, land-impact decisions and candidate scoring. It is stateless and
is called only by the Java backend; it has no authentication of its own and must not be exposed to
the network.

For the design, see [`../docs/architecture/Python Engine - Architecture.md`](../docs/architecture/Python%20Engine%20-%20Architecture.md).
For ticket history and scope, see [`../docs/planning/Surge MVP Ticket Plan.md`](../docs/planning/Surge%20MVP%20Ticket%20Plan.md).
For setup of the whole system, see the [root README](../README.md).

## Endpoints

| Endpoint | Used by |
| --- | --- |
| `GET /api/v1/health` | Docker healthcheck |
| `POST /api/v1/optimise` | The Java backend (`PythonOptimizationClient`). A compatibility request/response that already carries `cable_config`, `costing_config` and `land_context`. |
| `POST /api/v2/optimise` | Nothing in this repository yet. The richer, strictly validated request (`extra="forbid"`) and a top-level four-value `status`. |

OpenAPI docs are served at `/docs` unless `ENVIRONMENT=production`.

## Layout

```text
app/
├── main.py           FastAPI application and router mounting
├── core/             settings (ENVIRONMENT, LOG_LEVEL, API prefixes)
├── api/v1, api/v2    HTTP endpoints
├── schemas/          request/response models; legacy_mapping.py adapts v1 to the workflow
├── gis/              CRS handling, GeoJSON, cost surface, constraint rasterisation, ROW analysis
├── algorithms/       grouping, MST, A*, route refinement, pole placement and micro-siting
├── pnc/              assembly of a validated collector network from topology and routes
├── electrical/       cable sizing, voltage drop, pandapower load flow, repair
├── costing/          lifecycle cost model
├── land/             per-parcel land decisions
├── optimisation/     orchestrator, scenario generation, candidate evaluation, scoring, search
├── presentation/     map-ready result packaging
└── reporting/        decision report builder (tested, not yet exposed over HTTP)
tests/                pytest suite (api/, fixtures/)
scripts/              generate_search_corpus.py
```

## Running locally

Use a virtual environment inside this directory, on Python 3.11 (the version CI and the Docker image
use) or 3.13.

```bash
py -3.11 -m venv .venv && .venv/Scripts/activate   # Windows; use python3.11 -m venv .venv on Linux/macOS
python -m pip install -r requirements.lock.txt
uvicorn app.main:app --reload --port 8000
```

## Checks

These are the commands CI runs:

```bash
python -m ruff check app tests
python -m mypy app
python -m pytest -q
```

## Configuration

Read by `app/core/config.py` from the environment or a local `.env` (see `.env.example`):
`PROJECT_NAME`, `VERSION`, `ENVIRONMENT` (`development`, `testing` or `production`), `LOG_LEVEL`,
`API_V1_PREFIX`, `API_V2_PREFIX`. `ENVIRONMENT=production` turns the OpenAPI docs off. `LOG_LEVEL` is
read but nothing applies it to logging yet.

## Route Refinement

`app/algorithms/route_refinement.py` converts raw A* grid paths into cleaner projected LineStrings. It removes duplicate and collinear coordinates and accepts a visibility shortcut only when its raster supercover contains no blocked cell and its integrated cost does not exceed the subpath it replaces. Exact endpoints and original/refined length and traversal-cost measurements are preserved. Coincident endpoints are rejected as spatially infeasible because they cannot form a non-degenerate refined route.
