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
14  Unified group scoring and effective metric weights
15  Unified tie-breaking prefers electrical contribution
16  Invalid group and subweight configurations are rejected
17  Cost-aware ties prefer engineering strength before lifecycle cost
18  Missing lifecycle costs disqualify only the affected candidate
19  Economic context mismatches disqualify the incomparable cohort
20  Zero lifecycle cost remains a valid deterministic tie-breaker
21  Evaluated scenarios reject mismatched cost assessments
22  Legacy cost-assessment mappings remain supported
"""

import datetime
import math
from dataclasses import replace
from decimal import Decimal
from typing import cast

import pytest

from app.algorithms.pole_placement import CollectorPoleResult
from app.algorithms.wtg_grouping import GroupingObjective
from app.costing.models import CandidateCostAssessment, CandidateLifecycleCost
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import (
    LoadFlowBusResult,
    LoadFlowFeederResult,
    LoadFlowNetworkResult,
    LoadFlowSegmentResult,
    LoadFlowViolation,
    LoadFlowViolationCode,
)
from app.optimisation.engineering_metric_models import (
    CandidateEngineeringAssessment,
    CandidateEngineeringMetrics,
    EngineeringMetricFailure,
    EngineeringMetricFailureCode,
)
from app.optimisation.scenario_models import (
    PNCScenario,
    ScenarioParameters,
    ScenarioStrategy,
    TopologyWeightProfile,
)
from app.optimisation.scoring import evaluate_cohort
from app.optimisation.scoring_models import (
    CandidateScoringConfig,
    CostAwareRecommendationConfig,
    DisqualificationCode,
    ElectricallyEvaluatedScenario,
    ElectricalScoringWeights,
    EngineeringEvaluatedScenario,
    OptimizationRecommendationStatus,
    RecommendationReasonCode,
    ScoringMetric,
    ScoringPolicyMode,
    SpatialScoringWeights,
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
        policy_mode=ScoringPolicyMode.LEGACY_COMPATIBILITY,
        physical_weight=0.4,
        spatial_weight=0.0,
        infrastructure_weight=0.0,
        electrical_weight=0.6,
        spatial_subweights=SpatialScoringWeights(0.0, 0.0, 0.0, 0.0),
        electrical_subweights=ElectricalScoringWeights(
            active_loss=0.25 / 0.6,
            cable_loading=0.2 / 0.6,
            voltage_margin=0.15 / 0.6,
        ),
    )


def make_mock_network(length: float) -> ProjectPNCNetwork:
    """Create a minimal mock of ProjectPNCNetwork with total_route_length_m."""

    class MockNetwork:
        total_route_length_m = length
        feeder_count = 3
        wtg_count = 10
        segment_count = 9

    return cast(ProjectPNCNetwork, MockNetwork())


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
            grouping_objective=GroupingObjective.MINIMIZE_DISTANCE,
            topology_weight_profile=TopologyWeightProfile.DEFAULT,
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
    loading: float | None = 50.0,
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
    *,
    total_traversal_cost: float | None = None,
    affected_parcel_count: int = 10,
    road_crossing_count: int = 2,
    soft_constraint_overlap_length_m: float = 0.0,
    physical_pole_count: int = 20,
) -> EngineeringEvaluatedScenario:
    metrics = None
    if (
        result.is_valid
        and result.converged
        and result.total_active_loss_mw is not None
        and result.maximum_loading_percent is not None
    ):
        v_margin = 0.0
        if (
            result.minimum_voltage_pu is not None
            and result.maximum_voltage_pu is not None
        ):
            v_margin = min(
                result.minimum_voltage_pu - 0.95,
                1.05 - result.maximum_voltage_pu,
            )
        metrics = CandidateEngineeringMetrics(
            total_route_length_m=scenario.total_route_length_m,
            total_traversal_cost=(
                scenario.total_route_length_m
                if total_traversal_cost is None
                else total_traversal_cost
            ),
            affected_parcel_count=affected_parcel_count,
            road_crossing_count=road_crossing_count,
            soft_constraint_overlap_length_m=soft_constraint_overlap_length_m,
            physical_pole_count=physical_pole_count,
            total_active_loss_mw=result.total_active_loss_mw,
            maximum_loading_percent=result.maximum_loading_percent,
            voltage_margin_pu=v_margin,
            environmental_overlap_m2=0.0,
            owner_interaction_count=0,
        )

    assessment = CandidateEngineeringAssessment(
        scenario_id=scenario.scenario_id,
        engineering_metrics_available=metrics is not None,
        extraction_failures=(
            ()
            if metrics
            else (
                EngineeringMetricFailure(
                    code=EngineeringMetricFailureCode.POLE_CONFIG_MISSING,
                    message="Missing",
                ),
            )
        ),
        hard_violation_ids=(),
        metrics=metrics,
        pole_result=(
            CollectorPoleResult(
                routes=(),
                total_poles=physical_pole_count,
                total_spans=max(physical_pole_count - 1, 0),
            )
            if metrics
            else None
        ),
    )

    return EngineeringEvaluatedScenario(
        electrical=ElectricallyEvaluatedScenario(
            scenario=scenario,
            load_flow_result=result,
            electrical_context_id=electrical_context_id,
        ),
        engineering_assessment=assessment,
    )


def make_cost_assessment(
    scenario_id: str,
    lifecycle_cost: str,
    *,
    catalogue_version: str = "1.0",
) -> CandidateCostAssessment:
    amount = Decimal(lifecycle_cost)
    basis_date = datetime.date(2026, 1, 1)
    cost = CandidateLifecycleCost(
        scenario_id=scenario_id,
        conductor_capex=amount,
        pole_capex=Decimal(0),
        land_purchase_capex=Decimal(0),
        total_capex=amount,
        land_recurring_cost_pv=Decimal(0),
        land_access_present_value=Decimal(0),
        annual_loss_energy_mwh=Decimal(0),
        annual_loss_cost=Decimal(0),
        present_value_factor=Decimal(0),
        present_value_opex=Decimal(0),
        lifecycle_cost=amount,
        line_items=(),
        currency="USD",
        catalogue_id="CAT-1",
        catalogue_version=catalogue_version,
        catalogue_price_basis_date=basis_date,
        energy_price_basis_date=basis_date,
        cost_model_version="1.0",
        analysis_period_years=25,
        discount_rate=Decimal("0.08"),
        annual_operating_hours=8760,
        loss_load_factor=Decimal("0.3"),
        energy_price_per_mwh=Decimal("50.0"),
    )
    return CandidateCostAssessment(
        scenario_id=scenario_id,
        cost=cost,
        failures=(),
        conductor_capex_amount=amount,
        pole_capex_amount=Decimal(0),
        land_purchase_capex_amount=Decimal(0),
        total_capex_amount=amount,
        land_recurring_cost_pv_amount=Decimal(0),
        land_access_present_value_amount=Decimal(0),
        annual_loss_energy_mwh=Decimal(0),
        annual_loss_cost_amount=Decimal(0),
        present_value_factor=Decimal(0),
        present_value_opex_amount=Decimal(0),
    )


def test_shortest_candidate_routing_advantage(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
) -> None:
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

    rec = evaluate_cohort((c1, c2), base_scoring_config)
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
) -> None:
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(loss=1.0),
    )
    c2 = make_wrapper(
        make_scenario("SCN-002", 50_000.0),
        make_load_flow_result(loss=0.8),
    )
    rec = evaluate_cohort((c1, c2), base_scoring_config)
    assert rec.recommended_scenario_id == "SCN-002"


def test_voltage_margin(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
) -> None:
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
    rec = evaluate_cohort((c1, c2, c3), base_scoring_config)
    assert rec.recommended_scenario_id == "SCN-002"

    evals = {e.assessment.scenario_id: e for e in rec.evaluations}
    assert all(
        evaluation.assessment.metrics is not None for evaluation in evals.values()
    )
    scn_002_metrics = evals["SCN-002"].assessment.metrics
    scn_001_metrics = evals["SCN-001"].assessment.metrics
    scn_003_metrics = evals["SCN-003"].assessment.metrics
    assert scn_002_metrics is not None
    assert scn_001_metrics is not None
    assert scn_003_metrics is not None
    assert math.isclose(scn_002_metrics.voltage_margin_pu, 0.02)
    assert math.isclose(scn_001_metrics.voltage_margin_pu, 0.01)
    assert math.isclose(scn_003_metrics.voltage_margin_pu, 0.005)


def test_lower_maximum_loading(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
) -> None:
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(loading=80.0),
    )
    c2 = make_wrapper(
        make_scenario("SCN-002", 50_000.0),
        make_load_flow_result(loading=70.0),
    )
    rec = evaluate_cohort((c1, c2), base_scoring_config)
    assert rec.recommended_scenario_id == "SCN-002"


def test_weighted_total_manual_calculation(
    base_load_flow_config: LoadFlowConfig,
) -> None:
    # Length: w=0.4, Loss: w=0.3, Loading: w=0.2, Voltage: w=0.1
    config = CandidateScoringConfig(
        policy_mode=ScoringPolicyMode.LEGACY_COMPATIBILITY,
        physical_weight=0.4,
        spatial_weight=0.0,
        infrastructure_weight=0.0,
        electrical_weight=0.6,
        spatial_subweights=SpatialScoringWeights(0.0, 0.0, 0.0, 0.0),
        electrical_subweights=ElectricalScoringWeights(
            active_loss=0.3 / 0.6,
            cable_loading=0.2 / 0.6,
            voltage_margin=0.1 / 0.6,
        ),
    )

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

    rec = evaluate_cohort((c1, c2), config)

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
) -> None:
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
    rec = evaluate_cohort((c1, c2), base_scoring_config)
    assert rec.recommended_scenario_id == "SCN-002"

    evals = {e.assessment.scenario_id: e for e in rec.evaluations}
    assert not evals["SCN-001"].assessment.eligible
    assert evals["SCN-001"].total_benefit_score is None


def test_all_candidates_invalid(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
) -> None:
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(converged=False),
    )
    rec = evaluate_cohort((c1,), base_scoring_config)
    assert rec.status == OptimizationRecommendationStatus.NO_FEASIBLE_CANDIDATE
    assert rec.recommended_scenario_id is None
    assert len(rec.evaluations) == 1
    assert not rec.evaluations[0].assessment.eligible


def test_deterministic_tie_breaking(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
) -> None:
    # Exactly same scores, different scenarios.
    c1 = make_wrapper(make_scenario("SCN-001", 50_000.0), make_load_flow_result())
    c2 = make_wrapper(make_scenario("SCN-002", 50_000.0), make_load_flow_result())

    # Tie break: length (same), loss (same), scenario_id asc
    rec1 = evaluate_cohort((c2, c1), base_scoring_config)
    assert rec1.recommended_scenario_id == "SCN-001"
    assert rec1.evaluations[0].assessment.scenario_id == "SCN-001"
    assert rec1.evaluations[1].assessment.scenario_id == "SCN-002"


def test_baseline_comparison(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
) -> None:
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

    rec = evaluate_cohort((c1, c2), base_scoring_config)
    assert rec.recommended_scenario_id == "SCN-001"
    assert rec.baseline_comparison_status == "baseline_comparable"

    # Check baseline comparisons
    route_comp = next(
        c for c in rec.baseline_comparisons if c.metric == ScoringMetric.ROUTE_LENGTH
    )
    assert route_comp.absolute_delta == -10_000.0
    assert route_comp.relative_delta_percent is not None
    assert math.isclose(route_comp.relative_delta_percent, -10_000.0 / 60_000.0 * 100.0)

    loss_comp = next(
        c for c in rec.baseline_comparisons if c.metric == ScoringMetric.ACTIVE_LOSS
    )
    assert math.isclose(loss_comp.absolute_delta, -0.2)
    assert loss_comp.relative_delta_percent is not None
    assert math.isclose(loss_comp.relative_delta_percent, -0.2 / 1.0 * 100.0)

    # Check reason includes BASELINE_IMPROVEMENT
    assert any(
        r.code == RecommendationReasonCode.BASELINE_IMPROVEMENT for r in rec.reasons
    )


def test_pairing_context_mismatch_rejection(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
) -> None:
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
        evaluate_cohort((c1, c2), base_scoring_config)

    c3 = make_wrapper(
        make_scenario("SCN-003", 50_000.0, comparison_group_id="CG-1"),
        make_load_flow_result(),
    )
    c4 = make_wrapper(
        make_scenario("SCN-004", 50_000.0, comparison_group_id="CG-2"),
        make_load_flow_result(),
    )
    with pytest.raises(ValueError, match="same comparison_group_id"):
        evaluate_cohort((c3, c4), base_scoring_config)

    c5 = make_wrapper(
        make_scenario("SCN-005", 50_000.0),
        make_load_flow_result(),
    )
    c6 = make_wrapper(
        make_scenario("SCN-005", 60_000.0),
        make_load_flow_result(),
    )
    with pytest.raises(ValueError, match="Duplicate scenario_id"):
        evaluate_cohort((c5, c6), base_scoring_config)


def test_single_eligible_candidate(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
) -> None:
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(),
    )
    rec = evaluate_cohort((c1,), base_scoring_config)
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
) -> None:
    c1 = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        # Converged but missing loading metric (simulating solver failure halfway)
        make_load_flow_result(loading=None),
    )
    c2 = make_wrapper(
        make_scenario("SCN-002", 50_000.0),
        make_load_flow_result(),
    )
    rec = evaluate_cohort((c1, c2), base_scoring_config)
    assert rec.recommended_scenario_id == "SCN-002"

    evals = {e.assessment.scenario_id: e for e in rec.evaluations}
    assert not evals["SCN-001"].assessment.eligible

    disqs = evals["SCN-001"].assessment.disqualifications
    assert any(
        d.code == DisqualificationCode.ENGINEERING_METRICS_UNAVAILABLE for d in disqs
    )


def test_complete_deterministic_result_across_multiple_runs(
    base_load_flow_config: LoadFlowConfig,
    base_scoring_config: CandidateScoringConfig,
) -> None:
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

    rec1 = evaluate_cohort((c1, c2), base_scoring_config)
    rec2 = evaluate_cohort((c2, c1), base_scoring_config)

    assert rec1 == rec2


def test_unified_group_scoring_uses_effective_metric_weights() -> None:
    config = CandidateScoringConfig(
        policy_mode=ScoringPolicyMode.UNIFIED_ENGINEERING,
        physical_weight=0.1,
        spatial_weight=0.4,
        infrastructure_weight=0.2,
        electrical_weight=0.3,
        spatial_subweights=SpatialScoringWeights(0.4, 0.3, 0.2, 0.1),
        electrical_subweights=ElectricalScoringWeights(0.5, 0.3, 0.2),
    )
    worse = make_wrapper(
        make_scenario("SCN-001", 60_000.0),
        make_load_flow_result(loss=1.0, loading=80.0, min_v=0.96, max_v=1.04),
        total_traversal_cost=75_000.0,
        affected_parcel_count=4,
        road_crossing_count=3,
        soft_constraint_overlap_length_m=100.0,
        physical_pole_count=30,
    )
    better = make_wrapper(
        make_scenario("SCN-002", 50_000.0),
        make_load_flow_result(loss=0.8, loading=70.0, min_v=0.97, max_v=1.03),
        total_traversal_cost=55_000.0,
        affected_parcel_count=2,
        road_crossing_count=1,
        soft_constraint_overlap_length_m=20.0,
        physical_pole_count=20,
    )

    recommendation = evaluate_cohort((worse, better), config)

    assert recommendation.recommended_scenario_id == "SCN-002"
    winner = recommendation.evaluations[0]
    assert winner.total_benefit_score == pytest.approx(1.0)
    assert all(score.group_score == pytest.approx(1.0) for score in winner.group_scores)
    for score in winner.metric_scores:
        assert score.weighted_benefit == pytest.approx(
            score.normalized_benefit * score.weight
        )
    assert any(
        reason.code == RecommendationReasonCode.LOWEST_SOFT_CONSTRAINT_OVERLAP
        for reason in recommendation.reasons
    )


def test_unified_tie_breaking_prefers_electrical_contribution() -> None:
    config = CandidateScoringConfig(
        policy_mode=ScoringPolicyMode.UNIFIED_ENGINEERING,
        physical_weight=0.0,
        spatial_weight=0.5,
        infrastructure_weight=0.0,
        electrical_weight=0.5,
        spatial_subweights=SpatialScoringWeights(1.0, 0.0, 0.0, 0.0),
        electrical_subweights=ElectricalScoringWeights(1.0, 0.0, 0.0),
    )
    electrical_best = make_wrapper(
        make_scenario("SCN-001", 60_000.0),
        make_load_flow_result(loss=0.8),
        total_traversal_cost=60_000.0,
    )
    spatial_best = make_wrapper(
        make_scenario("SCN-002", 50_000.0),
        make_load_flow_result(loss=1.0),
        total_traversal_cost=50_000.0,
    )

    first = evaluate_cohort((spatial_best, electrical_best), config)
    repeated = evaluate_cohort((electrical_best, spatial_best), config)

    assert first == repeated
    assert first.recommended_scenario_id == "SCN-001"
    assert first.evaluations[0].total_benefit_score == pytest.approx(0.5)


def test_cost_aware_tie_prefers_engineering_strength(
    base_scoring_config: CandidateScoringConfig,
) -> None:
    scoring_config = replace(
        base_scoring_config,
        policy_mode=ScoringPolicyMode.COST_AWARE,
    )
    cost_config = CostAwareRecommendationConfig(
        engineering_weight=0.5,
        lifecycle_cost_weight=0.5,
    )
    engineering_best = replace(
        make_wrapper(
            make_scenario("SCN-001", 50_000.0),
            make_load_flow_result(loss=0.8, loading=40.0, min_v=0.98, max_v=1.02),
        ),
        cost_assessment=make_cost_assessment("SCN-001", "200.00"),
    )
    lowest_cost = replace(
        make_wrapper(
            make_scenario("SCN-002", 60_000.0),
            make_load_flow_result(loss=1.0, loading=50.0, min_v=0.96, max_v=1.04),
        ),
        cost_assessment=make_cost_assessment("SCN-002", "100.00"),
    )

    recommendation = evaluate_cohort(
        (lowest_cost, engineering_best),
        scoring_config,
        cost_aware_config=cost_config,
    )

    assert recommendation.recommended_scenario_id == "SCN-001"
    assert recommendation.engineering_best_scenario_id == "SCN-001"
    assert recommendation.lowest_cost_scenario_id == "SCN-002"
    assert recommendation.economic_context_id is not None
    assert recommendation.evaluations[0].final_benefit_score == pytest.approx(0.5)
    assert recommendation.evaluations[1].final_benefit_score == pytest.approx(0.5)


def test_cost_aware_missing_cost_disqualifies_affected_candidate(
    base_scoring_config: CandidateScoringConfig,
) -> None:
    scoring_config = replace(
        base_scoring_config,
        policy_mode=ScoringPolicyMode.COST_AWARE,
    )
    cost_config = CostAwareRecommendationConfig(0.6, 0.4)
    complete = replace(
        make_wrapper(make_scenario("SCN-001", 50_000.0), make_load_flow_result()),
        cost_assessment=make_cost_assessment("SCN-001", "100.00"),
    )
    incomplete = make_wrapper(
        make_scenario("SCN-002", 40_000.0),
        make_load_flow_result(loss=0.5),
    )

    recommendation = evaluate_cohort(
        (incomplete, complete),
        scoring_config,
        cost_aware_config=cost_config,
    )

    assert recommendation.recommended_scenario_id == "SCN-001"
    evaluations = {
        evaluation.assessment.scenario_id: evaluation
        for evaluation in recommendation.evaluations
    }
    assert evaluations["SCN-002"].assessment.disqualifications[-1].code == (
        DisqualificationCode.INCOMPLETE_LIFECYCLE_COST
    )


def test_cost_aware_context_mismatch_disqualifies_incomparable_cohort(
    base_scoring_config: CandidateScoringConfig,
) -> None:
    scoring_config = replace(
        base_scoring_config,
        policy_mode=ScoringPolicyMode.COST_AWARE,
    )
    cost_config = CostAwareRecommendationConfig(0.6, 0.4)
    first = replace(
        make_wrapper(make_scenario("SCN-001", 50_000.0), make_load_flow_result()),
        cost_assessment=make_cost_assessment(
            "SCN-001",
            "100.00",
            catalogue_version="1.0",
        ),
    )
    second = replace(
        make_wrapper(make_scenario("SCN-002", 60_000.0), make_load_flow_result()),
        cost_assessment=make_cost_assessment(
            "SCN-002",
            "90.00",
            catalogue_version="2.0",
        ),
    )

    recommendation = evaluate_cohort(
        (first, second), scoring_config, cost_aware_config=cost_config
    )
    repeated = evaluate_cohort(
        (second, first), scoring_config, cost_aware_config=cost_config
    )

    assert recommendation == repeated
    assert (
        recommendation.status == OptimizationRecommendationStatus.NO_FEASIBLE_CANDIDATE
    )
    assert recommendation.economic_context_id is None
    assert all(
        evaluation.assessment.disqualifications[-1].code
        == DisqualificationCode.ECONOMIC_CONTEXT_MISMATCH
        for evaluation in recommendation.evaluations
    )


def test_economic_context_decimal_normalization_yields_same_fingerprint() -> None:
    from app.optimisation.scoring import compute_economic_context_id

    basis_date = datetime.date(2026, 1, 1)

    def make_assessment_with_rate(rate: str) -> CandidateCostAssessment:
        cost = CandidateLifecycleCost(
            scenario_id="SCN-1",
            conductor_capex=Decimal("100"),
            pole_capex=Decimal("0"),
            land_purchase_capex=Decimal("0"),
            total_capex=Decimal("100"),
            land_recurring_cost_pv=Decimal("0"),
            land_access_present_value=Decimal("0"),
            annual_loss_energy_mwh=Decimal("0"),
            annual_loss_cost=Decimal("0"),
            present_value_factor=Decimal("0"),
            present_value_opex=Decimal("0"),
            lifecycle_cost=Decimal("100"),
            line_items=(),
            currency="USD",
            catalogue_id="CAT-1",
            catalogue_version="1.0",
            catalogue_price_basis_date=basis_date,
            energy_price_basis_date=basis_date,
            cost_model_version="1.0",
            analysis_period_years=25,
            discount_rate=Decimal(rate),
            annual_operating_hours=8760,
            loss_load_factor=Decimal("0.3"),
            energy_price_per_mwh=Decimal("50.0"),
        )
        return CandidateCostAssessment(
            scenario_id="SCN-1",
            cost=cost,
            failures=(),
        )

    assessment_1 = make_assessment_with_rate("0.08")
    assessment_2 = make_assessment_with_rate("0.080")
    assessment_3 = make_assessment_with_rate("0.0800")

    fp1 = compute_economic_context_id(assessment_1)
    fp2 = compute_economic_context_id(assessment_2)
    fp3 = compute_economic_context_id(assessment_3)

    assert fp1 == fp2
    assert fp2 == fp3


def test_zero_lifecycle_cost_is_valid_tie_breaker(
    base_scoring_config: CandidateScoringConfig,
) -> None:
    scoring_config = replace(
        base_scoring_config,
        policy_mode=ScoringPolicyMode.COST_AWARE,
    )
    cost_config = CostAwareRecommendationConfig(1.0, 0.0)
    zero_cost = replace(
        make_wrapper(make_scenario("SCN-002", 50_000.0), make_load_flow_result()),
        cost_assessment=make_cost_assessment("SCN-002", "0.00"),
    )
    positive_cost = replace(
        make_wrapper(make_scenario("SCN-001", 50_000.0), make_load_flow_result()),
        cost_assessment=make_cost_assessment("SCN-001", "1.00"),
    )

    recommendation = evaluate_cohort(
        (positive_cost, zero_cost),
        scoring_config,
        cost_aware_config=cost_config,
    )

    assert recommendation.recommended_scenario_id == "SCN-002"
    assert recommendation.lowest_cost_scenario_id == "SCN-002"


def test_evaluated_scenario_rejects_mismatched_cost_assessment() -> None:
    wrapper = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(),
    )

    with pytest.raises(ValueError, match="cost_assessment scenario_id"):
        replace(
            wrapper,
            cost_assessment=make_cost_assessment("SCN-002", "100.00"),
        )

    assessment = make_cost_assessment("SCN-001", "100.00")
    assert assessment.cost is not None
    with pytest.raises(ValueError, match="lifecycle cost scenario_id"):
        replace(
            wrapper,
            cost_assessment=replace(
                assessment,
                cost=replace(assessment.cost, scenario_id="SCN-002"),
            ),
        )


def test_cost_aware_legacy_cost_mapping_remains_supported(
    base_scoring_config: CandidateScoringConfig,
) -> None:
    scoring_config = replace(
        base_scoring_config,
        policy_mode=ScoringPolicyMode.COST_AWARE,
    )
    wrapper = make_wrapper(
        make_scenario("SCN-001", 50_000.0),
        make_load_flow_result(),
    )

    recommendation = evaluate_cohort(
        (wrapper,),
        scoring_config,
        cost_assessments={"SCN-001": make_cost_assessment("SCN-001", "100.00")},
        cost_aware_config=CostAwareRecommendationConfig(0.6, 0.4),
    )

    assert recommendation.recommended_scenario_id == "SCN-001"
    assert recommendation.evaluations[0].lifecycle_cost == 100.0


def test_cost_aware_config_rejects_boolean_weights() -> None:
    with pytest.raises(ValueError, match="numbers, not booleans"):
        CostAwareRecommendationConfig(True, 0.0)


@pytest.mark.parametrize(
    ("spatial_subweights", "electrical_subweights", "message"),
    [
        (
            SpatialScoringWeights(-0.1, 0.4, 0.3, 0.4),
            ElectricalScoringWeights(0.5, 0.3, 0.2),
            "Spatial subweight weights must be non-negative",
        ),
        (
            SpatialScoringWeights(0.4, 0.3, 0.2, 0.1),
            ElectricalScoringWeights(math.inf, 0.0, 0.0),
            "Electrical subweight weights must be finite",
        ),
        (
            SpatialScoringWeights(0.4, 0.3, 0.2, 0.1),
            ElectricalScoringWeights(True, 0.0, 0.0),
            "Electrical subweight weights must be numbers",
        ),
    ],
)
def test_scoring_config_rejects_invalid_subweights(
    spatial_subweights: SpatialScoringWeights,
    electrical_subweights: ElectricalScoringWeights,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        CandidateScoringConfig(
            policy_mode=ScoringPolicyMode.UNIFIED_ENGINEERING,
            physical_weight=0.0,
            spatial_weight=0.5,
            infrastructure_weight=0.0,
            electrical_weight=0.5,
            spatial_subweights=spatial_subweights,
            electrical_subweights=electrical_subweights,
        )


def test_scoring_config_rejects_invalid_policy_mode() -> None:
    with pytest.raises(ValueError, match="policy_mode must be"):
        CandidateScoringConfig(
            policy_mode=cast(ScoringPolicyMode, "UNIFIED_ENGINEERING"),
            physical_weight=1.0,
            spatial_weight=0.0,
            infrastructure_weight=0.0,
            electrical_weight=0.0,
            spatial_subweights=SpatialScoringWeights(0.0, 0.0, 0.0, 0.0),
            electrical_subweights=ElectricalScoringWeights(0.0, 0.0, 0.0),
        )
