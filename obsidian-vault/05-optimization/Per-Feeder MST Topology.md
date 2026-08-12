# SURGE-PY-006: Per-Feeder MST Topology

> [!success] Algorithm status: Implemented and exposed as preliminary GeoJSON
> The per-feeder MST is built, routed over a base uniform cost surface, contributes to `metrics.total_length_m`, and is serialized as one routed LineString Feature per selected edge.

## Purpose

WTG grouping answers **which turbines belong to each feeder**. Topology answers **which assets should be connected within that feeder**. Geographic routing later answers **where each selected connection should run across the ground**.

SURGE-PY-006 creates one preliminary radial topology for every `FeederAssignment`. Each tree contains the feeder's WTGs and the project substation.

## Minimum Spanning Tree Concept

A **spanning tree** connects every node in a graph without cycles. For `N` nodes, a valid tree has exactly `N - 1` edges.

A **minimum spanning tree (MST)** is the spanning tree with the smallest sum of edge weights. The current candidate graph is complete and each edge weight is its straight-line Euclidean distance in the project's UTM CRS. The selected MST therefore minimizes preliminary straight-line topology length for that feeder.

An MST does not choose a terrain-safe corridor, create junction nodes, check voltage drop, or avoid restricted polygons. Those are later stages.

## Inputs

`build_feeder_mst(graph, grouping)` consumes:

- the complete NetworkX graph from `build_project_graph`
- the deterministic `FeederGroupingResult` from `group_wtgs`

Graph nodes use namespaced identifiers:

- `substation:<substation_id>`
- `wtg:<turbine_id>`

Every graph edge currently carries identical `weight` and `distance_m` values measured in meters.

## Algorithm

For each feeder assignment, `app/algorithms/topology.py`:

1. Requires exactly one graph node whose `type` is `substation`.
2. Converts every raw turbine ID in the assignment to its `wtg:` graph ID.
3. Rejects an assigned turbine that is absent from the graph.
4. Rejects a WTG assigned to more than one feeder.
5. Creates an induced subgraph containing only that feeder's WTGs and the substation.
6. Calls `networkx.minimum_spanning_tree` using the `weight` edge attribute.
7. Verifies the result with `networkx.is_tree`; a disconnected feeder subgraph is rejected.
8. Sums `distance_m` across the selected edges.
9. Sorts normalized edge pairs for deterministic output.
10. Checks that assignment count matches `feeder_count` and that the assigned-WTG count matches the graph WTG count.

The substation is intentionally included in every feeder tree. WTGs belong to one feeder because the grouping stage produces disjoint assignments.

## Output Models

`FeederTopology` contains:

- `feeder_id`
- ordered `node_ids`
- `total_capacity_mw` copied from the grouping result
- `total_length_m`, the sum of routed edge distances
- deterministic `mst_edges`
- the NetworkX `mst_graph`

`CollectorTopologyResult` contains the tuple of feeder trees.

Although `FeederTopology` is a frozen dataclass, `mst_graph` is a mutable NetworkX object. Callers should treat it as read-only.

## Service Integration

`OptimisationService.optimise` runs the stages in this order:

```text
GeoJSON preprocessing
    -> complete project graph
    -> capacity-constrained WTG grouping
    -> one MST per feeder
    -> sum feeder MST lengths
    -> OptimisationResponse.metrics.total_length_m
```

`metrics.total_length_m` is the routed path length. For every selected edge, the service routes it over the base cost surface, transforms coordinates back to WGS84, and emits a LineString Feature with `feederName` and an `edge` label.

The GeoJSON now makes topology visible, but it uses the route response field before physical routing exists. Downstream consumers must treat these features as preliminary edges.

## Correctness Invariants

For data produced by the current pipeline:

- each feeder tree contains its assigned WTGs and the substation
- each tree is connected and acyclic
- each tree has `node_count - 1` edges
- feeder capacity is preserved from the validated grouping stage
- edge and feeder ordering is deterministic
- lengths use projected meter coordinates rather than longitude/latitude degrees

## Contract Assumptions and Limitations

- Exactly one substation, matching `feeder_count`, and duplicate assignments are now explicitly validated.
- WTG coverage is checked by comparing counts rather than comparing `assigned_wtgs` with `all_wtgs`. For a malformed graph containing a `wtg:`-named node with the wrong type, equal counts could still hide the real unassigned WTG. Normal graphs from `build_project_graph` cannot produce this mismatch.
- NetworkX uses `weight` to select edges. Graphs supplied outside `build_project_graph` must provide valid finite weights and `distance_m` values.
- Each feeder is optimized independently. The implementation does not optimize shared trunks or junctions between feeders.
- The complete candidate graph and Euclidean MST ignore terrain, parcels, exclusions, crossings, and existing infrastructure.
- The API exposes selected edges as individual Features rather than one connected feature per feeder.
- Python writes the property `feeder_id`, while the current Java route importer recognizes `feederName`, `feeder_name`, `name`, or `id`. Java therefore falls back to generated names and loses the original feeder identifier.
- Java persists every edge Feature as a separate `GeneratedRoute`, so feeder edge count can be mistaken for feeder route count.

## Test Coverage

`tests/test_topology.py` verifies node inclusion, substation inclusion, connectivity, acyclicity, `N - 1` edges, minimum-weight selection, length summation, multiple feeders, a single-WTG feeder, and rejection of an unknown turbine.

Missing focused cases include no/multiple substations, disconnected feeder subgraphs, inconsistent grouping metadata, duplicate/cross-feeder assignments, exact set coverage, deterministic edge order, and assertions for the returned WGS84 GeoJSON contract.

## Next Integration Step

The next routing stage should convert each selected MST edge into a [[GIS Cost Surface]] routing request. Routed LineStrings can then replace straight segments. Before persistence, the Python and Java property contract must agree on feeder identity and whether a Feature represents one feeder, one topology edge, or one routed segment.

## Related Notes

- [[WTG Grouping]]
- [[Feeder Planning]]
- [[Routing]]
- [[GIS Cost Surface]]
- [[Geospatial Integrity & CRS]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]
