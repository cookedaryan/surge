# Feeder Topology Planning

> [!warning] Implementation status: Partial
> WTG groups and a complete candidate graph exist. The feeder tree, MST extraction, junction model, and route geometry do not.

## Concepts

A **radial collector network** connects each turbine to a substation through one electrical path. It is simpler to protect and operate than a meshed network, but a single fault can disconnect downstream turbines.

A **topology** describes which assets are connected, independent of the exact geographic path followed by each connection. A **route** is the physical LineString corridor used to realize a topology edge.

A **minimum spanning tree (MST)** connects all graph nodes without cycles while minimizing the sum of edge weights. With straight-line weights it gives a useful baseline topology, but it does not automatically respect terrain, restricted areas, electrical direction, feeder separation, or capacity.

## Current Foundation

`build_project_graph` creates an undirected complete NetworkX graph:

- one node for the substation and one per WTG
- namespaced IDs such as `wtg:WTG-001` and `substation:SUB-001`
- projected x/y coordinates, capacity, type, and Shapely Point on each node
- straight-line Euclidean `distance_m` and `weight` on every edge
- the selected CRS stored in graph metadata

For `N` nodes, the graph contains `N(N-1)/2` edges. This preserves every direct candidate but has quadratic memory and construction cost.

## Planned Topology Flow

1. Use [[WTG Grouping]] assignments to define feeder membership.
2. Select an MST or another radial tree for each group plus the substation.
3. Decide whether shared junctions are permitted and represent them explicitly.
4. Replace straight graph edges with obstacle- and terrain-aware routes.
5. Recalculate weights from actual routed length and engineering cost.
6. Verify connectivity, radiality, capacity, and electrical limits.

## Important Design Decision Still Open

The current graph includes the substation in one global complete graph, while feeder groups are calculated separately. The integration rule—per-group subgraphs, shared trunks, or independently routed feeders—must be defined before MST code is added. This is a business and electrical topology decision, not merely an implementation detail.

## Related Notes

- [[WTG Grouping]]
- [[Routing]]
- [[Pole Placement]]
