# Project Scope

## In Scope (MVP & Phase 1)
- Radial collector network routing for wind turbine generator (WTG) groups.
- PostGIS spatial data ingestion (DEM, cadastral parcels, roads, forests, substations).
- Multi-objective A* / Minimum Spanning Tree routing algorithms.
- pandapower electrical load flow simulation & voltage drop analysis.
- Variable span pole placement algorithm based on elevation profile.
- Scenario comparison UI using the API contract values: Minimum Cost, Minimum Land Impact, Minimum Environmental Impact, and Balanced.
- GeoJSON export and basic engineering summary reports.

## Out of Scope (Future Phases)
- Ring / mesh topology routing.
- Dynamic real-time weather grid degradation models.
- 3D CAD / BIM export integrations.

## Current Delivery State

The repository currently implements the application foundation, spatial persistence, Point preprocessing, candidate-graph construction, capacity-constrained WTG grouping, per-feeder MST topology, A* routing over a uniform cost surface, and obstacle-safe route refinement. SURGE-PY-010 adds standalone geometry-based pole placement, and SURGE-PY-011 adds standalone projected [[ROW Corridor Analysis]] over constraint geometries. Neither standalone stage is called by the service or exposed through the API. Production terrain-layer processing, constraint transport, terrain/clearance-aware pole engineering, electrical simulation, scenario scoring, and comparison remain planned. See [[Dashboard]] and [[System Overview]] for the detailed implementation boundary.
