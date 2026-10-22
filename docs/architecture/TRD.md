# Technical Requirements Document (TRD)
## SURGE — Smart Utility Routing and Grid Evacuation

**Status:** Living document — MVP phase
**Companion documents:** [PRD.md](../product/PRD.md) (what/why), [APP-FLOW.md](../product/APP-FLOW.md) (user journeys)
**Last aligned with repo state:** 2026-08-08

---

## 1. Scope

This document specifies the technical architecture, components, data contracts, and quality gates required to deliver the SURGE MVP described in the PRD. It reflects the actual repository baseline where noted, and marks planned work explicitly.

---

## 2. System Architecture

```text
                       WEB GIS CLIENT
         Map, WTG input, layers, scenarios, comparison
                              │
                         REST / GeoJSON
                              │
                    JAVA SPRING BOOT API
     Authentication, projects, jobs, persistence, reports
                              │
           ┌──────────────────┴─────────────────┐
           │                                     │
       PostGIS                            Python FastAPI
  Spatial/project data               Optimisation service
                                              │
                              ┌───────────────┼───────────────┐
                              │               │                │
                          GIS engine    Routing engine   Electrical engine
                          GeoPandas      A* / MST          pandapower
                              │               │                │
                              └───────────────┼────────────────┘
                                              │
                                     ML ranking model
                                              │
                                Ranked routes + explanations
```

### 2.1 Components

| Component | Path | Responsibility |
|---|---|---|
| **Web GIS Frontend** | `/web-map` | Interactive map UI: plot WTGs/substation, drag-and-drop GeoJSON, configure scenarios, visualize routes, view BOM dashboard, export CSV |
| **Java Backend API** | `/backend-java` | Enterprise workflows: auth, project/org management, PostGIS persistence, job orchestration, calling the Python service, storing results, reporting/exports |
| **Python Optimisation Engine** | `/optimisation-python` | Computational core: GIS validation, terrain/cost-surface, WTG clustering, feeder topology, routing, pole placement, ROW/parcel analysis, electrical validation, ML ranking, explainability |

### 2.2 Component Interaction Flow
1. Browser exchanges REST + WGS84 GeoJSON with Spring Boot.
2. Spring Boot validates and persists spatial/application state in PostGIS.
3. On an optimisation job request, Spring Boot serializes stored WTGs/substation and calls the Python service synchronously (async processing is planned, not current).
4. Python converts geographic coordinates into a single metric UTM CRS before graph/grouping calculations.
5. Java persists returned metrics and route features; the browser refreshes map and report views.

This split keeps authentication, transactions, and project ownership in Java, and scientific types/solvers in Python.

---

## 3. Technology Stack

### 3.1 Java Backend (`backend-java`)
- **Framework:** Spring Boot (Java 21)
- **Spatial persistence:** PostGIS
- **Migrations:** Flyway
- **Packaging:** Docker
- **Responsibilities:** Authentication/RBAC, organisation/project APIs, WTG/substation APIs, GIS-layer metadata, file-upload workflow, scenario configuration, optimisation-job lifecycle, Python-service client, route-result persistence, audit logging, map-interface integration, exports/reports.

### 3.2 Python Optimisation Engine (`optimisation-python`)

| Concern | Technology |
|---|---|
| API service | FastAPI |
| Data validation | Pydantic |
| Tabular processing | Pandas |
| Vector GIS | GeoPandas |
| Geometry | Shapely |
| Raster / DEM | Rasterio |
| Numerical processing | NumPy |
| Graph algorithms | NetworkX + custom A* |
| Machine learning | scikit-learn |
| Electrical analysis | pandapower |
| Model persistence | joblib |
| Testing | pytest |
| Code quality | Ruff, mypy |
| Environment | PyCharm, Python venv |
| Packaging | Docker |

### 3.3 Web Frontend (`web-map`)
- **Build tool:** Vite
- **Styling:** Vanilla CSS (dark-mode glassmorphism theme)
- **Mapping:** Leaflet, with custom markers and drag-and-drop GeoJSON upload
- **Features implemented today:** optimisation control panel, live BOM dashboard, CSV report export, responsive UI; several API failures currently fall back to demo data.

---

## 4. Data Model and Domain Objects

### 4.1 Core Domain Concepts
- `Project` — study-area boundary, owning org/user, configuration.
- `WTG` (Point, `capacity_mw`) and `Substation` (Point).
- `GISLayer` — roads, forest, water, parcels, elevation (DEM), restricted areas, land rates.
- `FeederAssignment` — WTG-to-feeder membership under capacity constraints.
- `Topology` — per-feeder graph (currently MST) over assigned nodes + substation.
- `Route` — geographic LineString realizing a topology edge/connection.
- `ROWCorridor` — buffered polygon around a route (planned).
- `Parcel impact` — intersecting cadastral parcels + compensation estimate (planned).
- `ElectricalResult` — voltage drop %, power loss, conductor loading (planned).
- `OptimisationMetrics` — aggregate metrics per alternative (`total_length_m` implemented; cost/land/electrical metrics planned).

### 4.2 Candidate Feature Set for Scoring/ML (planned)
```text
total_length_km, estimated_capex, pole_count, angle_pole_count,
affected_parcel_count, row_area_m2, land_compensation,
forest_intersection_m2, road_crossings, river_crossings,
average_slope, maximum_slope, accessibility_score,
voltage_drop_percent, power_loss_kw, maximum_conductor_loading
```
Model choice: gradient boosting or random forest as the first ML model. If insufficient labeled historical data exists, deterministic scoring is the **official** result, and any ML output is labeled **experimental** — never silently substituted for the deterministic score.

---

## 5. Python Service — Internal Structure

```text
optimisation-python/
├── app/
│   ├── algorithms/
│   │   ├── cost_function.py         # Placeholder — lifecycle-cost evaluation
│   │   ├── electrical_analysis.py   # Placeholder — load flow, voltage drop, losses
│   │   └── route_graph.py           # Implemented — candidate graph construction
│   ├── api/v1/
│   │   ├── endpoints/{health.py, optimise.py}
│   │   └── router.py
│   ├── core/config.py
│   ├── gis/
│   │   ├── cost_surface.py          # Implemented standalone (SURGE-PY-007)
│   │   └── (GeoJSON parsing, UTM selection, transforms — implemented for Points)
│   ├── models/                      # Frozen projected spatial domain objects — implemented
│   ├── schemas/optimise.py          # Pydantic request/response contract — implemented
│   ├── services/optimisation_service.py
│   ├── utils/coordinate_transform.py
│   └── main.py
├── tests/
├── notebooks/
├── pyproject.toml
├── requirements.txt / requirements.lock.txt
└── Dockerfile
```

### 5.1 Package Responsibility / Status Matrix

| Package or module | Responsibility | Status |
|---|---|---|
| `app/api/v1` | FastAPI routes, expected-error translation | Implemented |
| `app/schemas` | Request/response contract | Implemented |
| `app/gis` | GeoJSON parsing, validation, UTM selection/transforms | Implemented (Points only) |
| `app/gis/cost_surface.py` | Uniform raster + affine transform + coordinate helpers | Implemented, standalone (not yet wired into API pipeline) |
| `app/models` | Frozen projected spatial domain objects | Implemented |
| `route_graph.py` | Complete undirected graph, Euclidean edge weights | Implemented |
| `wtg_grouping.py` | Capacity-constrained feeder assignment (K-Means-assisted MILP) | Implemented |
| `topology.py` | Per-feeder MST topology (SURGE-PY-006) | Implemented |
| `cost_function.py` | Lifecycle-cost evaluation | Placeholder |
| `electrical_analysis.py` | Load flow, voltage drop, losses | Placeholder |

### 5.2 Current Pipeline (as implemented)
```text
Spring Boot POST /api/v1/optimise
    → Pydantic request validation
    → WGS84 GeoJSON Point preprocessing
    → unified UTM projection
    → complete metric candidate graph
    → K-Means-assisted MILP feeder grouping
    → per-feeder minimum spanning trees
    → WGS84 preliminary edge GeoJSON
    → feeder count + aggregate preliminary length
```
Known limitation: MST minimizes straight-line Euclidean topology length only — it does not yet account for terrain, exclusions, parcels, access, junctions, shared trunks, electrical performance, or true routed-corridor length.

### 5.3 Target Full Pipeline (planned)
```text
Validate GIS data
→ group WTGs
→ assign feeders
→ create topology
→ generate routes (A* over cost surface)
→ place poles (variable spans)
→ generate ROW corridors
→ analyse parcel impact + compensation
→ validate electrically (pandapower)
→ rank alternatives (deterministic + experimental ML)
```

---

## 6. API Contract

### 6.1 Endpoints (current)
```http
GET  /api/v1/health
POST /api/v1/optimise
```

### 6.2 `POST /api/v1/optimise` — Request Shape
```json
{
  "request_id": "req-987654",
  "project_id": "proj-123456",
  "scenario": "Balanced",
  "wtg_geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": { "type": "Point", "coordinates": [77.2302, 28.6301] },
        "properties": { "id": "WTG-001", "capacity_mw": 3.0 }
      }
    ]
  },
  "substation_geojson": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": { "type": "Point", "coordinates": [77.2090, 28.6139] },
        "properties": { "id": "SUB-001" }
      }
    ]
  },
  "electrical_params": {
    "feeder_capacity_mw": 20.0,
    "max_voltage_drop_pct": 5.0,
    "row_width_m": 18.0
  }
}
```

### 6.3 Known Contract Gap
The current response property `feeder_id` does not match the feeder-name keys `RouteService` (Java) expects, so Java currently generates its own names and persists each edge as a separate route record. **Before treating these preliminary features as true feeder routes, both services must agree on feeder identity and whether one Feature represents an edge, a segment, or a complete feeder.** This is a required cross-service contract fix, tracked as pre-work for SURGE-PY-009/016.

---

## 7. Repository Structure (target)

```text
surge/
├── AGENTS.md
├── README.md
├── compose.yaml
├── .env.example
├── backend-java/
│   ├── src/
│   ├── build.gradle
│   └── Dockerfile
├── optimisation-python/
│   ├── app/{algorithms,api,core,gis,models,schemas,services,utils}
│   ├── tests/
│   ├── notebooks/
│   ├── pyproject.toml
│   └── Dockerfile
├── web-map/
├── contracts/
│   ├── openapi.yaml
│   ├── schemas/
│   └── examples/
├── database/migrations/
├── sample-data/{public-demo/, README.md}
├── docs/
│   ├── architecture.md
│   ├── domain-rules.md
│   ├── data-dictionary.md
│   ├── acceptance-tests/
│   └── adr/
└── tools/
    ├── validate_dataset.py
    ├── benchmark_routes.py
    └── local_review.py
```

---

## 8. Environment Configuration

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=surgedb
DB_USER=postgres
DB_PASSWORD=postgres

# Java Backend
PORT=8080
SPRING_PROFILES_ACTIVE=dev

# Python Optimisation Engine
PYTHON_ENGINE_URL=http://localhost:8000
```

---

## 9. Non-Functional / Engineering Requirements

| Category | Requirement |
|---|---|
| **Determinism** | Selected edges/topologies must be normalized and sorted for deterministic output (already enforced in MST implementation). |
| **Validation** | Topology construction must reject: zero/multiple substations, feeder-count mismatch, duplicate assignments, missing assigned nodes, incomplete coverage, disconnected results. |
| **Statelessness** | The Python service is a stateless computation boundary — no persistence responsibility. |
| **Explainability** | Cost/rank outputs must retain raw metrics, weights, and rejection reasons, not just a final score. |
| **CI Quality Gates — Python** | `ruff check`, `ruff format --check`, `mypy`, `pytest`, GIS golden-dataset test, routing benchmark, electrical-validation test |
| **CI Quality Gates — Java** | compile, unit tests, integration tests, architecture tests, database migration test, OpenAPI compatibility test |
| **CI Quality Gates — System** | Docker image build, service health checks, end-to-end optimisation test, GeoJSON schema validation, security/dependency scan, demo-dataset run |
| **Security** | Secrets and private GIS data must stay outside of AI-assisted prompts/tooling. Database migrations and API contract changes require human (both-developer) review. |
| **Branching** | One issue per branch, one code-changing agent per branch; agents never work directly on `main`/`develop`; all merges require human-reviewed PR. |

---

## 10. Golden Demonstration Dataset (acceptance basis)

A small controlled dataset must exist containing:
- 8–12 WTGs, one substation, two likely feeder groups
- One forest exclusion, one high-cost land parcel
- One road crossing, one water crossing
- Irregular parcel polygons
- A DEM with moderate slopes
- At least two feasible route corridors

**Expected system behavior against this dataset:**
- Produce at least two feeders
- Avoid hard exclusions
- Generate at least three valid alternatives
- Show different winners across the four scenarios
- Place poles with non-uniform spans
- Calculate ROW–parcel intersections
- Reject at least one electrically invalid candidate
- Explain why the Balanced route ranked first

---

## 11. Open Technical Risks

1. **Feeder-identity contract mismatch** between Python response and Java `RouteService` (see §6.3) — must be resolved before route persistence is trustworthy.
2. **Cost-surface not yet wired into the API pipeline** — SURGE-PY-007 exists standalone; zero-padding boundary behavior is untested and can place points one index outside the raster array.
3. **No terrain/exclusion-aware routing yet** — current topology is Euclidean-only, so it understates real corridor length and ignores hard constraints in routing (though grouping/topology validation does reject some invalid structures).
4. **Electrical validation and cost function are placeholders** — scenario differentiation and hard-constraint rejection are not yet possible until these land.
5. **No authentication, async processing, or production deployment controls yet** — acceptable for MVP, but must be scoped before any real deployment.
