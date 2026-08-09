# Testing Strategy and Current Status

## Purpose

Tests provide evidence at different boundaries. A unit test verifies an isolated function or class; an integration test verifies components working together; an end-to-end test follows a user workflow across the browser, backend, database, and optimizer.

## Python Service

The Python suite uses pytest and FastAPI's test client.

- GIS tests cover CRS selection, GeoJSON parsing, geometry repair, and preprocessing validation.
- Graph tests cover node identifiers, graph metadata, complete edge construction, and metric distances.
- Grouping tests cover capacity constraints, determinism, invalid values, and multi-feeder behavior.
- Endpoint tests cover health, scenario validation, parameters, and invalid GeoJSON.

Run from `optimisation-python`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

### Verification snapshot: 2026-08-08

The suite produced 56 passes and one failure. `test_optimise_stub` expects a request without WTG `capacity_mw` to succeed, but the implemented grouping stage requires a positive WTG capacity and returns HTTP 422. This is test/contract drift; the maintained API documentation now records capacity as required by the current pipeline.

The documented one-WTG API example was executed separately and returned HTTP 200 with feeder count 1 and the expected UTM projection message.

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
