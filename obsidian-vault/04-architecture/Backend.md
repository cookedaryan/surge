# Backend Architecture (Java Spring Boot)

Source Code:
`backend-java/src/`

## Tech Stack
- **Framework**: Java 21, Spring Boot 3.3.x
- **Database Access**: Spring Data JPA / Hibernate Spatial
- **Security**: Spring Security with JWT tokens
- **Report Generation**: JasperReports / Apache PDFBox

## Core Modules
1. `project-service`: Manages wind farm project metadata, WTG catalog, and substation inputs.
2. `job-orchestrator`: Handles async dispatch of optimization jobs to the Python FastAPI engine.
3. `report-service`: Generates downloadable engineering BOM and line schedule reports.

## Current Foundation (2026-08-08)

- **Flyway Database Migrations (V1 & V2)**:
  - `V1__create_project_workspace.sql`: Provisions PostGIS extension, `projects`, `wtg_locations`, and `substations`.
  - `V2__create_optimization_and_gis_tables.sql`: Provisions `cadastral_parcels`, `restricted_areas`, `optimization_jobs`, and `generated_routes` with GIST spatial indexes and SRID 4326 checks.
- **Domain Persistence & JTS Geometries**:
  - JPA entities map all workspace & spatial layers (`Project`, `WtgLocation`, `Substation`, `CadastralParcel`, `RestrictedArea`, `OptimizationJob`, `GeneratedRoute`).
- **Implemented REST APIs**:
  1. `ProjectController` (`/api/v1/projects`): Workspace creation, listing, retrieval, update.
  2. `ProjectAssetController` (`/api/v1/projects/{projectId}/assets`): RFC 7946 GeoJSON `FeatureCollection` ingestion & WTG/Substation asset retrieval.
  3. `OptimizationJobController` (`/api/v1/projects/{projectId}/jobs`): Optimization job dispatch & status tracking.
  4. `GeneratedRouteController` (`/api/v1/projects/{projectId}/jobs/{jobId}/routes`): Route persistence, LineString/MultiPoint geometry transformation, Haversine distance verification, and GeoJSON export.
  5. `CadastralParcelController` & `RestrictedAreaController` (`/parcels`, `/restricted-areas`): Spatial polygon ingestion & retrieval.
  6. `ReportController` (`/reports/bom`, `/csv`): Engineering Bill of Materials calculation & downloadable CSV exporter.
- **IPC Client**:
  - `PythonOptimizationClient` built with Spring 6.1 `RestClient` targeting Python FastAPI microservice.
- **CORS Support**:
  - `WebConfig` configured to allow Web GIS frontend origins.

## Next Backend Tasks

1. **Async Job Orchestration**: Real-time progress updates via WebSockets or Server-Sent Events (SSE) for long-running optimization jobs.
2. **Multi-Scenario Analytics**: Endpoints to compare candidate routes across scenarios (cost, power loss, land ROW impact).
3. **Security Integration**: Spring Security JWT authentication & RBAC.
4. **PDF Report Generation**: Apache PDFBox / JasperReports engine integration for formal PDF engineering reports.

---

## Related Notes
- [[System Overview]]
- [[Python Engine]]
- [[Database]]
