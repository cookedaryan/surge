"""Domain models for SURGE-PY-017 candidate PNC scenario generation.

All models are frozen dataclasses.  Note that `ProjectPNCNetwork` contains
`dict` and `nx.Graph` fields which are not deeply immutable; callers must
treat those nested structures as read-only.

Fingerprint schema version
--------------------------
The topology fingerprint is prefixed with the schema version string
``v1:`` so future schema changes can be detected without silently producing
incompatible comparisons.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

# ---------------------------------------------------------------------------
# Re-export GroupingObjective from wtg_grouping so callers only need to
# import from this package.
# ---------------------------------------------------------------------------
from app.algorithms.wtg_grouping import GroupingObjective  # noqa: F401
from app.pnc.models import ProjectPNCNetwork

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ScenarioStrategy(StrEnum):
    """The named generation personality for a scenario candidate.

    BASELINE
        Runs the existing Surge pipeline without modification.  Provides a
        reference design identical to the pre-PY-017 output.

    ALTERNATIVE_GROUPING
        Uses a different KMeans ``random_state`` seed to produce a different
        MILP centroid initialisation, yielding a spatially different feeder
        grouping while still minimising turbine-to-centroid distance.

    BALANCED_FEEDERS
        Replaces the distance-minimisation MILP objective with an explicit
        balance objective that minimises the maximum absolute deviation of
        per-feeder WTG count from the ideal equal split (n / k).  The feeder
        capacity constraint is unchanged.

    LONG_EDGE_PENALTY
        Applies a non-uniform edge-weight transformation to the project graph
        before building the MST.  Edges longer than the mean are penalised by a
        convex amplification: ``w' = w * (1 + alpha * w / w_max)``.  This
        breaks the weight-scaling symmetry that would leave the MST unchanged,
        because edges are penalised by different *relative* amounts.  The
        grouping is identical to BASELINE.

    ALTERNATIVE_GROUPING_BALANCED
        Combines a different KMeans seed with the BALANCE_WTG_COUNT MILP
        objective.  Used for candidate_count 5 to provide a fifth distinct
        personality.
    """

    BASELINE = "baseline"
    ALTERNATIVE_GROUPING = "alternative_grouping"
    BALANCED_FEEDERS = "balanced_feeders"
    LONG_EDGE_PENALTY = "long_edge_penalty"
    ALTERNATIVE_GROUPING_BALANCED = "alternative_grouping_balanced"


class TopologyWeightProfile(StrEnum):
    """Controls how graph edge weights are transformed before MST construction.

    DEFAULT
        Edge weights are unchanged (Euclidean distance).

    LONG_EDGE_PENALTY
        Applies ``w' = w * (1 + alpha * w / w_max)`` where ``alpha`` is the
        topology_penalty from ``ScenarioParameters``.  Longer edges are
        penalised more severely than shorter ones, breaking the weight-scaling
        symmetry and potentially changing the MST.
    """

    DEFAULT = "default"
    LONG_EDGE_PENALTY = "long_edge_penalty"


class AttemptOutcome(StrEnum):
    """The result of one scenario generation attempt."""

    ACCEPTED = "accepted"
    DUPLICATE_TOPOLOGY = "duplicate_topology"
    ROUTING_FAILED = "routing_failed"
    ASSEMBLY_FAILED = "assembly_failed"
    GROUPING_FAILED = "grouping_failed"


# ---------------------------------------------------------------------------
# Parameter schedule
# ---------------------------------------------------------------------------

#: Stable parameter-set schedule covering candidate_count 1–5.
#: Each entry is (parameter_set_id, strategy, grouping_seed, objective,
#: topology_weight_profile, topology_penalty).
#: The schedule is fixed and documented; do not alter without incrementing
#: the fingerprint schema version.
PARAMETER_SCHEDULE: tuple[
    tuple[str, ScenarioStrategy, int, GroupingObjective, TopologyWeightProfile, float],
    ...,
] = (
    # SCN-001 — Baseline
    (
        "PS-001",
        ScenarioStrategy.BASELINE,
        42,
        GroupingObjective.MINIMIZE_DISTANCE,
        TopologyWeightProfile.DEFAULT,
        0.0,
    ),
    # SCN-002 — Alternative grouping (different KMeans seed)
    (
        "PS-002",
        ScenarioStrategy.ALTERNATIVE_GROUPING,
        17,
        GroupingObjective.MINIMIZE_DISTANCE,
        TopologyWeightProfile.DEFAULT,
        0.0,
    ),
    # SCN-003 — Balanced feeder WTG count
    (
        "PS-003",
        ScenarioStrategy.BALANCED_FEEDERS,
        42,
        GroupingObjective.BALANCE_WTG_COUNT,
        TopologyWeightProfile.DEFAULT,
        0.0,
    ),
    # SCN-004 — Long-edge penalised MST
    (
        "PS-004",
        ScenarioStrategy.LONG_EDGE_PENALTY,
        42,
        GroupingObjective.MINIMIZE_DISTANCE,
        TopologyWeightProfile.LONG_EDGE_PENALTY,
        2.0,  # alpha
    ),
    # SCN-005 — Alternative grouping seed + explicit balance objective
    (
        "PS-005",
        ScenarioStrategy.ALTERNATIVE_GROUPING_BALANCED,
        7,
        GroupingObjective.BALANCE_WTG_COUNT,
        TopologyWeightProfile.DEFAULT,
        0.0,
    ),
)


# ---------------------------------------------------------------------------
# Configuration model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioGenerationConfig:
    """Configuration for deterministic PNC scenario generation.

    Attributes
    ----------
    candidate_count:
        Number of distinct PNC candidates to attempt.  Must be an integer
        in the range [1, 5].  ``bool`` values are rejected.
    base_seed:
        Base seed for any deterministic random state not derived from the
        parameter schedule.  Must be a non-negative integer.
    project_id:
        Identifier stored on every returned ``ProjectPNCNetwork``.  Must be
        non-blank.

    Determinism guarantee
    ---------------------
    Given identical ``ScenarioGenerationConfig``, project data, and
    cost surface the generator always returns the same candidates in the
    same order with the same fingerprints.
    """

    candidate_count: int = 3
    base_seed: int = 42
    project_id: str = "PROJECT"

    def __post_init__(self) -> None:
        # Reject bool subclass — isinstance(True, int) is True in Python.
        if isinstance(self.candidate_count, bool):
            raise InvalidScenarioConfigError(
                "candidate_count must be an int, not bool"
            )
        if not isinstance(self.candidate_count, int):
            raise InvalidScenarioConfigError(
                "candidate_count must be an int, got "
                f"{type(self.candidate_count).__name__}"
            )
        if not (1 <= self.candidate_count <= 5):
            raise InvalidScenarioConfigError(
                f"candidate_count must be between 1 and 5, got {self.candidate_count}"
            )
        if isinstance(self.base_seed, bool):
            raise InvalidScenarioConfigError("base_seed must be an int, not bool")
        if not isinstance(self.base_seed, int):
            raise InvalidScenarioConfigError(
                f"base_seed must be an int, got {type(self.base_seed).__name__}"
            )
        if self.base_seed < 0:
            raise InvalidScenarioConfigError(
                f"base_seed must be non-negative, got {self.base_seed}"
            )
        if not self.project_id or not self.project_id.strip():
            raise InvalidScenarioConfigError("project_id must be non-blank")


# ---------------------------------------------------------------------------
# Scenario parameter model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioParameters:
    """Complete description of algorithm inputs for one candidate scenario.

    Every field maps directly to an input consumed by an existing algorithm
    boundary.  No field describes post-hoc network mutation.

    Attributes
    ----------
    parameter_set_id:
        Stable identifier from ``PARAMETER_SCHEDULE``, e.g. ``PS-001``.
    strategy:
        Named generation personality.
    grouping_seed:
        ``random_state`` passed to ``group_wtgs``.
    grouping_objective:
        ``objective`` passed to ``group_wtgs``.
    topology_weight_profile:
        Describes how graph edge weights are transformed before MST construction.
    topology_penalty:
        Alpha factor used when ``topology_weight_profile`` is
        ``LONG_EDGE_PENALTY``.  Zero means no penalty.  Must be finite and
        non-negative.
    effective_feeder_capacity_mw:
        The feeder capacity passed to ``group_wtgs``.  Always equals the
        caller-supplied project feeder capacity; scenario generation never
        silently changes this constraint.
    """

    parameter_set_id: str
    strategy: ScenarioStrategy
    grouping_seed: int
    grouping_objective: GroupingObjective
    topology_weight_profile: TopologyWeightProfile
    topology_penalty: float
    effective_feeder_capacity_mw: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.topology_penalty) or self.topology_penalty < 0.0:
            raise ValueError(
                f"topology_penalty must be finite and non-negative, "
                f"got {self.topology_penalty}"
            )
        if (
            not math.isfinite(self.effective_feeder_capacity_mw)
            or self.effective_feeder_capacity_mw <= 0.0
        ):
            raise ValueError(
                f"effective_feeder_capacity_mw must be positive and finite, "
                f"got {self.effective_feeder_capacity_mw}"
            )


# ---------------------------------------------------------------------------
# Scenario domain model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PNCScenario:
    """One candidate PNC network produced by the scenario generator.

    Structural metrics are validated in ``__post_init__`` against the
    authoritative values on ``network`` to prevent silent disagreement.

    Immutability note
    -----------------
    This dataclass is frozen, but ``network`` contains ``dict`` and
    ``nx.Graph`` fields that are not deeply immutable.  Treat those nested
    structures as read-only.

    Attributes
    ----------
    scenario_id:
        Stable human-readable identifier, e.g. ``SCN-001``.
    strategy:
        Named generation personality (matches ``parameters.strategy``).
    parameters:
        Full algorithm-input description for this candidate.
    network:
        The assembled ``ProjectPNCNetwork``.
    topology_fingerprint:
        Stable SHA-256 fingerprint of feeder memberships and MST topology
        edges (schema version ``v1:``).  Used for duplicate detection.
    comparison_group_id:
        Identifier shared by all candidates in one generation run.  Suitable
        for use as ``comparison_group_id`` in route-scoring later (PY-018).
    feeder_count:
        Copied from ``network.feeder_count`` and validated.
    wtg_count:
        Copied from ``network.wtg_count`` and validated.
    segment_count:
        Copied from ``network.segment_count`` and validated.
    total_route_length_m:
        Copied from ``network.total_route_length_m`` and validated.
    route_length_by_feeder:
        Per-feeder total cable length (metres).
    wtg_count_by_feeder:
        Per-feeder WTG count.
    """

    scenario_id: str
    strategy: str
    parameters: ScenarioParameters
    network: ProjectPNCNetwork
    topology_fingerprint: str
    comparison_group_id: str
    feeder_count: int
    wtg_count: int
    segment_count: int
    total_route_length_m: float
    route_length_by_feeder: dict[str, float]
    wtg_count_by_feeder: dict[str, int]

    def __post_init__(self) -> None:
        # Validate copied metrics against authoritative network values.
        n = self.network
        if self.feeder_count != n.feeder_count:
            raise ValueError(
                f"feeder_count {self.feeder_count} != "
                f"network.feeder_count {n.feeder_count}"
            )
        if self.wtg_count != n.wtg_count:
            raise ValueError(
                f"wtg_count {self.wtg_count} != network.wtg_count {n.wtg_count}"
            )
        if self.segment_count != n.segment_count:
            raise ValueError(
                f"segment_count {self.segment_count} != "
                f"network.segment_count {n.segment_count}"
            )
        if not math.isclose(
            self.total_route_length_m,
            n.total_route_length_m,
            rel_tol=1e-9,
            abs_tol=1e-6,
        ):
            raise ValueError(
                f"total_route_length_m {self.total_route_length_m} != "
                f"network.total_route_length_m {n.total_route_length_m}"
            )


# ---------------------------------------------------------------------------
# Attempt diagnostics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioAttempt:
    """Diagnostic record for one generation attempt.

    Attributes
    ----------
    parameter_set_id:
        Which parameter set was attempted.
    strategy:
        The strategy used.
    outcome:
        What happened (accepted, duplicate, routing_failed, etc.).
    topology_fingerprint:
        Fingerprint if topology was computed, else ``None``.
    detail:
        Human-readable explanation for non-accepted outcomes.
    """

    parameter_set_id: str
    strategy: str
    outcome: AttemptOutcome
    topology_fingerprint: str | None
    detail: str


# ---------------------------------------------------------------------------
# Generation result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioGenerationResult:
    """Complete result of one ``generate_pnc_scenarios`` call.

    Attributes
    ----------
    requested_candidate_count:
        The ``candidate_count`` from ``ScenarioGenerationConfig``.
    candidates:
        The accepted ``PNCScenario`` objects in deterministic order.
    attempts:
        Full diagnostic record of every attempt, including rejections.
        Preserves deterministic diagnostics without ranking candidates.
    comparison_group_id:
        Shared identifier for all candidates in this result.
    """

    requested_candidate_count: int
    candidates: tuple[PNCScenario, ...]
    attempts: tuple[ScenarioAttempt, ...]
    comparison_group_id: str


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ScenarioGenerationError(Exception):
    """Base class for scenario generation failures."""


class NoValidScenarioError(ScenarioGenerationError):
    """Raised when zero valid PNC candidates could be generated.

    This is an explicit generation failure distinct from the case where
    fewer candidates than requested were produced.
    """


class InvalidScenarioConfigError(ScenarioGenerationError):
    """Raised when ``ScenarioGenerationConfig`` validation fails."""
