# SURGE Knowledge Dashboard

SURGE (Smart Utility Routing and Grid Evacuation) is a platform for designing and evaluating wind-farm collector networks. The repository combines a browser-based GIS interface, a Java application service, a spatial database, and a Python optimization service.

## How to Read This Vault

Implementation notes use three status labels:

- **Implemented**: executable code exists in the repository.
- **Partial**: an interface or foundation exists, but the engineering calculation or workflow is incomplete.
- **Planned**: a design decision or target capability exists, but no working implementation exists yet.

Historical journal entries describe the repository at the time they were written and may use older directory names.

## Start Here

- [[Vision]] — product purpose and long-term capabilities
- [[Scope]] — current MVP boundary and future scope
- [[System Overview]] — components, responsibilities, and end-to-end flow
- [[Backend]] — Spring Boot orchestration and persistence
- [[Frontend]] — Vite, vanilla JavaScript, and Leaflet client
- [[Python Engine]] — FastAPI computation service
- [[Overview & Layout]] — Python package structure and execution pipeline
- [[FastAPI Endpoints|FastAPI Microservice Specification]] — current Python HTTP contract
- [[Geospatial Integrity & CRS]] — coordinate-system rules and implementation
- [[Database]] — PostGIS schema and spatial storage
- [[Deployment]] — current local deployment model
- [[Authentication]] — planned security boundary
- [[Testing Status]] — test layers, commands, and known gaps

## Current Implementation Status

| Area | Status | What Works Now | Important Limitation |
| --- | --- | --- | --- |
| Web GIS | Implemented with demo fallbacks | Projects, GeoJSON upload, Leaflet layers, job submission, BOM display, CSV link | API failures can fall back to demonstration data; progress is simulated |
| Java backend | Implemented foundation | CRUD-style project/assets APIs, PostGIS persistence, job dispatch, route storage, BOM/CSV aggregation | Job execution is synchronous; no authentication or PDF report generation |
| PostGIS | Implemented | Flyway V1/V2 tables, SRID 4326 geometry constraints, GiST indexes | DEM/raster storage and migrations are not implemented |
| Python GIS boundary | Implemented | GeoJSON parsing, Point validation, unified UTM selection, immutable spatial models | Only WTG and one substation are accepted by the optimization endpoint |
| WTG grouping | Implemented | Capacity-aware grouping with K-Means seeds and a MILP assignment | Group assignments are not returned by the public response schema |
| Candidate graph | Implemented | Complete undirected graph with metric Euclidean edge weights | It is not yet converted into an MST or routed around constraints |
| Route generation | Partial | Response schema and empty GeoJSON FeatureCollection exist | No A*, MST, cost-surface, or route geometry generation yet |
| Electrical analysis | Planned | Module boundary and dependency exist | `electrical_analysis.py` contains no load-flow implementation |
| Cost, ROW, poles, ML | Planned | Concepts and module placeholders are documented | No solver implementation exists yet |
| Deployment | Partial | Docker Compose runs PostGIS, backend, and optimizer | The web client is not containerized; no Kubernetes or CI/CD files exist |

## Current End-to-End Flow

1. The browser sends project and GeoJSON requests to Spring Boot at `/api/v1`.
2. Spring Boot validates and persists WGS84 geometries in PostGIS.
3. Creating an optimization job causes Spring Boot to build a Python request and synchronously call `/api/v1/optimise`.
4. Python validates the GeoJSON, chooses one UTM CRS, builds a complete candidate graph, and groups WTGs by feeder capacity.
5. Python currently returns an empty route collection plus grouping metrics.
6. Spring Boot records the job result. Route persistence only occurs when Python returns non-empty route features.
7. The web client refreshes assets, routes, and BOM data; when calls fail, some reads use local demo data.

## Next Engineering Milestones

1. Produce feeder topology and route geometries from the candidate graph.
2. Add restricted-area and terrain-aware cost-surface routing.
3. Add pole placement, ROW intersections, and accurate parcel compensation.
4. Add electrical validation and lifecycle-cost scoring.
5. Replace simulated frontend progress with real asynchronous status updates.
6. Add authentication, authorization, CI, and production deployment configuration.

## Related Notes

- [[Goals]]
- [[Roadmap]]
- [[ADR-005 Python Service Architecture and Schemas]]
- [[ADR-006 Spatial Models and Unified UTM]]
