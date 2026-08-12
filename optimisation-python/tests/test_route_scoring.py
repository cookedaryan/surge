import math

import pytest

from app.algorithms.route_scoring import (
    NetworkCandidateMetrics,
    RouteScoringWeights,
    evaluate_network_candidates,
)


def default_weights(**overrides: float) -> RouteScoringWeights:
    w = {
        "length": 0.2,
        "traversal_cost": 0.1,
        "row_area": 0.1,
        "parcel_count": 0.2,
        "road_crossings": 0.1,
        "environmental_impact": 0.1,
        "pole_count": 0.2,
    }
    w.update(overrides)
    return RouteScoringWeights(**w)


def make_candidate(
    candidate_id: str,
    comparison_group_id: str = "group1",
    total_length_m: float = 1000.0,
    traversal_cost: float = 1000.0,
    unique_row_footprint_area_m2: float = 20000.0,
    affected_parcel_ids: frozenset[str] = frozenset(["p1", "p2"]),
    road_crossing_count: int = 1,
    unique_environmental_overlap_m2: float = 0.0,
    generated_pole_record_count: int = 20,
    hard_violation_ids: frozenset[str] = frozenset(),
) -> NetworkCandidateMetrics:
    return NetworkCandidateMetrics(
        candidate_id=candidate_id,
        comparison_group_id=comparison_group_id,
        total_length_m=total_length_m,
        traversal_cost=traversal_cost,
        unique_row_footprint_area_m2=unique_row_footprint_area_m2,
        affected_parcel_ids=affected_parcel_ids,
        road_crossing_count=road_crossing_count,
        unique_environmental_overlap_m2=unique_environmental_overlap_m2,
        generated_pole_record_count=generated_pole_record_count,
        hard_violation_ids=hard_violation_ids,
    )


def test_weights_sum_to_one() -> None:
    w = default_weights()
    assert math.isclose(
        sum([
            w.length,
            w.traversal_cost,
            w.row_area,
            w.parcel_count,
            w.road_crossings,
            w.environmental_impact,
            w.pole_count,
        ]),
        1.0,
    )


def test_negative_weight_rejected() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        default_weights(length=-0.1, traversal_cost=0.4)


def test_nan_and_infinite_weights_rejected() -> None:
    with pytest.raises(ValueError, match="finite"):
        default_weights(length=float("nan"), traversal_cost=0.3)
    with pytest.raises(ValueError, match="finite"):
        default_weights(length=float("inf"), traversal_cost=-float("inf"))


def test_all_zero_weights_rejected() -> None:
    with pytest.raises(ValueError, match="must sum to 1.0"):
        RouteScoringWeights(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def test_slight_weight_sum_tolerance_behavior() -> None:
    # 1.0000000000000002 is close enough (rel_tol=1e-9)
    w = RouteScoringWeights(0.2, 0.2, 0.2, 0.1, 0.1, 0.1, 0.10000000000000002)
    assert w is not None

    # but 1.00000001 is too far outside 1e-9
    with pytest.raises(ValueError, match="must sum to 1.0"):
        RouteScoringWeights(0.2, 0.2, 0.2, 0.1, 0.1, 0.1, 0.10000001)


def test_empty_candidate_collection() -> None:
    with pytest.raises(ValueError, match="at least one candidate"):
        evaluate_network_candidates((), default_weights())


def test_duplicate_candidate_ids() -> None:
    c1 = make_candidate("A")
    c2 = make_candidate("A")
    with pytest.raises(ValueError, match="Duplicate candidate ID: A"):
        evaluate_network_candidates((c1, c2), default_weights())


def test_blank_candidate_id() -> None:
    c1 = make_candidate("")
    c2 = make_candidate("   ")
    with pytest.raises(ValueError, match="blank or whitespace-only"):
        evaluate_network_candidates((c1,), default_weights())
    with pytest.raises(ValueError, match="blank or whitespace-only"):
        evaluate_network_candidates((c2,), default_weights())


def test_mixed_comparison_groups_rejected() -> None:
    c1 = make_candidate("A", comparison_group_id="g1")
    c2 = make_candidate("B", comparison_group_id="g2")
    c3 = make_candidate("C", comparison_group_id="   ")
    with pytest.raises(ValueError, match="mixed comparison groups"):
        evaluate_network_candidates((c1, c2), default_weights())
    with pytest.raises(ValueError, match="blank or whitespace-only"):
        evaluate_network_candidates((c3,), default_weights())


def test_negative_metrics_and_counts_rejected() -> None:
    c1 = make_candidate("A", total_length_m=-10.0)
    with pytest.raises(ValueError, match="non-negative"):
        evaluate_network_candidates((c1,), default_weights())

    c2 = make_candidate("B", road_crossing_count=-1)
    with pytest.raises(ValueError, match="non-negative"):
        evaluate_network_candidates((c2,), default_weights())


def test_nan_and_infinite_metrics_rejected() -> None:
    c1 = make_candidate("A", total_length_m=float("nan"))
    with pytest.raises(ValueError, match="finite"):
        evaluate_network_candidates((c1,), default_weights())


def test_fractional_counts_rejected() -> None:
    c1 = make_candidate("A", road_crossing_count=1.5) # type: ignore
    with pytest.raises(ValueError, match="must be integers"):
        evaluate_network_candidates((c1,), default_weights())


def test_one_feasible_candidate_scores_zero() -> None:
    c1 = make_candidate("A", total_length_m=1000.0)
    result = evaluate_network_candidates((c1,), default_weights())
    assert len(result.scores) == 1
    assert result.scores[0].total_score == 0.0


def test_normalization_between_zero_and_one() -> None:
    c1 = make_candidate("A", total_length_m=1000.0)
    c2 = make_candidate("B", total_length_m=2000.0)
    c3 = make_candidate("C", total_length_m=1500.0)
    
    # Weights for length=1.0, rest=0
    w = RouteScoringWeights(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    res = evaluate_network_candidates((c1, c2, c3), w)
    
    a_score = next(s for s in res.scores if s.candidate_id == "A")
    b_score = next(s for s in res.scores if s.candidate_id == "B")
    c_score = next(s for s in res.scores if s.candidate_id == "C")

    # Lower is better: A is min (0.0), B is max (1.0), C is mid (0.5)
    assert a_score.total_score == pytest.approx(0.0)
    assert b_score.total_score == pytest.approx(1.0)
    assert c_score.total_score == pytest.approx(0.5)


def test_equal_metric_values_normalize_safely() -> None:
    c1 = make_candidate("A", total_length_m=1000.0)
    c2 = make_candidate("B", total_length_m=1000.0)
    
    w = RouteScoringWeights(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    res = evaluate_network_candidates((c1, c2), w)
    
    assert res.scores[0].total_score == 0.0
    assert res.scores[1].total_score == 0.0
    assert res.normalization_ranges[0].constant is True


def test_constant_criterion_with_nonzero_weight() -> None:
    # All candidates have 1 road crossing. The normalized value should be 0,
    # so the weight for road_crossings (0.5) contributes 0 to the total score.
    c1 = make_candidate("A", total_length_m=1000.0, road_crossing_count=1)
    c2 = make_candidate("B", total_length_m=2000.0, road_crossing_count=1)
    
    w = RouteScoringWeights(0.5, 0.0, 0.0, 0.0, 0.5, 0.0, 0.0)
    res = evaluate_network_candidates((c1, c2), w)
    
    a = next(s for s in res.scores if s.candidate_id == "A")
    b = next(s for s in res.scores if s.candidate_id == "B")
    
    assert a.total_score == pytest.approx(0.0)
    assert b.total_score == pytest.approx(0.5)  # 0.5 * 1.0 (length) + 0.5 * 0.0 (roads)


def test_zero_weight_criterion() -> None:
    # A is much worse in row_area, but row_area weight is 0. 
    # Length weight is 1.0. A is better in length.
    c1 = make_candidate(
        "A", total_length_m=1000.0, unique_row_footprint_area_m2=999999.0
    )
    c2 = make_candidate(
        "B", total_length_m=2000.0, unique_row_footprint_area_m2=0.0
    )
    
    w = RouteScoringWeights(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    res = evaluate_network_candidates((c1, c2), w)
    
    assert res.best_candidate_id == "A"


def test_score_bounded_within_0_1() -> None:
    c1 = make_candidate("A", total_length_m=10.0, traversal_cost=10.0)
    c2 = make_candidate("B", total_length_m=20.0, traversal_cost=20.0)
    
    w = RouteScoringWeights(0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0)
    res = evaluate_network_candidates((c1, c2), w)
    
    for s in res.scores:
        assert s.total_score is not None
        assert 0.0 <= s.total_score <= 1.0


def test_weighted_score_calculated_correctly() -> None:
    c1 = make_candidate(
        "A", 
        total_length_m=1000.0, # min
        road_crossing_count=2, # max
    )
    c2 = make_candidate(
        "B", 
        total_length_m=2000.0, # max
        road_crossing_count=0, # min
    )
    w = RouteScoringWeights(0.7, 0.0, 0.0, 0.0, 0.3, 0.0, 0.0)
    res = evaluate_network_candidates((c1, c2), w)
    
    a = next(s for s in res.scores if s.candidate_id == "A")
    b = next(s for s in res.scores if s.candidate_id == "B")
    
    # A length norm = 0, road norm = 1.0 -> 0*0.7 + 1*0.3 = 0.3
    assert a.total_score == pytest.approx(0.3)
    # B length norm = 1, road norm = 0.0 -> 1*0.7 + 0*0.3 = 0.7
    assert b.total_score == pytest.approx(0.7)


def test_lower_length_scores_better() -> None:
    c1 = make_candidate("A", total_length_m=100.0)
    c2 = make_candidate("B", total_length_m=200.0)
    w = RouteScoringWeights(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert evaluate_network_candidates((c1, c2), w).best_candidate_id == "A"


def test_multiple_routes_normalized_together() -> None:
    c1 = make_candidate("A", total_length_m=100.0)
    c2 = make_candidate("B", total_length_m=200.0)
    c3 = make_candidate("C", total_length_m=300.0)
    w = RouteScoringWeights(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    res = evaluate_network_candidates((c1, c2, c3), w)
    
    b = next(s for s in res.scores if s.candidate_id == "B")
    # (200 - 100) / (300 - 100) = 0.5
    assert b.total_score == pytest.approx(0.5)


def test_adding_candidate_changes_relative_normalization() -> None:
    c1 = make_candidate("A", total_length_m=100.0)
    c2 = make_candidate("B", total_length_m=200.0)
    w = RouteScoringWeights(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    
    res_2 = evaluate_network_candidates((c1, c2), w)
    b_score_2 = next(s for s in res_2.scores if s.candidate_id == "B").total_score
    assert b_score_2 == pytest.approx(1.0)
    
    # Adding a worse candidate makes B look relatively better
    c3 = make_candidate("C", total_length_m=300.0)
    res_3 = evaluate_network_candidates((c1, c2, c3), w)
    b_score_3 = next(s for s in res_3.scores if s.candidate_id == "B").total_score
    assert b_score_3 == pytest.approx(0.5)


def test_hard_violation_marks_route_infeasible() -> None:
    c1 = make_candidate("A", hard_violation_ids=frozenset(["hv1"]))
    res = evaluate_network_candidates((c1,), default_weights())
    assert res.scores[0].feasible is False
    assert res.scores[0].total_score is None


def test_infeasible_candidates_excluded_from_normalization_bounds() -> None:
    # A is feasible, length 100
    # B is infeasible, length 500 (this should not become the max for normalization)
    # C is feasible, length 200 (this should be the max)
    c1 = make_candidate("A", total_length_m=100.0)
    c2 = make_candidate("B", total_length_m=500.0, hard_violation_ids=frozenset(["v1"]))
    c3 = make_candidate("C", total_length_m=200.0)
    
    w = RouteScoringWeights(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    res = evaluate_network_candidates((c1, c2, c3), w)
    
    # Since C is the worst *feasible*, it should get score 1.0
    c_score = next(s for s in res.scores if s.candidate_id == "C")
    assert c_score.total_score == pytest.approx(1.0)


def test_extreme_infeasible_values_do_not_distort_feasible_scores() -> None:
    c1 = make_candidate("A", total_length_m=100.0)
    c2 = make_candidate("B", total_length_m=200.0)
    c_infeasible = make_candidate(
        "C", total_length_m=999999.0, hard_violation_ids=frozenset(["v"])
    )
    
    w = RouteScoringWeights(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    res = evaluate_network_candidates((c1, c2, c_infeasible), w)
    
    b_score = next(s for s in res.scores if s.candidate_id == "B")
    # If C distorted it, B would be near 0. But C is excluded, so B is the max (1.0).
    assert b_score.total_score == pytest.approx(1.0)


def test_all_candidates_infeasible() -> None:
    c1 = make_candidate("A", hard_violation_ids=frozenset(["v1"]))
    c2 = make_candidate("B", hard_violation_ids=frozenset(["v2"]))
    
    res = evaluate_network_candidates((c1, c2), default_weights())
    assert all(not s.feasible for s in res.scores)
    assert res.best_candidate_id is None
    assert res.ranked_candidate_ids == ()
    assert res.normalization_ranges == ()


def test_raw_metrics_preserved_for_infeasible_candidates() -> None:
    c1 = make_candidate("A", total_length_m=123.4, hard_violation_ids=frozenset(["v"]))
    res = evaluate_network_candidates((c1,), default_weights())
    
    # We should have criteria populated for telemetry, but marked infeasible
    assert not res.scores[0].feasible
    assert "Hard violation: v" in res.scores[0].rejection_reasons
    assert len(res.scores[0].criteria) == 7
    length_crit = next(c for c in res.scores[0].criteria if c.criterion == "length")
    assert length_crit.raw_value == 123.4
    assert length_crit.normalized_value == 0.0
    assert length_crit.weighted_score == 0.0


def test_no_feasible_route_returns_none() -> None:
    c1 = make_candidate("A", hard_violation_ids=frozenset(["v"]))
    res = evaluate_network_candidates((c1,), default_weights())
    assert res.best_candidate_id is None


def test_deterministic_ranking() -> None:
    c1 = make_candidate("A", total_length_m=300.0)
    c2 = make_candidate("B", total_length_m=100.0)
    c3 = make_candidate("C", total_length_m=200.0)
    
    w = RouteScoringWeights(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    res = evaluate_network_candidates((c1, c2, c3), w)
    
    assert res.ranked_candidate_ids == ("B", "C", "A")


def test_score_tie_breaking() -> None:
    # A and B tie in score.
    # B has shorter length, so B should rank ahead of A.
    # If they tied in length too, alphabetical ID breaks the tie.
    c1 = make_candidate("A", total_length_m=100.0, road_crossing_count=2)
    c2 = make_candidate("B", total_length_m=90.0, road_crossing_count=2)
    
    # Give all weight to road crossing, so they have the exact same score (0.0).
    w = RouteScoringWeights(0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    res = evaluate_network_candidates((c1, c2), w)
    
    assert res.scores[0].total_score == res.scores[1].total_score
    assert res.ranked_candidate_ids == ("B", "A")


def test_score_breakdown_preserves_raw_metrics() -> None:
    c1 = make_candidate("A", total_length_m=1234.5)
    res = evaluate_network_candidates((c1,), default_weights())
    
    score = res.scores[0]
    length_crit = next(c for c in score.criteria if c.criterion == "length")
    
    assert length_crit.raw_value == 1234.5
    assert length_crit.normalized_value == 0.0


def test_normalization_ranges_preserved() -> None:
    c1 = make_candidate("A", total_length_m=100.0)
    c2 = make_candidate("B", total_length_m=200.0)
    
    res = evaluate_network_candidates((c1, c2), default_weights())
    length_range = next(r for r in res.normalization_ranges if r.criterion == "length")
    
    assert length_range.minimum == 100.0
    assert length_range.maximum == 200.0
    assert not length_range.constant


def test_rejection_reasons_preserved() -> None:
    c1 = make_candidate("A", hard_violation_ids=frozenset(["zone1", "zone2"]))
    res = evaluate_network_candidates((c1,), default_weights())
    
    reasons = ("Hard violation: zone1", "Hard violation: zone2")
    assert res.scores[0].rejection_reasons == reasons


def test_input_order_independence() -> None:
    c1 = make_candidate("A", total_length_m=100.0)
    c2 = make_candidate("B", total_length_m=200.0)
    c3 = make_candidate("C", total_length_m=300.0)
    w = default_weights()
    
    res_1 = evaluate_network_candidates((c1, c2, c3), w)
    res_2 = evaluate_network_candidates((c3, c2, c1), w)
    
    assert res_1.ranked_candidate_ids == res_2.ranked_candidate_ids
    
    scores_1_dict = {s.candidate_id: s.total_score for s in res_1.scores}
    scores_2_dict = {s.candidate_id: s.total_score for s in res_2.scores}
    assert scores_1_dict == scores_2_dict
