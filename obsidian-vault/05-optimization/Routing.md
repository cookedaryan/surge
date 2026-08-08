# Spatial Routing Design

> [!warning] Implementation status: Planned
> The repository currently builds straight-line candidate edges only. It does not build a raster cost surface or run A* or Dijkstra.

## Topology Versus Routing

Topology chooses which assets connect. Spatial routing chooses the geographic path used by each selected connection. Keeping the stages separate allows a network tree to be evaluated over different environmental or land-cost scenarios.

## Cost Surface

A cost surface divides a project area into cells or graph edges and assigns traversal cost. A general weighted cost is:

$$
C = w_d C_d + w_s C_s + w_l C_l + w_a C_a + w_e C_e
$$

- `C_d`: base distance or construction length
- `C_s`: terrain slope/foundation difficulty
- `C_l`: land and compensation impact
- `C_a`: construction access or road proximity
- `C_e`: environmental impact
- `w_*`: scenario-specific weights

A **hard exclusion** is an impassable region, represented by removing nodes/edges or using infinite cost. A **soft penalty** remains traversable but more expensive. The distinction must be explicit because an arbitrarily large penalty does not guarantee zero encroachment.

## A* and Dijkstra

**Dijkstra's algorithm** expands paths in increasing accumulated cost and finds a least-cost route when weights are non-negative.

**A*** adds a heuristic estimate of remaining cost. It finds the same optimum when the heuristic never overestimates. A distance heuristic must be scaled consistently with the minimum traversal cost; otherwise optimality can be lost.

## Planned Pipeline

1. Transform all vector and raster inputs into one projected project CRS.
2. Clip data to a buffered project extent.
3. Derive slope and other raster/vector penalty layers.
4. Rasterize hard exclusions and weighted costs at a documented resolution.
5. Route selected topology edges with A*; use Dijkstra as a correctness baseline.
6. Convert cell paths to LineStrings and simplify cautiously.
7. Recheck all simplified segments against exclusions.
8. Transform final GeoJSON back to WGS84.

## Decisions That Must Be Documented During Implementation

- grid resolution and its accuracy/performance trade-off
- diagonal movement and corner-cutting rules
- how line crossings and shared corridors are scored
- behavior when no feasible route exists
- path simplification tolerance
- reproducibility and scenario weight normalization

## Related Notes

- [[Feeder Planning]]
- [[Cost Model]]
- [[Geospatial Integrity & CRS]]
- [[Pole Placement]]
- [[Explainability]]
