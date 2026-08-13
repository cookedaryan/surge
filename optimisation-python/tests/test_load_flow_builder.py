"""Tests for building the Pandapower network from PNC domain models."""

import networkx as nx
import pyproj
import pytest
from shapely.geometry import LineString, Point

from app.electrical.load_flow.builder import build_pandapower_network
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import WTGOperatingPoint
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork

_CRS = pyproj.CRS("EPSG:32630")
PNCFixture = tuple[ProjectPNCNetwork, list[WTGOperatingPoint]]


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


def test_builder_mappings_and_conversions(
    valid_pnc: PNCFixture, base_config: LoadFlowConfig
) -> None:
    net, ops = valid_pnc
    # Make length a specific value to check conversion to km
    # and update geometry to match length exactly to pass validation
    import networkx as nx
    import pyproj
    from shapely.geometry import Point

    from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork

    crs = pyproj.CRS("EPSG:32630")

    mst = nx.Graph()
    mst.add_edge("SUB1", "WTG1")

    seg = PNCSegment(
        segment_id="SEG1",
        feeder_id="F1",
        from_node_id="SUB1",
        to_node_id="WTG1",
        route_geometry=LineString([(0, 0), (1375.5, 0)]),
        route_length_m=1375.5,
        traversal_cost=1375.5,
        segment_type="substation_to_wtg",
    )

    feeder = PNCFeeder(
        feeder_id="F1",
        substation_id="SUB1",
        wtg_ids=("WTG1",),
        ordered_node_ids=("SUB1", "WTG1"),
        segments=(seg,),
        total_length_m=1375.5,
        mst_graph=mst,
    )

    net = ProjectPNCNetwork(
        project_id="P1",
        substation_id="SUB1",
        substation_geometry=Point(0, 0),
        feeders=(feeder,),
        wtg_coordinates={"WTG1": Point(1375.5, 0)},
        total_route_length_m=1375.5,
        feeder_count=1,
        wtg_count=1,
        segment_count=1,
        crs=crs,
        route_length_by_feeder={"F1": 1375.5},
        wtg_count_by_feeder={"F1": 1},
    )

    ops = [
        WTGOperatingPoint(node_id="WTG1", active_power_mw=5.5, reactive_power_mvar=1.2)
    ]

    res = build_pandapower_network(net, ops, base_config)

    # 1. Bus mappings
    assert "SUB1" in res.node_to_bus
    assert "WTG1" in res.node_to_bus
    sub_bus_idx = res.node_to_bus["SUB1"]
    wtg_bus_idx = res.node_to_bus["WTG1"]

    # 2. Ext grid
    assert len(res.net.ext_grid) == 1
    assert res.net.ext_grid.at[0, "bus"] == sub_bus_idx
    assert res.net.ext_grid.at[0, "vm_pu"] == 1.0

    # 3. Static generator
    assert len(res.net.sgen) == 1
    sgen_idx = res.wtg_to_sgen["WTG1"]
    assert res.net.sgen.at[sgen_idx, "bus"] == wtg_bus_idx
    assert res.net.sgen.at[sgen_idx, "p_mw"] == 5.5
    assert res.net.sgen.at[sgen_idx, "q_mvar"] == 1.2
    assert bool(res.net.sgen.at[sgen_idx, "in_service"])
    # 4. Lines & unit conversions
    assert len(res.net.line) == 1
    line_idx = res.segment_to_line["SEG1"]
    # 1375.5 m -> 1.3755 km
    assert res.net.line.at[line_idx, "length_km"] == pytest.approx(1.3755)
    # 300 A -> 0.3 kA
    assert res.net.line.at[line_idx, "max_i_ka"] == pytest.approx(0.3)
    assert res.net.line.at[line_idx, "r_ohm_per_km"] == 0.1
    assert res.net.line.at[line_idx, "c_nf_per_km"] == 100.0


def test_builder_deterministic_order(
    valid_pnc: PNCFixture, base_config: LoadFlowConfig
) -> None:
    # This just ensures we don't crash when running, actual stability is checked
    # by ensuring dicts are populated in sorted order of IDs in the builder.py.
    net, ops = valid_pnc
    res1 = build_pandapower_network(net, ops, base_config)
    res2 = build_pandapower_network(net, ops, base_config)

    assert list(res1.node_to_bus.keys()) == list(res2.node_to_bus.keys())
    assert list(res1.segment_to_line.keys()) == list(res2.segment_to_line.keys())
