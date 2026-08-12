"""Domain models for deterministic multi-objective electrical + physical scoring."""

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from app.electrical.load_flow.models import LoadFlowNetworkResult
from app.optimisation.scenario_models import PNCScenario


class ScoringMetric(StrEnum):
    ROUTE_LENGTH = "ROUTE_LENGTH"
    ACTIVE_LOSS = "ACTIVE_LOSS"
    CABLE_LOADING = "CABLE_LOADING"
    VOLTAGE_MARGIN = "VOLTAGE_MARGIN"


@dataclass(frozen=True)
class CandidateScoringConfig:
    route_length_weight: float
    electrical_loss_weight: float
    cable_loading_weight: float
    voltage_margin_weight: float

    def __post_init__(self) -> None:
        weights = [
            self.route_length_weight,
            self.electrical_loss_weight,
            self.cable_loading_weight,
            self.voltage_margin_weight,
        ]
        if any(isinstance(w, bool) for w in weights):
            raise ValueError("Weights must be numbers, not booleans")
        if any(not math.isfinite(w) for w in weights):
            raise ValueError("All scoring weights must be finite")
        if any(w < 0.0 for w in weights):
            raise ValueError("All scoring weights must be non-negative")

        total_weight = math.fsum(weights)
        if not math.isclose(total_weight, 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(f"Scoring weights must sum to 1.0, got {total_weight}")


@dataclass(frozen=True)
class ElectricallyEvaluatedScenario:
    """Atomic input binding a PNC scenario to its load flow result and context."""

    scenario: PNCScenario
    load_flow_result: LoadFlowNetworkResult
    electrical_context_id: str


@dataclass(frozen=True)
class CandidateMetrics:
    total_route_length_m: float
    total_active_loss_mw: float
    maximum_loading_percent: float
    voltage_margin_pu: float

    def __post_init__(self) -> None:
        vals = [
            self.total_route_length_m,
            self.total_active_loss_mw,
            self.maximum_loading_percent,
            self.voltage_margin_pu,
        ]
        if any(not math.isfinite(v) for v in vals):
            raise ValueError("Candidate metrics must be finite floats")


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
class MetricComparison:
    metric: ScoringMetric
    recommended_value: float
    baseline_value: float
    absolute_delta: float
    relative_delta_percent: float | None
    preferred_direction: Literal["higher", "lower"]


class DisqualificationCode(StrEnum):
    LOAD_FLOW_NOT_CONVERGED = "LOAD_FLOW_NOT_CONVERGED"
    ELECTRICAL_VIOLATION = "ELECTRICAL_VIOLATION"
    ELECTRICAL_METRICS_MISSING = "ELECTRICAL_METRICS_MISSING"
    RESULT_NOT_FINITE = "RESULT_NOT_FINITE"
    COMPARISON_CONTEXT_MISMATCH = "COMPARISON_CONTEXT_MISMATCH"
    TOPOLOGY_MISMATCH = "TOPOLOGY_MISMATCH"


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
    metrics: CandidateMetrics | None


@dataclass(frozen=True)
class CandidateEvaluation:
    assessment: CandidateAssessment
    metric_scores: tuple[MetricScore, ...]
    total_benefit_score: float | None
    rank: int | None


class RecommendationReasonCode(StrEnum):
    ONLY_ELIGIBLE_CANDIDATE = "ONLY_ELIGIBLE_CANDIDATE"
    HIGHEST_TOTAL_BENEFIT = "HIGHEST_TOTAL_BENEFIT"
    SHORTEST_ROUTE = "SHORTEST_ROUTE"
    LOWEST_ACTIVE_LOSS = "LOWEST_ACTIVE_LOSS"
    LOWEST_CABLE_LOADING = "LOWEST_CABLE_LOADING"
    BEST_VOLTAGE_MARGIN = "BEST_VOLTAGE_MARGIN"
    BASELINE_IMPROVEMENT = "BASELINE_IMPROVEMENT"


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
