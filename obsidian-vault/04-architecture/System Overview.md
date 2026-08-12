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
            ├── Per-Feeder Euclidean MST Topology (implemented)
            ├── Uniform GIS Cost Surface (implemented foundation)
            ├── Uniform-Surface A* Routing & Refinement (implemented)
            ├── Pole Placement (implemented standalone)
            ├── ROW Corridor & Constraint Analysis (implemented standalone)
            ├── Pandapower Electrical Load Flow
            └── ML Route Ranking & GeoJSON Result Generation
```

---

## Microservice Responsibility Split

- **Java Spring Boot Backend (`backend-java`)**: Primary system orchestrator. Manages user authentication, project workspace lifecycle, PostGIS database persistence, job dispatch, engineering report generation (BOM & CSV), and IPC communication with the Python engine.
- **Python FastAPI Microservice (`optimisation-python`)**: Stateless computation engine invoked by Spring Boot. Its service pipeline currently performs Point validation, UTM projection, feeder grouping, complete-graph construction, per-feeder MST topology, uniform cost-surface routing, and obstacle-safe route refinement. Pole placement and ROW constraint analysis exist as standalone tested modules but are not called by the service because the request/response contract does not yet carry their required inputs or outputs. True terrain routing and Pandapower analysis remain planned.
- **PostGIS Database (`db`)**: Relational and geospatial PostgreSQL 16 + PostGIS 3.4 database serving spatial tables (`wtg_locations`, `substations`, `cadastral_parcels`, `restricted_areas`, `generated_routes`).
- **Web GIS Client (`web-map`)**: Interactive Vite + Leaflet web dashboard for drag-and-drop GeoJSON ingestion, live GIS layer rendering, parameter tweaking, and report download export.

---

## Containerized Local Stack

The system is fully containerized using Docker Compose (`docker-compose.yml`):
- `db`: `postgis/postgis:16-3.4` (Port 5432)
- `backend`: Java 21 Spring Boot service (Port 8080)
- `optimizer`: Python FastAPI microservice (Port 8000)

---

## Related Notes
- [[Backend]]
- [[Python Engine]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]
- [[Frontend]]
- [[Database]]
- [[Deployment]]
