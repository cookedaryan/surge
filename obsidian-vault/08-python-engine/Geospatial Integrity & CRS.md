# Geospatial Integrity & Coordinate Systems

Geospatial accuracy is critical when computing cable lengths, slope penalties, ROW corridor buffers, and pole placement intervals.

## Core Rules for Coordinate Systems

1. **API Interchange Coordinates (WGS84 / RFC 7946)**
   - All GeoJSON inputs (`wtg_geojson`, `substation_geojson`) and GeoJSON outputs (`feeder_routes_geojson`) exchanged over the HTTP API MUST use RFC 7946 WGS84 coordinates in decimal degrees (`longitude, latitude` order).

2. **Internal Spatial Calculations (Meter-based Projected CRS)**
   - Before performing distance calculations, terrain slope analysis, buffer creation, cost-surface rasterization, routing, or span optimization, geometries MUST be transformed to an appropriate projected coordinate reference system (e.g., UTM zone in meters such as EPSG:32643 / EPSG:3857).
   - **Never** calculate meter-based distances or areas directly from geographic longitude/latitude degrees.

3. **Transformation Pipeline**
   ```text
   GeoJSON (WGS84 EPSG:4326) 
             │ (Input)
             ▼
   Transform to Meter Projected CRS (e.g. UTM / EPSG:32643)
             │
             ├─► Spatial Cost Surface & DEM Slope Calculation
             ├─► A* / Dijkstra Route Optimization
             ├─► Pole Placement & Variable Span Solver
             ├─► ROW Corridor Buffer & Parcel Intersection
             ▼
   Transform back to WGS84 (EPSG:4326)
             │ (Output)
             ▼
   GeoJSON API Response
   ```
