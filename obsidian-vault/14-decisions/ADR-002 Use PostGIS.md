# ADR-002: Use PostGIS for Spatial Persistence

- **Status**: Accepted and implemented
- **Date**: 2026-08-04

## Context

SURGE must persist application records together with WTG/substation Points, project and parcel Polygons, exclusion zones, route LineStrings, and pole MultiPoints. These objects need referential integrity, transactions, coordinate metadata, and spatial indexing.

## Decision

Use PostgreSQL with PostGIS as the authoritative database. Store API-facing vector geometries in SRID 4326 and use Flyway migrations to version the schema.

## Why This Decision

- PostgreSQL handles relational workflows and transactions.
- PostGIS provides standard geometry types, predicates, transforms, and GiST indexes.
- One database can enforce project ownership and geometry constraints without splitting metadata from spatial data.
- Flyway makes schema changes ordered and reviewable with the Java application.

## Consequences

- **Positive**: Spatial and relational records share transactional boundaries.
- **Positive**: Future ROW intersection and proximity queries can execute close to stored data.
- **Negative**: Local and production environments require a PostGIS-enabled database.
- **Negative**: SRID 4326 geometries must be projected before accurate meter/area calculations.

## Implementation

Flyway V1 creates projects, WTGs, and substations. V2 adds parcels, restricted areas, jobs, and generated routes with foreign keys, check constraints, uniqueness, and GiST indexes. Raster/DEM persistence is not implemented.
