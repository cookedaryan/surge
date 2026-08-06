# ADR-002: Use PostGIS for Spatial Data Persistence

* Status: **Accepted**
* Date: 2026-08-04

## Context
SURGE handles cadastral parcel boundaries, DEM elevation contours, WTG points, and LineString feeder routes requiring spatial index queries (bounding boxes, intersections, distance computations).

## Decision
Use **PostgreSQL with PostGIS extension** as the spatial and relational database.

## Consequences
- **Positive**: Native spatial SQL support (`ST_Intersects`, `ST_Buffer`, `ST_DWithin`).
- **Negative**: Requires PostGIS-enabled database container in deployment.
