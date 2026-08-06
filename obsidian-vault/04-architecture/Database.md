# Database Architecture (PostGIS)

## Overview
PostgreSQL with PostGIS extension for storing both project metadata and spatial layers.

## Core Schema Tables
- `projects`: Wind farm project metadata, bounding box, CRS details.
- `wtg_locations`: Points for each wind turbine generator.
- `substations`: Substation coordinates and capacity limits.
- `cadastral_parcels`: Polygons representing land parcels and ownership.
- `restricted_areas`: Polygons representing forests, water bodies, and environmental zones.
- `optimization_jobs`: Job status, objective weights, and JSON output summary.
- `generated_routes`: LineStrings representing solved feeder corridors and pole coordinates.

---

## Related Notes
- [[System Overview]]
- [[ADR-002 Use PostGIS]]
