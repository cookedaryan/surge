# Variable-Span Pole Placement

> [!note] Implementation status: Recommended-network workflow integration implemented — SURGE-PY-010/PY-023/PY-024
> `app/algorithms/pole_placement.py` provides geometry-based route placement, an explicit distinct-structure post-pass, and `place_poles_on_network()` for the winning PNC. `OptimisationWorkflowResult.pole_network` owns the canonical deduplicated domain result. DEM sag/clearance analysis and structural optimisation remain planned for later work.

## SURGE-PY-010 Implementation

`place_poles_on_route(route, config)` accepts one projected `RefinedPhysicalRoute` from SURGE-PY-009 and a `PolePlacementConfig`. It returns a `PoleRouteResult` containing ordered `Pole` and `PoleSpan` objects. The geometry must be a valid, finite, non-degenerate LineString whose coordinates use the same metre-based projected CRS as the upstream route.

Key behaviours:

- **Mandatory structures**: route start/end (terminal) and interior LineString vertices with deflection ≥ `angle_pole_threshold_deg` (angle). Deflection is the angle between the incoming and outgoing forward vectors: 0° is straight, 90° is a right-angle turn, and 180° is a reversal. With a threshold of 180°, exact reversals still become angle poles.
- **Independent sections**: mandatory positions divide a route into sections. Intermediate fill poles are calculated separately inside each section, so an angle pole is never displaced merely to improve the spacing of a neighbouring section.
- **Span-count rule**: for a section longer than `min_span_m`, the first candidate is `max(1, round(section_length / target_span_m))`. Python's `round` uses ties-to-even. The count increases until the section's arc-length interval is no greater than `max_span_m`.
- **Soft minimum**: `min_span_m` controls whether a section is subdivided; it is not enforced as a lower bound on every resulting span. A section at or below the minimum receives no fill pole. A whole short route can still contain more than two poles when it has mandatory angle vertices.
- **Span measurement**: `distance_along_route_m` is arc length measured along the LineString. `PoleSpan.span_length_m` is instead the Euclidean chord between adjacent pole Points, so it can be shorter than their arc-length separation when the route bends between them.
- **Deterministic IDs**: IDs use `{feeder_id}-P{sequence:03d}`. Direct single-route placement starts at one by default. `place_poles_on_routes()` maintains a separate cumulative sequence for each feeder, preventing collisions when several routes share a `feeder_id`.
- **Batch result**: `place_poles_on_routes()` returns a `CollectorPoleResult` with one route result per input route, a route-local `PhysicalPole` view, and aggregate pole/span counts. Route order determines feeder-wide route-local sequences and must therefore be deterministic when those IDs matter.
- **Network endpoint deduplication (SURGE-PY-023)**: `deduplicate_pole_endpoints()` returns a new `CollectorPoleResult` whose `physical_poles` view merges terminal records only when different routes declare the same topology node and their coordinates are within tolerance. Route-local poles/spans remain unchanged for traceability; `total_poles` becomes the distinct physical-structure count, while `total_spans` remains the route conductor-span count.
- **Merged identity and role**: a shared endpoint becomes a `junction` structure with a deterministic hash-based ID plus sorted feeder, route/segment, and source-pole references. Its coordinate is a deterministic existing endpoint coordinate rather than an off-route centroid. PNC presentation adapters preserve each canonical `PNCSegment.segment_id` as the route reference rather than replacing it with an inferred node-pair label.
- **Clustering rule**: strict pairwise membership is used. A candidate joins a cluster only when it is within tolerance of every existing member, so transitive A–B/B–C proximity cannot merge A and C when they exceed tolerance. Nearby mid-route poles and endpoints with different topology node IDs never merge.

## How the Components Work Together

1. SURGE-PY-009 produces projected `RefinedPhysicalRoute` objects after A* routing and geometry refinement.
2. `PolePlacementConfig` supplies the preferred, soft-minimum, hard-maximum, and angle-threshold policies.
3. `place_poles_on_route()` detects mandatory positions, fills each resulting section, interpolates exact Point geometries, classifies poles, and connects adjacent poles with `PoleSpan` records.
4. `place_poles_on_routes()` applies that route-local operation to a batch and coordinates feeder-wide numbering.
5. `place_poles_on_network()` converts the recommended PNC's actual routed segments while preserving their stable IDs.
6. `deduplicate_pole_endpoints()` creates the distinct physical-structure view returned by the optimisation workflow before persistence, costing, or future scoring.

The route-local and batch APIs are deliberately independent of `CostSurface`. Pole placement consumes the refined geometry rather than GIS raster internals, which keeps the algorithm testable and allows later terrain, crossing, or policy stages to add mandatory locations without coupling span placement to A* implementation details.

## Current Integration Boundary

The rich optimisation path selects its recommended scenario before running pole
placement. PY-024 then applies route-local placement and PY-023 deduplication to
that exact `ProjectPNCNetwork` and attaches the result to
`OptimisationWorkflowResult.pole_network`. Pole count remains an engineering
metric and does not participate in candidate scoring.

Network-level endpoint deduplication is implemented as an explicit post-pass.
It does not rewrite route-local pole IDs or spans. Downstream consumers must use
the returned `physical_poles` view and deduplicated `total_poles`; PY-025 owns
the formal public GeoJSON/API contract.

## Concepts

A **span** is the horizontal distance between adjacent supports. Span selection affects pole count, sag, conductor clearance, structural loads, access, and cost. A maximum span alone is not sufficient: terrain, conductor properties, wind/ice loading, line angle, crossings, and required clearance also matter.

Common preliminary pole roles include:

- **Suspension/tangent**: supports a relatively straight run.
- **Angle/tension**: resists unbalanced forces at direction changes.
- **Terminal/dead-end**: anchors conductor at a feeder end.
- **Crossing**: provides special clearance or reliability at roads and other infrastructure.
- **Junction**: supports a modeled branch or shared-trunk connection.

## Planned Engineering Extensions

1. Sample a DEM elevation profile along a routed LineString.
2. Add mandatory crossing structures and engineering-specific junction classes beyond the geometry-only PY-023 merge role.
3. Generate terrain-aware candidate support positions.
4. Check conductor sag, ground clearance, structural loading, and applicable engineering standards.
5. Select structural pole classes rather than only geometric terminal/angle/intermediate roles.
6. Feed deduplicated quantities and future foundation classes into [[Cost Model]].

## Safety Boundary

Documentation values such as a 250 m maximum or a 15-degree angle rule are project requirements, not universal engineering standards. Production rules must reference the selected conductor, voltage, pole catalogue, governing standard, and approved structural calculations.

## Related Notes

- [[Routing]]
- [[Feeder Planning]]
- [[Cost Model]]
