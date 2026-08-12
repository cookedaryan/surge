"""Tests for AC load flow configuration validation."""

import pytest

from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig


def test_cable_type_valid():
    """Valid cable configuration should instantiate without errors."""
    c = LoadFlowCableType(
        cable_type_id="CABLE-1",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=100.0,
        max_current_a=300.0,
        parallel_count=2,
        derating_factor=0.9,
    )
    assert c.cable_type_id == "CABLE-1"
    assert c.parallel_count == 2
    assert c.derating_factor == 0.9


def test_cable_type_invalid_id():
    with pytest.raises(ValueError, match="blank"):
        LoadFlowCableType(
            cable_type_id="   ",
            resistance_ohm_per_km=0.1,
            reactance_ohm_per_km=0.1,
            capacitance_nf_per_km=100.0,
            max_current_a=300.0,
        )


@pytest.mark.parametrize(
    "r, x, c, i",
    [
        (-0.1, 0.1, 100.0, 300.0),
        (0.1, -0.1, 100.0, 300.0),
        (0.1, 0.1, -100.0, 300.0),
        (0.1, 0.1, 100.0, -10.0),
        (0.1, 0.1, 100.0, 0.0),
    ],
)
def test_cable_type_negative_values(r: float, x: float, c: float, i: float):
    with pytest.raises(ValueError):
        LoadFlowCableType(
            cable_type_id="C1",
            resistance_ohm_per_km=r,
            reactance_ohm_per_km=x,
            capacitance_nf_per_km=c,
            max_current_a=i,
        )


@pytest.mark.parametrize(
    "parallel, derating",
    [
        (0, 1.0),
        (-1, 1.0),
        (1, 0.0),
        (1, 1.1),
        (1, -0.5),
    ],
)
def test_cable_type_invalid_parallel_or_derating(parallel: int, derating: float):
    with pytest.raises(ValueError):
        LoadFlowCableType(
            cable_type_id="C1",
            resistance_ohm_per_km=0.1,
            reactance_ohm_per_km=0.1,
            capacitance_nf_per_km=100.0,
            max_current_a=300.0,
            parallel_count=parallel,
            derating_factor=derating,
        )


def test_config_valid():
    """Valid config should instantiate."""
    c = LoadFlowCableType(
        cable_type_id="C1",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=100.0,
        max_current_a=300.0,
    )
    conf = LoadFlowConfig(
        nominal_voltage_kv=33.0,
        slack_voltage_pu=1.0,
        min_voltage_pu=0.95,
        max_voltage_pu=1.05,
        system_base_mva=100.0,
        cable_types=(c,),
        default_cable_type_id="C1",
        segment_cable_type_ids={"SEG1": "C1"},
    )
    assert conf.nominal_voltage_kv == 33.0


def test_config_invalid_voltage_bounds():
    c = LoadFlowCableType(
        cable_type_id="C1",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=100.0,
        max_current_a=300.0,
    )
    # min > max
    with pytest.raises(ValueError, match="strictly less"):
        LoadFlowConfig(
            nominal_voltage_kv=33.0,
            slack_voltage_pu=1.0,
            min_voltage_pu=1.05,
            max_voltage_pu=0.95,
            system_base_mva=100.0,
            cable_types=(c,),
            default_cable_type_id="C1",
            segment_cable_type_ids={},
        )
    # min == max
    with pytest.raises(ValueError, match="strictly less"):
        LoadFlowConfig(
            nominal_voltage_kv=33.0,
            slack_voltage_pu=1.0,
            min_voltage_pu=1.0,
            max_voltage_pu=1.0,
            system_base_mva=100.0,
            cable_types=(c,),
            default_cable_type_id="C1",
            segment_cable_type_ids={},
        )


def test_config_duplicate_cable_types():
    c1 = LoadFlowCableType(
        cable_type_id="C1",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=100.0,
        max_current_a=300.0,
    )
    c2 = LoadFlowCableType(
        cable_type_id="C1",  # duplicate ID
        resistance_ohm_per_km=0.2,
        reactance_ohm_per_km=0.2,
        capacitance_nf_per_km=200.0,
        max_current_a=400.0,
    )
    with pytest.raises(ValueError, match="Duplicate"):
        LoadFlowConfig(
            nominal_voltage_kv=33.0,
            slack_voltage_pu=1.0,
            min_voltage_pu=0.95,
            max_voltage_pu=1.05,
            system_base_mva=100.0,
            cable_types=(c1, c2),
            default_cable_type_id="C1",
            segment_cable_type_ids={},
        )
