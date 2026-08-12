import math

import networkx as nx
import pytest
from shapely.geometry import Point

from app.algorithms.route_graph import turbine_node_id
from app.algorithms.topology import build_feeder_mst
from app.algorithms.wtg_grouping import FeederAssignment, FeederGroupingResult


def create_mock_graph() -> nx.Graph:
    g = nx.Graph()
    g.add_node("substation:SUB1", type="substation")
    g.add_node(turbine_node_id("T1"), type="wtg")
    g.add_node(turbine_node_id("T2"), type="wtg")
    g.add_node(turbine_node_id("T3"), type="wtg")

    # Fully connect the nodes with given weights
    nodes = list(g.nodes)
    weights = {
        ("substation:SUB1", "wtg:T1"): 100,
        ("substation:SUB1", "wtg:T2"): 500,
        ("substation:SUB1", "wtg:T3"): 1000,
        ("wtg:T1", "wtg:T2"): 150,
        ("wtg:T1", "wtg:T3"): 800,
        ("wtg:T2", "wtg:T3"): 200,
    }

    for u in nodes:
        for v in nodes:
            if u != v:
                edge = tuple(sorted((u, v)))
                if edge in weights:
                    w = weights[edge]
                    g.add_edge(u, v, weight=w, distance_m=w)
    return g


def test_mst_contains_all_feeder_nodes() -> None:
    g = create_mock_graph()
    grouping = FeederGroupingResult(
        feeder_count=1,
        assignments=(FeederAssignment("F1", ("T1", "T2"), 10.0, Point(0, 0)),),
    )
    g.remove_node(turbine_node_id("T3"))
    res = build_feeder_mst(g, grouping)
    f1 = res.feeders[0]
    assert set(f1.node_ids) == {"substation:SUB1", "wtg:T1", "wtg:T2"}
    assert set(f1.mst_graph.nodes) == {"substation:SUB1", "wtg:T1", "wtg:T2"}


def test_substation_in_every_feeder_tree() -> None:
    g = create_mock_graph()
    grouping = FeederGroupingResult(
        feeder_count=2,
        assignments=(
            FeederAssignment("F1", ("T1",), 5.0, Point(0, 0)),
            FeederAssignment("F2", ("T2", "T3"), 10.0, Point(0, 0)),
        ),
    )
    res = build_feeder_mst(g, grouping)
    for f in res.feeders:
        assert "substation:SUB1" in f.node_ids
        assert "substation:SUB1" in f.mst_graph.nodes


def test_mst_is_connected() -> None:
    g = create_mock_graph()
    grouping = FeederGroupingResult(
        feeder_count=1,
        assignments=(FeederAssignment("F1", ("T1", "T2", "T3"), 15.0, Point(0, 0)),),
    )
    res = build_feeder_mst(g, grouping)
    assert nx.is_connected(res.feeders[0].mst_graph)


def test_mst_is_acyclic() -> None:
    g = create_mock_graph()
    grouping = FeederGroupingResult(
        feeder_count=1,
        assignments=(FeederAssignment("F1", ("T1", "T2", "T3"), 15.0, Point(0, 0)),),
    )
    res = build_feeder_mst(g, grouping)
    try:
        nx.find_cycle(res.feeders[0].mst_graph)
        pytest.fail("Graph contains a cycle")
    except nx.NetworkXNoCycle:
        pass


def test_mst_has_n_minus_one_edges() -> None:
    g = create_mock_graph()
    grouping = FeederGroupingResult(
        feeder_count=1,
        assignments=(FeederAssignment("F1", ("T1", "T2", "T3"), 15.0, Point(0, 0)),),
    )
    res = build_feeder_mst(g, grouping)
    mst = res.feeders[0].mst_graph
    assert len(mst.edges) == len(mst.nodes) - 1
    assert len(res.feeders[0].mst_edges) == len(mst.nodes) - 1


def test_mst_uses_minimum_weight_edges() -> None:
    g = create_mock_graph()
    grouping = FeederGroupingResult(
        feeder_count=1,
        assignments=(FeederAssignment("F1", ("T1", "T2", "T3"), 15.0, Point(0, 0)),),
    )
    res = build_feeder_mst(g, grouping)
    f1 = res.feeders[0]
    # SUB1 - T1 (100)
    # T1 - T2 (150)
    # T2 - T3 (200)
    # Total = 450
    assert f1.total_length_m == 450.0


def test_total_length_matches_edge_sum() -> None:
    g = create_mock_graph()
    grouping = FeederGroupingResult(
        feeder_count=1,
        assignments=(FeederAssignment("F1", ("T1", "T2", "T3"), 15.0, Point(0, 0)),),
    )
    res = build_feeder_mst(g, grouping)
    f1 = res.feeders[0]

    edge_sum = sum(
        data.get("distance_m", 0) for u, v, data in f1.mst_graph.edges(data=True)
    )
    assert math.isclose(f1.total_length_m, edge_sum)


def test_multiple_feeders_generate_separate_trees() -> None:
    g = create_mock_graph()
    grouping = FeederGroupingResult(
        feeder_count=2,
        assignments=(
            FeederAssignment("F1", ("T1",), 5.0, Point(0, 0)),
            FeederAssignment("F2", ("T2", "T3"), 10.0, Point(0, 0)),
        ),
    )
    res = build_feeder_mst(g, grouping)
    assert len(res.feeders) == 2
    f1 = res.feeders[0]
    f2 = res.feeders[1]

    assert set(f1.node_ids) == {"substation:SUB1", "wtg:T1"}
    assert set(f2.node_ids) == {"substation:SUB1", "wtg:T2", "wtg:T3"}

    assert f1.total_length_m == 100.0
    # For F2, SUB-T2 is 500, T2-T3 is 200, total 700
    assert f2.total_length_m == 700.0


def test_single_wtg_feeder() -> None:
    g = create_mock_graph()
    grouping = FeederGroupingResult(
        feeder_count=1, assignments=(FeederAssignment("F1", ("T3",), 5.0, Point(0, 0)),)
    )
    g.remove_node(turbine_node_id("T1"))
    g.remove_node(turbine_node_id("T2"))
    res = build_feeder_mst(g, grouping)
    assert len(res.feeders[0].mst_edges) == 1
    u, v = res.feeders[0].mst_edges[0]
    assert set([u, v]) == {"substation:SUB1", "wtg:T3"}


def test_unknown_turbine_assignment_rejected() -> None:
    g = create_mock_graph()
    grouping = FeederGroupingResult(
        feeder_count=1,
        assignments=(
            FeederAssignment("F1", ("T1", "T2", "T3", "UNKNOWN_T"), 10.0, Point(0, 0)),
        ),
    )
    with pytest.raises(ValueError, match="not found in graph"):
        build_feeder_mst(g, grouping)
