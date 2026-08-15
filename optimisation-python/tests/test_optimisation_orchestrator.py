from dataclasses import replace
from typing import Any, NoReturn

import numpy as np
import pytest

from app.algorithms.pole_placement import (
    CollectorPoleResult,
    PolePlacementConfig,
    place_poles_on_network,
)
from app.electrical.errors import CandidateElectricalEvaluationError
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import WTGOperatingPoint
from app.optimisation.orchestrator import optimise_project
from app.optimisation.scenario_models import ScenarioGenerationConfig
from app.optimisation.scoring_models import (
    CandidateScoringConfig,
    ElectricalScoringWeights,
    ScoringPolicyMode,
    SpatialScoringWeights,
)
from app.optimisation.search_models import CandidateSearchConfig
from app.optimisation.workflow_models import (
    OptimisationConfig,
    OptimisationInputError,
    OptimisationStatus,
    ProjectInput,
    WorkflowFailureCode,
    WorkflowStage,
)
from app.pnc.models import ProjectPNCNetwork
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
            policy_mode=ScoringPolicyMode.LEGACY_COMPATIBILITY,
            physical_weight=1.0,
            spatial_weight=0.0,
            infrastructure_weight=0.0,
            electrical_weight=0.0,
            spatial_subweights=SpatialScoringWeights(0.0, 0.0, 0.0, 0.0),
            electrical_subweights=ElectricalScoringWeights(0.0, 0.0, 0.0),
        ),
        pole=PolePlacementConfig(
            target_span_m=80.0,
            min_span_m=30.0,
            max_span_m=100.0,
            angle_pole_threshold_deg=10.0,
            coordinate_tolerance_m=0.1,
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


@pytest.fixture
def pole_config() -> PolePlacementConfig:
    return PolePlacementConfig(
        target_span_m=80.0,
        min_span_m=30.0,
        max_span_m=100.0,
        coordinate_tolerance_m=0.1,
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

    winner_id = result.recommendation.recommended_scenario_id
    winner_candidate = next(
        c for c in result.candidates if c.scenario.scenario_id == winner_id
    )
    assert winner_candidate.presentation_result is not None
    assert result.recommended_result == winner_candidate.presentation_result
    assert len([c for c in result.candidates if c.presentation_result is not None]) == 1
    assert all(candidate.packaging_failure is None for candidate in result.candidates)
    assert all(candidate.cable_sizing is not None for candidate in result.candidates)
    assert all(
        candidate.engineering_assessment is not None for candidate in result.candidates
    )
    assert all(
        candidate.engineering_assessment.engineering_metrics_available
        for candidate in result.candidates
        if candidate.engineering_assessment is not None
    )

    # Assert deterministic ordering of candidates matches PY-017
    assert tuple(c.scenario.scenario_id for c in result.candidates) == tuple(
        s.scenario_id for s in result.generation_result.candidates
    )


def test_enabled_candidate_search_evaluates_neighbors(
    project_input: ProjectInput, base_config: OptimisationConfig
) -> None:
    config = replace(
        base_config,
        search=CandidateSearchConfig(
            enabled=True,
            max_rounds=1,
            beam_width=1,
            max_neighbors_per_parent=1,
        ),
    )

    result = optimise_project(project_input, config)

    assert result.status == OptimisationStatus.SUCCESS
    assert result.search_result is not None
    assert result.search_result.rounds_completed == 1
    assert result.search_result.candidates_evaluated == 1
    search_candidates = [
        candidate
        for candidate in result.candidates
        if candidate.scenario.lineage is not None
    ]
    assert len(search_candidates) == 1
    assert search_candidates[0].scenario.lineage.search_round == 1


def test_candidate_search_config_requires_positive_integers() -> None:
    with pytest.raises(ValueError, match="max_rounds"):
        CandidateSearchConfig(max_rounds=0)
    with pytest.raises(ValueError, match="beam_width"):
        CandidateSearchConfig(beam_width=-1)
    with pytest.raises(ValueError, match="max_neighbors_per_parent"):
        CandidateSearchConfig(max_neighbors_per_parent=True)


def test_workflow_returns_canonical_poles_for_recommended_network(
    project_input: ProjectInput,
    base_config: OptimisationConfig,
    pole_config: PolePlacementConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected_networks: list[ProjectPNCNetwork] = []

    def capture_network(
        network: ProjectPNCNetwork,
        config: PolePlacementConfig,
    ) -> CollectorPoleResult:
        selected_networks.append(network)
        return place_poles_on_network(network, config)

    monkeypatch.setattr(
        "app.optimisation.engineering_metrics.place_poles_on_network",
        capture_network,
    )
    result = optimise_project(
        project_input,
        replace(base_config, pole=pole_config),
    )

    assert result.status == OptimisationStatus.SUCCESS
    assert result.recommendation is not None
    winner_id = result.recommendation.recommended_scenario_id
    winner = next(
        candidate
        for candidate in result.candidates
        if candidate.scenario.scenario_id == winner_id
    )
    assert selected_networks == [
        candidate.scenario.network for candidate in result.candidates
    ]
    assert all(
        candidate.engineering_assessment is not None
        and candidate.engineering_assessment.engineering_metrics_available
        for candidate in result.candidates
    )

    pole_network = result.pole_network
    assert pole_network is not None
    assert pole_network.total_poles == len(pole_network.physical_poles)
    assert pole_network.total_poles > 0
    assert any(pole.pole_type == "junction" for pole in pole_network.physical_poles)
    assert pole_network.total_poles < sum(
        len(route.poles) for route in pole_network.routes
    )

    winner_segments = {
        segment.segment_id: segment
        for feeder in winner.scenario.network.feeders
        for segment in feeder.segments
    }
    assert {route.route_id for route in pole_network.routes} == set(winner_segments)
    for route in pole_network.routes:
        segment = winner_segments[route.route_id]
        assert route.feeder_id == segment.feeder_id
        assert route.start_node_id == segment.from_node_id
        assert route.end_node_id == segment.to_node_id
        assert route.geometry.equals_exact(segment.route_geometry, 0.0)


def test_pole_integration_does_not_change_electrical_or_scoring_results(
    project_input: ProjectInput,
    base_config: OptimisationConfig,
    pole_config: PolePlacementConfig,
) -> None:
    without_poles = optimise_project(project_input, base_config)
    with_poles = optimise_project(
        project_input,
        replace(base_config, pole=pole_config),
    )

    assert without_poles.recommendation == with_poles.recommendation
    assert tuple(
        (candidate.load_flow_result, candidate.evaluation)
        for candidate in without_poles.candidates
    ) == tuple(
        (candidate.load_flow_result, candidate.evaluation)
        for candidate in with_poles.candidates
    )
    for baseline, integrated in zip(
        without_poles.candidates,
        with_poles.candidates,
        strict=True,
    ):
        baseline_segments = tuple(
            segment.route_geometry.wkb
            for feeder in baseline.scenario.network.feeders
            for segment in feeder.segments
        )
        integrated_segments = tuple(
            segment.route_geometry.wkb
            for feeder in integrated.scenario.network.feeders
            for segment in feeder.segments
        )
        assert integrated_segments == baseline_segments


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
    with pytest.raises(
        OptimisationInputError,
        match="Manual segment_cable_type_ids are not accepted",
    ):
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
    project_input: ProjectInput, base_config: OptimisationConfig
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
    assert result.recommendation is None
    assert result.recommended_result is None
    assert len(result.failures) == 2
    assert result.failures[0].code == WorkflowFailureCode.ELECTRICAL_VALIDATION_FAILED


def test_electrical_execution_failure_isolation(
    project_input: ProjectInput,
    base_config: OptimisationConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.electrical.repair import ClosedLoopRepairResult, repair_electrical_design

    # We will just patch repair_electrical_design to throw on the second call
    call_count = 0

    def side_effect_repair_electrical_design(
        *args: object, **kwargs: object
    ) -> ClosedLoopRepairResult:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise CandidateElectricalEvaluationError("Pandapower crashed on scenario 2")
        return repair_electrical_design(*args, **kwargs)

    monkeypatch.setattr(
        "app.optimisation.candidate_evaluation.repair_electrical_design",
        side_effect_repair_electrical_design,
    )

    result = optimise_project(project_input, base_config)
    assert result.status == OptimisationStatus.PARTIAL_SUCCESS
    assert len(result.failures) == 1
    assert result.failures[0].code == WorkflowFailureCode.ELECTRICAL_EXECUTION_ERROR

    # One candidate failed execution, one succeeded and got evaluated
    assert sum(1 for c in result.candidates if c.execution_failure) == 1
    assert sum(1 for c in result.candidates if c.load_flow_result) == 1


def test_winner_packaging_failure_returns_structured_failure(
    project_input: ProjectInput,
    base_config: OptimisationConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.optimisation import orchestrator

    def fail_winner(*args: Any, **kwargs: Any) -> NoReturn:
        raise PresentationDataMismatchError("winner packaging mismatch")

    monkeypatch.setattr(orchestrator, "build_project_result", fail_winner)

    result = optimise_project(project_input, base_config)

    assert result.status == OptimisationStatus.FAILED
    assert result.recommendation is None
    assert result.recommended_result is None
    assert any(f.stage == WorkflowStage.PACKAGING for f in result.failures)
    failed = next(c for c in result.candidates if c.packaging_failure is not None)
    replace(failed)


def test_pole_generation_failure_returns_structured_failure(
    project_input: ProjectInput,
    base_config: OptimisationConfig,
    pole_config: PolePlacementConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.optimisation import engineering_metrics, orchestrator

    def fail_pole_generation(*args: Any, **kwargs: Any) -> NoReturn:
        raise ValueError("invalid routed geometry for pole placement")

    monkeypatch.setattr(
        engineering_metrics,
        "place_poles_on_network",
        fail_pole_generation,
    )
    monkeypatch.setattr(
        orchestrator,
        "place_poles_on_network",
        fail_pole_generation,
    )

    result = optimise_project(
        project_input,
        replace(base_config, pole=pole_config),
    )

    assert result.status == OptimisationStatus.NO_FEASIBLE_CANDIDATE

    # Verify that the pole placement failure is recorded for the candidates
    assert len(result.candidates) > 0
    for candidate in result.candidates:
        assert candidate.engineering_assessment is not None
        assert not candidate.engineering_assessment.engineering_metrics_available
        assert any(
            f.code == "POLE_PLACEMENT_FAILED"
            for f in candidate.engineering_assessment.extraction_failures
        )


def test_scoring_failure_returns_structured_failure(
    project_input: ProjectInput,
    base_config: OptimisationConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_scoring(*args: Any, **kwargs: Any) -> NoReturn:
        raise RuntimeError("scoring crashed")

    monkeypatch.setattr(
        "app.optimisation.candidate_search.evaluate_cohort", fail_scoring
    )

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
            pole_network=None,
            failures=(),
        )


def test_deterministic_runs(
    project_input: ProjectInput,
    base_config: OptimisationConfig,
    pole_config: PolePlacementConfig,
) -> None:
    config = replace(base_config, pole=pole_config)
    result1 = optimise_project(project_input, config)
    result2 = optimise_project(project_input, config)

    # Check stable IDs and evaluations
    assert result1.recommendation is not None
    assert result2.recommendation is not None
    assert (
        result1.recommendation.recommended_scenario_id
        == result2.recommendation.recommended_scenario_id
    )
    c1 = result1.candidates[0]
    c2 = result2.candidates[0]
    assert c1.evaluation is not None
    assert c2.evaluation is not None
    assert c1.scenario.topology_fingerprint == c2.scenario.topology_fingerprint
    assert c1.evaluation.total_benefit_score == c2.evaluation.total_benefit_score
    assert result1.pole_network == result2.pole_network
