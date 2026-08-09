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

The repository currently implements the application foundation, spatial persistence, Point preprocessing, candidate-graph construction, and WTG grouping. Route generation, terrain processing, electrical simulation, pole placement, ROW intersection, scenario scoring, and comparison remain planned. See [[Dashboard]] and [[System Overview]] for the detailed implementation boundary.
