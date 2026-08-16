from dataclasses import dataclass, field


@dataclass(frozen=True)
class CandidateSearchConfig:
    """Configuration for deterministic candidate beam search.

    PY-032 explicitly defaults to False to preserve performance and V1 behavior.
    """

    enabled: bool = False
    max_rounds: int = 2
    beam_width: int = 3
    max_neighbors_per_parent: int = 5

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
class CandidateSearchResult:
    """Evidence from the search process."""

    rounds_completed: int
    designs_generated: int
    duplicate_designs_skipped: int
    candidates_evaluated: int
    candidates_failed: int
    initial_best_scenario_id: str | None
    final_best_scenario_id: str | None
    initial_route_length_m: float | None
    final_route_length_m: float | None
    initial_lifecycle_cost: float | None
    final_lifecycle_cost: float | None
