# System Architecture Overview

## Purpose

SURGE separates user interaction, application workflow, durable storage, and numerical optimization. This separation lets each part use tools suited to its job: Leaflet for interactive maps, Spring Boot for transactional workflows, PostGIS for spatial persistence, and Python scientific libraries for geometry and optimization.

## Component Model

```text
Browser: Vite + vanilla JavaScript + Leaflet
        |
        | REST and GeoJSON
        v
Java 21 + Spring Boot 3.3.2
        |\
        | \ JDBC/JPA + spatial geometry
        |  v
        | PostgreSQL 16 + PostGIS 3.4
        |
        | POST /api/v1/optimise
        v
Python 3.11 + FastAPI
```

### Web GIS client (`web-map`)

The web client owns presentation and user interaction. It renders WTG, substation, route, cadastral, and restricted-area GeoJSON with Leaflet. It does not perform authoritative engineering calculations. Its API base URL is currently hard-coded to `http://localhost:8080/api/v1`, and several read operations return demonstration data if the backend is unavailable.

### Java backend (`backend-java`)

The Java service is the system of record and workflow boundary. Controllers expose project, asset, parcel, restricted-area, job, route, and report APIs. Services validate requests, use Spring Data repositories for persistence, and call the Python service through `PythonOptimizationClient`.

Optimization job execution is currently synchronous: the POST request remains in the Java call path while Java invokes Python. The stored job changes from `PENDING` to `RUNNING`, then to `COMPLETED` or `FAILED` before the response returns.

### PostGIS database (`db`)

PostGIS stores application records and WGS84 geometry columns. PostgreSQL transactions protect application state; PostGIS geometry types and GiST indexes support spatial storage and later spatial queries. Current migrations store vectors only—there is no DEM raster schema yet.

### Python engine (`optimisation-python`)

The Python service is a stateless computation boundary. It does not access the database or manage users. The implemented pipeline validates Point GeoJSON, translates WGS84 coordinates into one UTM coordinate system, constructs a complete NetworkX graph, and calculates capacity-constrained feeder groups. It currently returns no route geometry.

## Why Separate Java and Python?

- Spring Boot already provides strong patterns for REST APIs, validation, persistence, transactions, and operational configuration.
- Python provides the geospatial, scientific, graph, and optimization libraries needed by the algorithm layer.
- A JSON/GeoJSON HTTP contract prevents Python-specific types from leaking into the Java domain model.
- The cost is an additional network boundary and a contract that both services must maintain.

## Data and Control Flow

### Asset ingestion

1. The browser uploads an RFC 7946 GeoJSON FeatureCollection.
2. Spring Boot identifies asset types, validates values, creates JTS geometries with SRID 4326, and persists them.
3. Later GET requests serialize stored geometries back into GeoJSON for Leaflet.

### Optimization job

1. The browser posts scenario and electrical parameters to `/api/v1/projects/{projectId}/jobs`.
2. Java loads WTGs and substations from PostGIS and builds the Python request.
3. `request_id` is derived from the database job ID so logs and responses can be correlated.
4. Python preprocesses the spatial data, builds a graph, and groups WTGs.
5. Java stores returned metrics in the job result summary and persists route features if any are present.

### Reporting

The report service aggregates fields already stored on generated routes. It does not currently run engineering calculations. Parcel compensation is a placeholder estimate based on parcel geometry area; it is not yet a route-ROW intersection calculation.

## Deployment Boundary

Docker Compose currently defines three services: `db`, `backend`, and `optimizer`. The browser application is run separately with Vite. This is a local development stack, not a complete production deployment.

## Implemented Versus Planned

Implemented behavior is described above. A*, MST route extraction, DEM processing, pole placement, pandapower analysis, ML ranking, JWT/RBAC, asynchronous progress, Kubernetes, and CI/CD are planned capabilities rather than current behavior.

## Related Notes

- [[Backend]]
- [[Python Engine]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]
- [[Frontend]]
- [[Database]]
- [[Deployment]]
- [[Authentication]]
