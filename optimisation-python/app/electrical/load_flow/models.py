"""Domain models for AC load flow results and violations."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

import pandapower as pp


class LoadFlowViolationCode(StrEnum):
    """Specific codes for electrical violations and solver errors."""

    LOAD_FLOW_NOT_CONVERGED = "LOAD_FLOW_NOT_CONVERGED"
    BUS_UNDERVOLTAGE = "BUS_UNDERVOLTAGE"
    BUS_OVERVOLTAGE = "BUS_OVERVOLTAGE"
    CABLE_OVERLOAD = "CABLE_OVERLOAD"
    RESULT_NOT_FINITE = "RESULT_NOT_FINITE"


@dataclass(frozen=True)
class WTGOperatingPoint:
    """Explicit operating point for a Wind Turbine Generator.

    Active and reactive power use positive generator conventions
    (positive p_mw = injecting active power into grid,
    positive q_mvar = injecting reactive power into grid).
    """

    node_id: str
    active_power_mw: float
    reactive_power_mvar: float

    def __post_init__(self) -> None:
        for val, name in [
            (self.active_power_mw, "active_power_mw"),
            (self.reactive_power_mvar, "reactive_power_mvar"),
        ]:
            if not math.isfinite(val):
                raise ValueError(f"{name} must be finite")
            if isinstance(val, bool):
                raise ValueError(f"{name} must not be a boolean")


@dataclass(frozen=True)
class LoadFlowViolation:
    """An electrical constraint violation or load-flow error."""

    code: LoadFlowViolationCode
    message: str
    node_id: str | None = None
    segment_id: str | None = None
    feeder_id: str | None = None
    measured_value: float | None = None
    limit_value: float | None = None


@dataclass(frozen=True)
class LoadFlowBusResult:
    """AC load flow result for a single node (bus)."""

    node_id: str
    node_type: Literal["substation", "wtg"]
    voltage_pu: float
    voltage_kv: float
    voltage_angle_degree: float
    net_active_power_demand_mw: float
    net_reactive_power_demand_mvar: float


@dataclass(frozen=True)
class LoadFlowSegmentResult:
    """AC load flow result for a physical routed segment (line)."""

    segment_id: str
    feeder_id: str
    p_from_mw: float
    q_from_mvar: float
    p_to_mw: float
    q_to_mvar: float
    active_loss_mw: float
    reactive_loss_mvar: float
    current_from_a: float
    current_to_a: float
    maximum_current_a: float
    loading_percent: float


@dataclass(frozen=True)
class LoadFlowFeederResult:
    """Summary of load flow results across a single feeder."""

    feeder_id: str
    wtg_count: int
    active_loss_mw: float
    reactive_loss_mvar: float
    minimum_voltage_pu: float
    maximum_voltage_pu: float
    maximum_loading_percent: float
    worst_voltage_node_id: str | None
    most_loaded_segment_id: str | None
    valid: bool


@dataclass(frozen=True)
class LoadFlowNetworkResult:
    """Complete summary of the electrical analysis for a PNC Network.

    If `converged` is False, the collections of results will be empty
    and violations will contain LOAD_FLOW_NOT_CONVERGED.
    `is_valid` is true only if converged is true and violations is empty.
    """

    converged: bool
    is_valid: bool
    solver_algorithm: str | None
    total_generation_mw: float | None
    slack_power_mw: float | None
    total_active_loss_mw: float | None
    total_reactive_loss_mvar: float | None
    minimum_voltage_pu: float | None
    maximum_voltage_pu: float | None
    maximum_loading_percent: float | None
    buses: tuple[LoadFlowBusResult, ...]
    segments: tuple[LoadFlowSegmentResult, ...]
    feeders: tuple[LoadFlowFeederResult, ...]
    violations: tuple[LoadFlowViolation, ...]


@dataclass(frozen=True)
class PandapowerBuildResult:
    """Immutable build artifact holding the pandapower network and stable ID mappings.

    The maps relate domain IDs to pandapower integer indices and vice-versa.
    """

    net: pp.pandapowerNet
    node_to_bus: Mapping[str, int]
    bus_to_node: Mapping[int, str]
    segment_to_line: Mapping[str, int]
    line_to_segment: Mapping[int, str]
    wtg_to_sgen: Mapping[str, int]
