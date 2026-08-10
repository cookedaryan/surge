with open("tests/test_physical_routing.py", "a") as f:
    f.write('''
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
''')
