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
- `ProjectAssetController`: import and retrieve WTGs and substations, including GeoJSON.
- `CadastralParcelController`: import and retrieve parcel polygons.
- `RestrictedAreaController`: import and retrieve exclusion polygons.
- `OptimizationJobController`: create and query optimization jobs.
- `GeneratedRouteController`: store and retrieve route records and GeoJSON.
- `ReportController`: return BOM summaries and CSV exports.
- `ApiExceptionHandler`: converts expected service errors into API responses.

### Services

Services contain workflow logic and transaction boundaries. For example, `OptimizationJobService` loads project assets, creates a job, calls Python, records returned metrics, and marks the job completed or failed.

### Repositories

Spring Data repositories isolate database access. Repository methods are scoped by project or job where required, while services verify that nested resources belong to the requested project.

### Domain entities and DTOs

JPA entities represent persisted state. DTOs form the external API contract so persistence objects are not serialized directly. JTS geometries represent Points, Polygons, LineStrings, and MultiPoints in Java.

## Optimization Job Lifecycle

1. `POST /api/v1/projects/{projectId}/jobs` validates that the project has WTGs and at least one substation.
2. A database job is saved as `PENDING`, then marked `RUNNING`.
3. Java serializes stored WTG/substation records into WGS84 GeoJSON.
4. `PythonOptimizationClient` posts to `/api/v1/optimise`.
5. Returned metrics are stored as JSON. Non-empty route features are passed to `RouteService`.
6. The job becomes `COMPLETED` or `FAILED`.

This flow is synchronous despite the persistent job model: the create-job HTTP request waits for Python. A later asynchronous design should move execution to a queue or worker and expose polling or server-pushed progress.

## Reporting Behavior

`ReportService` aggregates length, pole count, cost, and loss fields already stored on `GeneratedRoute` records. CSV generation formats the same aggregation.

Current parcel compensation is provisional. It estimates the area of each entire parcel using a degrees-to-meters approximation; it does not intersect the route ROW corridor with parcels. It must not be treated as survey-grade compensation output.

## Failure Handling

Python or serialization exceptions are logged and converted into a failed job with an error message. The Java endpoint still returns the stored job response, so callers must inspect job status rather than assuming an HTTP success means optimization succeeded.

## Planned Improvements & Backend Task Backlog

- **SURGE-JV-001: Data Persistence & PostGIS Spatial Model Integration**
  - Flyway database migration `V3` to persist poles, candidate route alternatives, parcel compensation line items, and electrical load flow metrics.
  - Configure Hibernate Spatial types for PostGIS indexing (`GIST(geometry)`).
- **SURGE-JV-002: Asynchronous Job Execution & Status Polling**
  - Convert blocking optimization calls to Spring `@Async` task execution with status endpoints (`/api/v1/jobs/{id}/status` and `/api/v1/jobs/{id}/results`) and SSE event streaming.
- **SURGE-JV-003: Engineering BOM & Export Reporting Service**
  - Implement full BOM calculation: conductor length by type, pole count by type, insulator hardware, parcel compensation total, and estimated annual electrical loss cost.
  - Support exporting BOM reports in CSV and formatted PDF summary formats.
- **SURGE-JV-004: PostGIS Query & Spatial Index Optimization**
  - Implement optimized PostGIS spatial queries using `ST_Intersects`, `ST_Buffer`, `ST_DWithin`, and spatial indexing to rapidly analyze parcel boundaries and restricted areas.
- **SURGE-JV-005: API Security & Robust Exception Handling**
  - Implement global `@ControllerAdvice` for exception handling, request validation, and OpenAPI documentation updates.
- **SURGE-QA-002: Backend Automated Testing & Verification**
  - Unit tests for `OptimizationJobService`, `EngineeringReportService`, DTO mappers, and Flyway migrations.
  - Integration testing with PostGIS queries using `Testcontainers` (PostgreSQL/PostGIS container).

## Related Notes

- [[System Overview]]
- [[Python Engine]]
- [[Database]]
- [[Authentication]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]

