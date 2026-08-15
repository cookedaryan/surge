# Development Roadmap

> **Current Status (2026-08-16):** Phases 1 through 3 are fully completed and verified against the golden Uravakonda wind farm dataset. Phase 4 (Production Readiness & Security Hardening) is in the final release stages, while Phase 5 outlines planned post-MVP capabilities.

---

## Master Development Timeline

```mermaid
gantt
    title SURGE Platform Development Roadmap
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d

    section Phase 1: Foundation & Stack
    Repository Setup & Architecture Vault       :done, 2026-08-01, 2026-08-07
    PostGIS Schema (Flyway V1–V3)              :done, 2026-08-01, 2026-08-08
    Java API & Async Foundation                 :done, 2026-08-04, 2026-08-08
    Docker Compose Containerization             :done, 2026-08-05, 2026-08-08

    section Phase 2: Python Optimizer Pipeline
    GIS Models & Spatial Transformations        :done, 2026-08-04, 2026-08-08
    Capacity WTG Grouping & Feeder MST          :done, 2026-08-08, 2026-08-11
    Cost-Surface A* & Path Refinement           :done, 2026-08-09, 2026-08-12
    4-Class Dynamic Pole Placement              :done, 2026-08-11, 2026-08-13
    Pandapower AC Load Flow & Screening         :done, 2026-08-12, 2026-08-14

    section Phase 3: Multi-Scenario & Web GIS
    Multi-Objective Candidate Scoring (PY-018)  :done, 2026-08-13, 2026-08-15
    25-Year Decimal Lifecycle Costing (PY-028)  :done, 2026-08-14, 2026-08-15
    Flyway Migrations (V4–V13) & Persistence    :done, 2026-08-14, 2026-08-15
    React 18 Web GIS UI (`web-map-next`)        :done, 2026-08-13, 2026-08-16
    Real-Time SSE Streaming & Explainability   :done, 2026-08-15, 2026-08-16

    section Phase 4: Production Hardening
    JWT Token & User Lockout Hardening          :done, 2026-08-15, 2026-08-16
    Security Audit Logs & Admin Portal          :done, 2026-08-15, 2026-08-16
    Golden Dataset Acceptance Testing           :done, 2026-08-15, 2026-08-16
    Rate Limiting & Production TLS Setup        :active, 2026-08-16, 2026-08-20

    section Phase 5: Post-MVP Enhancements
    Dynamic GeoTIFF DEM Rasterizer              :2026-08-21, 2026-09-05
    Machine Learning Route Surrogate Ranker     :2026-09-01, 2026-09-20
    3D Line Sag & Terrain Profile Visualizer    :2026-09-15, 2026-09-30
```

---

## Detailed Milestone Delivery Summary

### Milestone 1: Core Architecture, Database & Baseline Containerization
> [!success] **Completed: 2026-08-08**
- **Database & Spatial Storage**: Deployed PostgreSQL 16 + PostGIS 3.4 with Flyway migrations establishing spatial schemas with GIST indexing and WGS84 (`SRID 4326`) geometry constraints.
- **Java Orchestrator Baseline**: Spring Boot 3.3.2 application foundation with project entity CRUD, DTO validation, and basic REST endpoints.
- **Python Microservice Baseline**: FastAPI microservice with Pydantic v2 schemas and health probes.
- **DevOps Baseline**: Multi-container Docker Compose file (`docker-compose.yml`) orchestrating 4 services with integrated healthchecks and automated CI workflow in `.github/workflows/ci.yml`.

### Milestone 2: Algorithmic Routing, Pole Placement & Electrical Validation
> [!success] **Completed: 2026-08-12**
- **Spatial Preprocessing**: Automatic EPSG UTM zone projection (`EPSG:32643` / `EPSG:32644`), geometry buffering, and multi-layer avoidance boundaries (roads, watercourses, high-tension lines, forest parcels).
- **WTG Grouping**: Capacity-constrained clustering via balanced K-Means and Mixed-Integer Linear Programming (MILP).
- **Network Topology**: Per-feeder radial Minimum Spanning Tree (MST) topology generation.
- **Spatial Pathfinding**: Cost-surface $A^*$ grid pathfinding with farthest-visible shortcutting line refinement.
- **Structural Pole Engineering**: Variable-span pole placement algorithm supporting 4 classes (Tangent, Angle, Junction, Terminal) with slope checks ($\le 30^\circ$) and coordinate deduplication.
- **Electrical Verification**: Newton-Raphson Pandapower AC load flow simulation and linear electrical screening enforcing $V_{\text{drop}} \le 5.0\%$ and thermal limits.

### Milestone 3: Multi-Scenario Engine, Full Lifecycle Costing & Modern Web GIS
> [!success] **Completed: 2026-08-16**
- **4 Real Deterministic Scenarios**: Implemented `ScenarioProfile` domain model driving distinct mathematical outcomes: Balanced, Minimum Cost, Minimum Land Impact, and Minimum Environmental Impact.
- **Multi-Objective Scoring & Explainability**: PY-018 weighted score decomposition, canonical candidate engineering metrics (PY-026), and frontend "Why this route?" decision breakdown card.
- **High-Precision Lifecycle Costing (PY-028)**: 25-year `Decimal` LCC calculation incorporating CAPEX (cables, 4 pole classes, civil works), ROW parcel compensation, and NPV of technical line losses.
- **Database Schema Expansion**: Applied Flyway migrations **V4 through V13** to persist poles, parcel impacts, electrical results, and user audit trails.
- **Modern Web GIS UI (`web-map-next`)**: Built complete React 18 + TypeScript + Vite + Leaflet Canvas client with TanStack Query v5, Zustand v4, Radix UI modals, interactive BOM pane, and real-time SSE progress streaming.
- **Enterprise Reporting**: Apache PDFBox executive PDF engineering report generation and CSV Bill of Materials export.

### Milestone 4: Security Hardening & Release Verification (Current)
> [!note] **Active: Target Completion 2026-08-20**
- **Security Hardening**: Enforced mandatory `APP_JWT_SECRET`, database-backed token active checks, admin lockout protection, and structured audit logs (`/api/v1/audit-logs`).
- **Comprehensive Quality Assurance**: Verified 209 Java backend tests, ~489 Python optimizer tests, and 26 frontend Vitest tests.
- **Golden Benchmark Acceptance**: End-to-end verification against real Uravakonda wind survey dataset.
- **Remaining Production Tasks**: Configure login rate limiting, TLS reverse proxy termination, and KMZ upload parser hardening.

### Milestone 5: Post-MVP & Next-Gen Capabilities (Future)
> [!tip] **Planned: Q3 / Q4 2026**
- **Real-Time DEM Rasterizer**: Dynamic on-the-fly GeoTIFF digital elevation model processing for continuous slope cost surfaces.
- **ML Route Surrogate Ranker**: Deep learning heuristic model trained on historical EPC wind farm topologies to accelerate candidate generation.
- **3D Terrain & Sag Visualizer**: WebGL/Three.js 3D profile viewer showing conductor catenary sag, tower heights, and minimum ground clearance under maximum ambient temperatures.
- **Ring / Mesh Collector Topology**: Support for looped collector configurations with automated tie-breaker switchgear placement.

---

## Related Notes

- 🎯 **Vision & Goals**: [[Vision]] · [[Goals]] · [[Scope]]
- 📋 **Requirements**: [[Functional Requirements]] · [[Non Functional Requirements]] · [[Constraints]]
- 🏗️ **Architecture**: [[System Overview]] · [[Backend]] · [[Python Engine]] · [[Frontend]] · [[Database]]
- 🧪 **Testing Status**: [[Testing Status]] · [[MVP Execution Plan - Frontend & Java]]
- 📜 **ADRs**: [[ADR-001 Use FastAPI]] · [[ADR-004 Lifecycle Cost Objective]] · [[ADR-007 Pandapower AC Load Flow Validation]]
