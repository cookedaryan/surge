# Spatial Routing Design

## Current Status

[[Per-Feeder MST Topology]] selects the logical collector-network connections. SURGE-PY-008 routes every selected edge with A* over the projected [[GIS Cost Surface]], and SURGE-PY-009 refines each grid path into a cleaner LineString before it is transformed to WGS84.

The production surface is currently uniform with cost `1.0`. The pipeline is therefore cost-surface-aware, but it is not terrain-aware until restrictions, slope, land, access, and environmental layers are rasterized.

## Topology, Routing, and Refinement

The three stages solve different problems:

1. **Topology** decides which substation and WTG nodes connect.
2. **A* routing** chooses a sequence of traversable raster cells for each topology edge.
3. **Route refinement** removes unnecessary grid-shaped bends without crossing hard exclusions or increasing the integrated traversal cost of the replaced subpath.

Keeping these stages separate allows the same electrical topology to be evaluated under different spatial scenarios while retaining the original A* measurements for audit.

## Cost Surface

A raster cost surface assigns each cell a traversal cost:

$$
C = w_d C_d + w_s C_s + w_l C_l + w_a C_a + w_e C_e
$$

- `C_d`: base distance cost
- `C_s`: slope or construction difficulty
- `C_l`: land or ROW impact
- `C_a`: accessibility or road proximity
- `C_e`: environmental impact
- `w_*`: scenario-specific weights

A finite value is a soft traversal cost. Positive infinity is a hard exclusion. SURGE-PY-007 currently initializes only the uniform `C_d = 1.0` base; the other layers remain planned.

## A* Routing

For each selected MST edge, the pipeline:

1. Converts the exact projected endpoints to raster cells.
2. Runs deterministic eight-neighbor A*.
3. Prevents diagonal corner cutting beside blocked cells.
4. Converts intermediate cells back to projected cell centers.
5. Preserves the exact start and end coordinates.
6. Raises a domain error when an endpoint is blocked, outside the surface, or no path exists.

Routing failures are returned as HTTP 422 because they describe an infeasible spatial request rather than an unexpected server failure.

## SURGE-PY-009 Refinement

Refinement first validates every original segment, removes consecutive duplicates, and removes forward-moving collinear points. It then uses deterministic farthest-visible shortcutting.

A shortcut is accepted only when:

- Both endpoints remain within the closed raster extent.
- Its supercover touches no blocked cell.
- Its integrated traversal cost is no greater than the cost of the subpath it replaces, within floating-point tolerance.

The supercover checks all cells touched at internal grid boundaries and corners. At the outer raster boundary, only cells that actually exist inside the surface are considered; an endpoint that genuinely lies outside the extent is still rejected.

Refined traversal cost is calculated from the physical length inside each crossed cell multiplied by that cell's cost. When a segment follows an internal cell boundary, the higher adjacent cost is used conservatively.

Coincident endpoints are rejected because duplicate removal would otherwise leave fewer than two distinct coordinates and produce a degenerate route. The API reports this as HTTP 422.

## API Measurements

Each routed-edge Feature exposes:

- `length_m` and `traversal_cost`: compatibility aliases for the refined values
- `original_length_m`: raw A* LineString length
- `refined_length_m`: post-refinement LineString length
- `original_traversal_cost`: discrete A* traversal cost
- `refined_traversal_cost`: continuously integrated cost of the refined geometry

The original and refined traversal costs use related but different measurement models and should not be compared as if they were identical calculations. Cost-preserving shortcut decisions compare continuous integrated costs on both candidate and replaced geometry.

## Remaining Decisions

- GIS layer rasterization and cost normalization
- Grid resolution versus memory and geometric accuracy
- Performance limits for very long obstacle-rich paths
- Feeder-segment aggregation in Java reports
- Route smoothing beyond visibility shortcutting
- Pole placement and ROW corridor generation

## Related Notes

- [[GIS Cost Surface]]
- [[Per-Feeder MST Topology]]
- [[Feeder Planning]]
- [[Cost Model]]
- [[Geospatial Integrity & CRS]]
