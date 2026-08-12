"""Immutable inputs and results for deterministic electrical screening."""

import math
from dataclasses import dataclass
from typing import Literal


def _require_finite_number(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a real number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True)
class ConductorElectricalProperties:
    """Positive ampacity and non-negative series impedance per kilometre."""

    resistance_ohm_per_km: float
    reactance_ohm_per_km: float
    ampacity_a: float

    def __post_init__(self) -> None:
        _require_finite_number("Conductor resistance", self.resistance_ohm_per_km)
        _require_finite_number("Conductor reactance", self.reactance_ohm_per_km)
        _require_finite_number("Conductor ampacity", self.ampacity_a)
        if self.resistance_ohm_per_km < 0:
            raise ValueError("Conductor resistance must be non-negative")
        if self.reactance_ohm_per_km < 0:
            raise ValueError("Conductor reactance must be non-negative")
        if self.ampacity_a <= 0:
            raise ValueError("Conductor ampacity must be positive")


@dataclass(frozen=True)
class ElectricalDesignConfig:
    """Operating point, voltage limit, and conductor used by the proxy."""

    nominal_line_voltage_kv: float
    power_factor: float
    power_factor_mode: Literal["lagging", "leading"]
    operating_factor: float
    max_voltage_deviation_percent: float
    conductor: ConductorElectricalProperties

    def __post_init__(self) -> None:
        _require_finite_number("Nominal line voltage", self.nominal_line_voltage_kv)
        _require_finite_number("Power factor", self.power_factor)
        _require_finite_number("Operating factor", self.operating_factor)
        _require_finite_number(
            "Max voltage deviation percent",
            self.max_voltage_deviation_percent,
        )
        if self.nominal_line_voltage_kv <= 0:
            raise ValueError("Nominal line voltage must be positive")
        if not 0 < self.power_factor <= 1:
            raise ValueError("Power factor must be > 0 and <= 1")
        if self.power_factor_mode not in ("lagging", "leading"):
            raise ValueError("Power factor mode must be 'lagging' or 'leading'")
        if not 0 < self.operating_factor <= 1:
            raise ValueError("Operating factor must be > 0 and <= 1")
        if self.max_voltage_deviation_percent <= 0:
            raise ValueError("Max voltage deviation percent must be positive")
        if not isinstance(self.conductor, ConductorElectricalProperties):
            raise ValueError("conductor must be ConductorElectricalProperties")


@dataclass(frozen=True)
class SegmentImpedance:
    resistance_ohm: float
    reactance_ohm: float

    def __post_init__(self) -> None:
        _require_finite_number("Segment resistance", self.resistance_ohm)
        _require_finite_number("Segment reactance", self.reactance_ohm)
        if self.resistance_ohm < 0 or self.reactance_ohm < 0:
            raise ValueError("Segment resistance and reactance must be non-negative")


@dataclass(frozen=True)
class VoltageChangeResult:
    voltage_change_v: float
    voltage_change_percent: float
    absolute_deviation_percent: float


@dataclass(frozen=True)
class ElectricalSegmentResult:
    feeder_id: str
    parent_node_id: str
    child_node_id: str
    route_length_m: float
    downstream_active_power_mw: float
    current_a: float
    impedance: SegmentImpedance
    voltage_change_v: float
    voltage_change_percent: float
    ampacity_a: float
    loading_percent: float
    ampacity_exceeded: bool


@dataclass(frozen=True)
class TurbineElectricalResult:
    feeder_id: str
    turbine_node_id: str
    active_power_mw: float
    path_from_substation: tuple[str, ...]
    cumulative_voltage_change_v: float
    cumulative_voltage_change_percent: float
    estimated_terminal_voltage_v: float
    voltage_limit_exceeded: bool


@dataclass(frozen=True)
class ElectricalViolation:
    code: Literal[
        "VOLTAGE_LIMIT_EXCEEDED",
        "AMPACITY_EXCEEDED",
        "SUBSTATION_CAPACITY_EXCEEDED",
    ]
    feeder_id: str
    node_id: str | None
    edge: tuple[str, str] | None
    measured_value: float
    limit_value: float


@dataclass(frozen=True)
class FeederElectricalResult:
    feeder_id: str
    substation_node_id: str
    total_active_power_mw: float
    segments: tuple[ElectricalSegmentResult, ...]
    turbines: tuple[TurbineElectricalResult, ...]
    maximum_voltage_deviation_percent: float
    maximum_loading_percent: float
    worst_voltage_turbine_id: str | None
    most_loaded_edge: tuple[str, str] | None
    is_valid: bool
    violations: tuple[ElectricalViolation, ...]


@dataclass(frozen=True)
class ElectricalValidationResult:
    feeders: tuple[FeederElectricalResult, ...]
    maximum_voltage_deviation_percent: float
    maximum_loading_percent: float
    is_valid: bool
    violations: tuple[ElectricalViolation, ...]
