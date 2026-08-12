import math

import pytest

from app.electrical.models import SegmentImpedance
from app.electrical.voltage_drop import (
    calculate_segment_impedance,
    calculate_three_phase_current_a,
    calculate_voltage_change,
)


def test_three_phase_current_calculation_unity_pf() -> None:
    # 10 MW at 33 kV, pf=1.0
    # I = 10,000,000 / (sqrt(3) * 33,000 * 1.0) = 174.954 A
    current = calculate_three_phase_current_a(
        active_power_mw=10.0,
        nominal_line_voltage_kv=33.0,
        power_factor=1.0,
    )
    assert current == pytest.approx(174.9546, abs=1e-4)


def test_three_phase_current_calculation_lagging_pf() -> None:
    # 10 MW at 33 kV, pf=0.9
    # I = 10,000,000 / (sqrt(3) * 33,000 * 0.9) = 194.393 A
    current = calculate_three_phase_current_a(
        active_power_mw=10.0,
        nominal_line_voltage_kv=33.0,
        power_factor=0.9,
    )
    assert current == pytest.approx(194.3940, abs=1e-4)


def test_three_phase_current_zero_active_power() -> None:
    current = calculate_three_phase_current_a(
        active_power_mw=0.0,
        nominal_line_voltage_kv=33.0,
        power_factor=0.9,
    )
    assert current == 0.0


def test_three_phase_current_scales_linearly() -> None:
    current_10 = calculate_three_phase_current_a(10.0, 33.0, 0.95)
    current_20 = calculate_three_phase_current_a(20.0, 33.0, 0.95)
    assert current_20 == pytest.approx(current_10 * 2.0)


def test_three_phase_current_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="positive"):
        calculate_three_phase_current_a(10.0, 0.0, 0.95)
    with pytest.raises(ValueError, match="positive"):
        calculate_three_phase_current_a(10.0, -33.0, 0.95)
    with pytest.raises(ValueError, match="Power factor"):
        calculate_three_phase_current_a(10.0, 33.0, 0.0)
    with pytest.raises(ValueError, match="Power factor"):
        calculate_three_phase_current_a(10.0, 33.0, 1.1)
    with pytest.raises(ValueError, match="non-negative"):
        calculate_three_phase_current_a(-1.0, 33.0, 0.95)
    with pytest.raises(ValueError, match="finite"):
        calculate_three_phase_current_a(float("nan"), 33.0, 0.95)
    with pytest.raises(ValueError, match="finite"):
        calculate_three_phase_current_a(10.0, float("inf"), 0.95)


def test_segment_impedance_calculation() -> None:
    impedance = calculate_segment_impedance(
        route_length_m=2500.0,
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.15,
    )
    assert impedance.resistance_ohm == pytest.approx(0.25)
    assert impedance.reactance_ohm == pytest.approx(0.375)


def test_segment_impedance_zero_length() -> None:
    impedance = calculate_segment_impedance(
        route_length_m=0.0,
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.15,
    )
    assert impedance.resistance_ohm == 0.0
    assert impedance.reactance_ohm == 0.0


def test_segment_impedance_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="negative"):
        calculate_segment_impedance(-100.0, 0.1, 0.1)
    with pytest.raises(ValueError, match="non-negative"):
        calculate_segment_impedance(100.0, -0.1, 0.1)
    with pytest.raises(ValueError, match="non-negative"):
        calculate_segment_impedance(100.0, 0.1, -0.1)
    with pytest.raises(ValueError, match="finite"):
        calculate_segment_impedance(float("nan"), 0.1, 0.1)
    with pytest.raises(ValueError, match="finite"):
        calculate_segment_impedance(100.0, float("inf"), 0.1)


def test_voltage_change_lagging() -> None:
    # I = 200 A, Z = 0.5 + j0.8, pf = 0.9 lagging
    # phi = acos(0.9) = 25.84 deg
    # V_change = sqrt(3) * 200 * (0.5 * 0.9 + 0.8 * sin(25.84))
    # sin(25.84) = 0.43588989
    # V_change = 1.732 * 200 * (0.45 + 0.3487) = 346.41 * 0.7987 = 276.68 V
    current = 200.0
    impedance = SegmentImpedance(0.5, 0.8)
    res = calculate_voltage_change(
        current_a=current,
        impedance=impedance,
        power_factor=0.9,
        power_factor_mode="lagging",
        nominal_line_voltage_kv=33.0,
    )
    expected_v = math.sqrt(3) * 200.0 * (0.5 * 0.9 + 0.8 * math.sin(math.acos(0.9)))
    assert res.voltage_change_v == pytest.approx(expected_v)

    expected_pct = (expected_v / 33000.0) * 100.0
    assert res.voltage_change_percent == pytest.approx(expected_pct)
    assert res.absolute_deviation_percent == pytest.approx(abs(expected_pct))


def test_voltage_change_leading() -> None:
    # For leading, reactive term is negative
    current = 200.0
    impedance = SegmentImpedance(0.5, 0.8)
    res = calculate_voltage_change(
        current_a=current,
        impedance=impedance,
        power_factor=0.9,
        power_factor_mode="leading",
        nominal_line_voltage_kv=33.0,
    )
    expected_v = math.sqrt(3) * 200.0 * (0.5 * 0.9 - 0.8 * math.sin(math.acos(0.9)))
    assert res.voltage_change_v == pytest.approx(expected_v)
    assert res.voltage_change_percent == pytest.approx((expected_v / 33000.0) * 100.0)


def test_voltage_change_resistance_only() -> None:
    res = calculate_voltage_change(
        current_a=100.0,
        impedance=SegmentImpedance(1.0, 0.0),
        power_factor=0.8,
        power_factor_mode="lagging",
        nominal_line_voltage_kv=33.0,
    )
    expected_v = math.sqrt(3) * 100.0 * 1.0 * 0.8
    assert res.voltage_change_v == pytest.approx(expected_v)


def test_voltage_change_reactance_only() -> None:
    res = calculate_voltage_change(
        current_a=100.0,
        impedance=SegmentImpedance(0.0, 1.0),
        power_factor=0.8,
        power_factor_mode="lagging",
        nominal_line_voltage_kv=33.0,
    )
    expected_v = math.sqrt(3) * 100.0 * 1.0 * math.sin(math.acos(0.8))
    assert res.voltage_change_v == pytest.approx(expected_v)


def test_voltage_change_invalid_inputs() -> None:
    impedance = SegmentImpedance(0.1, 0.1)
    with pytest.raises(ValueError, match="negative"):
        calculate_voltage_change(-10.0, impedance, 0.9, "lagging", 33.0)
    with pytest.raises(ValueError, match="Power factor"):
        calculate_voltage_change(10.0, impedance, 1.1, "lagging", 33.0)
    with pytest.raises(ValueError, match="mode"):
        calculate_voltage_change(10.0, impedance, 0.9, "unknown", 33.0)  # type: ignore
    with pytest.raises(ValueError, match="positive"):
        calculate_voltage_change(10.0, impedance, 0.9, "lagging", -33.0)
    with pytest.raises(ValueError, match="finite"):
        calculate_voltage_change(float("nan"), impedance, 0.9, "lagging", 33.0)


def test_segment_impedance_model_rejects_non_finite_values() -> None:
    with pytest.raises(ValueError, match="finite"):
        SegmentImpedance(float("inf"), 0.1)
