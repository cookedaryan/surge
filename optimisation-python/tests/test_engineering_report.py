import ast
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.optimisation.search_models import (
    CandidateSearchResult,
    CandidateSearchStatistics,
    FeederReassignmentMutation,
    SearchTerminationReason,
)
from app.optimisation.workflow_models import (
    OptimisationStatus,
    OptimisationWorkflowResult,
)
from app.reporting.builder import build_decision_report
from app.reporting.decision_models import (
    AlternativeStatus,
    AlternativeSummary,
    CandidateReference,
    DecisionReport,
    DecisionReportStatus,
    EconomicsSummary,
    ElectricalSummary,
    LandDecisionSummary,
    OptimizationEvidence,
    PhysicalSummary,
    RecommendationReasoning,
    RecommendationSummary,
    ReportProvenance,
    ReportWarning,
    ScoreSummary,
    SpatialSummary,
)
from app.reporting.renderers.text import TextRenderer
from app.reporting.report import build_engineering_report
from tests.test_decision_report import create_mock_candidate


@pytest.fixture
def base_report() -> DecisionReport:
    return DecisionReport(
        schema_version="1.0.0",
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
            micro_siting_enabled=None,
        ),
        recommendation=RecommendationSummary(
            reference=CandidateReference(
                candidate_id="cand-1",
                candidate_signature="sig",
                parent_candidate_id=None,
                search_round=0,
                mutation=None,
            ),
            physical=PhysicalSummary(
                total_route_length_m=1000.0,
                segment_count=5,
            ),
            electrical=ElectricalSummary(
                feasible=True,
                total_active_loss_mw=0.5,
                maximum_loading_percent=80.0,
                minimum_voltage_pu=0.95,
                maximum_voltage_pu=1.05,
                violation_count=0,
            ),
            spatial=SpatialSummary(
                road_crossing_count=2,
                soft_constraint_overlap_length_m=50.0,
                hard_exclusion_violation_count=0,
            ),
            land=LandDecisionSummary(
                affected_parcels=10,
                unique_owners=None,
                owner_interactions=12,
            ),
            poles=None,
            economics=EconomicsSummary(
                lifecycle_cost=Decimal("1000000.00"),
                conductor_capex=Decimal("500000.00"),
                pole_capex=Decimal("300000.00"),
                land_capex=Decimal("200000.00"),
                present_value_opex=Decimal("0.00"),
                currency="USD",
            ),
            scores=ScoreSummary(
                engineering_benefit_score=85.0,
                economic_benefit_score=90.0,
                final_benefit_score=87.5,
                rank=1,
            ),
        ),
        reasoning=RecommendationReasoning(),
    )


def _render(report: DecisionReport) -> str:
    return TextRenderer().render(build_engineering_report(report))


def _search_statistics() -> CandidateSearchStatistics:
    return CandidateSearchStatistics(
        proposed_count=6,
        unique_count=5,
        duplicate_count=1,
        structural_rejection_count=0,
        evaluation_cache_hit_count=3,
        search_evaluations_used=2,
        feasible_count=4,
        failure_count=1,
        search_evaluation_budget=10,
        proposed_candidate_budget=20,
        termination_reason=SearchTerminationReason.NO_NEW_UNIQUE_CANDIDATES,
        ranking_model_enabled=False,
        ranking_model_loaded=False,
        model_rank_calls=0,
        model_ranked_mutations=0,
        model_fallback_count=0,
    )


def test_hard_exclusion_is_suppressed_by_schema_version(
    base_report: DecisionReport,
) -> None:
    rendered = _render(base_report)

    assert "Hard-exclusion Violations: 0" not in rendered
    assert "Hard-exclusion compliance count is not reported" in rendered

    verified_schema = replace(base_report, schema_version="2.0.0")
    verified_rendered = _render(verified_schema)

    assert "Hard-exclusion Violations: 0" in verified_rendered
    assert "Hard-exclusion compliance count is not reported" not in verified_rendered


def test_unique_owners_is_explicitly_not_available(
    base_report: DecisionReport,
) -> None:
    rendered = _render(base_report)

    assert "Unique Owners: Not available" in rendered
    assert (
        "Unique Owners value is not available in the upstream decision report."
        in rendered
    )


def test_empty_reasoning_does_not_synthesize_an_explanation(
    base_report: DecisionReport,
) -> None:
    rendered = _render(base_report)

    assert "selected because" not in rendered.lower()
    assert "[Tradeoffs]" not in rendered
    assert "[Alternative Decisions]" not in rendered


def test_warning_is_rendered_as_an_executive_notice(
    base_report: DecisionReport,
) -> None:
    report = replace(
        base_report,
        warnings=(ReportWarning(code="PARTIAL_DATA", message="One stage degraded."),),
    )

    assert "[PARTIAL_DATA] One stage degraded." in _render(report)


def test_economics_preserves_decimal_precision(base_report: DecisionReport) -> None:
    assert base_report.recommendation is not None
    assert base_report.recommendation.economics is not None
    precise_value = Decimal("10000000000000000.02")
    economics = replace(
        base_report.recommendation.economics,
        lifecycle_cost=precise_value,
    )
    recommendation = replace(base_report.recommendation, economics=economics)

    assert f"Lifecycle Cost: {precise_value}" in _render(
        replace(base_report, recommendation=recommendation)
    )


def test_missing_alternative_values_are_not_reported_as_false_facts(
    base_report: DecisionReport,
) -> None:
    alternative = AlternativeSummary(
        reference=CandidateReference(
            candidate_id="ALT-1",
            candidate_signature="alt-signature",
            parent_candidate_id=None,
            search_round=0,
            mutation=None,
        ),
        status=AlternativeStatus.FEASIBLE,
        physical=None,
        electrical=None,
        spatial=None,
        land=None,
        poles=None,
        economics=None,
        scores=None,
    )
    engineering_report = build_engineering_report(
        replace(base_report, alternatives=(alternative,))
    )
    section = next(
        item for item in engineering_report.sections if item.title == "Alternatives"
    )

    assert section.tables[0].headers == (
        "Candidate ID",
        "Status",
        "Total Route Length (m)",
        "Final Benefit Score",
    )
    assert section.tables[0].rows == (("ALT-1", "FEASIBLE", "N/A", "N/A"),)


def test_traceability_renders_search_statistics_and_mutation(
    base_report: DecisionReport,
) -> None:
    mutation = FeederReassignmentMutation(
        wtg_id="WTG-1",
        source_feeder_id="F-1",
        target_feeder_id="F-2",
    )
    lineage = CandidateReference(
        candidate_id="cand-search-1",
        candidate_signature="search-signature",
        parent_candidate_id="cand-1",
        search_round=1,
        mutation=mutation,
    )
    evidence = OptimizationEvidence(
        search_statistics=_search_statistics(),
        termination_reason=SearchTerminationReason.NO_NEW_UNIQUE_CANDIDATES,
        winner_lineage=(lineage,),
    )
    rendered = _render(replace(base_report, optimization_evidence=evidence))

    assert "Total Candidates Evaluated: 5" in rendered
    assert "Feasible Candidates Found: 4" in rendered
    assert "NO_NEW_UNIQUE_CANDIDATES" in rendered
    assert "FEEDER_REASSIGNMENT" in rendered


def test_no_recommendation_sections_remain_explicit(
    base_report: DecisionReport,
) -> None:
    report = replace(
        base_report,
        status=DecisionReportStatus.FAILED,
        recommendation=None,
        reasoning=None,
    )
    rendered = _render(report)

    assert "Status: FAILED" in rendered
    assert "No recommendation available." in rendered
    assert "No economic assessment available." in rendered


def test_rendering_is_deterministic(base_report: DecisionReport) -> None:
    assert _render(base_report) == _render(base_report)


def test_sections_and_renderers_only_import_reporting_domain_modules() -> None:
    reporting_dir = Path(__file__).parent.parent / "app" / "reporting"
    target_dirs = (reporting_dir / "sections", reporting_dir / "renderers")

    for target_dir in target_dirs:
        for py_file in target_dir.rglob("*.py"):
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
            for node in ast.walk(tree):
                imported_modules: tuple[str, ...] = ()
                if isinstance(node, ast.Import):
                    imported_modules = tuple(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported_modules = (node.module,)

                for module in imported_modules:
                    if module.startswith("app."):
                        assert module.startswith("app.reporting."), (
                            f"Non-reporting import {module} found in {py_file}"
                        )


def test_integration_from_workflow_result_to_text_report() -> None:
    winner = create_mock_candidate(
        "SCN-1",
        feasible=True,
        total_length=1000.0,
        cost=1000000.0,
        rank=1,
        parcels=3,
    )
    recommendation = MagicMock(recommended_scenario_id="SCN-1")
    generation = MagicMock(requested_candidate_count=1)
    search_result = CandidateSearchResult(
        rounds_completed=1,
        statistics=_search_statistics(),
        initial_best_scenario_id="SCN-1",
        final_best_scenario_id="SCN-1",
        initial_route_length_m=1000.0,
        final_route_length_m=1000.0,
        initial_lifecycle_cost=None,
        final_lifecycle_cost=None,
    )
    workflow_result = OptimisationWorkflowResult(
        status=OptimisationStatus.SUCCESS,
        generation_result=generation,
        candidates=(winner,),
        recommendation=recommendation,
        recommended_result=winner.presentation_result,
        failures=(),
        search_result=search_result,
    )

    rendered = _render(build_decision_report(workflow_result, "PRJ-123"))

    assert "ENGINEERING DECISION REPORT" in rendered
    assert "Candidate ID: SCN-1" in rendered
    assert "Total Candidates Evaluated: 5" in rendered
    assert "Hard-exclusion compliance count is not reported" in rendered
    assert "Hard-exclusion Violations:" not in rendered
