# SURGE-PY-011: ROW Corridor and Constraint Analysis

> [!success] Algorithm status: Implemented standalone
> `app/gis/row_analysis.py` builds projected right-of-way corridors and analyses them against projected project constraints. The FastAPI pipeline does not yet receive constraint layers or expose these results.

## Purpose

A **right-of-way (ROW) corridor** is the land footprint reserved around a route centreline for construction, operation, access, safety clearance, and maintenance. SURGE represents the configured width as the **total corridor width**. A route with an 18 m ROW is therefore buffered by 9 m on each side.

The analysis answers questions such as:

- Which cadastral parcels overlap the proposed corridor?
- Does the corridor enter a hard restricted or environmental area?
- How much corridor area overlaps each areal constraint?
- How much of the route centreline lies inside a constraint?
- How many transverse road crossings or road-footprint passages occur?
- How much ROW area is summed across segments, and how much unique land is occupied after overlaps are dissolved?

## Spatial Contract

Shapely geometries do not carry CRS metadata. `analyse_row_corridors` therefore receives route CRS provenance explicitly, while `ProjectConstraintLayers` carries the constraint CRS. Both values are `pyproj.CRS` objects and must describe equivalent projected coordinate systems whose axes are measured in metres.

CRS is deliberately not stored in `RowConfig`. Corridor width is an analysis policy; CRS is provenance supplied by the higher-level project spatial context. When the module is integrated, `ProjectSpatialData.projected_crs` should be passed as the route CRS.

Geographic longitude/latitude coordinates are rejected because buffering a route by a value expressed in metres is not meaningful in angular degrees. Projected CRSs using feet are also rejected unless the data is first transformed into the project metric CRS.

## Domain Models

### `RowConfig`

- `corridor_width_m`: total ROW width; it must be positive and finite.
- `cap_style`: defaults to `flat`, so the buffer stops at exact route endpoints.
- `join_style`: defaults to `round` around route turns.
- `minimum_overlap_area_m2`: optional filter for insignificant areal contact.
- `minimum_overlap_length_m`: optional filter for insignificant linear contact.
- `crossing_tolerance_m`: tolerance used to deduplicate multipart road-crossing points.

### `ConstraintFeature`

Each feature has a stable identifier, layer type, projected geometry, and optional `hard` or `soft` severity. Supported layers are parcel, restricted, forest, road, water, and environmental.

Areal layers require Polygon or MultiPolygon geometry. Roads and water may be represented by linear or areal geometry. This distinction matters because a road centreline produces point crossing events, while a road footprint produces a positive-length passage along the route.

### `RouteRowCorridor`

The corridor retains feeder ID, start/end node IDs, refined centreline geometry, buffered ROW geometry, route length, corridor width, and segment-level area. Route-edge identity is retained because one feeder normally contains several refined physical route segments.

### `RowIntersection`

One record represents one route-segment/constraint event and reports:

- `intersection_area_m2`: ROW area overlapping the constraint.
- `route_overlap_length_m`: route centreline length inside or on the constraint.
- `constraint_length_within_corridor_m`: linear constraint length inside the ROW.
- `touches_only`: whether the geometries only meet at their boundaries.
- Feeder, route-edge, constraint, layer, and severity metadata.

These measurements are separate because the boundary length of a polygon overlap is not an engineering exposure length.

## Analysis Flow

1. Validate corridor configuration and metric CRS compatibility.
2. Validate identifiers, layer types, severity, and geometry families.
3. Repair invalid Shapely geometries with `validate_geometry` when possible.
4. Reject invalid or empty critical constraints; record empty non-critical constraints as skipped.
5. Validate each refined route and create a flat-ended buffer at half the total width.
6. Build one Shapely `STRtree` over validated constraint geometries.
7. Query bounding-box candidates for each corridor and calculate exact intersections.
8. Sort events by route and constraint identity for deterministic output.
9. Calculate segment sums, unique footprint area, parcel/restricted aggregates, road crossings, and the hard-violation flag.

## Summed Area vs Unique Footprint

`total_row_area_m2` is the sum of each route segment's corridor area. It is useful for segment-level engineering quantities but double-counts overlap at junctions and shared alignments.

`unique_row_footprint_area_m2` dissolves all corridor polygons with a spatial union before measuring area. It represents the unique projected land footprint and is the appropriate starting point for total land-take reporting.

## Contact and Threshold Semantics

By default, any non-empty spatial contact is recorded, including a boundary-only touch. A caller can set positive minimum area and length thresholds to filter insignificant touches or floating-point slivers. The record preserves `touches_only` so later policy can distinguish contact from interior overlap.

The analysis reports a hard violation when an included intersection has `severity="hard"`. Layer type alone does not silently assign severity; constraint ingestion must provide the applicable project policy.

## Road Crossings

- Linear road geometry: count distinct transverse intersection points. Tangencies and collinear overlaps are not counted as crossings.
- Areal road geometry: count positive-length connected route passages through the road footprint.
- Multipart point results are deduplicated within `crossing_tolerance_m`.

`road_crossing_count` is a count of route/road crossing events, not a count of unique road feature IDs.

## Current Boundary

The algorithm has no FastAPI, GeoJSON, Java, database, or cost-surface dependency. This keeps its metric geometry calculations independently testable, but it also means the feature is not yet end-to-end:

- `OptimisationRequest` has no project constraint layers.
- The Java optimization client does not send parcel, road, forest, water, environmental, or restricted-zone features to Python.
- `OptimisationService` does not invoke the analysis.
- Corridors and intersection results are not transformed to WGS84, serialized, or persisted.
- Compensation rates and parcel ownership are outside SURGE-PY-011.

## Related Notes

- [[Python Engine]]
- [[Routing]]
- [[GIS Cost Surface]]
- [[Per-Feeder MST Topology]]
- [[Pole Placement]]
