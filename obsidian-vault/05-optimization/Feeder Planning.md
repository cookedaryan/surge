# Feeder Topology Planning

## Current Status

Per-feeder radial topology is implemented by [[Per-Feeder MST Topology]]. Capacity-constrained grouping runs first, then every feeder receives an independent minimum spanning tree rooted at the project substation.

The result is a preliminary logical topology, not a constructible geographic route.

## Concepts

A **radial collector network** gives each WTG one electrical path to the substation. A **topology** describes which nodes connect; it does not describe the physical corridor followed by conductor.

A **candidate graph** contains possible connections. The current graph is complete, so every WTG and the substation are directly connected to every other node with a straight-line metric weight.

An **MST** selects the lowest-total-weight acyclic set of edges that connects all nodes in one feeder. This supplies a deterministic radial baseline without attempting the more difficult Steiner-tree problem, which may introduce new junction locations.

## Implemented Flow

1. [[WTG Grouping]] creates disjoint capacity-safe feeder assignments.
2. `build_project_graph` creates the complete projected graph.
3. `build_feeder_mst` extracts one subgraph per feeder plus the substation.
4. NetworkX selects the minimum-distance spanning tree for each subgraph.
5. The service sums all feeder tree lengths into the API metric.

## What Is Not Yet Implemented

- shared trunks or intermediate junction optimization
- route corridors around obstacles or across a cost surface
- conversion of selected edges to GeoJSON
- electrical direction, conductor sizing, voltage drop, or protection constraints
- persistence of feeder membership and selected topology edges
- replacement of Euclidean edge length with terrain-aware routed length

## Related Notes

- [[Per-Feeder MST Topology]]
- [[WTG Grouping]]
- [[Routing]]
- [[Cost Model]]
