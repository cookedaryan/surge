# Routing Algorithm Design

## Overview
The multi-objective routing algorithm finds optimal overhead line paths across a continuous cost surface built from terrain, land ownership, environmental restrictions, and road proximity.

## Core Steps
1. **Cost Grid Formulation**: Convert DEM rasters and vector polygons into a regular spatial grid.
2. **A* / Dijkstra Path Finding**: Calculate minimum cost path from WTG clusters / junctions to the substation.
3. **Path Smoothing**: Apply Bezier / Douglas-Peucker simplification while maintaining clearance constraints.

---

## Related Notes
- [[WTG Grouping]]
- [[Pole Placement]]
- [[Cost Model]]
- [[ML Ranking]]
- [[Explainability]]
