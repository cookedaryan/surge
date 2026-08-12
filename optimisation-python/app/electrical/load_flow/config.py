"""Electrical configuration models for AC load flow."""

import math
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class LoadFlowCableType:
    """Explicit domain configuration for a cable type used in AC load flow.

    Provides parameters explicitly rather than relying on Pandapower standard
    libraries.
    """

    cable_type_id: str
    resistance_ohm_per_km: float
    reactance_ohm_per_km: float
    capacitance_nf_per_km: float
    max_current_a: float
    parallel_count: int = 1
    derating_factor: float = 1.0

    def __post_init__(self) -> None:
        if not self.cable_type_id.strip():
            raise ValueError("cable_type_id cannot be blank")

        for val, name in [
            (self.resistance_ohm_per_km, "resistance_ohm_per_km"),
            (self.reactance_ohm_per_km, "reactance_ohm_per_km"),
            (self.capacitance_nf_per_km, "capacitance_nf_per_km"),
            (self.max_current_a, "max_current_a"),
            (self.derating_factor, "derating_factor"),
        ]:
            if not math.isfinite(val):
                raise ValueError(f"{name} must be finite")
            if isinstance(val, bool):
                raise ValueError(f"{name} must not be a boolean")

        if self.resistance_ohm_per_km < 0:
            raise ValueError("resistance_ohm_per_km cannot be negative")
        if self.reactance_ohm_per_km < 0:
            raise ValueError("reactance_ohm_per_km cannot be negative")
        if self.capacitance_nf_per_km < 0:
            raise ValueError("capacitance_nf_per_km cannot be negative")
        if self.max_current_a <= 0:
            raise ValueError("max_current_a must be positive")

        if (
            not isinstance(self.parallel_count, int)
            or isinstance(self.parallel_count, bool)
            or self.parallel_count < 1
        ):
            raise ValueError("parallel_count must be >= 1 and an integer")

        if not (0.0 < self.derating_factor <= 1.0):
            raise ValueError("derating_factor must be in (0, 1]")


@dataclass(frozen=True)
class LoadFlowConfig:
    """Overall AC load flow configuration for a project simulation.

    Includes global system parameters and explicit cable type assignments.
    If a segment does not have an entry in `segment_cable_type_ids`, the
    `default_cable_type_id` is used. The builder will fail if a required cable
    is missing from `cable_types`.
    """

    nominal_voltage_kv: float
    slack_voltage_pu: float
    min_voltage_pu: float
    max_voltage_pu: float
    system_base_mva: float
    cable_types: tuple[LoadFlowCableType, ...]
    default_cable_type_id: str
    segment_cable_type_ids: Mapping[str, str]

    def __post_init__(self) -> None:
        for val, name in [
            (self.nominal_voltage_kv, "nominal_voltage_kv"),
            (self.slack_voltage_pu, "slack_voltage_pu"),
            (self.min_voltage_pu, "min_voltage_pu"),
            (self.max_voltage_pu, "max_voltage_pu"),
            (self.system_base_mva, "system_base_mva"),
        ]:
            if not math.isfinite(val):
                raise ValueError(f"{name} must be finite")
            if isinstance(val, bool):
                raise ValueError(f"{name} must not be a boolean")

        if self.nominal_voltage_kv <= 0:
            raise ValueError("nominal_voltage_kv must be positive")
        if self.slack_voltage_pu <= 0:
            raise ValueError("slack_voltage_pu must be positive")
        if self.min_voltage_pu < 0 or self.max_voltage_pu < 0:
            raise ValueError("voltage limits must be positive")
        if self.min_voltage_pu >= self.max_voltage_pu:
            raise ValueError("min_voltage_pu must be strictly less than max_voltage_pu")
        if self.system_base_mva <= 0:
            raise ValueError("system_base_mva must be positive")

        cable_ids = [c.cable_type_id for c in self.cable_types]
        if len(cable_ids) != len(set(cable_ids)):
            raise ValueError("Duplicate cable_type_id found in cable_types")
