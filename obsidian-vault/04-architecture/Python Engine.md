# Python Optimization Engine (FastAPI)

Source Code:
`optimizer/app/`

## Tech Stack
- **Framework**: FastAPI (Uvicorn / Gunicorn)
- **Spatial Processing**: GeoPandas, Shapely, Rasterio, PyPROJ
- **Electrical Simulation**: pandapower
- **Graph Optimization**: NetworkX, SciPy, Custom A* / MST

## Core Workflows
1. **WTG Clustering**: Groups wind turbines into feeders under thermal ampacity limits.
2. **Cost Surface Generation**: Combines DEM slope rasters, forest boundaries, road proximity, and parcel compensation into a spatial cost grid.
3. **Route Pathfinding**: Runs multi-objective A* search across cost surface to determine line corridors.
4. **Pole Placement & Span Solver**: Places suspension and tension poles along candidate paths according to terrain profile and sag equations.
5. **Electrical Flow Simulation**: Runs load flow via pandapower to compute losses and voltage drops.

---

## Related Notes
- [[System Overview]]
- [[Routing]]
- [[WTG Grouping]]
- [[Cost Model]]
