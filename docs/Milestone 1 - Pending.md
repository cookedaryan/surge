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
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                     # Application factory (FastAPI)
    │   ├── core/
    │   │   ├── __init__.py
    │   │   └── config.py               # Pydantic 2 BaseSettings
    │   ├── api/
    │   │   ├── __init__.py
    │   │   └── v1/
    │   │       ├── __init__.py
    │   │       ├── router.py           # Includes health and optimise routers
    │   │       └── endpoints/
    │   │           ├── __init__.py
    │   │           ├── health.py       # GET /api/v1/health
    │   │           └── optimise.py     # POST /api/v1/optimise
    │   ├── schemas/
    │   │   ├── __init__.py
    │   │   └── optimise.py             # Pydantic 2 models with validation
    │   ├── services/
    │   │   ├── __init__.py
    │   │   └── optimisation_service.py # Optimisation service layer
    │   ├── algorithms/
    │   │   ├── __init__.py
    │   │   ├── route_graph.py          # A* / Dijkstra & MST solvers
    │   │   ├── cost_function.py        # Terrain & cost surface logic
    │   │   └── electrical_analysis.py  # Load flow & voltage drop solvers
    │   └── utils/
    │       ├── __init__.py
    │       └── coordinate_transform.py # WGS84 GeoJSON <-> Projected meter CRS
    ├── tests/
    │   ├── __init__.py
    │   ├── test_health.py
    │   └── test_optimise.py
    ├── .env.example
    ├── .dockerignore
    ├── .gitignore
    ├── AGENTS.md                       # LLM agent instructions & constraints
    ├── Dockerfile                      # Non-root slim container
    ├── pyproject.toml
    ├── requirements.txt
    ├── requirements.lock.txt            # Pin-locked environment dependencies
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

## Main endpoints

```http
GET  /api/v1/health
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

