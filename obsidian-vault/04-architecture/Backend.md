# Backend Architecture (Java Spring Boot)

Source Code:
`backend/src/`

## Tech Stack
- **Framework**: Java 17, Spring Boot 3.x
- **Database Access**: Spring Data JPA / Hibernate Spatial
- **Security**: Spring Security with JWT tokens
- **Report Generation**: JasperReports / Apache PDFBox

## Core Modules
1. `project-service`: Manages wind farm project metadata, WTG catalog, and substation inputs.
2. `job-orchestrator`: Handles async dispatch of optimization jobs to the Python FastAPI engine.
3. `report-service`: Generates downloadable engineering BOM and line schedule reports.

---

## Related Notes
- [[System Overview]]
- [[Python Engine]]
- [[Database]]
