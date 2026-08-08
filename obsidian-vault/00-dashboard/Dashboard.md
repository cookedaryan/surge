# 00 - SURGE Master Dashboard

Welcome to the **SURGE Knowledge Vault**.

## Quick Navigation

- 🎯 [[Vision]] — Product vision and core capabilities
- 📋 [[Functional Requirements]] — System requirements & user stories
- 🏗️ [[System Overview]] — System architecture & tech stack
- ☕ [[Backend]] — Java Spring Boot backend architecture & REST endpoints
- 💻 [[Frontend]] — Web GIS interactive frontend (`web-map`)
- 🐍 [[Python Engine]] — Python FastAPI microservice architecture & layout
- 🔌 [[FastAPI Microservice Specification]] — REST API endpoints & Pydantic 2 contracts
- 🌐 [[Geospatial Integrity & CRS]] — WGS84 GeoJSON interchange vs Projected CRS calculations
- ⚡ [[Routing]] — Optimization algorithms & feeder planning
- 📜 [[ADR-005 Python Service Architecture and Schemas]] — Architecture Decision Records
- 🔬 [[Paper - Multi Objective Routing]] — Research notes & literature

---

## High-Level Status

| Domain | Status | Owner | Next Milestone |
| --- | --- | --- | --- |
| Architecture | Complete & Containerized | Core Team | E2E Integration Testing |
| Python Engine | Foundation & IPC Ready | Algo Team | Spatial A* Routing & Pandapower Integration |
| Backend API | Full REST API & Report Engine Complete | Backend Team | Async WebSockets / SSE Notifications |
| GIS & Database | PostGIS V1 & V2 Migrations Complete | GIS Team | DEM Elevation Raster Processing |
| Web GIS UI | Interactive Dashboard (`web-map`) Functional | Frontend Team | Multi-Scenario Comparison Matrix |

---

## Key Completed Tasks (Latest Progress)

- ✅ **Flyway DB Migrations (V1 & V2)**: Spatial tables (`projects`, `wtg_locations`, `substations`, `cadastral_parcels`, `restricted_areas`, `optimization_jobs`, `generated_routes`) with GIST indexes and WGS84 (SRID 4326) constraints.
- ✅ **Full Spring Boot REST APIs**:
  - Project management (`/api/v1/projects`)
  - GeoJSON Asset Ingestion (`/api/v1/projects/{projectId}/assets`)
  - Optimization Jobs Orchestration (`/api/v1/projects/{projectId}/jobs`)
  - Generated Routes & GeoJSON Export (`/api/v1/projects/{projectId}/jobs/{jobId}/routes`)
  - Cadastral Parcels & Restricted Avoidance Areas (`/parcels`, `/restricted-areas`)
  - Engineering BOM Report Service & CSV Exporter (`/reports/bom`, `/csv`)
- ✅ **Python IPC Integration**: Spring `RestClient` integration (`PythonOptimizationClient`) connecting backend to Python FastAPI optimizer engine.
- ✅ **Web GIS Map Dashboard (`web-map`)**: Interactive Vite + Leaflet web frontend supporting drag-and-drop GeoJSON upload, live map visualization, parameter sliders, BOM summary cards, and CSV export.
- ✅ **CORS & Environment Setup**: Cross-Origin Resource Sharing configured in Spring Boot (`WebConfig`); Docker Compose (`docker-compose.yml`) & environment configurations (`.env.example`) updated.

---

## Next Steps & Roadmap

1. ⚙️ **Python Optimization Algorithms**:
   - Capacity-constrained WTG clustering (K-Means / Sweep algorithm)
   - Multi-objective A* grid/mesh routing avoiding restricted polygon areas
   - Pandapower electrical load flow & loss analysis integration
   - Terrain-aware pole placement & dynamic span calculation
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
- [[MVP - Minimum Viable Product]]
- [[Overview & Layout]]
