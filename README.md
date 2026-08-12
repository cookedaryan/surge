# SURGE — Smart Utility Routing and Grid Evacuation

SURGE is an enterprise, production-grade platform for renewable-energy collector and evacuation systems. It provides multi-objective routing, WTG grouping, feeder topology generation, intelligent pole placement, variable spans calculation, and engineering compliance analysis.

## Core Components

The SURGE platform consists of three main modules:

1. **Backend Java API (`/backend-java`)**
   - Built on Spring Boot and backed by PostGIS.
   - Handles enterprise workflows, data persistence, reporting, asset management, and job orchestration.
   - Manages GeoJSON and KMZ/KML asset ingestion (`POST /api/v1/projects/{projectId}/assets/kmz`), database migrations (Flyway), and API endpoints for the GIS frontend.
   
2. **Python Optimization Engine (`/optimisation-python`)**
   - A FastAPI microservice powering the computational intelligence of the system.
   - Processes GIS datasets, generates terrain and cost surfaces, runs A* routing, and validates electrical loads using `pandapower`.
   - Returns explainable route alternatives to the Java backend.

3. **Web GIS Map Frontend (`/web-map-next`)**
   - An interactive map interface built with React, TypeScript, Vite, Tailwind CSS, and Leaflet.
   - Allows users to drag-and-drop GeoJSON features, configure optimization scenarios, visualize routes, and download Bill of Materials (BOM) CSV reports.
   - Uses a "technical dashboard" design system — near-black surfaces, hairline borders, a single accent color, and monospace numerals for engineering readouts. `web-map/` (the previous vanilla-JS implementation) is retained for reference but no longer built or deployed.

## Documentation and Context

Detailed documentation is available in the `/docs` directory.
- For architectural details and MVP scope, see `docs/MVP - Minimum Viable Product.md`.
- For the latest project context and cross-component updates, please refer to `optimisation-python/CONTEXT.md`.

## Quick Start

### Web Map Frontend
```bash
cd web-map-next
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
