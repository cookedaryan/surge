# SURGE-PY-007: GIS Cost Surface

> [!success] Foundation status: Implemented
> `app/gis/cost_surface.py` creates a uniform projected raster and coordinate-conversion helpers. Environmental layers, obstacles, scenario weights, and A* integration are not implemented yet.

## Purpose

A **cost surface** is a raster in which every cell stores the cost of entering or traversing that location. A future routing algorithm can operate on numeric cells without knowing whether a cost came from slope, land, access, or environmental policy.

The initial SURGE-PY-007 abstraction deliberately assigns every cell a base cost of `1.0`. This creates the geometry, transform, data type, and indexing contract required by the upcoming routing stage while keeping policy-layer rasterization separate.

## CostSurface Model

The frozen `CostSurface` dataclass contains:

- `costs`: two-dimensional NumPy `float32` array indexed as `[row, column]`
- `transform`: affine mapping between raster indices and projected coordinates
- `crs`: the project's projected `pyproj.CRS`
- `width` and `height`: raster column and row counts
- `resolution_m`: square cell size in meters

The dataclass is frozen, but its NumPy array remains mutable. This is intentional for later penalty and exclusion layers; callers can change cell values without replacing the surface object.

## Extent Construction

`build_project_cost_surface` collects every projected WTG Point plus the substation Point, calculates their minimum and maximum x/y coordinates, expands each side by `padding_m`, and calculates dimensions with ceiling division:

$$
\text{width}=\left\lceil\frac{x_{max}-x_{min}}{r}\right\rceil,
\qquad
\text{height}=\left\lceil\frac{y_{max}-y_{min}}{r}\right\rceil
$$

where `r` is `resolution_m`. Width and height are forced to at least one cell.

The default resolution is 10 m and default padding is 100 m. Resolution must be positive and finite.

## Affine Transform

The raster uses a conventional north-up transform:

- origin at the padded upper-left corner `(min_x, max_y)`
- positive columns move east by `resolution_m`
- positive rows move south because the y scale is negative

`grid_to_world(row, col)` returns the projected center of a cell by applying the transform to `(col + 0.5, row + 0.5)`.

`world_to_grid(x, y)` applies the inverse transform and floors the fractional row and column.

## Cost Semantics

- `1.0`: current uniform traversable base cost
- larger finite value: intended soft penalty
- positive infinity: intended hard exclusion/non-traversable cell

The builder currently creates only `1.0` cells. Tests demonstrate that callers can assign infinity, but no GIS layer is rasterized yet.

## Known Review Findings

- `padding_m` is not validated. Negative or non-finite padding can create an invalid or misleading extent.
- With `padding_m=0`, points on `max_x` or `min_y` map to column `width` or row `height`, which is outside the array. A strictly positive padding currently avoids this for project points.
- `world_to_grid` and `grid_to_world` do not enforce bounds; negative NumPy indices could wrap if a caller indexes without checking.
- Raster dimensions and allocation size are unbounded. Very small resolution or very large extents can exhaust memory.
- `width`, `height`, and `costs.shape` can disagree if a `CostSurface` is constructed directly.
- The cost surface is not called by `OptimisationService` yet.

## Test Coverage

`tests/test_cost_surface.py` checks CRS preservation, project-point containment with padding, padding dimensions, resolution, default costs, infinity semantics, both coordinate helpers, round trips, invalid resolution, deterministic dimensions, and non-negative initial cells.

Missing cases include zero-padding boundary containment, negative/non-finite padding, out-of-bounds coordinates and indices, maximum allocation size, direct model consistency, and a real preprocessing-to-cost-surface integration test.

## Next Step

Future layer builders should copy or update the base array with explicit units and precedence rules. A* should depend only on the final raster contract: dimensions, transform, finite entry costs, and hard exclusions.

## Related Notes

- [[Geospatial Integrity & CRS]]
- [[Routing]]
- [[Per-Feeder MST Topology]]
- [[Cost Model]]
