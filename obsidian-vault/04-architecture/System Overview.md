# System Architecture Overview

SURGE uses a microservices architecture separating system orchestration and API management (Java Spring Boot) from computational optimization and spatial math (Python FastAPI Engine).

```text
                               Front-End Client
                       (React / Web GIS Interactive UI)
                                       │
                                 REST / GeoJSON
                                       │
                            Java Spring Boot Backend
            ├── Authentication & User Authorization
            ├── Projects & Workspace Persistence
            ├── Database Management (PostGIS / PostgreSQL)
            ├── File Storage & Management
            ├── Business Workflows & Job Orchestration
            └── Microservice HTTP Gateway
                       │
                       │ REST HTTP (JSON/GeoJSON payload with request_id)
                       ▼
             FastAPI Microservice (Python Engine)
            ├── GIS Validation & Coordinate Transformations
            ├── WTG Grouping & Capacity-Constrained Clustering
            ├── Multi-Objective A* / MST Pathfinding
            ├── Pole Placement & Variable Span Optimization
            ├── ROW Corridor & Cadastral Parcel Analysis
            ├── Pandapower Electrical Load Flow
            └── ML Route Ranking & GeoJSON Result Generation
```

---

## Microservice Responsibility Split

- **Java Spring Boot Backend**: Primary system backend. Manages user authentication, project creation, database persistence, job dispatch, PDF/Excel engineering report generation, and PostGIS storage.
- **Python FastAPI Microservice**: Stateless computation engine. Invoked by Spring Boot to perform GIS spatial calculations, route optimisation algorithms, electrical load-flow analysis, ML inference, and GeoJSON payload generation.
- **PostGIS Database**: Relational and geospatial database serving spatial layers, raster DEMs, and project entities.
- **Web GIS Client**: Interactive frontend for uploading GIS layers, configuring optimization parameters, running scenarios, and visualizing route candidates.

---

## Related Notes
- [[Backend]]
- [[Python Engine]]
- [[FastAPI Microservice Specification]]
- [[Frontend]]
- [[Database]]
- [[Deployment]]
