from dataclasses import replace

import numpy as np
import pytest

from app.electrical.errors import CandidateElectricalEvaluationError
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import WTGOperatingPoint
from app.optimisation.orchestrator import optimise_project
from app.optimisation.scenario_models import ScenarioGenerationConfig
from app.optimisation.scoring_models import (
    CandidateScoringConfig,
)
from app.optimisation.workflow_models import (
    OptimisationConfig,
    OptimisationInputError,
    OptimisationStatus,
    ProjectInput,
    WorkflowFailureCode,
    WorkflowStage,
)
from app.presentation.exceptions import PresentationDataMismatchError
from tests.fixtures.demo_project import build_demo_cost_surface, build_demo_project_data


@pytest.fixture
def base_config() -> OptimisationConfig:
    return OptimisationConfig(
        scenario=ScenarioGenerationConfig(candidate_count=2, base_seed=42),
        electrical=LoadFlowConfig(
            nominal_voltage_kv=33.0,
            slack_voltage_pu=1.0,
            min_voltage_pu=0.9,
            max_voltage_pu=1.1,
            system_base_mva=100.0,
            cable_types=(
                LoadFlowCableType(
                    cable_type_id="DEFAULT_CABLE",
                    resistance_ohm_per_km=0.1,
                    reactance_ohm_per_km=0.1,
                    capacitance_nf_per_km=200.0,
                    max_current_a=600.0,
                ),
            ),
            default_cable_type_id="DEFAULT_CABLE",
            segment_cable_type_ids={},
        ),
        scoring=CandidateScoringConfig(
            route_length_weight=1.0,
            electrical_loss_weight=0.0,
            cable_loading_weight=0.0,
            voltage_margin_weight=0.0,
        ),
    )


@pytest.fixture
def project_input() -> ProjectInput:
    project_data = build_demo_project_data()
    return ProjectInput(
        project_id="PROJ-DEMO",
        project_data=project_data,
        cost_surface=build_demo_cost_surface(),
        feeder_capacity_mw=15.0,
        operating_points=tuple(
            WTGOperatingPoint(
                node_id=f"wtg:{t.turbine_id}",
                active_power_mw=5.0,
                reactive_power_mvar=0.0,
            )
            for t in project_data.turbines
        ),
    )


def test_complete_successful_workflow(
    project_input: ProjectInput, base_config: OptimisationConfig
) -> None:
    result = optimise_project(project_input, base_config)
    assert result.status == OptimisationStatus.SUCCESS
    assert result.generation_result is not None
    assert len(result.candidates) == 2
    assert result.recommendation is not None
    assert result.recommendation.recommended_scenario_id is not None
    assert result.recommended_result is not None

    assert result.recommended_result.network_summary.wtg_count == 8
    assert all(candidate.presentation_result for candidate in result.candidates)
    assert all(candidate.packaging_failure is None for candidate in result.candidates)

    # Assert deterministic ordering of candidates matches PY-017
    assert tuple(c.scenario.scenario_id for c in result.candidates) == tuple(
        s.scenario_id for s in result.generation_result.candidates
    )


def test_invalid_project_input_raises(
    project_input: ProjectInput, base_config: OptimisationConfig
) -> None:
    invalid_input = ProjectInput(
        project_id="",
        project_data=project_input.project_data,
        cost_surface=project_input.cost_surface,
        feeder_capacity_mw=15.0,
        operating_points=project_input.operating_points,
    )
    with pytest.raises(OptimisationInputError, match="must not be blank"):
        optimise_project(invalid_input, base_config)


def test_segment_cable_type_ids_not_empty_raises(
    project_input: ProjectInput, base_config: OptimisationConfig
) -> None:
    invalid_config = OptimisationConfig(
        scenario=base_config.scenario,
        electrical=LoadFlowConfig(
            nominal_voltage_kv=33.0,
            slack_voltage_pu=1.0,
            min_voltage_pu=0.9,
            max_voltage_pu=1.1,
            system_base_mva=100.0,
            cable_types=base_config.electrical.cable_types,
            default_cable_type_id="DEFAULT_CABLE",
            segment_cable_type_ids={"SEG-1": "DEFAULT_CABLE"},
        ),
        scoring=base_config.scoring,
    )
    with pytest.raises(OptimisationInputError, match="must be empty"):
        optimise_project(project_input, invalid_config)


def test_missing_operating_points_raises(
    project_input: ProjectInput, base_config: OptimisationConfig
) -> None:
    invalid_input = ProjectInput(
        project_id="PROJ-DEMO",
        project_data=project_input.project_data,
        cost_surface=project_input.cost_surface,
        feeder_capacity_mw=15.0,
        operating_points=project_input.operating_points[:-1],  # Drop one
    )
    with pytest.raises(OptimisationInputError, match="exactly cover"):
        optimise_project(invalid_input, base_config)


def test_invalid_cost_surfaces_fail_fast(
    project_input: ProjectInput, base_config: OptimisationConfig
) -> None:
    surface = project_input.cost_surface
    invalid_surfaces = (
        replace(surface, width=surface.width + 1),
        replace(surface, costs=np.full_like(surface.costs, np.nan)),
        replace(surface, resolution_m=-1.0),
    )

    for invalid_surface in invalid_surfaces:
        with pytest.raises(OptimisationInputError, match="Invalid cost surface"):
            optimise_project(
                replace(project_input, cost_surface=invalid_surface),
                base_config,
            )


def test_invalid_default_cable_fails_fast(
    project_input: ProjectInput, base_config: OptimisationConfig
) -> None:
    invalid_electrical = replace(
        base_config.electrical,
        default_cable_type_id="UNKNOWN_CABLE",
    )

    with pytest.raises(OptimisationInputError, match="default_cable_type_id"):
        optimise_project(
            project_input,
            replace(base_config, electrical=invalid_electrical),
        )


def test_all_scenario_generation_fails(
    project_input: ProjectInput, base_config: OptimisationConfig, monkeypatch
) -> None:
    # Force generating zero valid scenarios by making feeder capacity impossible
    impossible_input = ProjectInput(
        project_id="PROJ-DEMO",
        project_data=project_input.project_data,
        cost_surface=project_input.cost_surface,
        feeder_capacity_mw=0.01,
        operating_points=project_input.operating_points,
    )
    result = optimise_project(impossible_input, base_config)
    assert result.status == OptimisationStatus.FAILED
    assert len(result.failures) > 0
    assert result.failures[0].stage == WorkflowStage.PNC_GENERATION


def test_all_electrical_candidates_infeasible(
    project_input: ProjectInput, base_config: OptimisationConfig
) -> None:
    # Set min_voltage to an impossible value so all candidates violate limits
    impossible_config = OptimisationConfig(
        scenario=base_config.scenario,
        electrical=LoadFlowConfig(
            nominal_voltage_kv=33.0,
            slack_voltage_pu=1.0,
            min_voltage_pu=1.2,  # Impossible since slack is 1.0
            max_voltage_pu=1.3,
            system_base_mva=100.0,
            cable_types=base_config.electrical.cable_types,
            default_cable_type_id="DEFAULT_CABLE",
            segment_cable_type_ids={},
        ),
        scoring=base_config.scoring,
    )

    result = optimise_project(project_input, impossible_config)
    assert result.status == OptimisationStatus.NO_FEASIBLE_CANDIDATE
    assert result.recommendation is not None
    assert result.recommendation.recommended_scenario_id is None
    assert result.recommended_result is None
    # No execution failures, just domain infeasibility
    assert len(result.failures) == 0


def test_electrical_execution_failure_isolation(
    project_input: ProjectInput, base_config: OptimisationConfig, monkeypatch
) -> None:
    from app.optimisation import orchestrator

    original_run_load_flow = orchestrator.run_load_flow

    # We will just patch run_load_flow to throw on the second call
    call_count = 0

    def side_effect_run_load_flow(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise CandidateElectricalEvaluationError("Pandapower crashed on scenario 2")
        return original_run_load_flow(*args, **kwargs)

    monkeypatch.setattr(orchestrator, "run_load_flow", side_effect_run_load_flow)

    result = optimise_project(project_input, base_config)
    assert result.status == OptimisationStatus.PARTIAL_SUCCESS
    assert len(result.failures) == 1
    assert result.failures[0].code == WorkflowFailureCode.ELECTRICAL_EXECUTION_ERROR

    # One candidate failed execution, one succeeded and got evaluated
    assert sum(1 for c in result.candidates if c.execution_failure) == 1
    assert sum(1 for c in result.candidates if c.load_flow_result) == 1


def test_non_winner_packaging_failure_preserves_completed_results(
    project_input: ProjectInput,
    base_config: OptimisationConfig,
    monkeypatch,
) -> None:
    from app.optimisation import orchestrator

    baseline = optimise_project(project_input, base_config)
    assert baseline.recommendation is not None
    winner_id = baseline.recommendation.recommended_scenario_id
    failure_index = next(
        index
        for index, candidate in enumerate(baseline.candidates, start=1)
        if candidate.scenario.scenario_id != winner_id
    )
    original_builder = orchestrator.build_project_result
    call_count = 0

    def fail_selected_candidate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == failure_index:
            raise PresentationDataMismatchError("candidate packaging mismatch")
        return original_builder(*args, **kwargs)

    monkeypatch.setattr(
        orchestrator,
        "build_project_result",
        fail_selected_candidate,
    )

    result = optimise_project(project_input, base_config)

    assert result.status == OptimisationStatus.PARTIAL_SUCCESS
    failed = next(c for c in result.candidates if c.packaging_failure is not None)
    assert failed.execution_failure is None
    assert failed.load_flow_result is not None
    assert failed.evaluation is not None
    assert failed.presentation_result is None
    assert failed.packaging_failure.code == WorkflowFailureCode.PACKAGING_FAILED
    replace(failed)  # Re-validation must preserve a legal domain state.


def test_winner_packaging_failure_returns_structured_failure(
    project_input: ProjectInput,
    base_config: OptimisationConfig,
    monkeypatch,
) -> None:
    from app.optimisation import orchestrator

    baseline = optimise_project(project_input, base_config)
    assert baseline.recommendation is not None
    winner_id = baseline.recommendation.recommended_scenario_id
    failure_index = next(
        index
        for index, candidate in enumerate(baseline.candidates, start=1)
        if candidate.scenario.scenario_id == winner_id
    )
    original_builder = orchestrator.build_project_result
    call_count = 0

    def fail_winner(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == failure_index:
            raise PresentationDataMismatchError("winner packaging mismatch")
        return original_builder(*args, **kwargs)

    monkeypatch.setattr(orchestrator, "build_project_result", fail_winner)

    result = optimise_project(project_input, base_config)

    assert result.status == OptimisationStatus.FAILED
    assert result.recommendation is None
    assert result.recommended_result is None
    assert any(f.stage == WorkflowStage.PACKAGING for f in result.failures)
    failed = next(c for c in result.candidates if c.packaging_failure is not None)
    replace(failed)


def test_scoring_failure_returns_structured_failure(
    project_input: ProjectInput,
    base_config: OptimisationConfig,
    monkeypatch,
) -> None:
    from app.optimisation import orchestrator

    def fail_scoring(*args, **kwargs):
        raise RuntimeError("scoring crashed")

    monkeypatch.setattr(orchestrator, "evaluate_cohort", fail_scoring)

    result = optimise_project(project_input, base_config)

    assert result.status == OptimisationStatus.FAILED
    assert result.recommendation is None
    assert result.candidates == ()
    assert result.failures[0].stage == WorkflowStage.SCORING
    assert result.failures[0].code == WorkflowFailureCode.SCORING_FAILED


def test_workflow_status_invariants(
    project_input: ProjectInput,
    base_config: OptimisationConfig,
) -> None:
    result = optimise_project(project_input, base_config)

    with pytest.raises(ValueError, match="PARTIAL_SUCCESS"):
        replace(result, status=OptimisationStatus.PARTIAL_SUCCESS)
    with pytest.raises(ValueError, match="requires failure diagnostics"):
        replace(
            result,
            status=OptimisationStatus.FAILED,
            recommendation=None,
            recommended_result=None,
            failures=(),
        )


def test_deterministic_runs(
    project_input: ProjectInput, base_config: OptimisationConfig
) -> None:
    result1 = optimise_project(project_input, base_config)
    result2 = optimise_project(project_input, base_config)

    # Check stable IDs and evaluations
    assert (
        result1.recommendation.recommended_scenario_id
        == result2.recommendation.recommended_scenario_id
    )
    c1 = result1.candidates[0]
    c2 = result2.candidates[0]
    assert c1.scenario.topology_fingerprint == c2.scenario.topology_fingerprint
    assert c1.evaluation.total_benefit_score == c2.evaluation.total_benefit_score
