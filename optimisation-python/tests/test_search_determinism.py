"""Tests for determinism in search."""

import networkx as nx
from shapely.geometry import Point

from app.algorithms.topology import CollectorTopologyResult, FeederTopology
from app.algorithms.wtg_grouping import FeederAssignment, FeederGroupingResult
from app.optimisation.scenarios import design_fingerprint


def test_hash_candidate_topology_is_order_independent():
    # Two identical networks constructed in different order
    mst = nx.Graph()
    mst.add_edges_from([("A", "B"), ("C", "D")])

    t1 = FeederTopology(
        feeder_id="F1",
        node_ids=("A", "B"),
        total_capacity_mw=1.0,
        total_length_m=1.0,
        mst_edges=(("A", "B"),),
        mst_graph=mst,
    )
    t2 = FeederTopology(
        feeder_id="F2",
        node_ids=("C", "D"),
        total_capacity_mw=1.0,
        total_length_m=1.0,
        mst_edges=(("C", "D"),),
        mst_graph=mst,
    )

    topology1 = CollectorTopologyResult(feeders=(t1, t2))
    topology2 = CollectorTopologyResult(feeders=(t2, t1))

    grouping1 = FeederGroupingResult(
        2,
        (
            FeederAssignment("F1", ("A", "B"), 1.0, Point(0, 0)),
            FeederAssignment("F2", ("C", "D"), 1.0, Point(1, 1)),
        ),
    )
    grouping2 = FeederGroupingResult(
        2,
        (
            FeederAssignment("F2", ("C", "D"), 1.0, Point(1, 1)),
            FeederAssignment("F1", ("A", "B"), 1.0, Point(0, 0)),
        ),
    )

    h1 = design_fingerprint(grouping1, topology1, "SUB")
    h2 = design_fingerprint(grouping2, topology2, "SUB")

    assert h1 == h2
