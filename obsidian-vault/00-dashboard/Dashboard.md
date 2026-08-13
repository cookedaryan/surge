# 00 - SURGE Master Dashboard

Welcome to the **SURGE Knowledge Vault**.

## Quick Navigation

- 🎯 [[Vision]] — Product vision and core capabilities
- 📋 [[Functional Requirements]] — System requirements & user stories
- 🏗️ [[System Overview]] — System architecture & tech stack
- ☕ [[Backend]] — Java Spring Boot backend architecture & REST endpoints
- 💻 [[Frontend]] — Web GIS interactive frontend (`web-map`)
- 🐍 [[Python Engine]] — Python FastAPI microservice architecture & layout
- 🔌 [[FastAPI Endpoints|FastAPI Microservice Specification]] — REST API endpoints & Pydantic 2 contracts
- 🌐 [[Geospatial Integrity & CRS]] — WGS84 GeoJSON interchange vs Projected CRS calculations
- ⚡ [[Routing]] — Optimization algorithms & feeder planning
- 📜 [[ADR-005 Python Service Architecture and Schemas]] — Architecture Decision Records
- 🔬 [[Paper - Multi Objective Routing]] — Research notes & literature

---

## High-Level Status

| Domain | Status | Owner | Next Milestone |
| --- | --- | --- | --- |
| Architecture | Complete & Containerized | Core Team | End-to-End E2E Integration Suite |
| Python Engine | PY-014-PY-017 Complete; PY-018 In Progress | Algo Team | PY-018 Scoring + Recommendation |
| Backend API | JWT Auth, SSE Streaming & Audit Logs Ready | Backend Team | Pandapower Load Flow Integration |
| GIS & Database | PostGIS V1-V3 Schema & Spatial Queries Ready | GIS Team | DEM Elevation Raster Processing |
| Web GIS UI | GeoJSON Drag & Drop & Map Rendering Active | Frontend Team | Interactive Point-to-Point Line Drawing |

---

## Key Completed Tasks (Latest Progress)

- ✅ **Web GIS Map GeoJSON Ingestion (`web-map`)**: Fixed Leaflet script loading order in `index.html` and upgraded map overlay groups to `L.featureGroup()` in `map.js` for automatic bounding box fitting across all imported features. Added null guards in `app.js` for event binding reliability.
- ✅ **Gujarat Kutch Mock Datasets (`/public/data/`)**: Created 4 realistic GeoJSON datasets (`wtgs_kutch.geojson`, `substations_kutch.geojson`, `parcels_kutch.geojson`, `restricted_kutch.geojson`) centered on the Gujarat Kutch wind corridor.
- ✅ **33kV Route Optimization Pipeline**: Documented the full 5-phase data flow spanning Frontend parameter sliders → Java Spring Boot orchestrator → Python FastAPI MILP/MST solver → PostGIS geometry persistence → Leaflet map rendering.
- ✅ **Enterprise Security & Audit Logging**: Built JWT authentication (`JwtTokenProvider`, `JwtAuthenticationFilter`, `AuthService`), SSE real-time job progress streaming (`SseProgressService`), PDF report exporter (`PdfReportService`), and system audit trail logging (`AuditLogService`).
- ✅ **Flyway DB Migrations (V1, V2, V3)**: Spatial tables (`projects`, `wtg_locations`, `substations`, `cadastral_parcels`, `restricted_areas`, `optimization_jobs`, `generated_routes`, `users`, `audit_logs`) with GIST indexes and WGS84 (SRID 4326) constraints.
- ✅ **Full Spring Boot REST APIs**:
  - Project management (`/api/v1/projects`)
  - GeoJSON Asset Ingestion (`/api/v1/projects/{projectId}/assets`)
  - Optimization Jobs Orchestration (`/api/v1/projects/{projectId}/jobs`)
  - Real-Time SSE Progress Stream (`/api/v1/projects/{projectId}/jobs/{jobId}/events`)
  - Generated Routes & GeoJSON Export (`/api/v1/projects/{projectId}/jobs/{jobId}/routes`)
  - Cadastral Parcels & Restricted Avoidance Areas (`/parcels`, `/restricted-areas`)
  - Engineering BOM & Executive PDF Reports (`/reports/bom`, `/csv`, `/pdf`)
  - User Authentication & Audit Logs (`/api/v1/auth`, `/api/v1/audit-logs`)
- ✅ **Docker Containerization & Git Hygiene**: Multi-container Docker Compose setup (`surge-web-map`, `surge-backend-java`, `surge-postgis`, `surge-optimizer-python`). Merged feature branch `fix/geojson-map-rendering` into `main` and pushed to remote GitHub repository (`cookedaryan/surge`).

---

## Next Steps & Roadmap

1. ⚙️ **Python Optimization Algorithms**:
   - Use the completed PY-018 recommendation and PY-019 orchestrator boundaries
   - `/api/v1/optimise` now exposes the orchestrator additively; `/api/v2/optimise` provides explicit engineering configuration; the three-candidate PY-020 golden fixture is validated (**Complete**)
   - Keep raw terrain/restriction rasterization and ML ranking post-MVP
2. 🔄 **Backend Enhancements**:
   - Async job execution with WebSocket / SSE progress updates
   - Side-by-side multi-scenario comparison endpoints
   - JWT Spring Security & RBAC authorization
   - PDF engineering report export (Apache PDFBox / JasperReports)
3. 🗺️ **Web GIS UI Enhancements**:
   - Multi-scenario comparison side-by-side UI
   - Manual vertex editing and route line tweaking on Leaflet map
   - Elevation profile graphs for route paths
4. 🚀 **DevOps & Verification**:
   - End-to-end integration test suite (Web UI -> Spring Boot -> PostGIS -> Python Engine)
   - GitHub Actions CI/CD pipelines for automated testing & Docker container builds

---

## Related Notes
- [[Goals]]
- [[Roadmap]]
- [[Scope]]
- [[Overview & Layout]]
- [[Surge MVP Ticket Plan]]
- [Sunday KMZ to 33 kV Network Plan](../08-python-engine/Sunday%20KMZ%20to%2033kV%20Network%20Plan.md)
