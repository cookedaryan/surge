# Python Optimization Engine (FastAPI Microservice)

## Role and Boundary

`optimisation-python` is a stateless computation service called by the Java backend. It validates algorithm inputs and performs spatial/optimization work. It does not authenticate users, manage projects, access PostGIS, or persist results.

The HTTP boundary is intentional: Java sends ordinary JSON/GeoJSON and Python returns an ordinary response schema. Shapely geometries, NetworkX graphs, NumPy arrays, and dataclasses remain internal implementation types.

## Current Pipeline

The `/api/v1/optimise` endpoint delegates to `OptimisationService.optimise`:

1. **Schema validation**: Pydantic checks IDs, scenario values, and electrical parameter ranges.
2. **GeoJSON preprocessing**: features are parsed with Shapely; coordinates, identifiers, geometry type, and capacities are validated.
3. **CRS selection**: the arithmetic mean longitude/latitude of all WTGs plus the substation selects one WGS84 UTM CRS.
4. **Domain translation**: projected Points are stored in frozen `WindTurbine`, `Substation`, and `ProjectSpatialData` dataclasses.
5. **Candidate graph**: NetworkX builds a complete undirected graph. Every pair of nodes receives a straight-line metric edge.
6. **WTG grouping**: K-Means provides spatial feeder seeds and SciPy MILP assigns every WTG without exceeding feeder MW capacity.
7. **Response**: the service returns feeder count and projection information, but route GeoJSON is currently empty.

## Why These Layers Exist

- `api/`: HTTP-specific routing and error translation.
- `schemas/`: external request/response contracts using Pydantic.
- `services/`: pipeline orchestration without HTTP details.
- `gis/`: parsing, validation, CRS selection, and transformation.
- `models/`: internal typed spatial entities.
- `algorithms/`: graph and optimization code independent of FastAPI.
- `core/`: environment-based service configuration.
- `utils/`: reusable compatibility helpers.

This layering lets algorithm tests construct `ProjectSpatialData` directly instead of building HTTP payloads, and lets API tests verify contracts without duplicating solver logic.

## Implemented Capabilities

- FastAPI application factory and environment-sensitive OpenAPI pages
- Health and optimization endpoints
- WGS84 Point GeoJSON validation
- Unified per-project UTM selection and projection
- Immutable internal spatial models
- Complete metric candidate graph
- Deterministic capacity-constrained WTG grouping
- Unit tests for GIS, graph, grouping, health, and endpoint behavior

## Partial or Planned Capabilities

- **MST topology**: planned; current graph is complete but not reduced to a feeder tree.
- **A*/Dijkstra routing**: planned; there is no cost grid or obstacle-aware path search.
- **Cost model**: planned; `cost_function.py` is only a module docstring.
- **Electrical analysis**: planned; `electrical_analysis.py` is only a module docstring despite `pandapower` being installed.
- **Pole placement, ROW, terrain, and ML**: planned; no solver modules implement them yet.
- **GeoJSON route output**: the response field exists but contains an empty FeatureCollection.

## Error Boundary

Pydantic validation failures produce HTTP 422 automatically. Expected preprocessing or grouping failures raise `ValueError`; the endpoint catches these and also returns HTTP 422 with the message in `detail`. Unexpected exceptions are not converted by the endpoint and produce the normal server-error path.

## Operational Characteristics

The optimization endpoint is a synchronous Python function. FastAPI provides the HTTP framework but does not make CPU-bound scientific work asynchronous or parallel. Long-running optimization will eventually require bounded workers, resource controls, cancellation, and an asynchronous application workflow.

## Related Notes

- [[System Overview]]
- [[Overview & Layout]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]
- [[Geospatial Integrity & CRS]]
- [[WTG Grouping]]
- [[Routing]]
- [[ADR-005 Python Service Architecture and Schemas]]
- [[ADR-006 Spatial Models and Unified UTM]]
