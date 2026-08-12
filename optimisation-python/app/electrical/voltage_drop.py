"""Pure balanced three-phase electrical screening primitives."""

import math
from typing import Literal

from app.electrical.models import SegmentImpedance, VoltageChangeResult


def _require_finite_number(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def calculate_three_phase_current_a(
    active_power_mw: float,
    nominal_line_voltage_kv: float,
    power_factor: float,
) -> float:
    """Return nominal-voltage line current for balanced three-phase power."""

    _require_finite_number("Active power", active_power_mw)
    _require_finite_number("Nominal line voltage", nominal_line_voltage_kv)
    _require_finite_number("Power factor", power_factor)
    if active_power_mw < 0:
        raise ValueError("Active power must be non-negative")
    if nominal_line_voltage_kv <= 0:
        raise ValueError("Nominal line voltage must be positive")
    if not 0 < power_factor <= 1:
        raise ValueError("Power factor must be > 0 and <= 1")
    if active_power_mw == 0:
        return 0.0

    current = (active_power_mw * 1_000_000.0) / (
        math.sqrt(3) * nominal_line_voltage_kv * 1000.0 * power_factor
    )
    if not math.isfinite(current):
        raise ValueError("Calculated current is not finite")
    return current


def calculate_segment_impedance(
    route_length_m: float,
    resistance_ohm_per_km: float,
    reactance_ohm_per_km: float,
) -> SegmentImpedance:
    """Return series impedance for a route length measured in metres."""

    _require_finite_number("Route length", route_length_m)
    _require_finite_number("Resistance", resistance_ohm_per_km)
    _require_finite_number("Reactance", reactance_ohm_per_km)
    if route_length_m < 0:
        raise ValueError("Route length cannot be negative")
    if resistance_ohm_per_km < 0 or reactance_ohm_per_km < 0:
        raise ValueError("Resistance and reactance must be non-negative")

    length_km = route_length_m / 1000.0
    resistance = resistance_ohm_per_km * length_km
    reactance = reactance_ohm_per_km * length_km
    if not math.isfinite(resistance) or not math.isfinite(reactance):
        raise ValueError("Calculated segment impedance is not finite")
    return SegmentImpedance(resistance, reactance)


def calculate_voltage_change(
    current_a: float,
    impedance: SegmentImpedance,
    power_factor: float,
    power_factor_mode: Literal["lagging", "leading"],
    nominal_line_voltage_kv: float,
) -> VoltageChangeResult:
    """Return linearized voltage drop (positive) or rise (negative)."""

    _require_finite_number("Current", current_a)
    _require_finite_number("Power factor", power_factor)
    _require_finite_number("Nominal line voltage", nominal_line_voltage_kv)
    if current_a < 0:
        raise ValueError("Current cannot be negative")
    if not isinstance(impedance, SegmentImpedance):
        raise ValueError("impedance must be SegmentImpedance")
    if not 0 < power_factor <= 1:
        raise ValueError("Power factor must be > 0 and <= 1")
    if power_factor_mode not in ("lagging", "leading"):
        raise ValueError("Power factor mode must be 'lagging' or 'leading'")
    if nominal_line_voltage_kv <= 0:
        raise ValueError("Nominal line voltage must be positive")

    reactive_sign = -1.0 if power_factor_mode == "leading" else 1.0
    sin_phi = math.sqrt(max(0.0, 1.0 - power_factor**2))
    voltage_change_v = (
        math.sqrt(3)
        * current_a
        * (
            impedance.resistance_ohm * power_factor
            + reactive_sign * impedance.reactance_ohm * sin_phi
        )
    )
    nominal_line_voltage_v = nominal_line_voltage_kv * 1000.0
    voltage_change_percent = voltage_change_v / nominal_line_voltage_v * 100.0
    if not math.isfinite(voltage_change_percent):
        raise ValueError("Calculated voltage change is not finite")

    return VoltageChangeResult(
        voltage_change_v=voltage_change_v,
        voltage_change_percent=voltage_change_percent,
        absolute_deviation_percent=abs(voltage_change_percent),
    )
