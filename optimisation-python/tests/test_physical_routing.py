import math

import networkx as nx
import numpy as np
import pyproj
import pytest
from affine import Affine
from shapely.geometry import LineString, Point

from app.algorithms.physical_routing import RouteNotFoundError, route_collector_topology
from app.algorithms.topology import CollectorTopologyResult, FeederTopology
from app.gis.cost_surface import CostSurface


@pytest.fixture
def mock_surface() -> CostSurface:
    return CostSurface(
        costs=np.ones((20, 20), dtype=np.float32),
        transform=Affine.translation(0, 200) * Affine.scale(10, -10),
        crs=pyproj.CRS("EPSG:32630"),
        width=20,
        height=20,
        resolution_m=10.0,
    )


def test_mst_edge_becomes_linestring(mock_surface: CostSurface) -> None:
    g = nx.Graph(crs=mock_surface.crs)
    g.add_node("sub", geometry=Point(5, 195))
    g.add_node("w1", geometry=Point(25, 195))

    feeder = FeederTopology(
        feeder_id="F1",
        node_ids=("sub", "w1"),
        total_capacity_mw=10.0,
        total_length_m=20.0,
        mst_edges=(("sub", "w1"),),
        mst_graph=nx.Graph(),
    )
    topo = CollectorTopologyResult(feeders=(feeder,))

    res = route_collector_topology(topo, g, mock_surface)
    assert len(res.routes) == 1
    route = res.routes[0]

    assert isinstance(route.geometry, LineString)
    coords = list(route.geometry.coords)
    assert len(coords) == 3
    assert coords[0] == (5.0, 195.0)
    assert coords[1] == (15.0, 195.0)
    assert coords[2] == (25.0, 195.0)


def test_route_preserves_exact_start_coordinate(mock_surface: CostSurface) -> None:
    g = nx.Graph(crs=mock_surface.crs)
    start_pt = Point(7.1, 192.8)
    end_pt = Point(25.0, 195.0)
    g.add_node("sub", geometry=start_pt)
    g.add_node("w1", geometry=end_pt)

    feeder = FeederTopology(
        feeder_id="F1",
        node_ids=("sub", "w1"),
        total_capacity_mw=10.0,
        total_length_m=20.0,
        mst_edges=(("sub", "w1"),),
        mst_graph=nx.Graph(),
    )
    topo = CollectorTopologyResult(feeders=(feeder,))

    res = route_collector_topology(topo, g, mock_surface)
    coords = list(res.routes[0].geometry.coords)
    assert coords[0] == (7.1, 192.8)
    assert coords[-1] == (25.0, 195.0)


def test_route_length_calculated_in_metres(mock_surface: CostSurface) -> None:
    g = nx.Graph(crs=mock_surface.crs)
    g.add_node("sub", geometry=Point(5, 195))
    g.add_node("w1", geometry=Point(25, 195))

    feeder = FeederTopology(
        "F1", ("sub", "w1"), 10.0, 20.0, (("sub", "w1"),), nx.Graph()
    )
    topo = CollectorTopologyResult(feeders=(feeder,))

    res = route_collector_topology(topo, g, mock_surface)
    # From (5,195) to (15,195) is 10, from (15,195) to (25,195) is 10. Total 20.
    assert math.isclose(res.routes[0].length_m, 20.0)


def test_validate_cost_surface_negative_inf(mock_surface: CostSurface) -> None:
    mock_surface.costs[5, 5] = -np.inf
    g = nx.Graph(crs=mock_surface.crs)
    topo = CollectorTopologyResult(feeders=())

    with pytest.raises(ValueError, match="contains negative infinity"):
        route_collector_topology(topo, g, mock_surface)


def test_validate_cost_surface_invalid_dimensions(mock_surface: CostSurface) -> None:
    # We have to bypass frozen dataclass
    object.__setattr__(mock_surface, "width", 0)
    g = nx.Graph(crs=mock_surface.crs)
    topo = CollectorTopologyResult(feeders=())

    with pytest.raises(ValueError, match="dimensions must be positive"):
        route_collector_topology(topo, g, mock_surface)


def test_validate_cost_surface_non_numeric(mock_surface: CostSurface) -> None:
    object.__setattr__(mock_surface, "costs", np.full((20, 20), "A"))
    g = nx.Graph(crs=mock_surface.crs)
    topo = CollectorTopologyResult(feeders=())

    with pytest.raises(ValueError, match="must be numeric"):
        route_collector_topology(topo, g, mock_surface)


def test_validate_cost_surface_degenerate_transform(mock_surface: CostSurface) -> None:
    from affine import Affine

    object.__setattr__(mock_surface, "transform", Affine(0, 0, 0, 0, 0, 0))
    g = nx.Graph(crs=mock_surface.crs)
    topo = CollectorTopologyResult(feeders=())

    with pytest.raises(ValueError, match="degenerate"):
        route_collector_topology(topo, g, mock_surface)


def test_traversal_cost_calculated_separately(mock_surface: CostSurface) -> None:
    mock_surface.costs[:, :] = np.inf
    mock_surface.costs[0, 0] = 1.0
    mock_surface.costs[0, 1] = 5.0
    mock_surface.costs[0, 2] = 1.0

    g = nx.Graph(crs=mock_surface.crs)
    g.add_node("sub", geometry=Point(5, 195))
    g.add_node("w1", geometry=Point(25, 195))

    feeder = FeederTopology(
        "F1", ("sub", "w1"), 10.0, 20.0, (("sub", "w1"),), nx.Graph()
    )
    topo = CollectorTopologyResult(feeders=(feeder,))

    res = route_collector_topology(topo, g, mock_surface)
    assert math.isclose(res.routes[0].traversal_cost, 60.0)


def test_every_mst_edge_gets_one_route(mock_surface: CostSurface) -> None:
    g = nx.Graph(crs=mock_surface.crs)
    g.add_node("sub", geometry=Point(5, 195))
    g.add_node("w1", geometry=Point(25, 195))
    g.add_node("w2", geometry=Point(5, 175))

    feeder = FeederTopology(
        "F1",
        ("sub", "w1", "w2"),
        10.0,
        40.0,
        (("sub", "w1"), ("sub", "w2")),
        nx.Graph(),
    )
    topo = CollectorTopologyResult(feeders=(feeder,))

    res = route_collector_topology(topo, g, mock_surface)
    assert len(res.routes) == 2


def test_multiple_feeders_route_independently(mock_surface: CostSurface) -> None:
    g = nx.Graph(crs=mock_surface.crs)
    g.add_node("sub", geometry=Point(5, 195))
    g.add_node("w1", geometry=Point(25, 195))
    g.add_node("w2", geometry=Point(5, 175))

    f1 = FeederTopology("F1", ("sub", "w1"), 5.0, 20.0, (("sub", "w1"),), nx.Graph())
    f2 = FeederTopology("F2", ("sub", "w2"), 5.0, 20.0, (("sub", "w2"),), nx.Graph())
    topo = CollectorTopologyResult(feeders=(f1, f2))

    res = route_collector_topology(topo, g, mock_surface)
    assert len(res.routes) == 2
    assert {r.feeder_id for r in res.routes} == {"F1", "F2"}


def test_route_not_found_raises_domain_error(mock_surface: CostSurface) -> None:
    mock_surface.costs[:, 1] = np.inf

    g = nx.Graph(crs=mock_surface.crs)
    g.add_node("sub", geometry=Point(5, 195))
    g.add_node("w1", geometry=Point(25, 195))

    feeder = FeederTopology(
        "F1", ("sub", "w1"), 10.0, 20.0, (("sub", "w1"),), nx.Graph()
    )
    topo = CollectorTopologyResult(feeders=(feeder,))

    with pytest.raises(RouteNotFoundError, match="no path found"):
        route_collector_topology(topo, g, mock_surface)


def test_result_preserves_feeder_id(mock_surface: CostSurface) -> None:
    g = nx.Graph(crs=mock_surface.crs)
    g.add_node("sub", geometry=Point(5, 195))
    g.add_node("w1", geometry=Point(25, 195))

    feeder = FeederTopology(
        "FEEDER-X", ("sub", "w1"), 10.0, 20.0, (("sub", "w1"),), nx.Graph()
    )
    topo = CollectorTopologyResult(feeders=(feeder,))

    res = route_collector_topology(topo, g, mock_surface)
    assert res.routes[0].feeder_id == "FEEDER-X"


def test_total_length_equals_sum_of_routes(mock_surface: CostSurface) -> None:
    g = nx.Graph(crs=mock_surface.crs)
    g.add_node("sub", geometry=Point(5, 195))
    g.add_node("w1", geometry=Point(25, 195))
    g.add_node("w2", geometry=Point(5, 175))

    feeder = FeederTopology(
        "F1",
        ("sub", "w1", "w2"),
        10.0,
        40.0,
        (("sub", "w1"), ("sub", "w2")),
        nx.Graph(),
    )
    topo = CollectorTopologyResult(feeders=(feeder,))

    res = route_collector_topology(topo, g, mock_surface)
    assert math.isclose(res.total_length_m, sum(r.length_m for r in res.routes))
    assert math.isclose(
        res.total_traversal_cost, sum(r.traversal_cost for r in res.routes)
    )


def test_route_same_cell_distinct_points(mock_surface: CostSurface) -> None:
    g = nx.Graph(crs=mock_surface.crs)
    g.add_node("sub", geometry=Point(5.0, 195.0))
    g.add_node("w1", geometry=Point(6.0, 194.0))

    feeder = FeederTopology(
        "F1", ("sub", "w1"), 10.0, 20.0, (("sub", "w1"),), nx.Graph()
    )
    topo = CollectorTopologyResult(feeders=(feeder,))

    res = route_collector_topology(topo, g, mock_surface)

    coords = list(res.routes[0].geometry.coords)
    assert len(coords) == 2
    assert coords[0] == (5.0, 195.0)
    assert coords[1] == (6.0, 194.0)
    assert res.routes[0].traversal_cost > 0.0
    assert math.isclose(res.routes[0].traversal_cost, res.routes[0].length_m * 1.0)


def test_route_coincident_points(mock_surface: CostSurface) -> None:
    g = nx.Graph(crs=mock_surface.crs)
    g.add_node("sub", geometry=Point(5.0, 195.0))
    g.add_node("w1", geometry=Point(5.0, 195.0))

    feeder = FeederTopology(
        "F1", ("sub", "w1"), 10.0, 20.0, (("sub", "w1"),), nx.Graph()
    )
    topo = CollectorTopologyResult(feeders=(feeder,))

    res = route_collector_topology(topo, g, mock_surface)

    coords = list(res.routes[0].geometry.coords)
    assert len(coords) == 2
    assert coords[0] == (5.0, 195.0)
    assert coords[1] == (5.0, 195.0)
    assert res.routes[0].length_m == 0.0
    assert res.routes[0].traversal_cost == 0.0
