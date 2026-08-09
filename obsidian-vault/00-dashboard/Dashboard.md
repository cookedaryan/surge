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
| Python Engine | MILP Grouping & MST Topology Active | Algo Team | Spatial A* Multi-Objective Terrain Routing |
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
   - SURGE-PY-008: Multi-objective A* grid/mesh routing avoiding restricted polygon areas
   - SURGE-PY-009: Convert per-feeder MST edges into routed GeoJSON corridors
   - SURGE-PY-010/011: Terrain-aware pole placement & dynamic span calculation
   - SURGE-PY-012/013: ROW corridor buffering & cadastral parcel compensation calculation
   - SURGE-PY-014: Pandapower electrical load flow & loss analysis integration
   - SURGE-PY-015: ML-based explainable route alternative ranking model

2. ☕ **Backend Java (`backend-java`) Tasks**:
   - SURGE-JV-001: Data Persistence & PostGIS Spatial Model Integration (Flyway V3, Poles, Parcels, Electrical metrics)
   - SURGE-JV-002: Asynchronous Job Processing & Status Polling / SSE (`@Async` task execution)
   - SURGE-JV-003: Engineering BOM & Report Export Service (CSV & PDF report generation)
   - SURGE-JV-004: PostGIS Query Optimization & Spatial Indexing (`ST_Intersects`, `ST_Buffer`, GIST indexes)
   - SURGE-JV-005: Security, API Rate Limiting & Global Exception Handling
   - SURGE-QA-002: Backend Integration & Testcontainers Verification (JUnit 5, PostGIS container testing)

3. 💻 **Web GIS Map (`web-map`) Tasks**:
   - SURGE-FE-001: Multi-Layer Web GIS Visualizer (Color-coded feeder polylines, pole markers, parcel boundaries, restricted areas, slope heatmap)
   - SURGE-FE-002: Route Scenario Comparison & Ranking Dashboard (Side-by-side comparison modal/view)
   - SURGE-FE-003: Real-Time Optimization Status & Async Polling/SSE UI
   - SURGE-FE-004: Interactive Pole/Route Nudging & Incremental Re-validation
   - SURGE-FE-005: Visual Excellence & Micro-Animations (Glassmorphism dark mode UI polish, responsive scaling)
   - SURGE-QA-003: Automated Web Map Testing (Vitest & Playwright E2E testing)

4. 🚀 **DevOps & Verification**:
   - SURGE-QA-004: Full System Integration Suite (`docker-compose` end-to-end verification, performance benchmarking with 50+ WTGs)
   - GitHub Actions CI/CD pipelines for automated testing & Docker container builds


---

## Related Notes
- [[Goals]]
- [[Roadmap]]
- [[Scope]]
- [[Overview & Layout]]
