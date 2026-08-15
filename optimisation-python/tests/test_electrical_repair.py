"""Tests for closed-loop electrical repair logic."""

import networkx as nx
import pyproj
import pytest
from shapely.geometry import LineString, Point

from app.electrical.cable_sizing import CableSizingResult
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import (
    LoadFlowBusResult,
    LoadFlowNetworkResult,
    LoadFlowSegmentResult,
    LoadFlowViolation,
    LoadFlowViolationCode,
)
from app.electrical.repair import (
    RepairStatus,
    repair_electrical_design,
)
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork


@pytest.fixture
def base_config() -> LoadFlowConfig:
    return LoadFlowConfig(
        nominal_voltage_kv=33.0,
        slack_voltage_pu=1.0,
        min_voltage_pu=0.95,
        max_voltage_pu=1.05,
        system_base_mva=100.0,
        cable_types=(
            LoadFlowCableType(
                cable_type_id="Cable-S",
                resistance_ohm_per_km=0.15,
                reactance_ohm_per_km=0.15,
                capacitance_nf_per_km=0.0,
                max_current_a=200.0,
            ),
            LoadFlowCableType(
                cable_type_id="Cable-M",
                resistance_ohm_per_km=0.10,
                reactance_ohm_per_km=0.12,
                capacitance_nf_per_km=0.0,
                max_current_a=300.0,
            ),
            LoadFlowCableType(
                cable_type_id="Cable-L",
                resistance_ohm_per_km=0.05,
                reactance_ohm_per_km=0.10,
                capacitance_nf_per_km=0.0,
                max_current_a=500.0,
            ),
            # Fake cable with higher ampacity but worse impedance to test voltage rule
            LoadFlowCableType(
                cable_type_id="Cable-Bad",
                resistance_ohm_per_km=0.20,
                reactance_ohm_per_km=0.20,
                capacitance_nf_per_km=0.0,
                max_current_a=600.0,
            ),
        ),
        default_cable_type_id="Cable-S",
        segment_cable_type_ids={},
    )


def test_repair_valid_immediately(monkeypatch, base_config):
    mst = nx.Graph()
    mst.add_edges_from([("SS", "W1")])
    network = ProjectPNCNetwork(
        project_id="P1",
        substation_id="SS",
        substation_geometry=Point(0, 0),
        feeders=(
            PNCFeeder(
                feeder_id="F1",
                substation_id="SS",
                wtg_ids=("W1",),
                ordered_node_ids=("SS", "W1"),
                segments=(
                    PNCSegment(
                        "S1",
                        "F1",
                        "SS",
                        "W1",
                        LineString([(0, 0), (1, 1)]),
                        1000.0,
                        1000.0,
                        "substation_to_wtg",
                    ),
                ),
                total_length_m=1000.0,
                mst_graph=mst,
            ),
        ),
        wtg_coordinates={"W1": Point(1, 1)},
        total_route_length_m=1000.0,
        feeder_count=1,
        wtg_count=1,
        segment_count=1,
        crs=pyproj.CRS.from_epsg(3857),
        route_length_by_feeder={"F1": 1000.0},
        wtg_count_by_feeder={"F1": 1},
    )

    mock_sizing = CableSizingResult(
        assignments=(),
        segment_cable_type_ids={"S1": "Cable-S"},
    )
    monkeypatch.setattr(
        "app.electrical.repair.size_cables_for_network", lambda *a, **kw: mock_sizing
    )

    lf_result = LoadFlowNetworkResult(
        converged=True,
        is_valid=True,
        solver_algorithm="nr",
        total_generation_mw=10.0,
        slack_power_mw=-10.0,
        total_active_loss_mw=0.1,
        total_reactive_loss_mvar=0.1,
        minimum_voltage_pu=0.98,
        maximum_voltage_pu=1.0,
        maximum_loading_percent=50.0,
        buses=(),
        segments=(),
        feeders=(),
        violations=(),
    )
    monkeypatch.setattr(
        "app.electrical.repair.run_load_flow", lambda *a, **kw: lf_result
    )

    result = repair_electrical_design(
        network=network,
        operating_points=[],
        config=base_config,
        wtg_active_power_mw={},
        wtg_reactive_power_mvar={},
    )

    assert result.status == RepairStatus.VALID
    assert len(result.repair_log) == 0
    assert result.final_electrical_config.segment_cable_type_ids["S1"] == "Cable-S"


def test_overload_repair(monkeypatch, base_config):
    mst = nx.Graph()
    mst.add_edges_from([("SS", "W1"), ("W1", "W2")])
    network = ProjectPNCNetwork(
        project_id="P1",
        substation_id="SS",
        substation_geometry=Point(0, 0),
        feeders=(
            PNCFeeder(
                feeder_id="F1",
                substation_id="SS",
                wtg_ids=("W1", "W2"),
                ordered_node_ids=("SS", "W1", "W2"),
                segments=(
                    PNCSegment(
                        "S1",
                        "F1",
                        "SS",
                        "W1",
                        LineString([(0, 0), (1, 1)]),
                        1000.0,
                        1000.0,
                        "substation_to_wtg",
                    ),
                    PNCSegment(
                        "S2",
                        "F1",
                        "W1",
                        "W2",
                        LineString([(1, 1), (2, 2)]),
                        1000.0,
                        1000.0,
                        "wtg_to_wtg",
                    ),
                ),
                total_length_m=2000.0,
                mst_graph=mst,
            ),
        ),
        wtg_coordinates={"W1": Point(1, 1), "W2": Point(2, 2)},
        total_route_length_m=2000.0,
        feeder_count=1,
        wtg_count=2,
        segment_count=2,
        crs=pyproj.CRS.from_epsg(3857),
        route_length_by_feeder={"F1": 2000.0},
        wtg_count_by_feeder={"F1": 2},
    )

    mock_sizing = CableSizingResult(
        assignments=(),
        segment_cable_type_ids={"S1": "Cable-S", "S2": "Cable-S"},
    )
    monkeypatch.setattr(
        "app.electrical.repair.size_cables_for_network", lambda *a, **kw: mock_sizing
    )

    # 1st iter: both overloaded
    lf_result_1 = LoadFlowNetworkResult(
        converged=True,
        is_valid=False,
        solver_algorithm="nr",
        total_generation_mw=20.0,
        slack_power_mw=-20.0,
        total_active_loss_mw=0.1,
        total_reactive_loss_mvar=0.1,
        minimum_voltage_pu=0.98,
        maximum_voltage_pu=1.0,
        maximum_loading_percent=120.0,
        buses=(),
        segments=(
            LoadFlowSegmentResult(
                "S1", "F1", 0, 0, 0, 0, 0, 0, 240.0, 240.0, 200.0, 120.0
            ),  # Needs >240A -> Cable-M (300A)
            LoadFlowSegmentResult(
                "S2", "F1", 0, 0, 0, 0, 0, 0, 310.0, 310.0, 200.0, 155.0
            ),  # Needs >310A -> Cable-L (500A)
        ),
        feeders=(),
        violations=(
            LoadFlowViolation(
                LoadFlowViolationCode.CABLE_OVERLOAD,
                "overload",
                segment_id="S1",
                measured_value=120.0,
            ),
            LoadFlowViolation(
                LoadFlowViolationCode.CABLE_OVERLOAD,
                "overload",
                segment_id="S2",
                measured_value=155.0,
            ),
        ),
    )

    # 2nd iter: VALID
    lf_result_2 = LoadFlowNetworkResult(
        converged=True,
        is_valid=True,
        solver_algorithm="nr",
        total_generation_mw=20.0,
        slack_power_mw=-20.0,
        total_active_loss_mw=0.1,
        total_reactive_loss_mvar=0.1,
        minimum_voltage_pu=0.98,
        maximum_voltage_pu=1.0,
        maximum_loading_percent=95.0,
        buses=(),
        segments=(
            LoadFlowSegmentResult(
                "S1", "F1", 0, 0, 0, 0, 0, 0, 240.0, 240.0, 300.0, 80.0
            ),
            LoadFlowSegmentResult(
                "S2", "F1", 0, 0, 0, 0, 0, 0, 310.0, 310.0, 500.0, 62.0
            ),
        ),
        feeders=(),
        violations=(),
    )

    responses = [lf_result_1, lf_result_2]
    monkeypatch.setattr(
        "app.electrical.repair.run_load_flow", lambda *a, **kw: responses.pop(0)
    )

    result = repair_electrical_design(
        network=network,
        operating_points=[],
        config=base_config,
        wtg_active_power_mw={},
        wtg_reactive_power_mvar={},
    )

    assert result.status == RepairStatus.VALID
    assert len(result.repair_log) == 2

    assert result.repair_log[0].segment_id == "S1"
    assert result.repair_log[0].original_cable_type_id == "Cable-S"
    assert result.repair_log[0].upgraded_cable_type_id == "Cable-M"
    assert result.repair_log[0].pre_repair_loading_pct == 120.0
    assert result.repair_log[0].post_repair_loading_pct == 80.0

    assert result.repair_log[1].segment_id == "S2"
    assert result.repair_log[1].original_cable_type_id == "Cable-S"
    assert result.repair_log[1].upgraded_cable_type_id == "Cable-L"
    assert result.repair_log[1].pre_repair_loading_pct == 155.0
    assert result.repair_log[1].post_repair_loading_pct == 62.0

    assert result.final_electrical_config.segment_cable_type_ids["S1"] == "Cable-M"
    assert result.final_electrical_config.segment_cable_type_ids["S2"] == "Cable-L"


def test_voltage_repair(monkeypatch, base_config):
    mst = nx.Graph()
    mst.add_edges_from([("SS", "W1"), ("W1", "W2")])
    network = ProjectPNCNetwork(
        project_id="P1",
        substation_id="SS",
        substation_geometry=Point(0, 0),
        feeders=(
            PNCFeeder(
                feeder_id="F1",
                substation_id="SS",
                wtg_ids=("W1", "W2"),
                ordered_node_ids=("SS", "W1", "W2"),
                segments=(
                    PNCSegment(
                        "S1",
                        "F1",
                        "SS",
                        "W1",
                        LineString([(0, 0), (1, 1)]),
                        1000.0,
                        1000.0,
                        "substation_to_wtg",
                    ),
                    PNCSegment(
                        "S2",
                        "F1",
                        "W1",
                        "W2",
                        LineString([(1, 1), (2, 2)]),
                        1000.0,
                        1000.0,
                        "wtg_to_wtg",
                    ),
                ),
                total_length_m=2000.0,
                mst_graph=mst,
            ),
        ),
        wtg_coordinates={"W1": Point(1, 1), "W2": Point(2, 2)},
        total_route_length_m=2000.0,
        feeder_count=1,
        wtg_count=2,
        segment_count=2,
        crs=pyproj.CRS.from_epsg(3857),
        route_length_by_feeder={"F1": 2000.0},
        wtg_count_by_feeder={"F1": 2},
    )

    mock_sizing = CableSizingResult(
        assignments=(),
        segment_cable_type_ids={"S1": "Cable-S", "S2": "Cable-S"},
    )
    monkeypatch.setattr(
        "app.electrical.repair.size_cables_for_network", lambda *a, **kw: mock_sizing
    )

    # 1st iter: undervoltage at W2 (most severe) and W1
    lf_result_1 = LoadFlowNetworkResult(
        converged=True,
        is_valid=False,
        solver_algorithm="nr",
        total_generation_mw=20.0,
        slack_power_mw=-20.0,
        total_active_loss_mw=0.1,
        total_reactive_loss_mvar=0.1,
        minimum_voltage_pu=0.92,
        maximum_voltage_pu=1.0,
        maximum_loading_percent=80.0,
        buses=(
            LoadFlowBusResult("SS", "substation", 1.0, 33.0, 0.0, 0.0, 0.0),
            LoadFlowBusResult("W1", "wtg", 0.96, 31.68, 0.0, 0.0, 0.0),
            LoadFlowBusResult("W2", "wtg", 0.92, 30.36, 0.0, 0.0, 0.0),
        ),
        segments=(
            LoadFlowSegmentResult(
                "S1", "F1", 0, 0, 0, 0, 0, 0, 100.0, 100.0, 200.0, 50.0
            ),
            LoadFlowSegmentResult(
                "S2", "F1", 0, 0, 0, 0, 0, 0, 100.0, 100.0, 200.0, 50.0
            ),
        ),
        feeders=(),
        violations=(
            LoadFlowViolation(
                LoadFlowViolationCode.BUS_UNDERVOLTAGE,
                "W1 undervolt",
                node_id="W1",
                measured_value=0.96,
                limit_value=0.95,
            ),
            LoadFlowViolation(
                LoadFlowViolationCode.BUS_UNDERVOLTAGE,
                "W2 undervolt",
                node_id="W2",
                measured_value=0.92,
                limit_value=0.95,
            ),
        ),
    )

    # W2 path: SS -> W1 (S1), W1 -> W2 (S2)
    # Voltage drops: S1 = 1.0 - 0.96 = 0.04
    #                S2 = 0.96 - 0.92 = 0.04
    # Tie break on segment_id => S1 chosen
    # S1 is upgraded from Cable-S to Cable-M (Cable-M has lower impedance)

    # 2nd iter: VALID
    lf_result_2 = LoadFlowNetworkResult(
        converged=True,
        is_valid=True,
        solver_algorithm="nr",
        total_generation_mw=20.0,
        slack_power_mw=-20.0,
        total_active_loss_mw=0.1,
        total_reactive_loss_mvar=0.1,
        minimum_voltage_pu=0.96,
        maximum_voltage_pu=1.0,
        maximum_loading_percent=80.0,
        buses=(
            LoadFlowBusResult("SS", "substation", 1.0, 33.0, 0.0, 0.0, 0.0),
            LoadFlowBusResult("W1", "wtg", 0.98, 32.34, 0.0, 0.0, 0.0),
            LoadFlowBusResult("W2", "wtg", 0.96, 31.68, 0.0, 0.0, 0.0),
        ),
        segments=(
            LoadFlowSegmentResult(
                "S1", "F1", 0, 0, 0, 0, 0, 0, 100.0, 100.0, 300.0, 33.3
            ),
            LoadFlowSegmentResult(
                "S2", "F1", 0, 0, 0, 0, 0, 0, 100.0, 100.0, 200.0, 50.0
            ),
        ),
        feeders=(),
        violations=(),
    )

    responses = [lf_result_1, lf_result_2]
    monkeypatch.setattr(
        "app.electrical.repair.run_load_flow", lambda *a, **kw: responses.pop(0)
    )

    result = repair_electrical_design(
        network=network,
        operating_points=[],
        config=base_config,
        wtg_active_power_mw={},
        wtg_reactive_power_mvar={},
    )

    assert result.status == RepairStatus.VALID
    assert len(result.repair_log) == 1

    assert result.repair_log[0].segment_id == "S1"
    assert result.repair_log[0].original_cable_type_id == "Cable-S"
    assert result.repair_log[0].upgraded_cable_type_id == "Cable-M"
    assert result.repair_log[0].trigger_violation_type == str(
        LoadFlowViolationCode.BUS_UNDERVOLTAGE
    )
    assert result.repair_log[0].trigger_bus_id == "W2"
    assert result.repair_log[0].pre_repair_voltage_pu == 0.92
    assert result.repair_log[0].post_repair_voltage_pu == 0.96

    assert result.final_electrical_config.segment_cable_type_ids["S1"] == "Cable-M"
    assert result.final_electrical_config.segment_cable_type_ids["S2"] == "Cable-S"


def test_voltage_upgrade_skips_worse_impedance(monkeypatch, base_config):
    mst = nx.Graph()
    mst.add_edges_from([("SS", "W1")])
    network = ProjectPNCNetwork(
        project_id="P1",
        substation_id="SS",
        substation_geometry=Point(0, 0),
        feeders=(
            PNCFeeder(
                feeder_id="F1",
                substation_id="SS",
                wtg_ids=("W1",),
                ordered_node_ids=("SS", "W1"),
                segments=(
                    PNCSegment(
                        "S1",
                        "F1",
                        "SS",
                        "W1",
                        LineString([(0, 0), (1, 1)]),
                        1000.0,
                        1000.0,
                        "substation_to_wtg",
                    ),
                ),
                total_length_m=1000.0,
                mst_graph=mst,
            ),
        ),
        wtg_coordinates={"W1": Point(1, 1)},
        total_route_length_m=1000.0,
        feeder_count=1,
        wtg_count=1,
        segment_count=1,
        crs=pyproj.CRS.from_epsg(3857),
        route_length_by_feeder={"F1": 1000.0},
        wtg_count_by_feeder={"F1": 1},
    )

    mock_sizing = CableSizingResult(
        assignments=(),
        segment_cable_type_ids={"S1": "Cable-L"},  # Max good cable
    )
    monkeypatch.setattr(
        "app.electrical.repair.size_cables_for_network", lambda *a, **kw: mock_sizing
    )

    # 1st iter: undervoltage
    lf_result_1 = LoadFlowNetworkResult(
        converged=True,
        is_valid=False,
        solver_algorithm="nr",
        total_generation_mw=10.0,
        slack_power_mw=-10.0,
        total_active_loss_mw=0.1,
        total_reactive_loss_mvar=0.1,
        minimum_voltage_pu=0.92,
        maximum_voltage_pu=1.0,
        maximum_loading_percent=80.0,
        buses=(
            LoadFlowBusResult("SS", "substation", 1.0, 33.0, 0.0, 0.0, 0.0),
            LoadFlowBusResult("W1", "wtg", 0.92, 30.36, 0.0, 0.0, 0.0),
        ),
        segments=(
            LoadFlowSegmentResult(
                "S1", "F1", 0, 0, 0, 0, 0, 0, 100.0, 100.0, 500.0, 20.0
            ),
        ),
        feeders=(),
        violations=(
            LoadFlowViolation(
                LoadFlowViolationCode.BUS_UNDERVOLTAGE,
                "W1 undervolt",
                node_id="W1",
                measured_value=0.92,
                limit_value=0.95,
            ),
        ),
    )

    monkeypatch.setattr(
        "app.electrical.repair.run_load_flow", lambda *a, **kw: lf_result_1
    )

    result = repair_electrical_design(
        network=network,
        operating_points=[],
        config=base_config,
        wtg_active_power_mw={},
        wtg_reactive_power_mvar={},
    )

    # Do not upgrade to Cable-Bad: its impedance is worse despite higher ampacity.
    # Therefore, exhausted.
    assert result.status == RepairStatus.REPAIR_EXHAUSTED
    assert len(result.repair_log) == 0
    assert result.final_electrical_config.segment_cable_type_ids["S1"] == "Cable-L"
