# SURGE Project Context

This file serves as the single source of truth regarding the implementation status and recent updates across the SURGE platform.

## Latest Updates (as of August 8, 2026)

**1. Java Backend (`backend-java`)**
- Completed Flyway Database Migration V2 (`V2__create_optimization_and_gis_tables.sql`).
- Created domain entities for `CadastralParcel`, `RestrictedArea`, `OptimizationJob`, and `GeneratedRoute` with PostGIS WGS84 SRID 4326 validation.
- Built Spring Data Repositories and full domain unit tests.
- Implemented GeoJSON Ingestion for WTGs and Substations.
- Developed the `OptimizationJobService` orchestrator that communicates with the Python engine via `http://optimizer:8000/api/v1/optimise`.
- Exposed REST endpoints for generated routes, cadastral parcels, and restricted areas.
- Built the Engineering Report Service (`report-service`) to calculate network totals (length, pole count, capex cost, electrical losses, ROW compensation) and generate CSV BOMs.

### 2026-08-08 — SURGE-PY-004 Built NetworkX Collector Graph Layer

**Changed:**
- Added: `app/algorithms/route_graph.py` with Euclidean undirected candidate topology generator.
- Added: `tests/test_route_graph.py` covering metric translation, edge counting, uniqueness constraints, and CRS attribution.

**Reason:**
- The MST algorithms need a deterministically sized foundational topological graph space initialized with metric Cartesian distances before GIS penalty surfaces are overlaid.

**Result:**
- `build_project_graph` turns `ProjectSpatialData` into a `networkx.Graph` complete candidate network. All node logic, Euclidean weights, and typing validations are strictly tested.

**Pending:**
- Generate per-feeder Minimum Spanning Tree topology (SURGE-PY-006).

### 2026-08-08 — SURGE-PY-005 Built Capacity-Constrained WTG Grouping

**Changed:**
- Added: `app/algorithms/wtg_grouping.py` using KMeans and greedy rebalancing.
- Added: `tests/test_wtg_grouping.py` covering capacities, bins, determinism, spatial clustering.

**Reason:**
- The network requires WTGs to be split into capacity-constrained feeders before MST topologies are generated to avoid overloaded cables.

**Result:**
- `group_wtgs` cleanly calculates bin-packed spatial clusters that obey `feeder_capacity_mw` using deterministic KMeans clustering and strict limits.

### 2026-08-08 — SURGE-PY-003 Wired preprocessing into /api/v1/optimise

**Changed:**
- Added: Validation failure handling for empty/invalid GeoJSON in `optimise` endpoint.
- Added: Integration tests for empty WTG collections, missing substations, and invalid polygon geometries.
- Modified: `optimisation_service.py` completely wires `process_project_data`.

**Affected files:**
- `app/api/v1/endpoints/optimise.py`, `tests/test_optimise.py`

**Reason:**
- Connect the API routing layer to the underlying GIS algorithms to ensure dirty HTTP requests are safely rejected or converted into spatial models.

**Result:**
- End-to-end WGS84 GeoJSON ingestion, UTM projection, and validation layer is live and protected by tests.

**Pending:**
- Graph network topology mapping (SURGE-PY-004).

**2. Web GIS Map Frontend (`web-map`)**
- Built an interactive Web GIS application using Vite, Vanilla CSS, and Leaflet.
- Features include custom Leaflet markers, Drag & Drop GeoJSON upload, optimization control panel, live BOM dashboard, CSV report export, and a responsive dark mode glassmorphism UI.

**3. Python Optimization Engine (`optimisation-python`)**
- Set up FastAPI project structure, endpoints, and validation models for GIS data and coordinates.
- Successfully implemented basic routing pipeline schemas.
- **Pending/In-Progress:** A* and Dijkstra routing over generated cost surfaces, terrain/slope analysis, WTG capacity-constrained clustering, and electrical load-flow validation using pandapower.

## System Architecture Overview

SURGE (Smart Utility Routing and Grid Evacuation) is comprised of three core components:
1. **Java Spring Boot API (`backend-java`)**: Handles enterprise workflows, data persistence via PostGIS, reporting, and job orchestration.
2. **Python FastAPI Service (`optimisation-python`)**: Serves as the computational intelligence engine handling GIS routing, terrain cost surfacing, machine learning ranking, and electrical validation.
3. **Web GIS Map Frontend (`web-map`)**: Provides the interactive UI for plotting WTGs, substations, generating routes, and analyzing impact.

## Documentation References
For more details, please refer to the project docs located in `/docs` and the Obsidian vault in `/obsidian-vault`.
- `docs/MVP - Minimum Viable Product.md`
- `docs/Milestone 1 - Pending.md`
- `docs/Python Engine - Architecture.md`
