"""Tests for PNC input validation before AC load flow building."""

import pyproj
import pytest
from shapely.geometry import LineString, Point

from app.electrical.load_flow.builder import _validate_inputs
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import WTGOperatingPoint
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork

_CRS = pyproj.CRS("EPSG:32630")
_GEO_CRS = pyproj.CRS("EPSG:4326")


@pytest.fixture
def base_config() -> LoadFlowConfig:
    c = LoadFlowCableType(
        cable_type_id="C1",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=100.0,
        max_current_a=300.0,
    )
    return LoadFlowConfig(
        nominal_voltage_kv=33.0,
        slack_voltage_pu=1.0,
        min_voltage_pu=0.95,
        max_voltage_pu=1.05,
        system_base_mva=100.0,
        cable_types=(c,),
        default_cable_type_id="C1",
        segment_cable_type_ids={},
    )


@pytest.fixture
def valid_pnc() -> tuple[ProjectPNCNetwork, list[WTGOperatingPoint]]:
    """A valid, simple one-feeder, one-WTG PNC network and its operating points."""
    import networkx as nx

    mst = nx.Graph()
    mst.add_edge("SUB1", "WTG1")

    seg = PNCSegment(
        segment_id="SEG1",
        feeder_id="F1",
        from_node_id="SUB1",
        to_node_id="WTG1",
        route_geometry=LineString([(0, 0), (100, 0)]),
        route_length_m=100.0,
        traversal_cost=100.0,
        segment_type="substation_to_wtg",
    )

    feeder = PNCFeeder(
        feeder_id="F1",
        substation_id="SUB1",
        wtg_ids=("WTG1",),
        ordered_node_ids=("SUB1", "WTG1"),
        segments=(seg,),
        total_length_m=100.0,
        mst_graph=mst,
    )

    net = ProjectPNCNetwork(
        project_id="P1",
        substation_id="SUB1",
        substation_geometry=Point(0, 0),
        feeders=(feeder,),
        wtg_coordinates={"WTG1": Point(100, 0)},
        total_route_length_m=100.0,
        feeder_count=1,
        wtg_count=1,
        segment_count=1,
        crs=_CRS,
        route_length_by_feeder={"F1": 100.0},
        wtg_count_by_feeder={"F1": 1},
    )

    ops = [
        WTGOperatingPoint(node_id="WTG1", active_power_mw=5.0, reactive_power_mvar=0.0)
    ]
    return net, ops


def test_validate_inputs_success(valid_pnc, base_config) -> None:  # type: ignore
    net, ops = valid_pnc
    _validate_inputs(net, ops, base_config)


def test_validate_missing_substation_id(valid_pnc, base_config) -> None:  # type: ignore
    net, ops = valid_pnc
    bad_net = ProjectPNCNetwork(
        project_id="P1",
        substation_id="",  # missing
        substation_geometry=net.substation_geometry,
        feeders=net.feeders,
        wtg_coordinates=net.wtg_coordinates,
        total_route_length_m=net.total_route_length_m,
        feeder_count=net.feeder_count,
        wtg_count=net.wtg_count,
        segment_count=net.segment_count,
        crs=net.crs,
        route_length_by_feeder=net.route_length_by_feeder,
        wtg_count_by_feeder=net.wtg_count_by_feeder,
    )
    with pytest.raises(
        ValueError, match="Project and substation IDs must be non-empty"
    ):
        _validate_inputs(bad_net, ops, base_config)


def test_validate_geographic_crs(valid_pnc, base_config) -> None:  # type: ignore
    net, ops = valid_pnc
    bad_net = ProjectPNCNetwork(
        project_id="P1",
        substation_id=net.substation_id,
        substation_geometry=net.substation_geometry,
        feeders=net.feeders,
        wtg_coordinates=net.wtg_coordinates,
        total_route_length_m=net.total_route_length_m,
        feeder_count=net.feeder_count,
        wtg_count=net.wtg_count,
        segment_count=net.segment_count,
        crs=_GEO_CRS,  # geographic
        route_length_by_feeder=net.route_length_by_feeder,
        wtg_count_by_feeder=net.wtg_count_by_feeder,
    )
    with pytest.raises(ValueError, match="projected"):
        _validate_inputs(bad_net, ops, base_config)


def test_validate_missing_cable_assignment(valid_pnc, base_config) -> None:  # type: ignore
    net, ops = valid_pnc
    bad_config = LoadFlowConfig(
        nominal_voltage_kv=33.0,
        slack_voltage_pu=1.0,
        min_voltage_pu=0.95,
        max_voltage_pu=1.05,
        system_base_mva=100.0,
        cable_types=base_config.cable_types,
        default_cable_type_id="C1",
        segment_cable_type_ids={"SEG1": "UNKNOWN_CABLE"},  # invalid assignment
    )
    with pytest.raises(ValueError, match="unknown cable type"):
        _validate_inputs(net, ops, bad_config)


def test_validate_missing_operating_point(valid_pnc, base_config) -> None:  # type: ignore
    net, _ = valid_pnc
    with pytest.raises(ValueError, match="Missing operating points"):
        _validate_inputs(net, [], base_config)


def test_validate_extra_operating_point(valid_pnc, base_config) -> None:  # type: ignore
    net, ops = valid_pnc
    ops.append(
        WTGOperatingPoint(node_id="WTG2", active_power_mw=5.0, reactive_power_mvar=0.0)
    )
    with pytest.raises(ValueError, match="unknown WTGs"):
        _validate_inputs(net, ops, base_config)


def test_validate_duplicate_operating_point(valid_pnc, base_config) -> None:  # type: ignore
    net, ops = valid_pnc
    # Add same WTG again
    ops.append(
        WTGOperatingPoint(node_id="WTG1", active_power_mw=5.0, reactive_power_mvar=0.0)
    )
    with pytest.raises(ValueError, match="Duplicate operating points"):
        _validate_inputs(net, ops, base_config)


def test_validate_self_loop(valid_pnc, base_config) -> None:  # type: ignore
    net, ops = valid_pnc
    seg = PNCSegment(
        segment_id="SEG2",
        feeder_id="F1",
        from_node_id="WTG1",
        to_node_id="WTG1",  # self loop
        route_geometry=LineString([(100, 0), (100, 0)]),
        route_length_m=10.0,
        traversal_cost=10.0,
        segment_type="wtg_to_wtg",
    )
    import networkx as nx

    mst = nx.Graph()
    mst.add_edge("SUB1", "WTG1")
    mst.add_edge("WTG1", "WTG1")

    bad_feeder = PNCFeeder(
        feeder_id="F1",
        substation_id="SUB1",
        wtg_ids=("WTG1",),
        ordered_node_ids=("SUB1", "WTG1"),
        segments=(net.feeders[0].segments[0], seg),
        total_length_m=110.0,
        mst_graph=mst,
    )

    bad_net = ProjectPNCNetwork(
        project_id="P1",
        substation_id="SUB1",
        substation_geometry=Point(0, 0),
        feeders=(bad_feeder,),
        wtg_coordinates={"WTG1": Point(100, 0)},
        total_route_length_m=110.0,
        feeder_count=1,
        wtg_count=1,
        segment_count=2,
        crs=_CRS,
        route_length_by_feeder={"F1": 110.0},
        wtg_count_by_feeder={"F1": 1},
    )

    with pytest.raises(ValueError, match="Self-loop"):
        _validate_inputs(bad_net, ops, base_config)


def test_validate_length_mismatch(valid_pnc, base_config) -> None:  # type: ignore
    net, ops = valid_pnc
    # segment route_length_m is 200, geometry length is 100
    seg = PNCSegment(
        segment_id="SEG1",
        feeder_id="F1",
        from_node_id="SUB1",
        to_node_id="WTG1",
        route_geometry=LineString([(0, 0), (100, 0)]),
        route_length_m=200.0,  # mismatch
        traversal_cost=200.0,
        segment_type="substation_to_wtg",
    )

    bad_feeder = PNCFeeder(
        feeder_id="F1",
        substation_id="SUB1",
        wtg_ids=("WTG1",),
        ordered_node_ids=("SUB1", "WTG1"),
        segments=(seg,),
        total_length_m=200.0,
        mst_graph=net.feeders[0].mst_graph,
    )

    bad_net = ProjectPNCNetwork(
        project_id="P1",
        substation_id="SUB1",
        substation_geometry=Point(0, 0),
        feeders=(bad_feeder,),
        wtg_coordinates={"WTG1": Point(100, 0)},
        total_route_length_m=200.0,
        feeder_count=1,
        wtg_count=1,
        segment_count=1,
        crs=_CRS,
        route_length_by_feeder={"F1": 200.0},
        wtg_count_by_feeder={"F1": 1},
    )

    with pytest.raises(ValueError, match="mismatches geometry length"):
        _validate_inputs(bad_net, ops, base_config)
