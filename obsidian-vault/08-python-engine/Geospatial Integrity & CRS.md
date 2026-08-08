# Geospatial Integrity and Coordinate Reference Systems

## Why Coordinate Systems Matter

Longitude and latitude describe positions on the Earth in angular degrees. Engineering quantities such as cable length, buffer width, parcel area, and pole span require linear units. Treating a degree as a meter produces invalid results, and applying a constant degrees-to-meters conversion becomes inaccurate away from the assumed latitude.

## Core Concepts

**CRS (coordinate reference system)** defines how coordinate numbers map to real locations. An **EPSG code** is a registry identifier for a CRS.

**WGS84 / EPSG:4326** is the geographic CRS used by the API and database. RFC 7946 GeoJSON uses longitude, latitude order and describes coordinates in WGS84.

**Projected CRS** maps part of the curved Earth onto a plane. Its axes can use meters, allowing ordinary Euclidean distance and area operations within the projection's valid region.

**UTM (Universal Transverse Mercator)** divides most of the world into six-degree longitude zones with northern and southern variants. UTM is appropriate for typical wind-farm footprints because local distortion is small and units are meters.

**Web Mercator / EPSG:3857** is designed for web-map display. Although its units are nominally meters, scale distortion varies by latitude. It must not be used for authoritative cable length, area, buffer, or pole-span calculations.

## SURGE Coordinate Rule

- API and database boundary: WGS84 GeoJSON and SRID 4326.
- Internal engineering calculations: one suitable projected CRS, currently a dynamically selected WGS84 UTM zone.
- Output route geometries: transform back to WGS84 before serializing as GeoJSON.

## Current Implementation

`process_project_data` accepts WTG GeoJSON plus substation GeoJSON and performs the following steps:

1. Accept a GeoJSON Feature or FeatureCollection.
2. Require at least one WTG and exactly one substation.
3. Parse each feature with Shapely and require Point geometry.
4. Validate finite longitude in `[-180, 180]` and latitude in `[-90, 90]`.
5. Require unique, non-empty IDs. WTG capacity must be positive and finite for the grouping stage.
6. Calculate the arithmetic mean longitude and latitude across all points.
7. Ask `pyproj` for the UTM CRS covering that mean point.
8. Build an `always_xy=True` transformer so coordinate order remains longitude/x then latitude/y.
9. Transform every Point into the same UTM CRS and return immutable `ProjectSpatialData`.

The implementation uses an arithmetic mean of point coordinates, not a polygon centroid or geodesic center. This is adequate for compact projects away from the antimeridian but should be revisited for unusually large or globally wrapping datasets.

## Why One CRS Per Project?

Projecting each WTG independently could place nearby turbines in different UTM coordinate spaces. Distances between coordinates from different CRSs are meaningless. Selecting one project CRS keeps graph weights, buffers, and future raster operations comparable.

## Current Limitations

- Projects spanning multiple UTM zones may experience edge distortion.
- Antimeridian and polar projects need special handling.
- The endpoint currently accepts only WTG and substation Points, not route, parcel, restricted-area, or DEM inputs.
- Output back-transformation is a design requirement but route generation is not implemented yet.
- `geometry.validate_geometry` can repair some invalid shapes, but the current Point preprocessing path does not call it.

## Related Notes

- [[Python Engine]]
- [[Overview & Layout]]
- [[Database]]
- [[ADR-006 Spatial Models and Unified UTM]]
