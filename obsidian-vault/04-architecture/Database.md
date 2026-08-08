# Database Architecture (PostGIS)

## Why PostGIS?

PostGIS extends PostgreSQL with geometry types, spatial functions, coordinate reference identifiers, and spatial indexes. PostgreSQL still supplies transactions, foreign keys, constraints, and relational querying; PostGIS adds the ability to store and query points, lines, and polygons without flattening them into ad-hoc JSON.

## Coordinate Storage Rule

All persisted geometry columns currently use SRID 4326 (WGS84). This is appropriate for interchange and map display. Accurate distance, area, and buffer calculations must transform data to a suitable projected CRS first; the SRID does not automatically make degree-based calculations metric.

## Schema

Flyway applies migrations in version order.

### V1: Project workspace

- `projects`: project metadata and optional Polygon boundary.
- `wtg_locations`: WTG identifier, positive MW capacity, and Point location.
- `substations`: substation identifier, optional positive MW capacity, and Point location.

### V2: Optimization and GIS records

- `cadastral_parcels`: parcel Polygon, owner, and non-negative acquisition rate.
- `restricted_areas`: exclusion Polygon, type, and non-negative buffer distance.
- `optimization_jobs`: lifecycle status, algorithm/scenario parameters, error text, and JSON result summary.
- `generated_routes`: feeder LineString, optional pole MultiPoint, length, cost, losses, and pole count.

Foreign keys connect all project-owned data to `projects`; routes belong to optimization jobs. Unique constraints prevent duplicate external IDs within a project. Check constraints reject negative capacities and metrics.

## Spatial Indexes

GiST indexes are defined on WTG points, substation points, parcel polygons, restricted polygons, and route paths. A spatial index narrows candidate geometries by bounding box before an exact predicate such as intersection is evaluated. It improves spatial query performance but does not replace correct predicates or CRS handling.

## Current Use

The Java backend persists and retrieves geometries through Hibernate Spatial/JTS. The Python service does not connect to PostGIS directly; Java serializes selected records into GeoJSON. This preserves Java as the persistence boundary and keeps Python stateless.

## Current Limitations

- No DEM/raster table or raster ingestion migration
- No authentication/user/project-membership schema
- No database-side ROW intersection query
- Route metrics are trusted values supplied when routes are stored
- Production backup, retention, and migration rollout procedures are not defined

## Related Notes

- [[System Overview]]
- [[Backend]]
- [[Geospatial Integrity & CRS]]
- [[ADR-002 Use PostGIS]]
