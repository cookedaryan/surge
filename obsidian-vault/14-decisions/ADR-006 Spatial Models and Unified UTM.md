# ADR-006: Use Typed Spatial Models and One UTM CRS per Project

- **Status**: Accepted and implemented for WTG/substation preprocessing
- **Date**: 2026-08-07

## Context

GeoJSON arrives in WGS84 longitude/latitude degrees, while graph distance, future buffers, and engineering dimensions require a shared linear coordinate system. Projecting every point independently could put neighboring assets in different UTM zones and make their coordinates incomparable.

## Decision

At the Python boundary:

1. Validate incoming WTG and substation Point features.
2. Calculate the arithmetic mean longitude/latitude of all points.
3. Select the WGS84 UTM CRS covering that mean point.
4. Transform all project Points into that single CRS with `always_xy=True`.
5. Store them in frozen `WindTurbine`, `Substation`, and `ProjectSpatialData` dataclasses.
6. Require algorithm code to operate on these projected models.

## Why UTM?

Typical wind farms occupy a compact region. UTM offers meter units and low local distortion, making it more appropriate than geographic degrees or Web Mercator for engineering calculations.

## Consequences

- **Positive**: Every internal graph coordinate and edge length uses one comparable metric space.
- **Positive**: Algorithms cannot accidentally read arbitrary GeoJSON structure.
- **Negative**: Large, polar, antimeridian, or multi-zone projects require a different projection policy.
- **Negative**: Outputs must be transformed back to WGS84 before GeoJSON serialization.

## Clarifications

The current center is an arithmetic mean, not a geodesic centroid. The code does not yet transform route outputs because route generation is not implemented. EPSG:3857 is not an approved engineering substitute for the selected UTM CRS.
