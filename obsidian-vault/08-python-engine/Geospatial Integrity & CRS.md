# Geospatial Integrity and Coordinate Reference Systems

**Module:** `optimisation-python/app/gis/` (`crs.py`, `preprocessing.py`, `constraints.py`, `cost_surface.py`, `geometry.py`, `geojson.py`, `row_analysis.py`)  
**Status:** Complete & Production-Ready  
**Dependencies:** `pyproj`, `shapely`, `numpy`

---

## The Fundamental Coordinate Rule

> [!important] The SURGE Geospatial Invariant
> 1. **Public Boundary (API & Database)**: All incoming payloads and outgoing responses strictly use **WGS84 (EPSG:4326)** coordinates adhering to RFC 7946 GeoJSON format ($[x, y] = [\text{longitude}, \text{latitude}]$).
> 2. **Internal Engineering Engine**: All distance, buffer, area, obstacle rasterization, A* corridor routing, and pole-span placement operations are executed in a **single dynamically determined projected UTM Coordinate Reference System (measured in metres)**.
> 3. **Never Mix Projections**: A project’s spatial entities (turbines, substation, roads, parcels, restrictions) are all projected into the same unified UTM CRS before any algorithm executes.

Treating angular degrees as linear metres produces severe geometric distortions (where 1° of longitude varies from ~111 km at the equator to 0 km at the poles). Conversely, using Web Mercator (EPSG:3857) introduces severe scale distortion away from the equator. A local Universal Transverse Mercator (UTM) projection provides conformal, metric geometry with minimal local scale distortion across a wind farm site.

---

## Coordinate Transformations & Projections (`crs.py`)

### 1. Dynamic UTM Zone Determination
When raw WGS84 GeoJSON data arrives at `app/gis/preprocessing.py`, the engine computes the arithmetic mean of all turbine and substation coordinates:

$$\bar{\lambda} = \frac{1}{N} \sum_{i=1}^N \lambda_i, \quad \bar{\phi} = \frac{1}{N} \sum_{i=1}^N \phi_i$$

The system queries `pyproj.database.query_utm_crs_info()` to select the optimal WGS84 UTM zone covering $(\bar{\lambda}, \bar{\phi})$ (e.g., `EPSG:32643` for UTM Zone 43N).

### 2. `always_xy=True` Coordinate Axis Ordering
Standard GIS libraries have historical inconsistencies regarding axis order (lat/lon vs lon/lat). SURGE enforces strict RFC 7946 compliance by initializing all `pyproj.Transformer` instances with `always_xy=True`:

```python
transformer_forward = Transformer.from_crs("EPSG:4326", projected_crs, always_xy=True)
transformer_reverse = Transformer.from_crs(projected_crs, "EPSG:4326", always_xy=True)
```

- **Forward Transformation**: Input $(x, y) = (\text{lon}, \text{lat}) \to (X_{\text{UTM}}, Y_{\text{UTM}})$.
- **Reverse Transformation**: $(X_{\text{UTM}}, Y_{\text{UTM}}) \to (\text{lon}, \text{lat})$.

---

## Spatial Preprocessing & Geometry Validation (`preprocessing.py` & `geometry.py`)

```mermaid
flowchart TD
    A[Raw GeoJSON Inputs<br/>Turbines, Substation, Avoidance Layers] --> B[GeoJSON Parser<br/>Validate Lon [-180, 180], Lat [-90, 90]]
    B --> C[Compute Center & Determine UTM CRS<br/>app/gis/crs.py]
    C --> D[Forward Transform to UTM Metres<br/>always_xy=True]
    D --> E[Geometry Validation & Repair<br/>shapely.make_valid & polygon orientation]
    E --> F[ProjectSpatialData & Constraint Layers]
    F --> G[Rasterization & Optimization Engine]
```

### Geometry Ingestion & Validation Rules
- **Point Entities**: Turbines and substations must be valid Shapely `Point` geometries with non-empty identifiers and positive capacities.
- **Polygons & MultiPolygons**: Cadastral parcels and restricted areas are validated. Self-intersecting rings or invalid orientations are repaired using `shapely.make_valid()`.
- **LineStrings**: Existing roads, transmission lines (HT lines), and watercourses are verified for finite coordinates and positive length.

---

## Avoidance Layers & Constraint Rasterization (`constraints.py`)

SURGE supports rich multi-layer spatial avoidance by rasterizing vector geometries onto the optimization `CostSurface`:

| Constraint Layer | Feature Category | Processing Mode | Default Buffer | Cost Weighting |
|---|---|---|---|---|
| **RESTRICTED_AREA** | Environmental, Forest, Defence, Buffer Zones | Hard Exclusion | User-defined / 0m | $\infty$ (Impenetrable Obstacle) |
| **ROAD** | Paved Roads, Highways, Farm Tracks | Soft Crossing Penalty | 5m – 10m | Additive Crossing Resistance |
| **HT_LINE** | Existing High-Tension Transmission Corridors | Soft / Clearance | 15m – 30m | Additive Resistance (Clearance buffer) |
| **WATERCOURSE** | Rivers, Streams, Canals | Soft Crossing Penalty | 10m – 20m | Additive Resistance |
| **PARCEL** | Cadastral Private Land Boundaries | Soft Land Impact | 0m | Additive Base Cost (Land acquisition penalty) |

### Hard Exclusion vs. Soft Crossing Resistance
- **Hard Exclusions**: Cells intersecting hard exclusion buffers are marked as impenetrable (`weight = inf`). A* routing will never traverse these cells. If a turbine or substation is located inside a hard exclusion buffer, the pre-validation pipeline immediately rejects the request with a clear diagnostic violation.
- **Soft Penalties**: Crossing or paralleling soft constraint buffers applies an additive multiplier to the cell traversal cost, encouraging routes to cross perpendicularly at the narrowest point rather than running along the corridor.

---

## Right-of-Way (ROW) Corridor Analysis (`row_analysis.py`)

For constructability evaluation and lifecycle costing, refined 2D route centrelines are expanded into flat-ended metric corridors:

```python
corridor_polygon = route_linestring.buffer(
    distance=row_width_m / 2.0,
    cap_style="flat",
    join_style="mitre"
)
```

Using a spatial index (`shapely.STRtree`), the system calculates:
- **Dissolved ROW Footprint**: Union of all feeder corridor polygons ($m^2$).
- **Cadastral Intersections**: Unique parcels intersected by the corridor polygon.
- **Road Crossings**: Exact line-line intersection events between route centrelines and road centrelines.
- **Soft / Environmental Overlap**: Centrelines and polygon areas overlapping sensitive zones.

---

## Back-Transformation & Presentation (`geojson.py`)

Before returning data over the HTTP API:
1. All projected `LineString` routes, `Point` turbines/substations, and `Point` pole locations are transformed back to WGS84 using the inverse `Transformer`.
2. Coordinates are formatted as $[ \text{longitude}, \text{latitude} ]$ with strict float finiteness checks.
3. A spatial bounding box `bbox = [min_lon, min_lat, max_lon, max_lat]` is calculated for map camera centering.

---

## Related Notes

- [[Overview & Layout]]
- [[Surge MVP Ticket Plan]]
- [[presentation-boundary|Python Presentation Boundary]]
- [[Canonical Candidate Engineering Metrics]]
- [[Route Scoring Architecture]]
