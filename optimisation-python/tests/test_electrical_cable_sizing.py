import math
from unittest.mock import MagicMock

import networkx as nx

from app.electrical.cable_sizing import size_cables_for_network
from app.electrical.load_flow.config import LoadFlowCableType


def make_mock_network() -> MagicMock:
    # 1 substation (SUB), 2 WTGs (WTG-1, WTG-2)
    # SUB -> WTG-1 -> WTG-2
    mst = nx.Graph()
    mst.add_edge("SUB", "WTG-1")
    mst.add_edge("WTG-1", "WTG-2")

    mock_segment_1 = MagicMock()
    mock_segment_1.segment_id = "SEG-1"
    mock_segment_1.from_node_id = "SUB"
    mock_segment_1.to_node_id = "WTG-1"

    mock_segment_2 = MagicMock()
    mock_segment_2.segment_id = "SEG-2"
    mock_segment_2.from_node_id = "WTG-1"
    mock_segment_2.to_node_id = "WTG-2"

    mock_feeder = MagicMock()
    mock_feeder.mst_graph = mst
    mock_feeder.ordered_node_ids = ("SUB", "WTG-1", "WTG-2")
    mock_feeder.segments = (mock_segment_1, mock_segment_2)

    mock_network = MagicMock()
    mock_network.substation_id = "SUB"
    mock_network.feeders = (mock_feeder,)

    return mock_network


def test_unit_current_calculation_formula() -> None:
    network = make_mock_network()
    # Both segments carry WTG-2's 5 MW downstream power.
    wtg_p = {"WTG-1": 0.0, "WTG-2": 5.0}
    wtg_q: dict[str, float] = {"WTG-1": 0.0, "WTG-2": 0.0}

    cable_type = LoadFlowCableType(
        cable_type_id="CABLE-1",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=0.1,
        max_current_a=1000.0,
        parallel_count=1,
        derating_factor=1.0,
    )

    result = size_cables_for_network(
        network,
        wtg_active_power_mw=wtg_p,
        wtg_reactive_power_mvar=wtg_q,
        nominal_voltage_kv=33.0,
        cable_types=(cable_type,),
        sizing_power_factor=0.9,
    )

    # I = active power / (sqrt(3) * voltage * power factor)
    # required = 5 * 1000 / (sqrt(3) * 33 * 0.9) = 5000 / 51.4416 = 97.197
    expected_current = (5.0 * 1000.0) / (math.sqrt(3) * 33.0 * 0.9)

    seg_2_sizing = next(s for s in result.assignments if s.segment_id == "SEG-2")
    assert math.isclose(seg_2_sizing.required_current_a, expected_current)
    assert seg_2_sizing.assumed_power_factor == 0.9
    assert seg_2_sizing.sizing_basis == "ACTIVE_POWER_ONLY"


def test_sizing_uses_apparent_power_when_q_is_present() -> None:
    network = make_mock_network()
    wtg_p = {"WTG-1": 0.0, "WTG-2": 4.0}
    wtg_q: dict[str, float] = {"WTG-1": 0.0, "WTG-2": 3.0}

    cable_type = LoadFlowCableType(
        cable_type_id="CABLE-1",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=0.1,
        max_current_a=1000.0,
        parallel_count=1,
        derating_factor=1.0,
    )

    result = size_cables_for_network(
        network,
        wtg_active_power_mw=wtg_p,
        wtg_reactive_power_mvar=wtg_q,
        nominal_voltage_kv=33.0,
        cable_types=(cable_type,),
        sizing_power_factor=0.9,
    )

    # Apparent power = sqrt(4^2 + 3^2) = 5 MVA
    expected_current = (5.0 * 1000.0) / (math.sqrt(3) * 33.0)

    seg_2_sizing = next(s for s in result.assignments if s.segment_id == "SEG-2")
    assert math.isclose(seg_2_sizing.required_current_a, expected_current)
    assert seg_2_sizing.assumed_power_factor is None
    assert seg_2_sizing.sizing_basis == "APPARENT_POWER"


def test_catalogue_sorting_resolves_ties_by_parallel_count_then_id() -> None:
    network = make_mock_network()
    wtg_p = {"WTG-1": 0.0, "WTG-2": 10.0}  # approximately 175 A
    wtg_q: dict[str, float] = {}

    cable_1 = LoadFlowCableType(
        cable_type_id="CABLE-1-TWIN",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=0.1,
        max_current_a=100.0,
        parallel_count=2,  # effective = 200 A
        derating_factor=1.0,
    )
    cable_2 = LoadFlowCableType(
        cable_type_id="CABLE-2-SINGLE",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=0.1,
        max_current_a=200.0,
        parallel_count=1,  # effective = 200 A
        derating_factor=1.0,
    )
    cable_3 = LoadFlowCableType(
        cable_type_id="CABLE-3-SINGLE",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=0.1,
        max_current_a=200.0,
        parallel_count=1,  # effective = 200 A
        derating_factor=1.0,
    )

    # Tie break order for 200A effective capacity:
    # 1. parallel_count (ascending): 1, 1, 2 -> SINGLE wins
    # 2. cable_type_id (ascending): CABLE-2-SINGLE wins

    result = size_cables_for_network(
        network,
        wtg_active_power_mw=wtg_p,
        wtg_reactive_power_mvar=wtg_q,
        nominal_voltage_kv=33.0,
        cable_types=(cable_1, cable_2, cable_3),
        sizing_power_factor=1.0,
    )

    seg_2_sizing = next(s for s in result.assignments if s.segment_id == "SEG-2")
    assert seg_2_sizing.selected_cable_type_id == "CABLE-2-SINGLE"
