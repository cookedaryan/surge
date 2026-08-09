# Variable-Span Pole Placement

> [!warning] Implementation status: Planned
> No pole-placement or elevation-profile solver exists in the current Python service.

## Concepts

A **span** is the horizontal distance between adjacent supports. Span selection affects pole count, sag, conductor clearance, structural loads, access, and cost. A maximum span alone is not sufficient: terrain, conductor properties, wind/ice loading, line angle, crossings, and required clearance also matter.

Common preliminary pole roles include:

- **Suspension/tangent**: supports a relatively straight run.
- **Angle/tension**: resists unbalanced forces at direction changes.
- **Terminal/dead-end**: anchors conductor at a feeder end.
- **Crossing**: provides special clearance or reliability at roads and other infrastructure.
- **Junction**: supports a modeled branch or shared-trunk connection.

## Planned Processing

1. Sample a DEM elevation profile along a routed LineString.
2. Insert mandatory supports at terminals, major angle changes, crossings, and junctions.
3. Generate optional candidate support positions.
4. Solve for spans within engineering bounds while checking ground clearance and structural rules.
5. Assign preliminary pole types from angle, load, and terminal conditions.
6. Feed quantities and foundation classes into [[Cost Model]].

## Safety Boundary

Documentation values such as a 250 m maximum or a 15-degree angle rule are project requirements, not universal engineering standards. Production rules must reference the selected conductor, voltage, pole catalogue, governing standard, and approved structural calculations.

## Related Notes

- [[Routing]]
- [[Feeder Planning]]
- [[Cost Model]]
