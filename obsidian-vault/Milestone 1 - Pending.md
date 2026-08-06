Your first technical milestone should be:

> **By the end of Day 5, SURGE must accept WTG, substation and GIS inputs and return at least one constraint-aware feeder route as GeoJSON.**



You are the **Python/GIS/ML developer**.
A suitable expansion for the name is:

**SURGE — Smart Utility Routing and Grid Evacuation**

The Java developer will handle the enterprise application layer, while you will own the intelligence and optimisation engine responsible for WTG grouping, feeder planning, routing, pole placement, ROW analysis, electrical validation and explainable ranking. These directly map to the required collector-network, multi-objective routing and pole-selection capabilities.

# Your role in SURGE

## Primary ownership

```text
Python FastAPI Optimisation Service
├── GIS data validation
├── Coordinate-system conversion
├── Terrain and slope analysis
├── WTG clustering
├── Feeder-capacity allocation
├── Collector-network topology
├── Cost-surface generation
├── A* and Dijkstra routing
├── Alternative-route generation
├── Pole placement
├── Variable-span optimisation
├── Pole-type recommendation
├── ROW corridor generation
├── Cadastral parcel intersection
├── Land-compensation calculation
├── Electrical validation
├── ML-based route ranking
└── Explainability output
```

# Your Python technology stack

|Component|Technology|
|---|---|
|API service|FastAPI|
|Data validation|Pydantic|
|Tabular processing|Pandas|
|Vector GIS|GeoPandas|
|Geometry|Shapely|
|Raster and DEM|Rasterio|
|Numerical processing|NumPy|
|Graph algorithms|NetworkX plus custom A*|
|Machine learning|scikit-learn|
|Electrical analysis|pandapower|
|Model persistence|joblib|
|Testing|pytest|
|Code quality|Ruff and mypy|
|Environment|PyCharm and Python virtual environment|
|Packaging|Docker|

# Recommended Python project structure

```text
surge/
└── optimisation-python/
    ├── src/
    │   └── surge_engine/
    │       ├── api/
    │       │   ├── routes.py
    │       │   ├── schemas.py
    │       │   └── dependencies.py
    │       ├── gis/
    │       │   ├── validators.py
    │       │   ├── crs.py
    │       │   ├── terrain.py
    │       │   ├── rasterizer.py
    │       │   └── cost_surface.py
    │       ├── clustering/
    │       │   ├── wtg_clustering.py
    │       │   └── feeder_assignment.py
    │       ├── topology/
    │       │   ├── mst.py
    │       │   ├── junctions.py
    │       │   └── network_builder.py
    │       ├── routing/
    │       │   ├── astar.py
    │       │   ├── dijkstra.py
    │       │   ├── alternatives.py
    │       │   └── route_features.py
    │       ├── poles/
    │       │   ├── placement.py
    │       │   ├── span_optimizer.py
    │       │   └── pole_selector.py
    │       ├── row/
    │       │   ├── corridor.py
    │       │   ├── parcel_impact.py
    │       │   └── compensation.py
    │       ├── electrical/
    │       │   ├── network_model.py
    │       │   ├── load_flow.py
    │       │   └── constraints.py
    │       ├── ranking/
    │       │   ├── deterministic_score.py
    │       │   ├── ml_model.py
    │       │   ├── explainability.py
    │       │   └── scenario_weights.py
    │       ├── models/
    │       ├── config/
    │       └── common/
    ├── tests/
    │   ├── unit/
    │   ├── integration/
    │   └── golden_data/
    ├── notebooks/
    ├── sample_data/
    ├── pyproject.toml
    ├── Dockerfile
    └── README.md
```

# Your two-week Python timeline

## Week 1: Core GIS and routing pipeline

### Day 1 — Service foundation

- Create the Python project and virtual environment.
    
- Configure FastAPI.
    
- Configure Ruff, mypy and pytest.
    
- Add `/health` endpoint.
    
- Define request and response schemas.
    
- Prepare Dockerfile.
    
- Create `AGENTS.md` instructions for Codex.
    

**Deliverable:** Running FastAPI service with tests.

### Day 2 — GIS validation

- Read GeoJSON and GeoPackage inputs.
    
- Validate geometries.
    
- Handle polygons and multipolygons.
    
- Convert layers into a common projected CRS.
    
- Clip layers to the project boundary.
    
- Validate WTG and substation coordinates.
    

**Deliverable:** Validated and standardised project dataset.

### Day 3 — Terrain and cost surface

- Read DEM raster.
    
- Calculate slope.
    
- Rasterise vector constraint layers.
    
- Implement hard exclusions.
    
- Implement configurable soft penalties.
    
- Generate a combined geospatial cost surface.
    

**Deliverable:** Visual and numerical cost grid.

### Day 4 — WTG grouping and feeder allocation

- Calculate required feeder count.
    
- Implement capacity-constrained clustering.
    
- Assign WTGs to feeders.
    
- Detect overloaded clusters.
    
- Generate two or three alternative groupings.
    

**Deliverable:** WTG-to-feeder assignment result.

### Day 5 — Route generation

- Implement A* routing.
    
- Implement Dijkstra as a baseline.
    
- Route each feeder connection over the cost surface.
    
- Add no-path handling.
    
- Simplify route geometry.
    
- Return routes as GeoJSON.
    

**Deliverable:** First end-to-end feeder routes.

## Week 2: Engineering intelligence

### Day 6 — Topology and junctions

- Build an MST-based radial topology.
    
- Merge overlapping route segments.
    
- Detect candidate junctions.
    
- Calculate feeder-level topology metrics.
    
- Check disconnected networks.
    

**Deliverable:** Complete preliminary collector network.

### Day 7 — Pole and span optimisation

- Place mandatory poles at terminals and junctions.
    
- Detect significant route-angle changes.
    
- Add angle poles.
    
- Handle road and water crossings.
    
- Optimise individual span lengths.
    
- Calculate pole count and span schedule.
    

**Deliverable:** Pole coordinates and span schedule.

### Day 8 — ROW and parcel intelligence

- Buffer route centreline into a ROW corridor.
    
- Intersect ROW with irregular cadastral parcels.
    
- Calculate affected area per parcel.
    
- Apply compensation rates.
    
- Count negotiations and impacted owners where data exists.
    

The original problem statement specifically requires corridor-area calculation, compensation estimation and support for irregular polygons and multipolygons.

**Deliverable:** Parcel-impact and compensation report.

### Day 9 — Electrical validation and scoring

- Construct the preliminary pandapower network.
    
- Calculate conductor loading.
    
- Run load flow.
    
- Calculate voltage drop and power losses.
    
- Reject invalid route candidates.
    
- Implement deterministic scenario scores.
    

**Deliverable:** Electrically validated alternatives.

### Day 10 — ML ranking and integration

- Build route-feature extraction.
    
- Train a baseline regression or ranking model.
    
- Combine deterministic and ML scores.
    
- Return feature-level explanations.
    
- Integrate with the Java backend.
    
- Complete tests and demo dataset.
    

**Deliverable:** Ranked and explainable route alternatives.

# Your initial FastAPI contract

## Optimisation request

```json
{
  "projectId": "SURGE-DEMO-001",
  "sourceCrs": "EPSG:4326",
  "workingCrs": "EPSG:32643",
  "substation": {
    "id": "SUB-01",
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "wtgs": [
    {
      "id": "WTG-01",
      "latitude": 28.6301,
      "longitude": 77.2302,
      "capacityMw": 3.0
    }
  ],
  "scenario": "BALANCED",
  "numberOfCandidates": 3,
  "feederCapacityMw": 15,
  "rowWidthMeters": 15,
  "minimumSpanMeters": 50,
  "normalSpanMeters": 100,
  "maximumSpanMeters": 180,
  "maximumVoltageDropPercent": 5
}
```

## Main endpoints

```http
GET  /health
POST /api/v1/datasets/validate
POST /api/v1/wtgs/cluster
POST /api/v1/cost-surfaces/generate
POST /api/v1/topologies/generate
POST /api/v1/routes/generate
POST /api/v1/poles/place
POST /api/v1/row/analyse
POST /api/v1/electrical/validate
POST /api/v1/routes/rank
POST /api/v1/optimise
```

The final `/optimise` endpoint should run the complete pipeline:

```text
Validate GIS data
→ group WTGs
→ assign feeders
→ create topology
→ generate routes
→ place poles
→ generate ROW
→ analyse parcels
→ validate electrically
→ rank alternatives
```

# Your PyCharm workflow

For each feature:

```text
Obsidian requirement
        ↓
GitHub issue
        ↓
Create feature branch
        ↓
Ask Codex for bounded implementation
        ↓
Review code in PyCharm
        ↓
Debug using sample GIS data
        ↓
Run Ruff + mypy + pytest
        ↓
Ask Ollama for local edge-case review
        ↓
Commit and create pull request
```

Recommended PyCharm run configurations:

```text
SURGE FastAPI
SURGE Unit Tests
SURGE GIS Tests
SURGE Routing Benchmark
SURGE Electrical Validation
SURGE Full Quality Check
```

# First tasks you should create

```text
SURGE-PY-001: Initialise FastAPI optimisation service
SURGE-PY-002: Implement GIS geometry validation
SURGE-PY-003: Implement CRS standardisation
SURGE-PY-004: Generate terrain slope raster
SURGE-PY-005: Generate weighted cost surface
SURGE-PY-006: Implement capacity-constrained WTG clustering
SURGE-PY-007: Implement A* routing
SURGE-PY-008: Generate alternative candidate routes
SURGE-PY-009: Implement MST collector topology
SURGE-PY-010: Implement pole placement
SURGE-PY-011: Implement variable-span optimisation
SURGE-PY-012: Generate ROW corridor
SURGE-PY-013: Calculate parcel impact and compensation
SURGE-PY-014: Implement electrical load-flow validation
SURGE-PY-015: Implement route scoring and ML ranking
SURGE-PY-016: Integrate Python service with Java backend
```

