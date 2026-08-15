"""Domain models for deterministic multi-objective electrical + physical scoring."""

import math
from dataclasses import dataclass
from enum import StrEnum
from numbers import Real
from typing import Literal

from app.costing.models import CandidateCostAssessment
from app.electrical.load_flow.models import LoadFlowNetworkResult
from app.optimisation.engineering_metric_models import (
    CandidateEngineeringAssessment,
    CandidateEngineeringMetrics,
)
from app.optimisation.scenario_models import PNCScenario


class ScoringPolicyMode(StrEnum):
    LEGACY_COMPATIBILITY = "LEGACY_COMPATIBILITY"
    UNIFIED_ENGINEERING = "UNIFIED_ENGINEERING"
    COST_AWARE = "COST_AWARE"


@dataclass(frozen=True)
class CostAwareRecommendationConfig:
    engineering_weight: float
    lifecycle_cost_weight: float

    def __post_init__(self) -> None:
        weights = (self.engineering_weight, self.lifecycle_cost_weight)
        if any(
            isinstance(weight, bool) or not isinstance(weight, Real)
            for weight in weights
        ):
            raise ValueError("Cost-aware weights must be numbers, not booleans")
        if any(not math.isfinite(weight) for weight in weights):
            raise ValueError("Cost-aware weights must be finite")
        if any(weight < 0 for weight in weights):
            raise ValueError("Cost-aware weights must be non-negative")
        total = math.fsum(weights)
        if not math.isclose(total, 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(f"cost-aware weights must sum to 1.0, got {total}")


class ScoringGroup(StrEnum):
    PHYSICAL = "PHYSICAL"
    SPATIAL = "SPATIAL"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    ELECTRICAL = "ELECTRICAL"


class ScoringMetric(StrEnum):
    ROUTE_LENGTH = "ROUTE_LENGTH"
    TRAVERSAL_COST = "TRAVERSAL_COST"
    AFFECTED_PARCEL_COUNT = "AFFECTED_PARCEL_COUNT"
    ROAD_CROSSING_COUNT = "ROAD_CROSSING_COUNT"
    SOFT_CONSTRAINT_OVERLAP_LENGTH = "SOFT_CONSTRAINT_OVERLAP_LENGTH"
    PHYSICAL_POLE_COUNT = "PHYSICAL_POLE_COUNT"
    ACTIVE_LOSS = "ACTIVE_LOSS"
    CABLE_LOADING = "CABLE_LOADING"
    VOLTAGE_MARGIN = "VOLTAGE_MARGIN"


@dataclass(frozen=True)
class SpatialScoringWeights:
    traversal_cost: float
    affected_parcels: float
    road_crossings: float
    soft_overlap_length: float


@dataclass(frozen=True)
class ElectricalScoringWeights:
    active_loss: float
    cable_loading: float
    voltage_margin: float


@dataclass(frozen=True)
class CandidateScoringConfig:
    policy_mode: ScoringPolicyMode
    physical_weight: float
    spatial_weight: float
    infrastructure_weight: float
    electrical_weight: float
    spatial_subweights: SpatialScoringWeights
    electrical_subweights: ElectricalScoringWeights

    def __post_init__(self) -> None:
        if not isinstance(self.policy_mode, ScoringPolicyMode):
            raise ValueError("policy_mode must be a ScoringPolicyMode")
        if not isinstance(self.spatial_subweights, SpatialScoringWeights):
            raise ValueError("spatial_subweights must be SpatialScoringWeights")
        if not isinstance(self.electrical_subweights, ElectricalScoringWeights):
            raise ValueError("electrical_subweights must be ElectricalScoringWeights")

        groups = [
            self.physical_weight,
            self.spatial_weight,
            self.infrastructure_weight,
            self.electrical_weight,
        ]
        self._validate_weights(groups, "Group")

        total_weight = math.fsum(groups)
        if not math.isclose(total_weight, 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(f"Group weights must sum to 1.0, got {total_weight}")

        spatial_subs = [
            self.spatial_subweights.traversal_cost,
            self.spatial_subweights.affected_parcels,
            self.spatial_subweights.road_crossings,
            self.spatial_subweights.soft_overlap_length,
        ]
        self._validate_weights(spatial_subs, "Spatial subweight")
        if self.spatial_weight > 0.0:
            if not math.isclose(
                math.fsum(spatial_subs), 1.0, rel_tol=1e-9, abs_tol=1e-9
            ):
                raise ValueError("Active spatial subweights must sum to 1.0")
        else:
            if any(w != 0.0 for w in spatial_subs):
                raise ValueError(
                    "Inactive spatial group must have exactly 0.0 subweights"
                )

        elec_subs = [
            self.electrical_subweights.active_loss,
            self.electrical_subweights.cable_loading,
            self.electrical_subweights.voltage_margin,
        ]
        self._validate_weights(elec_subs, "Electrical subweight")
        if self.electrical_weight > 0.0:
            if not math.isclose(math.fsum(elec_subs), 1.0, rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError("Active electrical subweights must sum to 1.0")
        else:
            if any(w != 0.0 for w in elec_subs):
                raise ValueError(
                    "Inactive electrical group must have exactly 0.0 subweights"
                )

    @staticmethod
    def _validate_weights(weights: list[float], label: str) -> None:
        if any(
            isinstance(weight, bool) or not isinstance(weight, Real)
            for weight in weights
        ):
            raise ValueError(f"{label} weights must be numbers, not booleans")
        if any(not math.isfinite(weight) for weight in weights):
            raise ValueError(f"{label} weights must be finite")
        if any(weight < 0.0 for weight in weights):
            raise ValueError(f"{label} weights must be non-negative")


@dataclass(frozen=True)
class ElectricallyEvaluatedScenario:
    """Atomic input binding a PNC scenario to its load flow result and context."""

    scenario: PNCScenario
    load_flow_result: LoadFlowNetworkResult
    electrical_context_id: str


@dataclass(frozen=True)
class EngineeringEvaluatedScenario:
    electrical: ElectricallyEvaluatedScenario
    engineering_assessment: CandidateEngineeringAssessment
    cost_assessment: CandidateCostAssessment | None = None

    def __post_init__(self) -> None:
        scenario_id = self.electrical.scenario.scenario_id
        if scenario_id != self.engineering_assessment.scenario_id:
            raise ValueError(
                "Evaluated scenario_id must match engineering_assessment scenario_id"
            )
        if (
            self.cost_assessment is not None
            and scenario_id != self.cost_assessment.scenario_id
        ):
            raise ValueError(
                "Evaluated scenario_id must match cost_assessment scenario_id"
            )
        if (
            self.cost_assessment is not None
            and self.cost_assessment.cost is not None
            and scenario_id != self.cost_assessment.cost.scenario_id
        ):
            raise ValueError(
                "Evaluated scenario_id must match lifecycle cost scenario_id"
            )


@dataclass(frozen=True)
class NormalizationRange:
    metric: ScoringMetric
    minimum: float
    maximum: float
    constant: bool


@dataclass(frozen=True)
class MetricScore:
    metric: ScoringMetric
    raw_value: float
    normalized_benefit: float
    weight: float
    weighted_benefit: float


@dataclass(frozen=True)
class GroupScore:
    group: ScoringGroup
    group_score: float
    group_weight: float
    weighted_score: float


@dataclass(frozen=True)
class MetricComparison:
    metric: ScoringMetric | str
    recommended_value: float
    baseline_value: float
    absolute_delta: float
    relative_delta_percent: float | None
    preferred_direction: Literal["higher", "lower"]

    @property
    def metric_name(self) -> str:
        return (
            self.metric.value if isinstance(self.metric, ScoringMetric) else self.metric
        )


class DisqualificationCode(StrEnum):
    LOAD_FLOW_NOT_CONVERGED = "LOAD_FLOW_NOT_CONVERGED"
    ELECTRICAL_VIOLATION = "ELECTRICAL_VIOLATION"
    ELECTRICAL_METRICS_MISSING = "ELECTRICAL_METRICS_MISSING"
    RESULT_NOT_FINITE = "RESULT_NOT_FINITE"
    COMPARISON_CONTEXT_MISMATCH = "COMPARISON_CONTEXT_MISMATCH"
    TOPOLOGY_MISMATCH = "TOPOLOGY_MISMATCH"
    ENGINEERING_METRICS_UNAVAILABLE = "ENGINEERING_METRICS_UNAVAILABLE"
    HARD_SPATIAL_VIOLATION = "HARD_SPATIAL_VIOLATION"
    INCOMPLETE_LIFECYCLE_COST = "INCOMPLETE_LIFECYCLE_COST"
    ECONOMIC_CONTEXT_MISMATCH = "ECONOMIC_CONTEXT_MISMATCH"


@dataclass(frozen=True)
class Disqualification:
    code: DisqualificationCode
    message: str
    underlying_violations: tuple[str, ...] = ()
    node_id: str | None = None
    segment_id: str | None = None
    feeder_id: str | None = None


@dataclass(frozen=True)
class CandidateAssessment:
    scenario_id: str
    eligible: bool
    disqualifications: tuple[Disqualification, ...]
    metrics: CandidateEngineeringMetrics | None


@dataclass(frozen=True)
class CandidateEvaluation:
    assessment: CandidateAssessment
    metric_scores: tuple[MetricScore, ...]
    group_scores: tuple[GroupScore, ...]
    total_benefit_score: float | None = None  # Kept for backward compatibility
    rank: int | None = None
    engineering_benefit_score: float | None = None
    economic_benefit_score: float | None = None
    final_benefit_score: float | None = None
    lifecycle_cost: float | None = None


class RecommendationReasonCode(StrEnum):
    ONLY_ELIGIBLE_CANDIDATE = "ONLY_ELIGIBLE_CANDIDATE"
    HIGHEST_TOTAL_BENEFIT = "HIGHEST_TOTAL_BENEFIT"
    SHORTEST_ROUTE = "SHORTEST_ROUTE"
    LOWEST_TRAVERSAL_COST = "LOWEST_TRAVERSAL_COST"
    FEWEST_AFFECTED_PARCELS = "FEWEST_AFFECTED_PARCELS"
    FEWEST_ROAD_CROSSINGS = "FEWEST_ROAD_CROSSINGS"
    LOWEST_SOFT_CONSTRAINT_OVERLAP = "LOWEST_SOFT_CONSTRAINT_OVERLAP"
    LOWEST_POLE_COUNT = "LOWEST_POLE_COUNT"
    LOWEST_ACTIVE_LOSS = "LOWEST_ACTIVE_LOSS"
    LOWEST_CABLE_LOADING = "LOWEST_CABLE_LOADING"
    BEST_VOLTAGE_MARGIN = "BEST_VOLTAGE_MARGIN"
    HIGHEST_PHYSICAL_SCORE = "HIGHEST_PHYSICAL_SCORE"
    HIGHEST_SPATIAL_SCORE = "HIGHEST_SPATIAL_SCORE"
    HIGHEST_INFRASTRUCTURE_SCORE = "HIGHEST_INFRASTRUCTURE_SCORE"
    HIGHEST_ELECTRICAL_SCORE = "HIGHEST_ELECTRICAL_SCORE"
    BASELINE_IMPROVEMENT = "BASELINE_IMPROVEMENT"
    TRADE_OFF_ACCEPTED = "TRADE_OFF_ACCEPTED"
    HIGHEST_ECONOMIC_BENEFIT = "HIGHEST_ECONOMIC_BENEFIT"
    HIGHEST_COST_AWARE_BENEFIT = "HIGHEST_COST_AWARE_BENEFIT"
    LOWEST_LIFECYCLE_COST = "LOWEST_LIFECYCLE_COST"
    LOWEST_TOTAL_CAPEX = "LOWEST_TOTAL_CAPEX"
    LOWEST_LOSS_OPEX = "LOWEST_LOSS_OPEX"
    BALANCED_ENGINEERING_AND_COST = "BALANCED_ENGINEERING_AND_COST"
    HIGHEST_ENGINEERING_BENEFIT = "HIGHEST_ENGINEERING_BENEFIT"


@dataclass(frozen=True)
class RecommendationReason:
    code: RecommendationReasonCode
    message: str
    metric: ScoringMetric | None = None
    candidate_value: float | None = None
    comparison_value: float | None = None


class OptimizationRecommendationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    NO_FEASIBLE_CANDIDATE = "NO_FEASIBLE_CANDIDATE"


@dataclass(frozen=True)
class OptimizationRecommendation:
    status: OptimizationRecommendationStatus
    recommended_scenario_id: str | None
    evaluations: tuple[CandidateEvaluation, ...]
    normalization_ranges: tuple[NormalizationRange, ...]
    reasons: tuple[RecommendationReason, ...]
    baseline_comparison_status: str
    baseline_comparisons: tuple[MetricComparison, ...]
    engineering_best_scenario_id: str | None = None
    lowest_cost_scenario_id: str | None = None
    policy: str | None = None
    economic_context_id: str | None = None
