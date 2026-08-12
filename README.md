# SURGE — Smart Utility Routing and Grid Evacuation

SURGE targets an enterprise platform for renewable-energy collector and evacuation systems. The repository contains an active MVP implementation; production hardening and several advanced engineering capabilities remain planned.

## Core Components

The SURGE platform consists of three main modules:

1. **Backend Java API (`/backend-java`)**
   - Built on Spring Boot and backed by PostGIS.
   - Handles enterprise workflows, data persistence, reporting, asset management, and job orchestration.
   - Manages GeoJSON and KMZ/KML asset ingestion (`POST /api/v1/projects/{projectId}/assets/kmz`), database migrations (Flyway), and API endpoints for the GIS frontend.
   
2. **Python Optimization Engine (`/optimisation-python`)**
   - A FastAPI microservice powering the computational intelligence of the system.
   - The API-integrated baseline validates/project Points, groups WTGs, builds MST topology, and routes/refines LineStrings over a uniform cost surface.
   - PNC assembly, pandapower validation, map-ready result packaging, and deterministic candidate generation are implemented as standalone modules.
   - Electrical-aware recommendation, orchestration, and the richer compatible API response are frozen as SURGE-PY-018 through SURGE-PY-020.

3. **Web GIS Map Frontend (`/web-map`)**
   - An interactive map interface built with Vite, HTML5, Vanilla CSS, and Leaflet.
   - Allows users to drag-and-drop GeoJSON features, configure optimization scenarios, visualize routes, and download Bill of Materials (BOM) CSV reports.
   - Features a premium dark mode glassmorphism design.

## Documentation and Context

Detailed documentation is available in the `/docs` directory.
- For architectural details and MVP scope, see `docs/MVP - Minimum Viable Product.md`.
- For the frozen Python ticket sequence, see `docs/Surge MVP Ticket Plan.md`.
- For the latest project context and cross-component updates, see `CONTEXT.md`.

## Quick Start

### Web Map Frontend
```bash
cd web-map
npm install
npm run dev
```

### Java Backend
```bash
cd backend-java
./mvnw spring-boot:run
```

### Python Optimization Engine
```bash
cd optimisation-python
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
