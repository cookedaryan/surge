import math
from dataclasses import dataclass
from typing import Literal

CriterionName = Literal[
    "length",
    "traversal_cost",
    "row_area",
    "parcel_count",
    "road_crossings",
    "environmental_impact",
    "pole_count",
]


@dataclass(frozen=True)
class RouteScoringWeights:
    length: float
    traversal_cost: float
    row_area: float
    parcel_count: float
    road_crossings: float
    environmental_impact: float
    pole_count: float

    def __post_init__(self) -> None:
        weights = [
            self.length,
            self.traversal_cost,
            self.row_area,
            self.parcel_count,
            self.road_crossings,
            self.environmental_impact,
            self.pole_count,
        ]

        if any(not math.isfinite(w) for w in weights):
            raise ValueError("All scoring weights must be finite")
        if any(w < 0.0 for w in weights):
            raise ValueError("All scoring weights must be non-negative")

        total_weight = math.fsum(weights)
        if not math.isclose(total_weight, 1.0, rel_tol=1e-9, abs_tol=1e-9):
            raise ValueError(f"Scoring weights must sum to 1.0, got {total_weight}")


@dataclass(frozen=True)
class NetworkCandidateMetrics:
    candidate_id: str
    comparison_group_id: str

    total_length_m: float
    traversal_cost: float
    unique_row_footprint_area_m2: float
    affected_parcel_ids: frozenset[str]
    road_crossing_count: int
    unique_environmental_overlap_m2: float
    generated_pole_record_count: int

    hard_violation_ids: frozenset[str]

    @property
    def unique_parcel_count(self) -> int:
        return len(self.affected_parcel_ids)

    @property
    def hard_violation_count(self) -> int:
        return len(self.hard_violation_ids)


@dataclass(frozen=True)
class NormalizationRange:
    criterion: CriterionName
    minimum: float
    maximum: float
    constant: bool


@dataclass(frozen=True)
class CriterionScore:
    criterion: CriterionName
    raw_value: float
    normalized_value: float
    weight: float
    weighted_score: float


@dataclass(frozen=True)
class CandidateScore:
    candidate_id: str
    feasible: bool
    rejection_reasons: tuple[str, ...]
    criteria: tuple[CriterionScore, ...]
    total_score: float | None


@dataclass(frozen=True)
class RouteScoringResult:
    comparison_group_id: str
    weights: RouteScoringWeights
    normalization_ranges: tuple[NormalizationRange, ...]
    scores: tuple[CandidateScore, ...]
    ranked_candidate_ids: tuple[str, ...]
    best_candidate_id: str | None


def evaluate_network_candidates(
    candidates: tuple[NetworkCandidateMetrics, ...],
    weights: RouteScoringWeights,
) -> RouteScoringResult:
    """
    Score, normalize, and rank comparable network-level route candidates.
    This is a standalone analytical method. It relies on the caller providing 
    deduplicated footprint areas and unique parcel identities.
    """
    if not candidates:
        raise ValueError("Must provide at least one candidate for scoring")

    comparison_group_id = candidates[0].comparison_group_id
    if any(c.comparison_group_id != comparison_group_id for c in candidates):
        raise ValueError("Cannot score candidates from mixed comparison groups")

    candidate_ids = set()
    for c in candidates:
        if not c.candidate_id or not c.candidate_id.strip():
            raise ValueError("Candidate ID cannot be blank or whitespace-only")
        if c.candidate_id in candidate_ids:
            raise ValueError(f"Duplicate candidate ID: {c.candidate_id}")
        candidate_ids.add(c.candidate_id)
        
        if not c.comparison_group_id or not c.comparison_group_id.strip():
            raise ValueError("Comparison group ID cannot be blank or whitespace-only")
        
        floats = [
            c.total_length_m,
            c.traversal_cost,
            c.unique_row_footprint_area_m2,
            c.unique_environmental_overlap_m2,
        ]
        if any(not math.isfinite(val) for val in floats):
            raise ValueError("All candidate floating-point metrics must be finite")
        if any(val < 0.0 for val in floats):
            raise ValueError(
                "All candidate floating-point metrics must be non-negative"
            )
            
        counts = [
            c.road_crossing_count,
            c.generated_pole_record_count,
        ]
        if any(not isinstance(val, int) for val in counts):
            raise ValueError("All candidate count metrics must be integers")
        if any(val < 0 for val in counts):
            raise ValueError("All candidate count metrics must be non-negative")

    # Build candidate lookup dictionary for ranking
    candidate_dict = {c.candidate_id: c for c in candidates}

    # Step 1: Feasibility determination
    feasible_candidates: list[NetworkCandidateMetrics] = []
    rejection_map: dict[str, tuple[str, ...]] = {}

    for candidate in candidates:
        if candidate.hard_violation_count > 0:
            reasons = tuple(
                f"Hard violation: {vid}" for vid in sorted(candidate.hard_violation_ids)
            )
            rejection_map[candidate.candidate_id] = reasons
        else:
            feasible_candidates.append(candidate)
            rejection_map[candidate.candidate_id] = ()

    # Step 2: Calculate normalization bounds on feasible candidates only
    ranges_dict: dict[CriterionName, NormalizationRange] = {}
    criteria_keys: list[CriterionName] = [
        "length",
        "traversal_cost",
        "row_area",
        "parcel_count",
        "road_crossings",
        "environmental_impact",
        "pole_count",
    ]

    def get_raw_val(c: NetworkCandidateMetrics, crit: CriterionName) -> float:
        if crit == "length":
            return c.total_length_m
        elif crit == "traversal_cost":
            return c.traversal_cost
        elif crit == "row_area":
            return c.unique_row_footprint_area_m2
        elif crit == "parcel_count":
            return float(c.unique_parcel_count)
        elif crit == "road_crossings":
            return float(c.road_crossing_count)
        elif crit == "environmental_impact":
            return c.unique_environmental_overlap_m2
        elif crit == "pole_count":
            return float(c.generated_pole_record_count)
        raise ValueError(f"Unknown criterion {crit}")

    def get_weight(crit: CriterionName) -> float:
        if crit == "length":
            return weights.length
        elif crit == "traversal_cost":
            return weights.traversal_cost
        elif crit == "row_area":
            return weights.row_area
        elif crit == "parcel_count":
            return weights.parcel_count
        elif crit == "road_crossings":
            return weights.road_crossings
        elif crit == "environmental_impact":
            return weights.environmental_impact
        elif crit == "pole_count":
            return weights.pole_count
        raise ValueError(f"Unknown criterion {crit}")

    if feasible_candidates:
        for crit in criteria_keys:
            vals = [get_raw_val(c, crit) for c in feasible_candidates]
            min_val = min(vals)
            max_val = max(vals)
            constant = min_val == max_val
            ranges_dict[crit] = NormalizationRange(
                criterion=crit,
                minimum=min_val,
                maximum=max_val,
                constant=constant,
            )

    # Step 3: Score candidates
    candidate_scores: list[CandidateScore] = []
    feasible_ids = {fc.candidate_id for fc in feasible_candidates}
    for candidate in candidates:
        if candidate.candidate_id not in feasible_ids:
            # Infeasible
            infeasible_c_scores: list[CriterionScore] = []
            for crit in criteria_keys:
                raw = get_raw_val(candidate, crit)
                w = get_weight(crit)
                infeasible_c_scores.append(
                    CriterionScore(
                        criterion=crit,
                        raw_value=raw,
                        normalized_value=0.0,
                        weight=w,
                        weighted_score=0.0,
                    )
                )
            
            candidate_scores.append(
                CandidateScore(
                    candidate_id=candidate.candidate_id,
                    feasible=False,
                    rejection_reasons=rejection_map[candidate.candidate_id],
                    criteria=tuple(infeasible_c_scores),
                    total_score=None,
                )
            )
            continue

        # Feasible
        c_scores: list[CriterionScore] = []
        weighted_scores: list[float] = []

        for crit in criteria_keys:
            raw = get_raw_val(candidate, crit)
            w = get_weight(crit)
            norm_range = ranges_dict[crit]

            if norm_range.constant:
                norm_val = 0.0
            else:
                norm_val = (raw - norm_range.minimum) / (
                    norm_range.maximum - norm_range.minimum
                )
                
            # Clamp in case of floating point drift near boundaries
            norm_val = max(0.0, min(1.0, norm_val))

            weighted = w * norm_val
            weighted_scores.append(weighted)

            c_scores.append(
                CriterionScore(
                    criterion=crit,
                    raw_value=raw,
                    normalized_value=norm_val,
                    weight=w,
                    weighted_score=weighted,
                )
            )

        total = math.fsum(weighted_scores)
        # Ensure exact bounding
        total = max(0.0, min(1.0, total))
        
        candidate_scores.append(
            CandidateScore(
                candidate_id=candidate.candidate_id,
                feasible=True,
                rejection_reasons=(),
                criteria=tuple(c_scores),
                total_score=total,
            )
        )

    # Step 4: Deterministic ranking
    feasible_scores = [cs for cs in candidate_scores if cs.feasible]
    
    # We also need length for tie-breaking. We can fetch it back from the dictionary
    def sort_key(cs: CandidateScore) -> tuple[float, float, str]:
        # total_score is not None for feasible scores
        c = candidate_dict[cs.candidate_id]
        return (cs.total_score, c.total_length_m, cs.candidate_id) # type: ignore

    feasible_scores.sort(key=sort_key)
    
    ranked_ids = tuple(cs.candidate_id for cs in feasible_scores)
    best_id = ranked_ids[0] if ranked_ids else None

    # Normalization ranges shouldn't be empty, but if no feasible 
    # candidates exist, it's empty
    ranges_tuple = tuple(ranges_dict[k] for k in criteria_keys if k in ranges_dict)

    return RouteScoringResult(
        comparison_group_id=comparison_group_id,
        weights=weights,
        normalization_ranges=ranges_tuple,
        scores=tuple(candidate_scores),
        ranked_candidate_ids=ranked_ids,
        best_candidate_id=best_id,
    )
