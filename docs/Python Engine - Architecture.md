# Python Engine Architecture and GIS Processing

## Purpose and Current Status

The SURGE Python service is the stateless numerical boundary behind the Java application. It currently implements request validation, GeoJSON Point preprocessing, unified UTM projection, a complete candidate graph, and capacity-constrained WTG grouping. It does not yet generate routes, run A*, calculate lifecycle cost, place poles, intersect ROW corridors, run pandapower, or rank routes with ML.

## Request Flow

```text
Spring Boot POST /api/v1/optimise
    -> Pydantic request validation
    -> Shapely GeoJSON parsing and Point validation
    -> pyproj unified UTM transformation
    -> frozen ProjectSpatialData models
    -> NetworkX complete candidate graph
    -> K-Means seeds + SciPy MILP feeder grouping
    -> response metrics + empty route FeatureCollection
```

The HTTP contract uses WGS84 GeoJSON. Algorithms use projected Shapely Points measured in meters. This translation prevents degree-based distance calculations and isolates algorithms from transport dictionaries.

## Package Responsibilities

| Package | Responsibility | Status |
| --- | --- | --- |
| `app/api/v1` | FastAPI routes and HTTP error translation | Implemented |
| `app/schemas` | Pydantic 2 request/response models | Implemented |
| `app/services` | Pipeline orchestration | Implemented foundation |
| `app/gis` | GeoJSON, validation, CRS choice, transforms | Implemented for Points |
| `app/models` | Immutable projected domain objects | Implemented |
| `app/algorithms/route_graph.py` | Complete straight-line graph | Implemented |
| `app/algorithms/wtg_grouping.py` | Capacity-constrained grouping | Implemented |
| `cost_function.py` | Lifecycle-cost calculation | Placeholder |
| `electrical_analysis.py` | Load flow and voltage analysis | Placeholder |

## Coordinate-System Decision

RFC 7946 GeoJSON uses WGS84 longitude/latitude. The service validates coordinates, calculates the arithmetic mean location of all WTGs and the substation, selects the WGS84 UTM CRS covering that point, and transforms every point with `always_xy=True`.

One CRS per project ensures all coordinates are comparable. UTM is suitable for compact project sites; EPSG:3857 is not used for authoritative engineering measurements. Large multi-zone, polar, or antimeridian projects need a future projection policy.

## WTG Grouping

The solver converts MW values to integer kW, estimates the minimum possible feeder count, creates deterministic K-Means seed centroids, and uses SciPy's mixed-integer linear programming solver to assign each WTG exactly once without exceeding feeder capacity. It minimizes squared spatial distance to the selected seeds.

This is an MW planning constraint, not a complete conductor ampacity or voltage-drop check. The latter belongs to the future electrical-analysis stage.

## API Semantics

`GET /api/v1/health` is a process-level health check. `POST /api/v1/optimise` is synchronous. A successful optimization response currently confirms preprocessing, graph construction, and grouping only; its route collection is empty and route length/cost remain zero or null.

## Design Rationale

- FastAPI and Pydantic provide a typed language-neutral service contract.
- Frozen dataclasses separate validated internal state from external JSON.
- A service layer keeps HTTP code out of algorithms.
- One UTM CRS makes Euclidean graph weights meaningful.
- A complete graph is a simple baseline but has quadratic edge growth.
- K-Means supplies spatial preference while MILP enforces hard capacity constraints.

## Source of Detailed Documentation

The Obsidian vault contains the maintained detailed notes: `04-architecture/Python Engine.md`, `08-python-engine/Overview & Layout.md`, `08-python-engine/Geospatial Integrity & CRS.md`, and `10-api/FastAPI Endpoints.md`.
