import math
from decimal import Decimal
import pytest
from unittest.mock import MagicMock

from app.costing.models import CandidateCostAssessment, CandidateLifecycleCost
from app.electrical.load_flow.models import LoadFlowNetworkResult
from app.optimisation.engineering_metric_models import CandidateEngineeringAssessment, CandidateEngineeringMetrics
from app.optimisation.scenario_models import PNCScenario, ScenarioParameters, ScenarioStrategy
from app.pnc.models import ProjectPNCNetwork
from app.optimisation.scoring_models import CandidateAssessment, CandidateEvaluation, GroupScore, MetricScore
from app.optimisation.workflow_models import (
    CandidateFailure,
    CandidateWorkflowResult,
    OptimisationStatus,
    OptimisationWorkflowResult,
    WorkflowFailureCode,
    WorkflowStage,
)
from app.reporting.builder import build_decision_report
from app.reporting.decision_models import (
    AlternativeStatus,
    ComparisonOutcome,
    DecisionReportStatus,
    MetricDirection,
)

def create_mock_candidate(
    scenario_id: str,
    feasible: bool = True,
    total_length: float = 1000.0,
    cost: float = 1000000.0,
    rank: int = 1,
    failure: CandidateFailure | None = None,
    pole_count: int = 10,
    parcels: int = 3,
) -> CandidateWorkflowResult:
    scenario = MagicMock(spec=PNCScenario)
    scenario.scenario_id = scenario_id
    scenario.topology_fingerprint = f"fingerprint_{scenario_id}"
    scenario.project_id = "PRJ-001"
    scenario.network = MagicMock()
    scenario.network.segment_count = 5
    scenario.lineage = None

    if failure:
        return CandidateWorkflowResult(
            scenario=scenario,
            load_flow_result=None,
            evaluation=None,
            execution_failure=failure,
            engineering_assessment=None,
            cost_assessment=None,
            presentation_result=None,
        )

    # Mock LoadFlow
    lf_result = MagicMock(spec=LoadFlowNetworkResult)
    lf_result.scenario_id = scenario_id
    lf_result.is_valid = feasible
    lf_result.total_active_loss_mw = 1.5
    lf_result.maximum_loading_percent = 85.0
    lf_result.minimum_voltage_pu = 0.95
    lf_result.maximum_voltage_pu = 1.05
    lf_result.violations = ()

    # Mock Engineering
    metrics = MagicMock(spec=CandidateEngineeringMetrics)
    metrics.total_route_length_m = total_length
    metrics.road_crossing_count = 1
    metrics.soft_constraint_overlap_length_m = 0.0
    metrics.affected_parcel_count = parcels
    metrics.owner_interaction_count = parcels
    
    eng_assess = MagicMock(spec=CandidateEngineeringAssessment)
    eng_assess.scenario_id = scenario_id
    eng_assess.metrics = metrics

    # Mock Cost
    cost_obj = MagicMock(spec=CandidateLifecycleCost)
    cost_obj.lifecycle_cost = Decimal(cost)
    cost_obj.conductor_capex = Decimal("500000.0")
    cost_obj.pole_capex = Decimal("200000.0")
    cost_obj.land_capex = Decimal("100000.0")
    cost_obj.present_value_opex = Decimal("200000.0")
    cost_obj.currency = "USD"
    
    cost_assess = MagicMock(spec=CandidateCostAssessment)
    cost_assess.scenario_id = scenario_id
    cost_assess.cost = cost_obj
    cost_assess.catalogue_id = "CAT-01"
    cost_assess.catalogue_version = "v1"
    cost_assess.cost_model_version = "v1"
    cost_assess.conductor_capex_amount = Decimal("500000.0")
    cost_assess.pole_capex_amount = Decimal("200000.0")
    cost_assess.land_purchase_capex_amount = Decimal("100000.0")
    cost_assess.present_value_opex_amount = Decimal("200000.0")
    cost_assess.currency = "USD"

    # Mock Evaluation
    eval_obj = MagicMock(spec=CandidateEvaluation)
    eval_obj.engineering_benefit_score = 0.8
    eval_obj.economic_benefit_score = 0.9
    eval_obj.final_benefit_score = 0.85
    eval_obj.rank = rank
    
    assessment = MagicMock(spec=CandidateAssessment)
    assessment.scenario_id = scenario_id
    assessment.eligible = feasible
    assessment.disqualifications = () if feasible else (MagicMock(message="Infeasible"),)
    eval_obj.assessment = assessment

    # Mock Presentation
    pres_obj = MagicMock()
    pres_obj.pole_summary = MagicMock()
    pres_obj.pole_summary.total_poles = pole_count
    pres_obj.pole_summary.terminal_poles = 2
    pres_obj.pole_summary.angle_poles = 2
    pres_obj.pole_summary.intermediate_poles = pole_count - 4
    pres_obj.pole_summary.junction_poles = 0

    return CandidateWorkflowResult(
        scenario=scenario,
        load_flow_result=lf_result,
        evaluation=eval_obj,
        execution_failure=None,
        engineering_assessment=eng_assess,
        cost_assessment=cost_assess,
        presentation_result=pres_obj,
    )

def test_decision_report_winner_and_feasible_alternative():
    winner = create_mock_candidate("SCN-1", feasible=True, total_length=1000.0, cost=1000000.0, rank=1, parcels=3)
    alt1 = create_mock_candidate("SCN-2", feasible=True, total_length=1200.0, cost=1100000.0, rank=2, parcels=4)
    
    recom = MagicMock()
    recom.recommended_scenario_id = "SCN-1"
    
    gen_mock = MagicMock()
    gen_mock.requested_candidate_count = 2

    workflow_result = OptimisationWorkflowResult(
        status=OptimisationStatus.SUCCESS,
        generation_result=gen_mock,
        candidates=(winner, alt1),
        recommendation=recom,
        recommended_result=winner.presentation_result,
        failures=(),
        pole_network=None,
        search_result=None,
    )
    
    report = build_decision_report(workflow_result)
    
    assert report.status == DecisionReportStatus.SUCCESS
    assert report.recommendation is not None
    assert report.recommendation.reference.candidate_id == "SCN-1"
    
    assert len(report.alternatives) == 1
    alt_summary = report.alternatives[0]
    assert alt_summary.reference.candidate_id == "SCN-2"
    assert alt_summary.status == AlternativeStatus.FEASIBLE
    
    # Check comparisons
    # Winner cost = 1M, Alt cost = 1.1M. Winner is LOWER_IS_BETTER. Delta = 1M - 1.1M = -100k (BETTER)
    cost_delta = next(c for c in alt_summary.comparisons if c.metric == "lifecycle_cost")
    assert cost_delta.absolute_delta == -100000.0
    assert cost_delta.outcome == ComparisonOutcome.BETTER
    assert math.isclose(cost_delta.relative_delta, -0.0909090909) # -100k / 1.1M
    
    # Check reasoning
    assert report.reasoning is not None
    assert len(report.reasoning.advantages) > 0 # Winner should have advantages over alt
    assert any(a.factor == "lifecycle_cost" for a in report.reasoning.advantages)


def test_decision_report_infeasible_alternative():
    winner = create_mock_candidate("SCN-1", feasible=True, rank=1)
    # Alt is infeasible
    alt1 = create_mock_candidate("SCN-2", feasible=False, rank=None)
    
    recom = MagicMock()
    recom.recommended_scenario_id = "SCN-1"
    
    gen_mock = MagicMock()
    gen_mock.requested_candidate_count = 2

    workflow_result = OptimisationWorkflowResult(
        status=OptimisationStatus.SUCCESS,
        generation_result=gen_mock,
        candidates=(winner, alt1),
        recommendation=recom,
        recommended_result=winner.presentation_result,
        failures=(),
    )
    
    report = build_decision_report(workflow_result)
    
    assert report.status == DecisionReportStatus.SUCCESS
    assert len(report.alternatives) == 0
    assert len(report.rejected_candidates) == 1
    
    rejected = report.rejected_candidates[0]
    assert rejected.reference.candidate_id == "SCN-2"
    assert rejected.failure_code == "DISQUALIFIED"
    assert rejected.failure_stage == WorkflowStage.SCORING


def test_decision_report_no_winner():
    alt1 = create_mock_candidate("SCN-1", feasible=False, rank=None)
    
    workflow_result = OptimisationWorkflowResult(
        status=OptimisationStatus.NO_FEASIBLE_CANDIDATE,
        generation_result=None,
        candidates=(alt1,),
        recommendation=None,
        recommended_result=None,
        failures=(),
    )
    
    report = build_decision_report(workflow_result)
    
    assert report.status == DecisionReportStatus.NO_FEASIBLE_CANDIDATE
    assert report.recommendation is None
    assert len(report.rejected_candidates) == 1
    
    rejected = report.rejected_candidates[0]
    assert rejected.reference.candidate_id == "SCN-1"


def test_decision_report_missing_data_preserves_none():
    winner = create_mock_candidate("SCN-1", feasible=True, rank=1)
    
    # Set something to None to test it preserves None, not 0
    winner.cost_assessment.cost = None
    
    recom = MagicMock()
    recom.recommended_scenario_id = "SCN-1"
    
    gen_mock = MagicMock()
    gen_mock.requested_candidate_count = 1

    workflow_result = OptimisationWorkflowResult(
        status=OptimisationStatus.SUCCESS,
        generation_result=gen_mock,
        candidates=(winner,),
        recommendation=recom,
        recommended_result=winner.presentation_result,
        failures=(),
    )
    
    report = build_decision_report(workflow_result)
    assert report.recommendation.economics.lifecycle_cost is None
    
    # Since cost is missing on winner, delta should also be None in alt comparison
    alt = create_mock_candidate("SCN-2", feasible=True, rank=2)
    alt.cost_assessment.cost = None
    
    gen_mock2 = MagicMock()
    gen_mock2.requested_candidate_count = 2

    workflow_result = OptimisationWorkflowResult(
        status=OptimisationStatus.SUCCESS,
        generation_result=gen_mock2,
        candidates=(winner, alt),
        recommendation=recom,
        recommended_result=winner.presentation_result,
        failures=(),
    )
    
    report2 = build_decision_report(workflow_result)
    cost_comp = next(c for c in report2.alternatives[0].comparisons if c.metric == "lifecycle_cost")
    assert cost_comp.absolute_delta is None
    assert cost_comp.relative_delta is None
    assert cost_comp.outcome is None
