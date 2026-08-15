from dataclasses import dataclass, field
from enum import StrEnum


class SearchTerminationReason(StrEnum):
    SEARCH_DISABLED = "SEARCH_DISABLED"
    MAX_ROUNDS_REACHED = "MAX_ROUNDS_REACHED"
    EVALUATION_BUDGET_EXHAUSTED = "EVALUATION_BUDGET_EXHAUSTED"
    PROPOSAL_BUDGET_EXHAUSTED = "PROPOSAL_BUDGET_EXHAUSTED"
    NO_NEW_UNIQUE_CANDIDATES = "NO_NEW_UNIQUE_CANDIDATES"
    NO_FEASIBLE_SEARCH_CANDIDATES = "NO_FEASIBLE_SEARCH_CANDIDATES"


@dataclass(frozen=True)
class CandidateSearchConfig:
    """Configuration for deterministic candidate beam search.

    PY-032 explicitly defaults to False to preserve performance and V1 behavior.
    """

    enabled: bool = False
    max_rounds: int = 2
    beam_width: int = 3
    max_neighbors_per_parent: int = 5
    max_search_evaluations: int = 40
    max_candidate_proposals: int = 200

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("enabled must be a boolean")
        for name, value in (
            ("max_rounds", self.max_rounds),
            ("beam_width", self.beam_width),
            ("max_neighbors_per_parent", self.max_neighbors_per_parent),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")

        for name, value in (
            ("max_search_evaluations", self.max_search_evaluations),
            ("max_candidate_proposals", self.max_candidate_proposals),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True)
class SearchMutation:
    """Base class for search mutations."""

    operator: str = field(init=False)


@dataclass(frozen=True)
class FeederReassignmentMutation(SearchMutation):
    operator: str = field(init=False, default="FEEDER_REASSIGNMENT")
    wtg_id: str
    source_feeder_id: str
    target_feeder_id: str


@dataclass(frozen=True)
class FeederSwapMutation(SearchMutation):
    operator: str = field(init=False, default="FEEDER_SWAP")
    wtg_id_1: str
    feeder_id_1: str
    wtg_id_2: str
    feeder_id_2: str


@dataclass(frozen=True)
class EdgeReconnectMutation(SearchMutation):
    operator: str = field(init=False, default="EDGE_RECONNECT")
    feeder_id: str
    removed_edge: tuple[str, str]
    added_edge: tuple[str, str]


@dataclass(frozen=True)
class CandidateLineage:
    """Records the mutation path that generated a candidate."""

    parent_scenario_id: str
    search_round: int
    mutation: SearchMutation


@dataclass(frozen=True)
class CandidateSearchStatistics:
    """Statistics for the candidate search process."""

    proposed_count: int
    unique_count: int
    duplicate_count: int
    structural_rejection_count: int
    evaluation_cache_hit_count: int
    search_evaluations_used: int
    feasible_count: int
    failure_count: int
    search_evaluation_budget: int
    proposed_candidate_budget: int
    termination_reason: SearchTerminationReason


@dataclass(frozen=True)
class CandidateSearchResult:
    """Evidence from the search process."""

    rounds_completed: int
    statistics: CandidateSearchStatistics
    initial_best_scenario_id: str | None
    final_best_scenario_id: str | None
    initial_route_length_m: float | None
    final_route_length_m: float | None
    initial_lifecycle_cost: float | None
    final_lifecycle_cost: float | None

    @property
    def designs_generated(self) -> int:
        """Backward-compatible alias for the proposal count."""
        return self.statistics.proposed_count

    @property
    def duplicate_designs_skipped(self) -> int:
        """Backward-compatible alias for duplicate proposals."""
        return self.statistics.duplicate_count

    @property
    def candidates_evaluated(self) -> int:
        """Count candidates served by evaluation or exact cache reuse."""
        return (
            self.statistics.search_evaluations_used
            + self.statistics.evaluation_cache_hit_count
        )

    @property
    def candidates_failed(self) -> int:
        """Backward-compatible alias for failed search candidates."""
        return self.statistics.failure_count
