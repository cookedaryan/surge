# Testing Strategy and Current Status

## Purpose

Tests provide evidence at different boundaries. A unit test verifies an isolated function or class; an integration test verifies components working together; an end-to-end test follows a user workflow across the browser, backend, database, and optimizer.

## Phase 0 build baseline

The repository standardizes on JDK 21, Python 3.11, Node.js 20, and Docker Compose v2. The root `README.md` contains the supported local commands.

- Java: `cd backend-java; .\mvnw.cmd test`
- Python: `cd optimisation-python; .\.venv\Scripts\python.exe -m ruff check app tests; .\.venv\Scripts\python.exe -m mypy app; .\.venv\Scripts\python.exe -m pytest -q`
- Frontend: `cd web-map; npm ci; npm test; npm run build`
- Full stack: `docker compose up --build`, then inspect the Java actuator and Python health endpoints.

The root GitHub Actions workflow runs these component checks and verifies the Docker image builds on every push and pull request. Full browser-to-PostGIS-to-Python acceptance coverage remains a later MVP task.

## Python Service

The Python suite uses pytest and FastAPI's test client.

- GIS tests cover CRS selection, GeoJSON parsing, geometry repair, and preprocessing validation.
- Graph tests cover node identifiers, graph metadata, complete edge construction, and metric distances.
- Grouping tests cover capacity constraints, determinism, invalid values, and multi-feeder behavior.
- Endpoint tests cover health, scenario validation, parameters, and invalid GeoJSON.
- Electrical tests cover finite input/configuration validation, three-phase current and impedance primitives, lagging/leading linear voltage change, radial downstream aggregation, project/topology/route reconciliation, route endpoint continuity, operating-factor consistency, and ampacity/voltage/substation limits.

Run from `optimisation-python`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### Verification snapshot: 2026-08-12

The Python suite produced 256 passes. Strict mypy reported no issues in 40 application source files, and Ruff reported no lint errors across `app` and `tests`. Two non-failing environment/dependency warnings remain: Starlette's current test client compatibility warning and joblib's physical-core detection fallback.

The electrical stage is tested as a standalone domain module. There is no endpoint or cross-service test for it because `OptimisationService` and the public response contract do not yet carry electrical results.

## Java Backend

The backend contains domain, service, repository, and MockMvc controller tests. The Maven Wrapper is the repository-provided entry point:

```powershell
cd backend-java
.\mvnw.cmd test
```

Java tests were not rerun during the documentation rewrite, so this note does not claim a current pass count.

## Frontend

`web-map` currently has build scripts but no automated test suite. Important future coverage includes API error states, demo-mode separation, GeoJSON upload validation, popup sanitization, layer toggles, and job progress behavior.

## Missing Cross-System Validation

- Docker Compose startup/health integration test
- Browser-to-Java-to-PostGIS asset workflow
- Java-to-Python contract test using representative projects
- Route persistence once Python returns non-empty features
- Migration tests against real PostGIS rather than only substitute databases
- Performance tests for graph/grouping size limits
- Deterministic reproducibility test recording inputs, versions, and outputs

## Related Notes

- [[System Overview]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]
- [[Python Engine]]
- [[Backend]]
