from dataclasses import dataclass

import networkx as nx

from app.algorithms.route_graph import turbine_node_id
from app.algorithms.wtg_grouping import FeederGroupingResult


@dataclass(frozen=True)
class FeederTopology:
    feeder_id: str
    node_ids: tuple[str, ...]
    total_capacity_mw: float
    total_length_m: float
    mst_edges: tuple[tuple[str, str], ...]
    mst_graph: nx.Graph


@dataclass(frozen=True)
class CollectorTopologyResult:
    feeders: tuple[FeederTopology, ...]


def build_feeder_mst(
    graph: nx.Graph,
    grouping: FeederGroupingResult,
) -> CollectorTopologyResult:
    """
    Builds a radial minimum spanning tree (MST) for each feeder group
    assigned in the FeederGroupingResult.

    Extracts the subgraph for the feeder's WTGs and the substation,
    computes the MST using NetworkX, and calculates total length.
    """
    substations = [
        n for n, data in graph.nodes(data=True) if data.get("type") == "substation"
    ]
    if len(substations) == 0:
        raise ValueError("Graph does not contain a substation node.")
    if len(substations) > 1:
        raise ValueError("Graph contains multiple substation nodes.")
    substation_id = substations[0]

    if len(grouping.assignments) != grouping.feeder_count:
        raise ValueError("Feeder count mismatch.")

    assigned_wtgs = set()
    feeders = []

    for assignment in grouping.assignments:
        feeder_nodes = [substation_id]
        for wtg_raw_id in assignment.turbine_ids:
            t_id = turbine_node_id(wtg_raw_id)
            if t_id not in graph:
                raise ValueError(
                    f"Assigned turbine {wtg_raw_id} (node {t_id}) not found in graph."
                )
            if t_id in assigned_wtgs:
                raise ValueError(f"WTG {wtg_raw_id} is assigned to multiple feeders.")
            assigned_wtgs.add(t_id)
            feeder_nodes.append(t_id)

        # Create subgraph containing only these nodes
        subgraph = graph.subgraph(feeder_nodes)

        # Compute Minimum Spanning Tree
        mst = nx.minimum_spanning_tree(subgraph, weight="weight")

        if not nx.is_tree(mst):
            raise RuntimeError(
                f"MST for feeder {assignment.feeder_id} is not a valid tree."
            )

        total_length_m = 0.0
        raw_edges = []

        for u, v, data in mst.edges(data=True):
            dist = data.get("distance_m", data.get("weight", 0.0))
            total_length_m += float(dist)
            raw_edges.append(tuple(sorted((u, v))))

        # Sort edges for deterministic output
        sorted_edges = tuple(sorted(raw_edges))

        feeders.append(
            FeederTopology(
                feeder_id=assignment.feeder_id,
                node_ids=tuple(feeder_nodes),
                total_capacity_mw=assignment.total_capacity_mw,
                total_length_m=total_length_m,
                mst_edges=sorted_edges,
                mst_graph=mst,
            )
        )

    all_wtgs = {n for n, data in graph.nodes(data=True) if data.get("type") == "wtg"}
    if len(assigned_wtgs) != len(all_wtgs):
        raise ValueError("Not all WTGs are assigned to a feeder.")

    return CollectorTopologyResult(feeders=tuple(feeders))
