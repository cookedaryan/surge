import pytest
from dataclasses import replace

from app.reporting.decision_models import (
    DecisionReport, DecisionReportStatus, ReportProvenance,
    RecommendationSummary, CandidateReference, PhysicalSummary,
    ElectricalSummary, SpatialSummary, LandDecisionSummary,
    EconomicsSummary, ScoreSummary, RecommendationReasoning
)
from app.reporting.report import build_engineering_report
from app.reporting.renderers.text import TextRenderer
from app.reporting.limitations import REPORT_SCHEMA_LIMITATIONS

@pytest.fixture
def base_report():
    return DecisionReport(
        schema_version="1.0",
        status=DecisionReportStatus.SUCCESS,
        project_id="PROJ-123",
        optimisation_run_id=None,
        provenance=ReportProvenance(
            engineering_fingerprint=None,
            economic_fingerprint=None,
            catalogue_id=None,
            catalogue_version=None,
            cost_model_version=None,
            search_enabled=None,
            micro_siting_enabled=None
        ),
        recommendation=RecommendationSummary(
            reference=CandidateReference(
                candidate_id="cand-1",
                candidate_signature="sig",
                parent_candidate_id=None,
                search_round=0,
                mutation=None
            ),
            physical=PhysicalSummary(
                total_route_length_m=1000.0,
                segment_count=5
            ),
            electrical=ElectricalSummary(
                feasible=True,
                total_active_loss_mw=0.5,
                maximum_loading_percent=80.0,
                minimum_voltage_pu=0.95,
                maximum_voltage_pu=1.05,
                violation_count=0
            ),
            spatial=SpatialSummary(
                road_crossing_count=2,
                soft_constraint_overlap_length_m=50.0,
                hard_exclusion_violation_count=0
            ),
            land=LandDecisionSummary(
                affected_parcels=10,
                unique_owners=None,
                owner_interactions=12
            ),
            poles=None,
            economics=EconomicsSummary(
                lifecycle_cost=1000000,
                conductor_capex=500000,
                pole_capex=300000,
                land_capex=200000,
                present_value_opex=0,
                currency="USD"
            ),
            scores=ScoreSummary(
                engineering_benefit_score=85.0,
                economic_benefit_score=90.0,
                final_benefit_score=87.5,
                rank=1
            )
        ),
        alternatives=(),
        rejected_candidates=(),
        reasoning=RecommendationReasoning(
            tradeoffs=(),
            alternative_decisions=()
        )
    )

def test_hard_exclusion_suppressed_based_on_schema(base_report):
    # Schema 1.0.0 suppresses hard exclusions
    report = replace(base_report, schema_version="1.0.0")
    eng_report = build_engineering_report(report)
    renderer = TextRenderer()
    rendered = renderer.render(eng_report)
    
    assert "Hard-exclusion Violations: 0" not in rendered
    assert "Hard-exclusion compliance count is not reported" in rendered
    
    # Fake schema 2.0 where it's not suppressed
    report_v2 = replace(base_report, schema_version="2.0")
    eng_report_v2 = build_engineering_report(report_v2)
    rendered_v2 = renderer.render(eng_report_v2)
    
    assert "Hard-exclusion Violations: 0" in rendered_v2
    assert "Hard-exclusion compliance count is not reported" not in rendered_v2

def test_unique_owners_not_available(base_report):
    # Base report has unique_owners=None
    eng_report = build_engineering_report(base_report)
    renderer = TextRenderer()
    rendered = renderer.render(eng_report)
    
    assert "Unique Owners: Not available" in rendered
    assert "Unique Owners value is not available in the upstream decision report." in rendered

def test_reasoning_no_synthesis_when_empty(base_report):
    # Base report has empty tradeoffs and alternative_decisions
    eng_report = build_engineering_report(base_report)
    renderer = TextRenderer()
    rendered = renderer.render(eng_report)
    
    assert "selected because" not in rendered.lower()
    assert "[Tradeoffs]" not in rendered
    assert "[Alternative Decisions]" not in rendered

def test_determinism(base_report):
    renderer = TextRenderer()
    render1 = renderer.render(build_engineering_report(base_report))
    render2 = renderer.render(build_engineering_report(base_report))
    assert render1 == render2
    
def test_architectural_boundary():
    # Verify we aren't importing forbidden modules in the reporting module statically using AST
    import ast
    from pathlib import Path
    
    # We restrict importing specific domains that should remain separate from reporting
    forbidden_modules = ["app.algorithms.physical_routing", "app.gis", "app.land", "app.electrical", "app.costing", "app.optimisation.candidate_evaluation"]
    
    reporting_dir = Path(__file__).parent.parent / "app" / "reporting"
    
    for py_file in reporting_dir.rglob("*.py"):
        with open(py_file, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(py_file))
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_modules:
                        assert not alias.name.startswith(forbidden), f"Forbidden import {forbidden} found in {py_file}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for forbidden in forbidden_modules:
                        assert not node.module.startswith(forbidden), f"Forbidden import {forbidden} found in {py_file}"

from tests.test_decision_report import create_mock_candidate
from unittest.mock import MagicMock
from app.optimisation.workflow_models import OptimisationWorkflowResult, OptimisationStatus
from app.reporting.builder import build_decision_report

def test_integration_end_to_end_report():
    # Create workflow result with a winner
    winner = create_mock_candidate(
        "SCN-1", feasible=True, total_length=1000.0, cost=1000000.0, rank=1, parcels=3
    )
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
        pole_network=None,
        search_result=None,
    )
    
    # 1. Build decision report
    decision_report = build_decision_report(workflow_result, "PRJ-123")
    
    # 2. Build engineering report
    eng_report = build_engineering_report(decision_report)
    
    # 3. Render
    renderer = TextRenderer()
    rendered = renderer.render(eng_report)
    
    # Verifications
    assert "ENGINEERING DECISION REPORT" in rendered
    assert "SCN-1" in rendered
    assert "Hard-exclusion compliance count is not reported" in rendered
    assert "Hard-exclusion Violations:" not in rendered

