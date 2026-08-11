# Backend Architecture (Java Spring Boot)

## Role

`backend-java` is the public application API and system-of-record boundary. It owns validation, transactional persistence, project workflows, optimization-job state, route storage, and report aggregation. Numerical spatial optimization is delegated to the Python service.

## Technology

- Java 21 and Spring Boot 3.3.2
- Spring MVC for REST controllers
- Spring Data JPA and Hibernate Spatial for persistence
- PostgreSQL/PostGIS for durable spatial data
- Flyway for ordered schema migrations
- Spring `RestClient` for Java-to-Python HTTP calls
- Maven Wrapper for reproducible build commands

Spring Security, JWT, WebSockets/SSE, PDFBox, and JasperReports are not currently dependencies.

## Layer Responsibilities

### Controllers

Controllers translate HTTP requests and responses. They should remain thin and delegate business rules to services.

- `ProjectController`: create, list, retrieve, and update projects.
- `ProjectAssetController`: import and retrieve WTGs, substations, evacuation towers, reference lines, and KMZ/GeoJSON file packages. Exposes `/assets/kmz/preview` (2-step preview), `/assets/import/commit` (2-step commit), and `/assets/kmz` (1-step import).
- `CadastralParcelController`: import and retrieve parcel polygons.
- `RestrictedAreaController`: import and retrieve exclusion polygons.
- `OptimizationJobController`: create and query optimization jobs.
- `GeneratedRouteController`: store and retrieve 33kV PCN route records and GeoJSON.
- `ReportController`: return BOM summaries, CSV exports, and executive PDF reports.
- `ApiExceptionHandler`: converts expected service errors (`DataIntegrityViolationException`, `IllegalArgumentException`, `ProjectNotFoundException`) into structured JSON API error responses.

### Services

Services contain workflow logic and transaction boundaries.
- `AssetService`: manages 33kV PCN project asset operations, spatial geometry creation, preview/commit staging, automatic external ID deduplication (`ensureUniqueExternalId`), smart fallback classification (`inferTypeFromText`), and persistence for WTGs, substations, evacuation towers, and reference lines.
- `KmzGeoJsonConverter`: converts KMZ/KML survey files into GeoJSON FeatureCollections using XXE-hardened XML parsing, depth-first KML folder tree parsing (`kmlFolderPath`), multi-geometry extraction (`Point`, `LineString`, `Polygon`), and coordinate fingerprint deduplication.
- `AssetClassifier`: rule-driven engine (`AssetClassificationRules`) classifying incoming KMZ/GeoJSON features into 33kV PCN domain types (WTG, Substation, Evacuation Tower, Reference Line, Cadastral Parcel, Restricted Area, Survey Point).
- `OptimizationJobService`: loads project assets, creates a 33kV optimization job, calls Python optimization engine, records returned metrics, and marks the job completed or failed.

### Repositories

Spring Data repositories isolate database access. Includes `WtgLocationRepository`, `SubstationRepository`, `EvacuationTowerRepository`, `ReferenceLineRepository`, `CadastralParcelRepository`, and `RestrictedAreaRepository`.

### Domain entities and DTOs

JPA entities represent persisted state (`WtgLocation`, `Substation`, `EvacuationTower`, `ReferenceLine`, `CadastralParcel`, `RestrictedArea`). DTOs form the external API contract so persistence objects are not serialized directly. JTS geometries represent Points, Polygons, LineStrings, and MultiPoints in Java.

## KMZ Asset Ingestion & Classification Workflow

1. `POST /api/v1/projects/{projectId}/assets/kmz/preview` parses and classifies KMZ/KML features into a staged preview (`AssetImportPreviewResponse`) displaying detected asset types, confidence rules, and folder paths without mutating database state.
2. Users review or override asset types per feature or bulk-assign types by KML folder path in the web-map UI modal.
3. `POST /api/v1/projects/{projectId}/assets/import/commit` persists the staged features into `wtg_locations`, `substations`, `evacuation_towers`, `reference_lines`, `cadastral_parcels`, or `restricted_areas` tables.
4. `POST /api/v1/projects/{projectId}/assets/kmz` provides single-step ingestion with automatic unique external ID generation (`ensureUniqueExternalId`) and smart text inference fallback (`inferTypeFromText`).

## Optimization Job Lifecycle

1. `POST /api/v1/projects/{projectId}/jobs` validates that the project has WTGs and at least one substation for a 33kV Power Collection Network.
2. A database job is saved as `PENDING`, then marked `RUNNING`.
3. Java serializes stored WTG/substation records into WGS84 GeoJSON.
4. `PythonOptimizationClient` posts to `/api/v1/optimise` specifying 33kV voltage parameters.
5. Returned metrics are stored as JSON. Non-empty route features are passed to `RouteService`.
6. The job becomes `COMPLETED` or `FAILED`.

## Reporting Behavior

`ReportService` aggregates length, pole count, cost, and loss fields for 33kV PCN routes. `PdfReportService` generates executive 33kV PDF reports with PDFBox, and CSV exports format BOM summaries.

## Planned Improvements & Backend Task Backlog

- **SURGE-JV-006: KMZ Ingestion & 33kV PCN Multi-Asset Classification** (Completed)
  - Implemented `KmzGeoJsonConverter`, `AssetClassifier`, `EvacuationTowerRepository`, `ReferenceLineRepository`, and Flyway migrations `V4`-`V7`.
- **SURGE-JV-002: Asynchronous Job Execution & Status Polling**
  - Convert blocking optimization calls to Spring `@Async` task execution with status endpoints and SSE event streaming.

## Related Notes

- [[System Overview]]
- [[Python Engine]]
- [[Database]]
- [[Authentication]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]

