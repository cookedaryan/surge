"""Tests for SURGE-PY-018: Multi-Objective Candidate Scoring + Recommendation.

Test matrix
-----------
 1  Shortest candidate gets routing advantage
 2  Lower-loss candidate scores better
 3  Stronger voltage margin scores better
 4  Lower maximum loading scores better
 5  Weighted total matches manual calculation
 6  Hard feasibility - invalid candidate cannot win
 7  All candidates invalid returns NO_FEASIBLE_CANDIDATE
 8  Deterministic tie-breaking
 9  Baseline comparison calculations
10  Deterministic complete result across multiple runs
11  Pairing and context mismatch rejection
12  Constant metric ranges result in 0.0 benefit
13  Single eligible candidate scores 0.0 with ONLY_ELIGIBLE_CANDIDATE
"""

import math

import pytest

from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import (
    LoadFlowBusResult,
    LoadFlowFeederResult,
    LoadFlowNetworkResult,
    LoadFlowSegmentResult,
    LoadFlowViolation,
    LoadFlowViolationCode,
)
from app.optimisation.scenario_models import (
    PNCScenario,
    ScenarioParameters,
    ScenarioStrategy,
)
from app.optimisation.scoring import (
    evaluate_cohort,
)
from app.optimisation.scoring_models import (
    CandidateScoringConfig,
    DisqualificationCode,
    ElectricallyEvaluatedScenario,
    OptimizationRecommendationStatus,
    RecommendationReasonCode,
    ScoringMetric,
)
from app.pnc.models import ProjectPNCNetwork


@pytest.fixture
def base_load_flow_config() -> LoadFlowConfig:
    cable = LoadFlowCableType(
        cable_type_id="CABLE-1",
        resistance_ohm_per_km=0.1,
        reactance_ohm_per_km=0.1,
        capacitance_nf_per_km=0.2,
        max_current_a=300.0,
    )
    return LoadFlowConfig(
        nominal_voltage_kv=33.0,
        slack_voltage_pu=1.0,
        min_voltage_pu=0.95,
        max_voltage_pu=1.05,
        system_base_mva=100.0,
        cable_types=(cable,),
        default_cable_type_id="CABLE-1",
        segment_cable_type_ids={},
    )


@pytest.fixture
def base_scoring_config() -> CandidateScoringConfig:
    return CandidateScoringConfig(
        route_length_weight=0.4,
        electrical_loss_weight=0.25,
        cable_loading_weight=0.2,
        voltage_margin_weight=0.15,
    )


def make_mock_network(length: float) -> ProjectPNCNetwork:
    """Create a minimal mock of ProjectPNCNetwork with total_route_length_m."""

    class MockNetwork:
        total_route_length_m = length
        feeder_count = 3
        wtg_count = 10
        segment_count = 9

    return MockNetwork()  # type: ignore


def make_scenario(
    scenario_id: str,
    length: float,
    strategy: ScenarioStrategy = ScenarioStrategy.ALTERNATIVE_GROUPING,
    comparison_group_id: str = "CG-1",
    topology_fingerprint: str | None = None,
) -> PNCScenario:
    """Create a PNCScenario with minimal required fields."""
    return PNCScenario(
        scenario_id=scenario_id,
        strategy=strategy.value,
        comparison_group_id=comparison_group_id,
        topology_fingerprint=topology_fingerprint or f"fp_{scenario_id}",
        network=make_mock_network(length),
        parameters=ScenarioParameters(
            parameter_set_id="PS-X",
            strategy=strategy,
            grouping_seed=42,
            grouping_objective="distance",
            topology_weight_profile="default",
            topology_penalty=0.0,
            effective_feeder_capacity_mw=10.0,
        ),
        feeder_count=3,
        wtg_count=10,
        segment_count=9,
        total_route_length_m=length,
        route_length_by_feeder={},
        wtg_count_by_feeder={},
    )


def make_load_flow_result(
    converged: bool = True,
    is_valid: bool = True,
    loss: float = 1.0,
    loading: float = 50.0,
    min_v: float = 0.98,
    max_v: float = 1.02,
    violations: tuple[LoadFlowViolation, ...] = (),
    bus_count: int = 11,
    segment_count: int = 9,
    feeder_count: int = 3,
) -> LoadFlowNetworkResult:
    """Create a LoadFlowNetworkResult."""
    return LoadFlowNetworkResult(
        converged=converged,
        is_valid=is_valid,
        solver_algorithm="nr",
        total_generation_mw=100.0,
        slack_power_mw=1.0,
        total_active_loss_mw=loss if converged else None,
        total_reactive_loss_mvar=0.5 if converged else None,
        minimum_voltage_pu=min_v if converged else None,
        maximum_voltage_pu=max_v if converged else None,
        maximum_loading_percent=loading if converged else None,
        buses=tuple(
            LoadFlowBusResult(
                node_id=str(i),
                node_type="wtg",
                voltage_pu=1.0,
                voltage_kv=33.0,
                voltage_angle_degree=0.0,
                net_active_power_demand_mw=0.0,
                net_reactive_power_demand_mvar=0.0,
            )
            for i in range(bus_count)
        ),
        segments=tuple(
            LoadFlowSegmentResult(
                segment_id=str(i),
                feeder_id="F-1",
                p_from_mw=10.0,
                q_from_mvar=0.0,
                p_to_mw=10.0,
                q_to_mvar=0.0,
                active_loss_mw=0.1,
                reactive_loss_mvar=0.1,
                current_from_a=10.0,
                current_to_a=10.0,
                maximum_current_a=100.0,
                loading_percent=50.0,
            )
            for i in range(segment_count)
        ),
        feeders=tuple(
            LoadFlowFeederResult(
                feeder_id=str(i),
                wtg_count=5,
                active_loss_mw=0.1,
                reactive_loss_mvar=0.1,
                minimum_voltage_pu=0.98,
                maximum_voltage_pu=1.02,
                maximum_loading_percent=50.0,
                worst_voltage_node_id="N-1",
                most_loaded_segment_id="S-1",
                valid=True,
            )
            for i in range(feeder_count)
        ),
        violations=violations,
    )


def make_wrapper(
    scenario: PNCScenario,
    result: LoadFlowNetworkResult,
    electrical_context_id: str = "EC-1",
) -> ElectricallyEvaluatedScenario:
    return ElectricallyEvaluatedScenario(
        scenario=scenario,
        load_flow_result=result,
        electrical_context_id=electrical_context_id,
    )


def test_shortest_candidate_routing_advantage(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
):
    # SCN-001: longer, SCN-002: shorter
    # Other metrics identical
    c1 = make_wrapper(
        make_scenario("SCN-001", 60_000.0),
        make_load_flow_result(),
    )
    c2 = make_wrapper(
        make_scenario("SCN-002", 50_000.0),
        make_load_flow_result(),
    )

    rec = evaluate_cohort((c1, c2), base_scoring_config, base_load_flow_config)
    assert rec.recommended_scenario_id == "SCN-002"
    assert rec.evaluations[0].assessment.scenario_id == "SCN-002"
    assert rec.evaluations[1].assessment.scenario_id == "SCN-001"

    # Route length score for winner should be full benefit
    winner_route_score = next(
        ms
        for ms in rec.evaluations[0].metric_scores
        if ms.metric == ScoringMetric.ROUTE_LENGTH
    )
    assert winner_route_score.normalized_benefit == 1.0


def test_lower_loss_candidate(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
):
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(loss=1.0),
    )
    c2 = make_wrapper(
        make_scenario("SCN-002", 50_000.0),
        make_load_flow_result(loss=0.8),
    )
    rec = evaluate_cohort((c1, c2), base_scoring_config, base_load_flow_config)
    assert rec.recommended_scenario_id == "SCN-002"


def test_voltage_margin(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
):
    # Limits are 0.95 and 1.05
    # c1 min_v=0.96 (margin 0.01), max_v=1.04 (margin 0.01) -> margin=0.01
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(min_v=0.96, max_v=1.04),
    )
    # c2 min_v=0.97 (margin 0.02), max_v=1.03 (margin 0.02) -> margin=0.02 (better)
    c2 = make_wrapper(
        make_scenario("SCN-002", 50_000.0),
        make_load_flow_result(min_v=0.97, max_v=1.03),
    )
    # c3 min_v=0.98 (margin 0.03), max_v=1.045 (margin 0.005) -> margin=0.005 (worse)
    c3 = make_wrapper(
        make_scenario("SCN-003", 50_000.0),
        make_load_flow_result(min_v=0.98, max_v=1.045),
    )
    rec = evaluate_cohort((c1, c2, c3), base_scoring_config, base_load_flow_config)
    assert rec.recommended_scenario_id == "SCN-002"

    evals = {e.assessment.scenario_id: e for e in rec.evaluations}
    assert math.isclose(evals["SCN-002"].assessment.metrics.voltage_margin_pu, 0.02)
    assert math.isclose(evals["SCN-001"].assessment.metrics.voltage_margin_pu, 0.01)
    assert math.isclose(evals["SCN-003"].assessment.metrics.voltage_margin_pu, 0.005)


def test_lower_maximum_loading(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
):
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(loading=80.0),
    )
    c2 = make_wrapper(
        make_scenario("SCN-002", 50_000.0),
        make_load_flow_result(loading=70.0),
    )
    rec = evaluate_cohort((c1, c2), base_scoring_config, base_load_flow_config)
    assert rec.recommended_scenario_id == "SCN-002"


def test_weighted_total_manual_calculation(
    base_load_flow_config: LoadFlowConfig,
):
    # Length: w=0.4, Loss: w=0.3, Loading: w=0.2, Voltage: w=0.1
    config = CandidateScoringConfig(0.4, 0.3, 0.2, 0.1)

    c1 = make_wrapper(
        make_scenario("SCN-001", 60_000.0),
        make_load_flow_result(
            loss=1.0, loading=80.0, min_v=0.96, max_v=1.04
        ),  # margin 0.01
    )
    c2 = make_wrapper(
        make_scenario("SCN-002", 50_000.0),
        make_load_flow_result(
            loss=0.8, loading=70.0, min_v=0.97, max_v=1.03
        ),  # margin 0.02
    )

    rec = evaluate_cohort((c1, c2), config, base_load_flow_config)

    # C2 has best of everything. Min length (50k vs 60k), Min loss (0.8 vs 1.0),
    # Min loading (70 vs 80), Max margin (0.02 vs 0.01).
    # Therefore C2 normalized benefits are all 1.0. Total score = 1.0
    # C1 normalized benefits are all 0.0. Total score = 0.0
    assert rec.recommended_scenario_id == "SCN-002"
    assert rec.evaluations[0].total_benefit_score == 1.0
    assert rec.evaluations[1].total_benefit_score == 0.0


def test_hard_feasibility(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
):
    # SCN-001 has better metrics but is overloaded
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(
            is_valid=False,
            violations=(
                LoadFlowViolation(
                    code=LoadFlowViolationCode.CABLE_OVERLOAD,
                    message="Overload",
                ),
            ),
        ),
    )
    c2 = make_wrapper(
        make_scenario("SCN-002", 60_000.0),
        make_load_flow_result(),
    )
    rec = evaluate_cohort((c1, c2), base_scoring_config, base_load_flow_config)
    assert rec.recommended_scenario_id == "SCN-002"

    evals = {e.assessment.scenario_id: e for e in rec.evaluations}
    assert not evals["SCN-001"].assessment.eligible
    assert evals["SCN-001"].total_benefit_score is None


def test_all_candidates_invalid(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
):
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(converged=False),
    )
    rec = evaluate_cohort((c1,), base_scoring_config, base_load_flow_config)
    assert rec.status == OptimizationRecommendationStatus.NO_FEASIBLE_CANDIDATE
    assert rec.recommended_scenario_id is None
    assert len(rec.evaluations) == 1
    assert not rec.evaluations[0].assessment.eligible


def test_deterministic_tie_breaking(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
):
    # Exactly same scores, different scenarios.
    c1 = make_wrapper(make_scenario("SCN-001", 50_000.0), make_load_flow_result())
    c2 = make_wrapper(make_scenario("SCN-002", 50_000.0), make_load_flow_result())

    # Tie break: length (same), loss (same), scenario_id asc
    rec1 = evaluate_cohort((c2, c1), base_scoring_config, base_load_flow_config)
    assert rec1.recommended_scenario_id == "SCN-001"
    assert rec1.evaluations[0].assessment.scenario_id == "SCN-001"
    assert rec1.evaluations[1].assessment.scenario_id == "SCN-002"


def test_baseline_comparison(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
):
    # Baseline is SCN-002 due to strategy
    c1 = make_wrapper(
        make_scenario(
            "SCN-001", 50_000.0, strategy=ScenarioStrategy.ALTERNATIVE_GROUPING
        ),
        make_load_flow_result(loss=0.8),
    )
    c2 = make_wrapper(
        make_scenario("SCN-002", 60_000.0, strategy=ScenarioStrategy.BASELINE),
        make_load_flow_result(loss=1.0),
    )

    rec = evaluate_cohort((c1, c2), base_scoring_config, base_load_flow_config)
    assert rec.recommended_scenario_id == "SCN-001"
    assert rec.baseline_comparison_status == "baseline_comparable"

    # Check baseline comparisons
    route_comp = next(
        c for c in rec.baseline_comparisons if c.metric == ScoringMetric.ROUTE_LENGTH
    )
    assert route_comp.absolute_delta == -10_000.0
    assert math.isclose(route_comp.relative_delta_percent, -10_000.0 / 60_000.0 * 100.0)

    loss_comp = next(
        c for c in rec.baseline_comparisons if c.metric == ScoringMetric.ACTIVE_LOSS
    )
    assert math.isclose(loss_comp.absolute_delta, -0.2)
    assert math.isclose(loss_comp.relative_delta_percent, -0.2 / 1.0 * 100.0)

    # Check reason includes BASELINE_IMPROVEMENT
    assert any(
        r.code == RecommendationReasonCode.BASELINE_IMPROVEMENT for r in rec.reasons
    )


def test_pairing_context_mismatch_rejection(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
):
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(),
        electrical_context_id="EC-1",
    )
    c2 = make_wrapper(
        make_scenario("SCN-002", 50_000.0),
        make_load_flow_result(),
        electrical_context_id="EC-2",
    )
    with pytest.raises(ValueError, match="same electrical_context_id"):
        evaluate_cohort((c1, c2), base_scoring_config, base_load_flow_config)

    c3 = make_wrapper(
        make_scenario("SCN-003", 50_000.0, comparison_group_id="CG-1"),
        make_load_flow_result(),
    )
    c4 = make_wrapper(
        make_scenario("SCN-004", 50_000.0, comparison_group_id="CG-2"),
        make_load_flow_result(),
    )
    with pytest.raises(ValueError, match="same comparison_group_id"):
        evaluate_cohort((c3, c4), base_scoring_config, base_load_flow_config)

    c5 = make_wrapper(
        make_scenario("SCN-005", 50_000.0),
        make_load_flow_result(),
    )
    c6 = make_wrapper(
        make_scenario("SCN-005", 60_000.0),
        make_load_flow_result(),
    )
    with pytest.raises(ValueError, match="Duplicate scenario_id"):
        evaluate_cohort((c5, c6), base_scoring_config, base_load_flow_config)


def test_single_eligible_candidate(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
):
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(),
    )
    rec = evaluate_cohort((c1,), base_scoring_config, base_load_flow_config)
    assert rec.recommended_scenario_id == "SCN-001"
    assert rec.evaluations[0].total_benefit_score == 0.0

    assert any(
        r.code == RecommendationReasonCode.ONLY_ELIGIBLE_CANDIDATE for r in rec.reasons
    )
    for ms in rec.evaluations[0].metric_scores:
        assert ms.normalized_benefit == 0.0
        assert ms.weighted_benefit == 0.0


def test_missing_metrics_disqualification(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
):
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        # Converged but missing loading metric (simulating solver failure halfway)
        make_load_flow_result(loading=None),
    )
    c2 = make_wrapper(
        make_scenario("SCN-002", 50_000.0),
        make_load_flow_result(),
    )
    rec = evaluate_cohort((c1, c2), base_scoring_config, base_load_flow_config)
    assert rec.recommended_scenario_id == "SCN-002"

    evals = {e.assessment.scenario_id: e for e in rec.evaluations}
    assert not evals["SCN-001"].assessment.eligible

    disqs = evals["SCN-001"].assessment.disqualifications
    assert any(d.code == DisqualificationCode.ELECTRICAL_METRICS_MISSING for d in disqs)


def test_complete_deterministic_result_across_multiple_runs(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
):
    c1 = make_wrapper(
        make_scenario("SCN-001", 60_000.0, strategy=ScenarioStrategy.BASELINE),
        make_load_flow_result(loss=1.0),
    )
    c2 = make_wrapper(
        make_scenario(
            "SCN-002", 50_000.0, strategy=ScenarioStrategy.ALTERNATIVE_GROUPING
        ),
        make_load_flow_result(loss=0.8),
    )

    rec1 = evaluate_cohort((c1, c2), base_scoring_config, base_load_flow_config)
    rec2 = evaluate_cohort((c2, c1), base_scoring_config, base_load_flow_config)

    assert rec1 == rec2
