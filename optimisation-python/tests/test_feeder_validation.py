import networkx as nx
import pytest
from pyproj import CRS
from shapely.geometry import LineString, Point

from app.algorithms.route_refinement import RefinedPhysicalRoute, RefinedRoutingResult
from app.algorithms.topology import CollectorTopologyResult, FeederTopology
from app.electrical.feeder_validation import (
    calculate_downstream_active_power_mw,
    validate_collector_network,
)
from app.electrical.models import (
    ConductorElectricalProperties,
    ElectricalDesignConfig,
)
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine


@pytest.fixture
def base_config() -> ElectricalDesignConfig:
    conductor = ConductorElectricalProperties(
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.15,
        ampacity_a=400.0,
    )
    return ElectricalDesignConfig(
        nominal_line_voltage_kv=33.0,
        power_factor=0.9,
        power_factor_mode="lagging",
        operating_factor=1.0,
        max_voltage_deviation_percent=5.0,
        conductor=conductor,
    )


def test_calculate_downstream_active_power() -> None:
    tree = nx.DiGraph()
    tree.add_edges_from(
        [
            ("SUB", "WTG-1"),
            ("WTG-1", "WTG-2"),
            ("WTG-2", "WTG-3"),
        ]
    )

    wtg_caps = {
        "WTG-1": 5.0,
        "WTG-2": 5.0,
        "WTG-3": 5.0,
    }

    res = calculate_downstream_active_power_mw(tree, wtg_caps)

    assert res[("SUB", "WTG-1")] == 15.0
    assert res[("WTG-1", "WTG-2")] == 10.0
    assert res[("WTG-2", "WTG-3")] == 5.0


def test_calculate_downstream_branched() -> None:
    tree = nx.DiGraph()
    tree.add_edges_from(
        [
            ("SUB", "WTG-1"),
            ("WTG-1", "WTG-2"),
            ("WTG-1", "WTG-3"),
        ]
    )

    wtg_caps = {
        "WTG-1": 2.0,
        "WTG-2": 3.0,
        "WTG-3": 4.0,
    }

    res = calculate_downstream_active_power_mw(tree, wtg_caps)

    assert res[("WTG-1", "WTG-2")] == 3.0
    assert res[("WTG-1", "WTG-3")] == 4.0
    assert res[("SUB", "WTG-1")] == 9.0


def test_validate_collector_network_valid(base_config: ElectricalDesignConfig) -> None:
    project = ProjectSpatialData(
        turbines=(
            WindTurbine("1", Point(0, 0), 5.0),
            WindTurbine("2", Point(0, 1000), 5.0),
        ),
        substation=Substation("SUB", Point(0, -1000), 20.0),
        projected_crs=CRS.from_epsg(32633),
    )

    mst = nx.Graph()
    mst.add_node("substation:SUB")
    mst.add_node("wtg:1")
    mst.add_node("wtg:2")
    mst.add_edge("substation:SUB", "wtg:1", weight=1000.0)
    mst.add_edge("wtg:1", "wtg:2", weight=1000.0)

    topology = CollectorTopologyResult(
        feeders=(
            FeederTopology(
                feeder_id="F1",
                node_ids=("substation:SUB", "wtg:1", "wtg:2"),
                total_capacity_mw=10.0,
                total_length_m=2000.0,
                mst_edges=(("substation:SUB", "wtg:1"), ("wtg:1", "wtg:2")),
                mst_graph=mst,
            ),
        )
    )

    routing = RefinedRoutingResult(
        routes=(
            RefinedPhysicalRoute(
                feeder_id="F1",
                start_node_id="substation:SUB",
                end_node_id="wtg:1",
                geometry=LineString([(0, -1000), (0, 0)]),
                original_length_m=1000.0,
                refined_length_m=1000.0,
                original_traversal_cost=1000.0,
                refined_traversal_cost=1000.0,
            ),
            RefinedPhysicalRoute(
                feeder_id="F1",
                start_node_id="wtg:1",
                end_node_id="wtg:2",
                geometry=LineString([(0, 0), (0, 1000)]),
                original_length_m=1000.0,
                refined_length_m=1000.0,
                original_traversal_cost=1000.0,
                refined_traversal_cost=1000.0,
            ),
        ),
        total_original_length_m=2000.0,
        total_refined_length_m=2000.0,
    )

    result = validate_collector_network(topology, routing, project, base_config)

    assert result.is_valid
    assert len(result.feeders) == 1
    assert len(result.violations) == 0

    f1 = result.feeders[0]
    assert f1.total_active_power_mw == 10.0
    assert len(f1.segments) == 2
    assert len(f1.turbines) == 2

    seg1 = next(
        s
        for s in f1.segments
        if s.parent_node_id == "substation:SUB" and s.child_node_id == "wtg:1"
    )
    assert seg1.downstream_active_power_mw == 10.0

    seg2 = next(
        s
        for s in f1.segments
        if s.parent_node_id == "wtg:1" and s.child_node_id == "wtg:2"
    )
    assert seg2.downstream_active_power_mw == 5.0

    wtg2_res = next(t for t in f1.turbines if t.turbine_node_id == "wtg:2")

    assert wtg2_res.cumulative_voltage_change_v == pytest.approx(
        seg1.voltage_change_v + seg2.voltage_change_v
    )


def test_validate_missing_route(base_config: ElectricalDesignConfig) -> None:
    project = ProjectSpatialData(
        turbines=(WindTurbine("1", Point(0, 0), 5.0),),
        substation=Substation("SUB", Point(0, -1000), 20.0),
        projected_crs=CRS.from_epsg(32633),
    )
    mst = nx.Graph()
    mst.add_edge("substation:SUB", "wtg:1")

    topology = CollectorTopologyResult(
        feeders=(
            FeederTopology(
                feeder_id="F1",
                node_ids=("substation:SUB", "wtg:1"),
                total_capacity_mw=5.0,
                total_length_m=1000.0,
                mst_edges=(("substation:SUB", "wtg:1"),),
                mst_graph=mst,
            ),
        )
    )

    routing = RefinedRoutingResult(
        routes=(), total_original_length_m=0.0, total_refined_length_m=0.0
    )

    with pytest.raises(ValueError, match="Missing physical route"):
        validate_collector_network(topology, routing, project, base_config)


def test_validate_extra_route(base_config: ElectricalDesignConfig) -> None:
    project = ProjectSpatialData(
        turbines=(WindTurbine("1", Point(0, 0), 5.0),),
        substation=Substation("SUB", Point(0, -1000), 20.0),
        projected_crs=CRS.from_epsg(32633),
    )
    mst = nx.Graph()
    mst.add_edge("substation:SUB", "wtg:1")

    topology = CollectorTopologyResult(
        feeders=(
            FeederTopology(
                feeder_id="F1",
                node_ids=("substation:SUB", "wtg:1"),
                total_capacity_mw=5.0,
                total_length_m=1000.0,
                mst_edges=(("substation:SUB", "wtg:1"),),
                mst_graph=mst,
            ),
        )
    )

    routing = RefinedRoutingResult(
        routes=(
            RefinedPhysicalRoute(
                feeder_id="F1",
                start_node_id="substation:SUB",
                end_node_id="wtg:1",
                geometry=LineString([(0, -1000), (0, 0)]),
                original_length_m=1000.0,
                refined_length_m=1000.0,
                original_traversal_cost=1000.0,
                refined_traversal_cost=1000.0,
            ),
            RefinedPhysicalRoute(
                feeder_id="F1",
                start_node_id="wtg:1",
                end_node_id="wtg:2",  # extra
                geometry=LineString([(0, 0), (0, 1000)]),
                original_length_m=1000.0,
                refined_length_m=1000.0,
                original_traversal_cost=1000.0,
                refined_traversal_cost=1000.0,
            ),
        ),
        total_original_length_m=2000.0,
        total_refined_length_m=2000.0,
    )

    with pytest.raises(ValueError, match="unknown project node"):
        validate_collector_network(topology, routing, project, base_config)


def test_validate_ampacity_violation(base_config: ElectricalDesignConfig) -> None:
    project = ProjectSpatialData(
        turbines=(WindTurbine("1", Point(0, 0), 30.0),),
        substation=Substation("SUB", Point(0, -1000), 100.0),
        projected_crs=CRS.from_epsg(32633),
    )
    mst = nx.Graph()
    mst.add_edge("substation:SUB", "wtg:1")

    topology = CollectorTopologyResult(
        feeders=(
            FeederTopology(
                feeder_id="F1",
                node_ids=("substation:SUB", "wtg:1"),
                total_capacity_mw=30.0,
                total_length_m=1000.0,
                mst_edges=(("substation:SUB", "wtg:1"),),
                mst_graph=mst,
            ),
        )
    )

    routing = RefinedRoutingResult(
        routes=(
            RefinedPhysicalRoute(
                feeder_id="F1",
                start_node_id="substation:SUB",
                end_node_id="wtg:1",
                geometry=LineString([(0, -1000), (0, 0)]),
                original_length_m=1000.0,
                refined_length_m=1000.0,
                original_traversal_cost=1000.0,
                refined_traversal_cost=1000.0,
            ),
        ),
        total_original_length_m=1000.0,
        total_refined_length_m=1000.0,
    )

    result = validate_collector_network(topology, routing, project, base_config)

    assert not result.is_valid
    assert any(v.code == "AMPACITY_EXCEEDED" for v in result.violations)

    seg = result.feeders[0].segments[0]
    assert seg.ampacity_exceeded
    assert seg.loading_percent > 100.0


def test_validate_voltage_violation(base_config: ElectricalDesignConfig) -> None:
    project = ProjectSpatialData(
        turbines=(WindTurbine("1", Point(0, 0), 10.0),),
        substation=Substation("SUB", Point(0, -100000), 100.0),
        projected_crs=CRS.from_epsg(32633),
    )
    mst = nx.Graph()
    mst.add_edge("substation:SUB", "wtg:1")

    topology = CollectorTopologyResult(
        feeders=(
            FeederTopology(
                feeder_id="F1",
                node_ids=("substation:SUB", "wtg:1"),
                total_capacity_mw=10.0,
                total_length_m=100000.0,
                mst_edges=(("substation:SUB", "wtg:1"),),
                mst_graph=mst,
            ),
        )
    )

    routing = RefinedRoutingResult(
        routes=(
            RefinedPhysicalRoute(
                feeder_id="F1",
                start_node_id="substation:SUB",
                end_node_id="wtg:1",
                geometry=LineString([(0, -100000), (0, 0)]),
                original_length_m=100000.0,
                refined_length_m=100000.0,
                original_traversal_cost=100000.0,
                refined_traversal_cost=100000.0,
            ),
        ),
        total_original_length_m=100000.0,
        total_refined_length_m=100000.0,
    )

    result = validate_collector_network(topology, routing, project, base_config)

    assert not result.is_valid
    assert any(v.code == "VOLTAGE_LIMIT_EXCEEDED" for v in result.violations)


def test_rejects_project_wtg_missing_from_topology(
    base_config: ElectricalDesignConfig,
) -> None:
    project = ProjectSpatialData(
        turbines=(
            WindTurbine("1", Point(0, 0), 5.0),
            WindTurbine("2", Point(0, 1000), 5.0),
        ),
        substation=Substation("SUB", Point(0, -1000), 20.0),
        projected_crs=CRS.from_epsg(32633),
    )
    mst = nx.Graph()
    mst.add_edge("substation:SUB", "wtg:1")
    topology = CollectorTopologyResult(
        feeders=(
            FeederTopology(
                feeder_id="F1",
                node_ids=("substation:SUB", "wtg:1"),
                total_capacity_mw=5.0,
                total_length_m=1000.0,
                mst_edges=(("substation:SUB", "wtg:1"),),
                mst_graph=mst,
            ),
        )
    )
    routing = RefinedRoutingResult(
        routes=(
            RefinedPhysicalRoute(
                feeder_id="F1",
                start_node_id="substation:SUB",
                end_node_id="wtg:1",
                geometry=LineString([(0, -1000), (0, 0)]),
                original_length_m=1000.0,
                refined_length_m=1000.0,
                original_traversal_cost=1000.0,
                refined_traversal_cost=1000.0,
            ),
        ),
        total_original_length_m=1000.0,
        total_refined_length_m=1000.0,
    )

    with pytest.raises(ValueError, match="missing from topology"):
        validate_collector_network(topology, routing, project, base_config)


def test_rejects_unknown_wtg_in_topology(
    base_config: ElectricalDesignConfig,
) -> None:
    project = ProjectSpatialData(
        turbines=(WindTurbine("1", Point(0, 0), 5.0),),
        substation=Substation("SUB", Point(0, -1000), 20.0),
        projected_crs=CRS.from_epsg(32633),
    )
    mst = nx.Graph()
    mst.add_edges_from([("substation:SUB", "wtg:1"), ("wtg:1", "wtg:unknown")])
    topology = CollectorTopologyResult(
        feeders=(
            FeederTopology(
                feeder_id="F1",
                node_ids=("substation:SUB", "wtg:1", "wtg:unknown"),
                total_capacity_mw=5.0,
                total_length_m=2000.0,
                mst_edges=(
                    ("substation:SUB", "wtg:1"),
                    ("wtg:1", "wtg:unknown"),
                ),
                mst_graph=mst,
            ),
        )
    )
    routing = RefinedRoutingResult(
        routes=(), total_original_length_m=0.0, total_refined_length_m=0.0
    )

    with pytest.raises(ValueError, match="unknown WTG"):
        validate_collector_network(topology, routing, project, base_config)


def test_rejects_route_geometry_that_does_not_connect_declared_nodes(
    base_config: ElectricalDesignConfig,
) -> None:
    project = ProjectSpatialData(
        turbines=(WindTurbine("1", Point(0, 0), 5.0),),
        substation=Substation("SUB", Point(0, -1000), 20.0),
        projected_crs=CRS.from_epsg(32633),
    )
    mst = nx.Graph()
    mst.add_edge("substation:SUB", "wtg:1")
    topology = CollectorTopologyResult(
        feeders=(
            FeederTopology(
                feeder_id="F1",
                node_ids=("substation:SUB", "wtg:1"),
                total_capacity_mw=5.0,
                total_length_m=1000.0,
                mst_edges=(("substation:SUB", "wtg:1"),),
                mst_graph=mst,
            ),
        )
    )
    routing = RefinedRoutingResult(
        routes=(
            RefinedPhysicalRoute(
                feeder_id="F1",
                start_node_id="substation:SUB",
                end_node_id="wtg:1",
                geometry=LineString([(100, -1000), (100, 0)]),
                original_length_m=1000.0,
                refined_length_m=1000.0,
                original_traversal_cost=1000.0,
                refined_traversal_cost=1000.0,
            ),
        ),
        total_original_length_m=1000.0,
        total_refined_length_m=1000.0,
    )

    with pytest.raises(ValueError, match="start does not match"):
        validate_collector_network(topology, routing, project, base_config)


def test_operating_factor_applies_to_reported_power_and_substation_limit() -> None:
    config = ElectricalDesignConfig(
        nominal_line_voltage_kv=33.0,
        power_factor=0.9,
        power_factor_mode="lagging",
        operating_factor=0.5,
        max_voltage_deviation_percent=5.0,
        conductor=ConductorElectricalProperties(0.1, 0.15, 400.0),
    )
    project = ProjectSpatialData(
        turbines=(WindTurbine("1", Point(0, 0), 10.0),),
        substation=Substation("SUB", Point(0, -1000), 6.0),
        projected_crs=CRS.from_epsg(32633),
    )
    mst = nx.Graph()
    mst.add_edge("substation:SUB", "wtg:1")
    topology = CollectorTopologyResult(
        feeders=(
            FeederTopology(
                feeder_id="F1",
                node_ids=("substation:SUB", "wtg:1"),
                total_capacity_mw=10.0,
                total_length_m=1000.0,
                mst_edges=(("substation:SUB", "wtg:1"),),
                mst_graph=mst,
            ),
        )
    )
    routing = RefinedRoutingResult(
        routes=(
            RefinedPhysicalRoute(
                feeder_id="F1",
                start_node_id="substation:SUB",
                end_node_id="wtg:1",
                geometry=LineString([(0, -1000), (0, 0)]),
                original_length_m=1000.0,
                refined_length_m=1000.0,
                original_traversal_cost=1000.0,
                refined_traversal_cost=1000.0,
            ),
        ),
        total_original_length_m=1000.0,
        total_refined_length_m=1000.0,
    )

    result = validate_collector_network(topology, routing, project, config)

    assert result.is_valid
    assert result.feeders[0].total_active_power_mw == 5.0
    assert result.feeders[0].turbines[0].active_power_mw == 5.0
    assert not any(
        violation.code == "SUBSTATION_CAPACITY_EXCEEDED"
        for violation in result.violations
    )


def test_rejects_non_metric_project_crs(
    base_config: ElectricalDesignConfig,
) -> None:
    project = ProjectSpatialData(
        turbines=(WindTurbine("1", Point(77.0, 8.0), 5.0),),
        substation=Substation("SUB", Point(77.0, 7.99), 20.0),
        projected_crs=CRS.from_epsg(4326),
    )
    with pytest.raises(ValueError, match="projected CRS"):
        validate_collector_network(
            CollectorTopologyResult(feeders=()),
            RefinedRoutingResult((), 0.0, 0.0),
            project,
            base_config,
        )
