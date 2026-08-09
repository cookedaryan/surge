# Spatial Routing Design

## Current Status

[[GIS Cost Surface]] now provides a uniform projected raster, affine transform, and coordinate helpers. [[Per-Feeder MST Topology]] provides the logical edges that must eventually be routed. A* and Dijkstra path search, GIS penalty layers, and route smoothing remain planned.

The current API exposes each MST edge as a two-coordinate WGS84 LineString. Those straight segments visualize topology only; they are not cost-surface routes.

## Topology Versus Routing

Topology chooses which assets connect. Routing chooses the geographic corridor used to realize each selected connection. Keeping them separate allows one topology edge to be evaluated over different land, terrain, and environmental scenarios.

## Cost Surface

A raster cost surface assigns each cell a traversal cost:

$$
C = w_d C_d + w_s C_s + w_l C_l + w_a C_a + w_e C_e
$$

- `C_d`: base distance cost
- `C_s`: slope or construction difficulty
- `C_l`: land/ROW impact
- `C_a`: accessibility or road proximity
- `C_e`: environmental impact
- `w_*`: scenario-specific weights

A hard exclusion should be represented as non-traversable, currently planned as positive infinity. A soft penalty stays traversable at increased cost.

SURGE-PY-007 implements only the uniform `C_d = 1.0` foundation. It does not yet produce the combined equation above.

## Planned A* Integration

1. Build one cost surface covering the projected project extent.
2. Rasterize restrictions, terrain, parcels, roads, and scenario weights.
3. Convert each MST edge endpoint with `world_to_grid`.
4. Run A* over finite cells, with Dijkstra as a correctness baseline.
5. Convert returned cell centers with `grid_to_world`.
6. create a projected LineString and verify it against hard exclusions.
7. Transform it back to WGS84 and return it as route GeoJSON.

## Required Routing Decisions

- four- or eight-neighbor movement
- diagonal cost and corner-cutting rules
- admissible A* heuristic
- no-path error semantics
- boundary and nodata behavior
- cost normalization across layers
- grid resolution versus memory and geometric accuracy
- simplification tolerance and post-simplification constraint checks

## Related Notes

- [[GIS Cost Surface]]
- [[Per-Feeder MST Topology]]
- [[Feeder Planning]]
- [[Cost Model]]
- [[Geospatial Integrity & CRS]]
