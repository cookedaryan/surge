"""Canonical candidate-level engineering metric domain models."""

import math
from dataclasses import dataclass
from enum import StrEnum

from app.algorithms.pole_placement import CollectorPoleResult


@dataclass(frozen=True)
class ParcelEngineeringExposure:
    parcel_id: str
    route_overlap_length_m: float
    row_intersection_area_m2: float


@dataclass(frozen=True)
class CandidateEngineeringMetrics:
    """Raw engineering quantities extracted for one PNC candidate."""

    total_route_length_m: float
    total_traversal_cost: float
    affected_parcel_count: int
    road_crossing_count: int
    soft_constraint_overlap_length_m: float
    environmental_overlap_m2: float
    physical_pole_count: int
    total_active_loss_mw: float
    maximum_loading_percent: float
    voltage_margin_pu: float

    def __post_init__(self) -> None:
        non_negative_values = {
            "total_route_length_m": self.total_route_length_m,
            "total_traversal_cost": self.total_traversal_cost,
            "soft_constraint_overlap_length_m": self.soft_constraint_overlap_length_m,
            "environmental_overlap_m2": self.environmental_overlap_m2,
            "total_active_loss_mw": self.total_active_loss_mw,
            "maximum_loading_percent": self.maximum_loading_percent,
        }
        if any(not math.isfinite(value) for value in non_negative_values.values()):
            raise ValueError("Engineering metric values must be finite")
        invalid_names = [
            name for name, value in non_negative_values.items() if value < 0.0
        ]
        if invalid_names:
            raise ValueError(
                "Engineering metric values must be non-negative: "
                + ", ".join(invalid_names)
            )
        if not math.isfinite(self.voltage_margin_pu):
            raise ValueError("voltage_margin_pu must be finite")

        counts = {
            "affected_parcel_count": self.affected_parcel_count,
            "road_crossing_count": self.road_crossing_count,
            "physical_pole_count": self.physical_pole_count,
        }
        if any(not isinstance(value, int) for value in counts.values()):
            raise ValueError("Engineering count metrics must be integers")
        invalid_counts = [name for name, value in counts.items() if value < 0]
        if invalid_counts:
            raise ValueError(
                "Engineering count metrics must be non-negative: "
                + ", ".join(invalid_counts)
            )


class EngineeringMetricFailureCode(StrEnum):
    """Stable reasons why a complete engineering metric set is unavailable."""

    PHYSICAL_METRICS_INVALID = "PHYSICAL_METRICS_INVALID"
    SPATIAL_ANALYSIS_FAILED = "SPATIAL_ANALYSIS_FAILED"
    POLE_CONFIG_MISSING = "POLE_CONFIG_MISSING"
    POLE_PLACEMENT_FAILED = "POLE_PLACEMENT_FAILED"
    LOAD_FLOW_NOT_CONVERGED = "LOAD_FLOW_NOT_CONVERGED"
    ELECTRICAL_METRICS_MISSING = "ELECTRICAL_METRICS_MISSING"
    ELECTRICAL_METRICS_NOT_FINITE = "ELECTRICAL_METRICS_NOT_FINITE"
    ELECTRICAL_METRICS_INVALID = "ELECTRICAL_METRICS_INVALID"


@dataclass(frozen=True)
class EngineeringMetricFailure:
    """One deterministic extraction diagnostic for a candidate."""

    code: EngineeringMetricFailureCode
    message: str

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Engineering metric failure message must not be blank")


@dataclass(frozen=True)
class CandidateEngineeringAssessment:
    """Complete metrics or explicit extraction failures for one candidate."""

    scenario_id: str
    metrics: CandidateEngineeringMetrics | None
    engineering_metrics_available: bool
    hard_violation_ids: tuple[str, ...]
    extraction_failures: tuple[EngineeringMetricFailure, ...]
    pole_result: CollectorPoleResult | None = None
    parcel_exposures: tuple[ParcelEngineeringExposure, ...] = ()

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("Engineering assessment scenario_id must not be blank")
        if self.hard_violation_ids != tuple(sorted(set(self.hard_violation_ids))):
            raise ValueError("hard_violation_ids must be sorted and unique")
        if self.engineering_metrics_available != (self.metrics is not None):
            raise ValueError(
                "engineering_metrics_available must match metrics availability"
            )
        if self.metrics is not None and self.extraction_failures:
            raise ValueError("Available metrics cannot have extraction failures")
        if self.metrics is None and not self.extraction_failures:
            raise ValueError("Unavailable metrics require extraction failures")
        if self.metrics is not None:
            if self.pole_result is None:
                raise ValueError("Available metrics require a cached pole result")
            if self.metrics.physical_pole_count != self.pole_result.total_poles:
                raise ValueError("Pole count must match the cached pole result")
