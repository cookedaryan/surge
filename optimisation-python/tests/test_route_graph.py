import math

import pyproj
import pytest
from shapely.geometry import Point

from app.algorithms.route_graph import (
    build_project_graph,
)
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine


@pytest.fixture
def mock_crs() -> pyproj.CRS:
    return pyproj.CRS.from_epsg(32631)


@pytest.fixture
def sample_project(mock_crs: pyproj.CRS) -> ProjectSpatialData:
    sub = Substation(
        substation_id="SUB-1",
        location=Point(100.0, 100.0),
        capacity_mw=150.0,
    )
    wtgs = (
        WindTurbine(
            turbine_id="WTG-1",
            location=Point(100.0, 200.0),  # Distance to SUB-1 = 100m
            capacity_mw=5.0,
        ),
        WindTurbine(
            turbine_id="WTG-2",
            location=Point(200.0, 100.0),  # Distance to SUB-1 = 100m
            capacity_mw=6.0,
        ),
    )
    return ProjectSpatialData(
        turbines=wtgs,
        substation=sub,
        projected_crs=mock_crs,
    )


def test_graph_contains_all_project_nodes(sample_project: ProjectSpatialData) -> None:
    graph = build_project_graph(sample_project)
    # 2 WTGs + 1 Substation = 3 Nodes
    assert graph.number_of_nodes() == 3
    assert "wtg:WTG-1" in graph.nodes
    assert "wtg:WTG-2" in graph.nodes
    assert "substation:SUB-1" in graph.nodes


def test_substation_node_attributes(sample_project: ProjectSpatialData) -> None:
    graph = build_project_graph(sample_project)
    node_data = graph.nodes["substation:SUB-1"]
    assert node_data["type"] == "substation"
    assert node_data["x"] == 100.0
    assert node_data["y"] == 100.0
    assert node_data["capacity_mw"] == 150.0
    assert isinstance(node_data["geometry"], Point)
    assert node_data["geometry"].x == 100.0


def test_wtg_node_attributes(sample_project: ProjectSpatialData) -> None:
    graph = build_project_graph(sample_project)
    node_data = graph.nodes["wtg:WTG-1"]
    assert node_data["type"] == "wtg"
    assert node_data["x"] == 100.0
    assert node_data["y"] == 200.0
    assert node_data["capacity_mw"] == 5.0
    assert isinstance(node_data["geometry"], Point)
    assert node_data["geometry"].y == 200.0


def test_complete_graph_edge_count(sample_project: ProjectSpatialData) -> None:
    graph = build_project_graph(sample_project)
    # N=3 -> E = 3(2)/2 = 3 edges
    assert graph.number_of_edges() == 3


def test_edge_distance_is_metric(sample_project: ProjectSpatialData) -> None:
    graph = build_project_graph(sample_project)
    # WTG-1 (100, 200) to SUB-1 (100, 100) -> 100.0m
    edge = graph.edges["wtg:WTG-1", "substation:SUB-1"]
    assert edge["distance_m"] == 100.0

    # WTG-1 (100, 200) to WTG-2 (200, 100) -> sqrt(100^2 + 100^2) = 141.42...
    edge2 = graph.edges["wtg:WTG-1", "wtg:WTG-2"]
    assert math.isclose(edge2["distance_m"], 141.421356, rel_tol=1e-5)


def test_edge_distance_is_symmetric(sample_project: ProjectSpatialData) -> None:
    graph = build_project_graph(sample_project)
    # Since it's undirected, accessing edge A->B is same as B->A
    d1 = graph.edges["wtg:WTG-1", "substation:SUB-1"]["distance_m"]
    d2 = graph.edges["substation:SUB-1", "wtg:WTG-1"]["distance_m"]
    assert d1 == d2


def test_edge_weight_matches_distance(sample_project: ProjectSpatialData) -> None:
    graph = build_project_graph(sample_project)
    for _, _, data in graph.edges(data=True):
        assert data["weight"] == data["distance_m"]


def test_single_wtg_project_graph(mock_crs: pyproj.CRS) -> None:
    sub = Substation(substation_id="S1", location=Point(0, 0), capacity_mw=100.0)
    wtgs = (WindTurbine(turbine_id="W1", location=Point(0, 10), capacity_mw=5.0),)
    project = ProjectSpatialData(turbines=wtgs, substation=sub, projected_crs=mock_crs)

    graph = build_project_graph(project)
    assert graph.number_of_nodes() == 2
    assert graph.number_of_edges() == 1
    assert graph.edges["wtg:W1", "substation:S1"]["distance_m"] == 10.0


def test_duplicate_node_ids_rejected(mock_crs: pyproj.CRS) -> None:
    sub = Substation(substation_id="DUP", location=Point(0, 0), capacity_mw=100.0)
    wtgs = (WindTurbine(turbine_id="DUP", location=Point(0, 10), capacity_mw=5.0),)
    project = ProjectSpatialData(turbines=wtgs, substation=sub, projected_crs=mock_crs)

    # substation_id and turbine_id are the same, but the helper makes them
    # "substation:DUP" and "wtg:DUP", so it SHOULD NOT crash here yet.
    graph = build_project_graph(project)
    assert graph.number_of_nodes() == 2

    # Now simulate a true collision by giving two WTGs the exact same ID
    wtgs2 = (
        WindTurbine(turbine_id="W1", location=Point(0, 10), capacity_mw=5.0),
        WindTurbine(turbine_id="W1", location=Point(0, 20), capacity_mw=5.0),
    )
    project2 = ProjectSpatialData(
        turbines=wtgs2, substation=sub, projected_crs=mock_crs
    )
    with pytest.raises(ValueError, match="Duplicate node ID encountered: wtg:W1"):
        build_project_graph(project2)


def test_graph_preserves_project_crs_metadata(
    sample_project: ProjectSpatialData,
) -> None:
    graph = build_project_graph(sample_project)
    assert graph.graph["graph_type"] == "collector_candidate"
    assert graph.graph["crs"] == sample_project.projected_crs
    assert isinstance(graph.graph["crs"], pyproj.CRS)
