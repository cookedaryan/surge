"""Immutable domain models for the PY-036 Decision Report."""

import datetime
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from app.algorithms.pole_micro_siting import PoleMicroSitingMove
from app.optimisation.search_models import (
    CandidateSearchStatistics,
    SearchMutation,
    SearchTerminationReason,
)
from app.optimisation.workflow_models import WorkflowFailureCode, WorkflowStage


class DecisionReportStatus(StrEnum):
    SUCCESS = "SUCCESS"
    NO_FEASIBLE_CANDIDATE = "NO_FEASIBLE_CANDIDATE"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class ReportProvenance:
    engineering_fingerprint: str
    economic_fingerprint: str
    catalogue_id: str | None
    catalogue_version: str | None
    cost_model_version: str | None
    search_enabled: bool
    micro_siting_enabled: bool
    report_schema_version: str = "1.0.0"


@dataclass(frozen=True)
class CandidateReference:
    candidate_id: str
    candidate_signature: str
    parent_candidate_id: str | None
    search_round: int
    mutation: SearchMutation | None


class MetricDirection(StrEnum):
    LOWER_IS_BETTER = "LOWER_IS_BETTER"
    HIGHER_IS_BETTER = "HIGHER_IS_BETTER"
    TARGET_IS_BETTER = "TARGET_IS_BETTER"
    INFORMATIONAL = "INFORMATIONAL"


class ComparisonOutcome(StrEnum):
    BETTER = "BETTER"
    WORSE = "WORSE"
    EQUAL = "EQUAL"


@dataclass(frozen=True)
class MetricDelta:
    metric: str
    recommended_value: float | int | Decimal | None
    alternative_value: float | int | Decimal | None
    absolute_delta: float | int | Decimal | None
    relative_delta: float | None
    preferred_direction: MetricDirection
    outcome: ComparisonOutcome | None
    unit: str | None = None


@dataclass(frozen=True)
class PhysicalSummary:
    total_route_length_m: float
    segment_count: int


@dataclass(frozen=True)
class ElectricalSummary:
    feasible: bool
    total_active_loss_mw: float | None
    maximum_loading_percent: float | None
    minimum_voltage_pu: float | None
    maximum_voltage_pu: float | None
    violation_count: int | None


@dataclass(frozen=True)
class SpatialSummary:
    road_crossing_count: int
    soft_constraint_overlap_length_m: float
    hard_exclusion_violation_count: int


@dataclass(frozen=True)
class LandDecisionSummary:
    affected_parcels: int
    unique_owners: int
    owner_interactions: int
    # Future: explicit parcel buy/lease/reroute decisions


@dataclass(frozen=True)
class PoleSummary:
    total_poles: int
    terminal_poles: int
    angle_poles: int
    intermediate_poles: int
    junction_poles: int
    moved_poles: int
    total_movement_m: float
    micro_siting_moves: tuple[PoleMicroSitingMove, ...] = ()


@dataclass(frozen=True)
class EconomicsSummary:
    lifecycle_cost: Decimal | None
    conductor_capex: Decimal | None
    pole_capex: Decimal | None
    land_capex: Decimal | None
    present_value_opex: Decimal | None
    currency: str | None


@dataclass(frozen=True)
class ScoreSummary:
    engineering_benefit_score: float | None
    economic_benefit_score: float | None
    final_benefit_score: float | None
    rank: int | None


@dataclass(frozen=True)
class RecommendationSummary:
    reference: CandidateReference
    physical: PhysicalSummary
    electrical: ElectricalSummary
    spatial: SpatialSummary
    land: LandDecisionSummary
    poles: PoleSummary | None
    economics: EconomicsSummary
    scores: ScoreSummary


class AlternativeStatus(StrEnum):
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    EVALUATION_FAILED = "EVALUATION_FAILED"


@dataclass(frozen=True)
class AlternativeSummary:
    reference: CandidateReference
    status: AlternativeStatus
    physical: PhysicalSummary | None
    electrical: ElectricalSummary | None
    spatial: SpatialSummary | None
    land: LandDecisionSummary | None
    poles: PoleSummary | None
    economics: EconomicsSummary | None
    scores: ScoreSummary | None
    comparisons: tuple[MetricDelta, ...] = ()


@dataclass(frozen=True)
class RejectedCandidate:
    reference: CandidateReference
    failure_code: WorkflowFailureCode | str
    failure_stage: WorkflowStage | str
    message: str


@dataclass(frozen=True)
class DecisionFactor:
    factor: str
    category: str
    comparison: MetricDelta
    significance: str  # e.g., "high", "medium", "low"


@dataclass(frozen=True)
class RecommendationReasoning:
    advantages: tuple[DecisionFactor, ...] = ()
    disadvantages: tuple[DecisionFactor, ...] = ()
    tradeoffs: tuple[DecisionFactor, ...] = ()
    alternative_decisions: tuple[str, ...] = ()


@dataclass(frozen=True)
class OptimizationEvidence:
    search_statistics: CandidateSearchStatistics | None
    termination_reason: SearchTerminationReason | None
    winner_lineage: tuple[CandidateReference, ...] = ()


@dataclass(frozen=True)
class ReportWarning:
    code: str
    message: str


@dataclass(frozen=True)
class DecisionReport:
    schema_version: str
    status: DecisionReportStatus
    project_id: str
    optimisation_run_id: str
    provenance: ReportProvenance
    recommendation: RecommendationSummary | None
    alternatives: tuple[AlternativeSummary, ...] = ()
    rejected_candidates: tuple[RejectedCandidate, ...] = ()
    reasoning: RecommendationReasoning | None = None
    optimization_evidence: OptimizationEvidence | None = None
    warnings: tuple[ReportWarning, ...] = ()
