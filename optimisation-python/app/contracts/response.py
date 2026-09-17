"""Additive V1 response blocks (C2).

Each block is optional on ``OptimisationResponse`` and is **absent** from the
JSON when not produced, because the endpoint serialises with
``response_model_exclude_none``. V0 responses therefore stay byte-identical.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.codes import (
    MetricDirection,
    RunTerminationReason,
    SizingBasis,
    SolverStatus,
)


class _Block(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class InstalledSegment(_Block):
    segment_id: str
    feeder_id: str
    initial_cable_type_id: str | None
    final_cable_type_id: str
    repaired: bool


class RepairActionRecord(_Block):
    segment_id: str
    original_cable_type_id: str
    upgraded_cable_type_id: str
    reason_code: str
    trigger_violation_type: str
    repair_iteration: int = Field(ge=0)


class DesignTruth(_Block):
    """What was actually installed for the recommended design (WP1)."""

    candidate_id: str
    candidate_sizing_basis: SizingBasis
    segments: list[InstalledSegment]
    repair_actions: list[RepairActionRecord]


class SearchCounts(_Block):
    """Count vocabulary; see ``contracts/reconcile.py`` for the equations."""

    requested_seeds: int = Field(ge=0)
    seed_evaluations: int = Field(ge=0)
    child_proposals: int = Field(ge=0)
    duplicates: int = Field(ge=0)
    structural_rejects: int = Field(ge=0)
    routed_proposals: int = Field(ge=0)
    routed_not_evaluated: int = Field(ge=0)
    cache_hits: int = Field(ge=0)
    child_evaluations: int = Field(ge=0)
    executed_evaluations: int = Field(ge=0)
    successful_evaluations: int = Field(ge=0)
    evaluation_failures: int = Field(ge=0)
    feasible: int = Field(ge=0)
    eligible: int = Field(ge=0)
    archive_size: int = Field(ge=0)
    rounds_completed: int = Field(ge=0)


class SearchCaps(_Block):
    seeds: int | None = Field(default=None, ge=0)
    children: int | None = Field(default=None, ge=0)
    archive: int | None = Field(default=None, ge=0)
    proposals: int | None = Field(default=None, ge=0)
    routed_proposals: int | None = Field(default=None, ge=0)
    evaluations: int | None = Field(default=None, ge=0)
    rounds: int | None = Field(default=None, ge=0)


class LineageEntry(_Block):
    candidate_id: str
    parent_id: str | None
    round: int = Field(ge=0)
    mutation_type: str | None
    discarded_duplicate_of: str | None = None


class SearchEvidence(_Block):
    """Public search provenance (WP4)."""

    enabled: bool
    caps: SearchCaps
    counts: SearchCounts
    lineage: list[LineageEntry]
    admission_deadline_s: float | None = Field(default=None, ge=0)
    admission_deadline_reached: bool = False
    routing_time_s: float | None = Field(default=None, ge=0)


class SolverRun(_Block):
    """One grouping MILP solve (WP4-6)."""

    objective: str
    feeder_count: int = Field(ge=1)
    status: SolverStatus
    wall_time_s: float = Field(ge=0)
    mip_gap: float | None = Field(default=None, ge=0)
    time_limit_s: float | None = Field(default=None, gt=0)
    node_limit: int | None = Field(default=None, gt=0)
    limit_reached: bool


class MetricContribution(_Block):
    metric: str
    direction: MetricDirection
    raw_value: float | None
    reference_min: float
    reference_max: float
    normalised_value: float | None
    weight: float = Field(ge=0)
    weighted_contribution: float | None


class GenerationPenalty(_Block):
    """A routing input, shown apart from ranking evidence."""

    name: str
    value: float
    unit: str


class CandidateExplanation(_Block):
    candidate_id: str
    eligible: bool
    rank: int | None = Field(default=None, ge=1)
    total_score: float | None
    contributions: list[MetricContribution]


class ScoringExplanation(_Block):
    """Why candidates ranked as they did (WP2-7)."""

    profile_id: str | None
    reference_ranges_version: str
    candidates: list[CandidateExplanation]
    generation_penalties: list[GenerationPenalty]


class EffectiveProfile(_Block):
    """The effective policy and flag state behind this response (WP3-7)."""

    profile_id: str | None
    profile_version: str | None
    policy_hash: str | None
    definition_hash: str | None
    metric_registry_version: str
    generation_settings_hash: str | None
    profiles_enabled: bool
    search_enabled: bool


class RunTermination(_Block):
    reason: RunTerminationReason
    message: str | None = None


# Response fields that legitimately differ between identical runs and are
# ignored by golden comparison. Paths use ``.`` for keys and ``[]`` for lists.
GOLDEN_COMPARISON_EXCLUSIONS: tuple[str, ...] = (
    "search_evidence.routing_time_s",
    "solver_runs[].wall_time_s",
)

# Additive blocks, in the order they appear on ``OptimisationResponse``.
ADDITIVE_RESPONSE_BLOCKS: tuple[str, ...] = (
    "design_truth",
    "search_evidence",
    "solver_runs",
    "scoring_explanation",
    "effective_profile",
    "termination",
)
