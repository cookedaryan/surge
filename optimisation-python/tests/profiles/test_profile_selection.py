"""WP3-3: fixed reference ranges and the remove-a-loser invariant.

Exit evidence: no cohort min-max normalisation, and removing any non-winner leaves
every profile's winner unchanged. The invariant is checked over seeded random
cohorts against all four registry profiles, with values drawn from small sets so
that ties and tolerance-bucket collisions actually occur.
"""

import random
from types import SimpleNamespace
from typing import Any

from app.contracts.codes import MetricDirection, ProfilePolicyMode
from app.contracts.profiles import MetricTerm, ProfileDefinition, ProfileId
from app.optimisation.engineering_metric_models import CandidateEngineeringMetrics
from app.optimisation.profiles.registry import PLACEHOLDER_DEFINITIONS, definition_for
from app.optimisation.profiles.selection import (
    CandidateEvidence,
    ordering_key,
    rank_candidates,
    select_winner,
)
from app.presentation.explanation import explain_candidates


def _metrics(**overrides: float) -> CandidateEngineeringMetrics:
    values: dict[str, Any] = {
        "total_route_length_m": 1000.0,
        "total_traversal_cost": 1000.0,
        "affected_parcel_count": 1,
        "owner_interaction_count": 1,
        "road_crossing_count": 0,
        "soft_constraint_overlap_length_m": 0.0,
        "environmental_overlap_m2": 0.0,
        "physical_pole_count": 10,
        "total_active_loss_mw": 0.1,
        "maximum_loading_percent": 50.0,
        "voltage_margin_pu": 0.03,
        "affected_parcel_row_area_m2": 0.0,
    }
    values.update(overrides)
    return CandidateEngineeringMetrics(**values)


def _evidence(
    candidate_id: str,
    *,
    eligible: bool = True,
    lifecycle_cost: float | None = 1_000_000.0,
    **metrics: float,
) -> CandidateEvidence:
    return CandidateEvidence(
        candidate_id=candidate_id,
        eligible=eligible,
        metrics=_metrics(**metrics),
        lifecycle_cost=lifecycle_cost,
    )


def _profile(profile_id: ProfileId) -> ProfileDefinition:
    definition = definition_for(profile_id.value, "1")
    assert definition is not None
    return definition


# --- The exit evidence: remove-a-loser --------------------------------------------


def _random_cohort(rng: random.Random) -> list[CandidateEvidence]:
    # Small value sets on purpose: equal values and shared tolerance buckets are
    # where an order-dependent implementation would show itself.
    cohort = []
    for index in range(rng.randint(2, 7)):
        cohort.append(
            CandidateEvidence(
                candidate_id=f"C{index}",
                eligible=rng.random() < 0.85,
                lifecycle_cost=rng.choice([None, 1e6, 2e6, 2e6, 3e6]),
                metrics=_metrics(
                    affected_parcel_row_area_m2=rng.choice([0, 20, 24, 26, 60, 110]),
                    affected_parcel_count=rng.choice([0, 1, 2, 3]),
                    owner_interaction_count=rng.choice([0, 1, 2]),
                    environmental_overlap_m2=rng.choice([0, 100, 200, 200]),
                    soft_constraint_overlap_length_m=rng.choice([0, 50, 100]),
                    total_route_length_m=rng.choice([900, 1000, 1000, 1100]),
                    total_traversal_cost=rng.choice([900, 1000, 1100]),
                    physical_pole_count=rng.choice([9, 10, 11]),
                    total_active_loss_mw=rng.choice([0.1, 0.2]),
                    maximum_loading_percent=rng.choice([40, 50, 60]),
                    voltage_margin_pu=rng.choice([0.02, 0.03, 0.04]),
                ),
            )
        )
    return cohort


def test_removing_any_non_winner_leaves_every_profiles_winner_unchanged() -> None:
    rng = random.Random(20260922)
    removals_checked = 0
    winners_seen: set[tuple[str, str]] = set()

    for _ in range(400):
        cohort = _random_cohort(rng)
        for definition in PLACEHOLDER_DEFINITIONS.definitions:
            winner = select_winner(cohort, definition)
            if winner is None:
                continue
            winners_seen.add((definition.profile_id.value, winner))
            for loser in cohort:
                if loser.candidate_id == winner:
                    continue
                remaining = [item for item in cohort if item is not loser]
                assert select_winner(remaining, definition) == winner, (
                    definition.profile_id.value,
                    loser.candidate_id,
                )
                removals_checked += 1

    # Guard against a vacuous pass: the loop must actually exercise removals, and
    # winners must vary across profiles and cohorts rather than being one constant.
    assert removals_checked > 3000
    assert len({profile for profile, _ in winners_seen}) == 4
    assert len({winner for _, winner in winners_seen}) >= 5


def test_the_full_ranking_of_survivors_is_unchanged_by_a_removal() -> None:
    # Stronger than the exit evidence: not only the winner, but the relative order
    # of every surviving candidate is independent of who else is present.
    rng = random.Random(7)
    for _ in range(200):
        cohort = _random_cohort(rng)
        for definition in PLACEHOLDER_DEFINITIONS.definitions:
            full = rank_candidates(cohort, definition)
            order = sorted(full, key=full.__getitem__)
            for removed in cohort:
                remaining = [item for item in cohort if item is not removed]
                after = rank_candidates(remaining, definition)
                assert sorted(after, key=after.__getitem__) == [
                    cid for cid in order if cid != removed.candidate_id
                ]


# --- Why the tolerance band sits on a fixed grid -----------------------------------


def _band_anchored_to_cohort_minimum(
    cohort: list[CandidateEvidence], tolerance: float
) -> str:
    """The natural reading of "within the band of the best", kept only as a foil."""
    best = min(
        item.metrics.affected_parcel_row_area_m2 for item in cohort if item.metrics
    )
    band = [
        item
        for item in cohort
        if item.metrics and item.metrics.affected_parcel_row_area_m2 <= best + tolerance
    ]
    return min(
        band,
        key=lambda item: (
            item.metrics.affected_parcel_count if item.metrics else 0,
            item.candidate_id,
        ),
    ).candidate_id


def test_a_band_anchored_to_the_cohort_minimum_would_break_the_invariant() -> None:
    # X sets the best area; W is inside its band and wins on parcel count; Y is
    # just outside the band. Remove X and a cohort-anchored band moves up, admits
    # Y, and Y wins on parcel count: a loser's removal changed the winner.
    x = _evidence("X", affected_parcel_row_area_m2=100, affected_parcel_count=9)
    w = _evidence("W", affected_parcel_row_area_m2=120, affected_parcel_count=3)
    y = _evidence("Y", affected_parcel_row_area_m2=130, affected_parcel_count=1)

    assert _band_anchored_to_cohort_minimum([x, w, y], 25) == "W"
    assert _band_anchored_to_cohort_minimum([w, y], 25) == "Y"

    # The fixed grid holds: the same cohort, the same removal, the same winner.
    land = _profile(ProfileId.MINIMUM_LAND_IMPACT)
    assert select_winner([x, w, y], land) == "W"
    assert select_winner([w, y], land) == "W"


# --- No cohort min-max normalisation -----------------------------------------------


def test_two_candidates_keep_their_order_whatever_else_is_present() -> None:
    # A and B mirror each other on land and environment. The extremes stretch the
    # land range far more than the environment range, so under a cohort min-max
    # adding them would reweight the two metrics against each other and flip A and
    # B. Under fixed ranges nothing the cohort contains can move their order.
    a = _evidence("A", affected_parcel_row_area_m2=500, environmental_overlap_m2=900)
    b = _evidence("B", affected_parcel_row_area_m2=900, environmental_overlap_m2=500)
    extremes = [
        _evidence("LOW", affected_parcel_row_area_m2=0, environmental_overlap_m2=0),
        _evidence(
            "HIGH", affected_parcel_row_area_m2=49_000, environmental_overlap_m2=900
        ),
    ]
    for definition in PLACEHOLDER_DEFINITIONS.definitions:
        key_a = ordering_key(a, definition)
        key_b = ordering_key(b, definition)
        assert key_a is not None and key_b is not None
        a_first = key_a < key_b

        for cohort in ([a, b], [a, b, *extremes], [extremes[0], a, b]):
            ranks = rank_candidates(cohort, definition)
            assert (ranks["A"] < ranks["B"]) == a_first, definition.profile_id


def test_published_normalised_values_are_unmoved_by_other_candidates() -> None:
    def normalised_for_a(*others: Any) -> list[float | None]:
        explanation = explain_candidates(
            [_carrier(_evidence("A", affected_parcel_row_area_m2=500)), *others],
            _profile(ProfileId.BALANCED),
        )
        a = next(item for item in explanation.candidates if item.candidate_id == "A")
        return [item.normalised_value for item in a.contributions]

    alone = normalised_for_a()
    with_extremes = normalised_for_a(
        _carrier(_evidence("LOW", affected_parcel_row_area_m2=0)),
        _carrier(_evidence("HIGH", affected_parcel_row_area_m2=49_000)),
    )
    assert alone == with_extremes


# --- Lexicographic profiles --------------------------------------------------------


def test_inside_the_band_the_next_rank_decides() -> None:
    # Buckets of 25 m2 from zero: 101 and 124 share bucket 4.
    land = _profile(ProfileId.MINIMUM_LAND_IMPACT)
    more_area_fewer_parcels = _evidence(
        "A", affected_parcel_row_area_m2=124, affected_parcel_count=1
    )
    less_area_more_parcels = _evidence(
        "B", affected_parcel_row_area_m2=101, affected_parcel_count=5
    )
    assert select_winner([more_area_fewer_parcels, less_area_more_parcels], land) == "A"


def test_outside_the_band_the_primary_decides_however_the_next_rank_looks() -> None:
    land = _profile(ProfileId.MINIMUM_LAND_IMPACT)
    small = _evidence("A", affected_parcel_row_area_m2=40, affected_parcel_count=9)
    large = _evidence("B", affected_parcel_row_area_m2=90, affected_parcel_count=0)
    assert select_winner([small, large], land) == "A"


def test_the_fixed_grid_has_a_boundary_effect() -> None:
    # The documented cost of the invariant: 99 and 101 are 2 m2 apart but fall in
    # different 25 m2 buckets, so the primary decides between them.
    land = _profile(ProfileId.MINIMUM_LAND_IMPACT)
    below = _evidence("A", affected_parcel_row_area_m2=99, affected_parcel_count=9)
    above = _evidence("B", affected_parcel_row_area_m2=101, affected_parcel_count=0)
    assert select_winner([below, above], land) == "A"


def test_explanation_ranks_follow_lexicographic_selection_not_total_score() -> None:
    # A lexicographic winner can have the lower weighted total. The explanation
    # publishes the order the profile actually selected in.
    land = _profile(ProfileId.MINIMUM_LAND_IMPACT)
    a = _evidence(
        "A",
        affected_parcel_row_area_m2=40,
        affected_parcel_count=90,
        owner_interaction_count=90,
    )
    b = _evidence(
        "B",
        affected_parcel_row_area_m2=90,
        affected_parcel_count=0,
        owner_interaction_count=0,
    )
    explanation = explain_candidates([_carrier(a), _carrier(b)], land)
    by_id = {item.candidate_id: item for item in explanation.candidates}

    assert by_id["A"].rank == 1
    assert (by_id["A"].total_score or 0) < (by_id["B"].total_score or 0)


# --- Weighted profiles, tie-breaks and missing evidence -----------------------------


def test_a_weighted_profile_selects_the_highest_total() -> None:
    balanced = _profile(ProfileId.BALANCED)
    better = _evidence("B", affected_parcel_row_area_m2=0, environmental_overlap_m2=0)
    worse = _evidence(
        "A", affected_parcel_row_area_m2=40_000, environmental_overlap_m2=40_000
    )
    assert select_winner([worse, better], balanced) == "B"


def test_equal_totals_fall_to_the_definitions_tie_breaks_then_candidate_id() -> None:
    cost = _profile(ProfileId.MINIMUM_COST)
    # Same lifecycle cost; the tie-break is route length, shorter first.
    shorter = _evidence("Z", total_route_length_m=900)
    longer = _evidence("A", total_route_length_m=1100)
    assert select_winner([longer, shorter], cost) == "Z"
    # Same cost and same length: candidate ID, ascending.
    assert select_winner([_evidence("B"), _evidence("A")], cost) == "A"


def test_a_maximised_tie_break_prefers_the_higher_value() -> None:
    definition = ProfileDefinition(
        profile_id=ProfileId.BALANCED,
        version="1",
        policy_mode=ProfilePolicyMode.UNIFIED_ENGINEERING,
        terms=[
            MetricTerm(
                metric="total_route_length_m",
                direction=MetricDirection.MINIMISE,
                weight="1",
                reference_min="0",
                reference_max="100000",
            )
        ],
        tie_breaks=["voltage_margin_pu", "candidate_id"],
    )
    lower = _evidence("A", voltage_margin_pu=0.02)
    higher = _evidence("B", voltage_margin_pu=0.04)
    assert select_winner([lower, higher], definition) == "B"


def test_missing_evidence_never_wins() -> None:
    cost = _profile(ProfileId.MINIMUM_COST)
    # No lifecycle cost at all cannot mean "cheapest".
    unknown_cost = _evidence("A", lifecycle_cost=None)
    known_cost = _evidence("B", lifecycle_cost=900_000_000.0)
    assert select_winner([unknown_cost, known_cost], cost) == "B"


def test_an_ineligible_candidate_never_wins() -> None:
    balanced = _profile(ProfileId.BALANCED)
    ineligible_but_best = _evidence("A", eligible=False, affected_parcel_row_area_m2=0)
    eligible = _evidence("B", affected_parcel_row_area_m2=40_000)
    assert select_winner([ineligible_but_best, eligible], balanced) == "B"


def test_no_selectable_candidate_means_no_winner() -> None:
    cost = _profile(ProfileId.MINIMUM_COST)
    assert select_winner([_evidence("A", lifecycle_cost=None)], cost) is None
    assert select_winner([], cost) is None


def _carrier(evidence: CandidateEvidence) -> Any:
    return SimpleNamespace(
        scenario=SimpleNamespace(scenario_id=evidence.candidate_id),
        evaluation=SimpleNamespace(
            assessment=SimpleNamespace(
                eligible=evidence.eligible, metrics=evidence.metrics
            ),
            lifecycle_cost=evidence.lifecycle_cost,
        ),
    )
