# Python Engine Architecture & GIS Processing

The **SURGE Python GIS & Optimization Service** provides high-performance spatial algorithms and electrical calculations for the SURGE platform.

## Directory Layout
```text
optimisation-python/
+--- app
|    +--- algorithms
|    +--- gis
|    |    +--- __init__.py
|    |    +--- crs.py
|    |    +--- geojson.py
|    |    +--- geometry.py
|    |    \--- preprocessing.py
|    +--- models
|    |    +--- __init__.py
|    |    \--- spatial.py
|    +--- api
|    +--- core
|    +--- services
|    \--- utils
\--- tests
     +--- test_crs.py
     +--- test_geojson.py
     +--- test_geometry.py
     +--- test_preprocessing.py
```

## Key Architectural Principles

1. **Decoupled Service Layer**: Endpoint functions in `app/api/` delegate execution to services in `app/services/`. Algorithms reside in `app/algorithms/`.
2. **GIS & Preprocessing**: The `app/gis/preprocessing.py` layer converts incoming WGS84 GeoJSON API objects into strictly-validated metric point entities (`app/models/spatial.py`), completely decoupling the algorithm logic from standard HTTP GeoJSON structures.
3. **Pydantic 2 Validation**: Model configuration uses `SettingsConfigDict` and typed models.

## Geospatial Integrity & Coordinate Systems

Geospatial accuracy is critical when computing cable lengths, slope penalties, ROW corridor buffers, and pole placement intervals.

1. **API Interchange Coordinates (WGS84 / RFC 7946)**
   All GeoJSON inputs (`wtg_geojson`, `substation_geojson`) exchanged over the HTTP API MUST use RFC 7946 WGS84 coordinates in decimal degrees (`longitude, latitude` order).

2. **Internal Spatial Calculations (Meter-based Projected CRS)**
   Before performing distance calculations, geometries MUST be transformed to an appropriate projected coordinate reference system (e.g., UTM zone in meters). 

3. **Transformation Pipeline**
   ```text
   GeoJSON (WGS84 EPSG:4326) 
             │ (Input)
             ▼
   `app/gis/preprocessing.py`
     - Validates geometries (Points)
     - Calculates project centroid
     - Selects unified dynamic Meter Projected CRS
     - Returns `ProjectSpatialData` 
             │
             ├─► Spatial Cost Surface & Route Optimization
             ▼
   Transform back to WGS84 (EPSG:4326)
             │ (Output)
             ▼
   GeoJSON API Response
   ```
