"""Tests for AC load flow execution and analysis."""

import math
from unittest.mock import patch

import pyproj
import pytest
from shapely.geometry import LineString, Point

from app.electrical.load_flow.analysis import run_load_flow
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import LoadFlowViolationCode, WTGOperatingPoint
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork

_CRS = pyproj.CRS("EPSG:32630")


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
def simple_pnc() -> tuple[ProjectPNCNetwork, list[WTGOperatingPoint]]:
    """A valid, simple one-feeder, one-WTG PNC network and its operating points."""
    import networkx as nx

    mst = nx.Graph()
    mst.add_edge("SUB1", "WTG1")

    # Use a length that makes electrical losses non-zero but reasonable
    seg = PNCSegment(
        segment_id="SEG1",
        feeder_id="F1",
        from_node_id="SUB1",
        to_node_id="WTG1",
        route_geometry=LineString([(0, 0), (5000, 0)]),
        route_length_m=5000.0,
        segment_type="substation_to_wtg",
    )

    feeder = PNCFeeder(
        feeder_id="F1",
        substation_id="SUB1",
        wtg_ids=("WTG1",),
        ordered_node_ids=("SUB1", "WTG1"),
        segments=(seg,),
        total_length_m=5000.0,
        mst_graph=mst,
    )

    net = ProjectPNCNetwork(
        project_id="P1",
        substation_id="SUB1",
        substation_geometry=Point(0, 0),
        feeders=(feeder,),
        wtg_coordinates={"WTG1": Point(5000, 0)},
        total_route_length_m=5000.0,
        feeder_count=1,
        wtg_count=1,
        segment_count=1,
        crs=_CRS,
        route_length_by_feeder={"F1": 5000.0},
        wtg_count_by_feeder={"F1": 1},
    )

    ops = [
        WTGOperatingPoint(node_id="WTG1", active_power_mw=5.0, reactive_power_mvar=1.0)
    ]
    return net, ops


def test_successful_convergence(simple_pnc, base_config):
    net, ops = simple_pnc
    res = run_load_flow(net, ops, base_config)

    assert res.converged is True
    assert res.is_valid is True
    assert len(res.violations) == 0

    assert len(res.buses) == 2
    assert len(res.segments) == 1
    assert len(res.feeders) == 1

    # Check that generation is 5.0
    assert res.total_generation_mw == 5.0
    # The slack bus should be negative (absorbing power) roughly
    # equal to generation minus losses
    assert res.slack_power_mw is not None
    assert res.slack_power_mw < 0
    assert math.isclose(
        -res.slack_power_mw + res.total_active_loss_mw,
        res.total_generation_mw,
        abs_tol=1e-3,
    )


def test_overvoltage_violation(simple_pnc):
    net, ops = simple_pnc

    c = LoadFlowCableType(
        cable_type_id="C1",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=100.0,
        max_current_a=300.0,
    )
    # Tightly constrain the max voltage to trigger violation
    # since wind pushes voltage up
    strict_config = LoadFlowConfig(
        nominal_voltage_kv=33.0,
        slack_voltage_pu=1.0,
        min_voltage_pu=0.95,
        max_voltage_pu=1.0001,  # extremely tight
        system_base_mva=100.0,
        cable_types=(c,),
        default_cable_type_id="C1",
        segment_cable_type_ids={},
    )

    res = run_load_flow(net, ops, strict_config)
    assert res.converged is True
    assert res.is_valid is False
    assert len(res.violations) >= 1
    assert any(v.code == LoadFlowViolationCode.BUS_OVERVOLTAGE for v in res.violations)


def test_cable_overload_violation(simple_pnc):
    net, ops = simple_pnc

    c = LoadFlowCableType(
        cable_type_id="C1",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=100.0,
        max_current_a=1.0,  # Ridiculously small current limit
    )
    config = LoadFlowConfig(
        nominal_voltage_kv=33.0,
        slack_voltage_pu=1.0,
        min_voltage_pu=0.95,
        max_voltage_pu=1.05,
        system_base_mva=100.0,
        cable_types=(c,),
        default_cable_type_id="C1",
        segment_cable_type_ids={},
    )

    res = run_load_flow(net, ops, config)
    assert res.converged is True
    assert res.is_valid is False
    assert any(v.code == LoadFlowViolationCode.CABLE_OVERLOAD for v in res.violations)


@patch("pandapower.runpp")
def test_non_convergence_graceful(mock_runpp, simple_pnc, base_config):
    """Test that a solver failure is caught and handled gracefully."""
    from pandapower.powerflow import LoadflowNotConverged

    mock_runpp.side_effect = LoadflowNotConverged("Did not converge")

    net, ops = simple_pnc
    res = run_load_flow(net, ops, base_config)

    assert res.converged is False
    assert res.is_valid is False
    assert len(res.buses) == 0
    assert len(res.segments) == 0
    assert len(res.feeders) == 0

    assert len(res.violations) == 1
    assert res.violations[0].code == LoadFlowViolationCode.LOAD_FLOW_NOT_CONVERGED
