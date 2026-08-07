# ADR-005: Python Microservice Architecture, Service Layer, and Pydantic 2 Schemas

- **Status**: Approved
- **Date**: 2026-08-06
- **Deciders**: SURGE Engineering Team

## Context
The SURGE Python service handles computationally heavy tasks: GIS processing, route optimization ($A^*$/Dijkstra), electrical load-flow analysis, and ML inference. The original initial draft contained missing router links, older Pydantic 1 nested `Config` classes, mutable dictionary defaults in response models (`metrics: Dict[str, Any] = {}`), unvalidated numeric inputs, and endpoint logic mixed directly in endpoint definitions.

## Decision
1. **Clarified System Boundary**: FastAPI acts strictly as a specialized microservice invoked by Java Spring Boot. Java retains authentication, project workflows, database management, and file storage.
2. **Explicit Application Structure (`app/`)**: Standardized Python package under `app/`:
   - `app/main.py`: Application factory using `create_application()` with environment-aware OpenAPI docs.
   - `app/api/v1/router.py`: `APIRouter` aggregating health and optimise endpoints.
   - `app/services/optimisation_service.py`: Service layer encapsulating pipeline execution.
   - `app/algorithms/`: Decoupled solvers (`route_graph.py`, `cost_function.py`, `electrical_analysis.py`).
   - `app/utils/`: Utility functions (`coordinate_transform.py`).
3. **Pydantic 2 Models & Validation**:
   - `SettingsConfigDict` in `app/core/config.py`.
   - `request_id` correlation ID field across Java Spring Boot and Python.
   - Numeric constraints (`gt=0`, `le=100`, `ge=0`) on `ElectricalParams` and `OptimisationMetrics`.
   - Replaced mutable defaults with `Field(default_factory=OptimisationMetrics)`.
4. **Geospatial Coordinate Standard**: RFC 7946 WGS84 for GeoJSON interchange; projected meter-based CRS for internal spatial math.
5. **Environment Reproducibility**: Locked dependencies via `requirements.lock.txt` and simplified non-root `python:3.11-slim` Docker container.

## Consequences
- **Positive**: Clean separation of concerns, robust input validation (422 responses on invalid scenarios/params), end-to-end request tracing via `request_id`, and repeatable builds.
- **Negative**: Requires maintaining `requirements.lock.txt` alongside `requirements.txt`.
