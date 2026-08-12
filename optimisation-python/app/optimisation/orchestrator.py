import hashlib
import json
import logging
import math
from dataclasses import replace
from typing import Any

from shapely.geometry import Point

from app.algorithms.physical_routing import validate_cost_surface
from app.electrical.errors import CandidateElectricalEvaluationError
from app.electrical.load_flow.analysis import run_load_flow
from app.electrical.load_flow.config import LoadFlowConfig
from app.electrical.load_flow.models import WTGOperatingPoint
from app.gis.cost_surface import world_to_grid
from app.optimisation.scenario_models import (
    ScenarioGenerationConfig,
    ScenarioGenerationError,
)
from app.optimisation.scenarios import generate_pnc_scenarios
from app.optimisation.scoring import evaluate_cohort
from app.optimisation.scoring_models import ElectricallyEvaluatedScenario
from app.optimisation.workflow_models import (
    CandidateFailure,
    CandidateWorkflowResult,
    OptimisationConfig,
    OptimisationInputError,
    OptimisationStatus,
    OptimisationWorkflowResult,
    ProjectInput,
    WorkflowFailureCode,
    WorkflowStage,
)
from app.presentation.exceptions import PresentationDataMismatchError
from app.presentation.result_builder import build_project_result

logger = logging.getLogger(__name__)


def _validate_input(project_input: ProjectInput, config: OptimisationConfig) -> None:
    """Fail-fast validation of inputs before any heavy computation."""
    if not project_input.project_id or not project_input.project_id.strip():
        raise OptimisationInputError("Project ID must not be blank.")

    project_data = project_input.project_data
    if not project_data.turbines:
        raise OptimisationInputError("Project must contain at least one WTG.")

    wtg_ids = [t.turbine_id for t in project_data.turbines]
    if any(not tid or not tid.strip() for tid in wtg_ids):
        raise OptimisationInputError("WTG IDs must not be blank.")
    if len(wtg_ids) != len(set(wtg_ids)):
        raise OptimisationInputError("WTG IDs must be unique.")

    if (
        not project_data.substation.substation_id
        or not project_data.substation.substation_id.strip()
    ):
        raise OptimisationInputError("Substation ID must not be blank.")

    # Check capacities
    if (
        not math.isfinite(project_input.feeder_capacity_mw)
        or project_input.feeder_capacity_mw <= 0
    ):
        raise OptimisationInputError("feeder_capacity_mw must be finite and positive.")
    for t in project_data.turbines:
        if (
            t.capacity_mw is None
            or not math.isfinite(t.capacity_mw)
            or t.capacity_mw <= 0
        ):
            raise OptimisationInputError(
                f"WTG {t.turbine_id} capacity must be finite and positive."
            )

    # Check geometries
    for t in project_data.turbines:
        if not isinstance(t.location, Point):
            raise OptimisationInputError(
                f"WTG {t.turbine_id} location must be a Point."
            )
        if t.location.is_empty or not t.location.is_valid:
            raise OptimisationInputError(
                f"WTG {t.turbine_id} location must be non-empty and valid."
            )
        if not math.isfinite(t.location.x) or not math.isfinite(t.location.y):
            raise OptimisationInputError(
                f"WTG {t.turbine_id} location must have finite coordinates."
            )
    if not isinstance(project_data.substation.location, Point):
        raise OptimisationInputError("Substation location must be a Point.")
    if (
        project_data.substation.location.is_empty
        or not project_data.substation.location.is_valid
    ):
        raise OptimisationInputError("Substation location must be non-empty and valid.")
    if not math.isfinite(project_data.substation.location.x) or not math.isfinite(
        project_data.substation.location.y
    ):
        raise OptimisationInputError(
            "Substation location must have finite coordinates."
        )

    # Cost surface CRS equivalence
    if not project_data.projected_crs.is_projected:
        raise OptimisationInputError(
            "Project CRS must be a projected (metre-based) CRS."
        )
    axis_units = {
        axis.unit_name.lower()
        for axis in project_data.projected_crs.axis_info
        if axis.unit_name
    }
    if not axis_units or not axis_units.issubset({"metre", "meter"}):
        raise OptimisationInputError("Project CRS axes must use metres.")
    if not project_data.projected_crs.equals(project_input.cost_surface.crs):
        raise OptimisationInputError("Project CRS must match CostSurface CRS.")

    # Cost surface properties
    cs = project_input.cost_surface
    try:
        validate_cost_surface(cs)
    except (TypeError, ValueError) as exc:
        raise OptimisationInputError(f"Invalid cost surface: {exc}") from exc

    # Bounds check
    for t in project_data.turbines:
        row, col = world_to_grid(t.location.x, t.location.y, cs)
        if not (0 <= row < cs.height and 0 <= col < cs.width):
            raise OptimisationInputError(
                f"WTG {t.turbine_id} is outside the cost surface bounds."
            )

    row, col = world_to_grid(
        project_data.substation.location.x, project_data.substation.location.y, cs
    )
    if not (0 <= row < cs.height and 0 <= col < cs.width):
        raise OptimisationInputError("Substation is outside the cost surface bounds.")

    # Operating points coverage
    op_ids = [op.node_id for op in project_input.operating_points]
    if len(op_ids) != len(set(op_ids)):
        raise OptimisationInputError("Operating points must have unique node IDs.")

    expected_ids = {f"wtg:{t.turbine_id}" for t in project_data.turbines}
    if set(op_ids) != expected_ids:
        raise OptimisationInputError(
            "Operating points must exactly cover all WTG node IDs."
        )

    # Configuration invariants
    if config.electrical.segment_cable_type_ids:
        raise OptimisationInputError(
            "segment_cable_type_ids must be empty for orchestrator cohort MVP. "
            "Use one default_cable_type_id to avoid cross-candidate assignment errors."
        )
    cable_ids = {cable.cable_type_id for cable in config.electrical.cable_types}
    if config.electrical.default_cable_type_id not in cable_ids:
        raise OptimisationInputError(
            "default_cable_type_id must reference a configured cable type."
        )


def _compute_electrical_context_id(
    operating_points: tuple[WTGOperatingPoint, ...],
    config: LoadFlowConfig,
) -> str:
    """Compute a stable hash representing the electrical evaluation context."""
    ops = sorted(
        [
            (op.node_id, op.active_power_mw, op.reactive_power_mvar)
            for op in operating_points
        ]
    )
    cables = sorted(
        [
            (
                c.cable_type_id,
                c.resistance_ohm_per_km,
                c.reactance_ohm_per_km,
                c.capacitance_nf_per_km,
                c.max_current_a,
                c.parallel_count,
                c.derating_factor,
            )
            for c in config.cable_types
        ]
    )

    state: dict[str, Any] = {
        "operating_points": ops,
        "cable_types": cables,
        "default_cable": config.default_cable_type_id,
        "system_base": config.system_base_mva,
        "voltage_kv": config.nominal_voltage_kv,
        "slack_pu": config.slack_voltage_pu,
        "min_pu": config.min_voltage_pu,
        "max_pu": config.max_voltage_pu,
    }

    serialized = json.dumps(state, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def optimise_project(
    project_input: ProjectInput,
    config: OptimisationConfig,
) -> OptimisationWorkflowResult:
    """Run the complete end-to-end Surge optimisation workflow."""

    # 1. Validation
    _validate_input(project_input, config)
    logger.info("Starting optimisation for %s", project_input.project_id)

    # 2. Stable Electrical Context
    electrical_context_id = _compute_electrical_context_id(
        project_input.operating_points,
        config.electrical,
    )

    # Inject project_id to avoid dual ownership issues
    scenario_config = ScenarioGenerationConfig(
        candidate_count=config.scenario.candidate_count,
        base_seed=config.scenario.base_seed,
        project_id=project_input.project_id,
    )

    # 3. Scenario Generation
    try:
        generation_result = generate_pnc_scenarios(
            project_data=project_input.project_data,
            feeder_capacity_mw=project_input.feeder_capacity_mw,
            cost_surface=project_input.cost_surface,
            config=scenario_config,
        )
    except ScenarioGenerationError as e:
        logger.error("Generation failed completely: %s", str(e))
        return OptimisationWorkflowResult(
            status=OptimisationStatus.FAILED,
            generation_result=None,
            candidates=(),
            recommendation=None,
            recommended_result=None,
            failures=(
                CandidateFailure(
                    stage=WorkflowStage.PNC_GENERATION,
                    code=WorkflowFailureCode.GENERATION_FAILED,
                    message=str(e),
                ),
            ),
        )

    logger.info("Generated %d scenario definitions", len(generation_result.candidates))

    if not generation_result.candidates:
        failure = CandidateFailure(
            stage=WorkflowStage.PNC_GENERATION,
            code=WorkflowFailureCode.GENERATION_FAILED,
            message="Scenario generation returned no candidates.",
        )
        return OptimisationWorkflowResult(
            status=OptimisationStatus.FAILED,
            generation_result=generation_result,
            candidates=(),
            recommendation=None,
            recommended_result=None,
            failures=(failure,),
        )

    # 4. Electrical Validation
    candidates = []
    failures = []
    evaluated_scenarios = []

    for scenario in generation_result.candidates:
        try:
            lf_result = run_load_flow(
                pnc_network=scenario.network,
                operating_points=project_input.operating_points,
                config=config.electrical,
            )
            logger.info("%s electrical validation completed", scenario.scenario_id)
            evaluated_scenarios.append(
                ElectricallyEvaluatedScenario(
                    scenario=scenario,
                    load_flow_result=lf_result,
                    electrical_context_id=electrical_context_id,
                )
            )
        except CandidateElectricalEvaluationError as e:
            logger.warning(
                "%s electrical execution failed: %s", scenario.scenario_id, str(e)
            )
            failures.append(
                CandidateFailure(
                    stage=WorkflowStage.ELECTRICAL_VALIDATION,
                    code=WorkflowFailureCode.ELECTRICAL_EXECUTION_ERROR,
                    message=str(e),
                    scenario_id=scenario.scenario_id,
                )
            )
            # Retain execution failure in candidate result
            candidates.append(
                CandidateWorkflowResult(
                    scenario=scenario,
                    load_flow_result=None,
                    evaluation=None,
                    execution_failure=failures[-1],
                )
            )
        except Exception as e:
            # Unexpected or global configuration exceptions abort the whole run
            logger.exception("Unexpected global failure during load flow")
            return OptimisationWorkflowResult(
                status=OptimisationStatus.FAILED,
                generation_result=generation_result,
                candidates=(),
                recommendation=None,
                recommended_result=None,
                failures=(
                    CandidateFailure(
                        stage=WorkflowStage.ELECTRICAL_VALIDATION,
                        code=WorkflowFailureCode.UNEXPECTED_EXCEPTION,
                        message=str(e),
                        scenario_id=scenario.scenario_id,
                    ),
                ),
            )

    # 5. Candidate Scoring
    recommendation = None
    if evaluated_scenarios:
        try:
            recommendation = evaluate_cohort(
                wrappers=tuple(evaluated_scenarios),
                scoring_config=config.scoring,
                load_flow_config=config.electrical,
            )
        except Exception as e:
            logger.exception("Candidate scoring failed")
            return OptimisationWorkflowResult(
                status=OptimisationStatus.FAILED,
                generation_result=generation_result,
                candidates=(),
                recommendation=None,
                recommended_result=None,
                failures=(
                    CandidateFailure(
                        stage=WorkflowStage.SCORING,
                        code=WorkflowFailureCode.SCORING_FAILED,
                        message=str(e),
                    ),
                ),
            )

        # Merge evaluations back to candidate results
        eval_map = {ev.assessment.scenario_id: ev for ev in recommendation.evaluations}
        for es in evaluated_scenarios:
            candidates.append(
                CandidateWorkflowResult(
                    scenario=es.scenario,
                    load_flow_result=es.load_flow_result,
                    evaluation=eval_map.get(es.scenario.scenario_id),
                    execution_failure=None,
                )
            )

    # Ensure deterministic order based on generation
    candidate_map = {c.scenario.scenario_id: c for c in candidates}
    ordered_candidates = tuple(
        candidate_map[s.scenario_id] for s in generation_result.candidates
    )

    # 6. Presentation Packaging
    packaged_candidates: list[CandidateWorkflowResult] = []
    for candidate in ordered_candidates:
        if candidate.load_flow_result is None:
            packaged_candidates.append(candidate)
            continue
        try:
            presentation = build_project_result(
                pnc_network=candidate.scenario.network,
                load_flow_result=candidate.load_flow_result,
            )
            packaged_candidates.append(
                replace(candidate, presentation_result=presentation)
            )
        except PresentationDataMismatchError as exc:
            logger.warning(
                "%s packaging failed: %s", candidate.scenario.scenario_id, str(exc)
            )
            failure = CandidateFailure(
                stage=WorkflowStage.PACKAGING,
                code=WorkflowFailureCode.PACKAGING_FAILED,
                message=str(exc),
                scenario_id=candidate.scenario.scenario_id,
            )
            failures.append(failure)
            packaged_candidates.append(replace(candidate, packaging_failure=failure))
        except Exception as exc:
            logger.exception(
                "Unexpected packaging failure for %s",
                candidate.scenario.scenario_id,
            )
            failure = CandidateFailure(
                stage=WorkflowStage.PACKAGING,
                code=WorkflowFailureCode.UNEXPECTED_EXCEPTION,
                message=str(exc),
                scenario_id=candidate.scenario.scenario_id,
            )
            return OptimisationWorkflowResult(
                status=OptimisationStatus.FAILED,
                generation_result=generation_result,
                candidates=(),
                recommendation=None,
                recommended_result=None,
                failures=(failure,),
            )

    ordered_candidates = tuple(packaged_candidates)
    candidate_map = {
        candidate.scenario.scenario_id: candidate for candidate in ordered_candidates
    }

    # 7. Recommendation and Status
    recommended_result = None
    if recommendation and recommendation.recommended_scenario_id:
        winner_id = recommendation.recommended_scenario_id
        winner_candidate = candidate_map[winner_id]

        # Verify invariants before packaging
        if not winner_candidate.load_flow_result:
            raise RuntimeError("Recommended scenario is missing a load flow result.")
        if (
            not winner_candidate.evaluation
            or not winner_candidate.evaluation.assessment.eligible
        ):
            raise RuntimeError("Recommended scenario must be eligible.")

        recommended_result = winner_candidate.presentation_result
        # If packaging failed for the winner, we have a problem
        if not recommended_result:
            logger.error("Recommended scenario %s failed packaging.", winner_id)
            status = OptimisationStatus.FAILED
            # In this case, we have a recommendation but no recommended_result,
            # which violates SUCCESS invariants.
            # We should probably clear recommendation or just fail the workflow.
            return OptimisationWorkflowResult(
                status=OptimisationStatus.FAILED,
                generation_result=generation_result,
                candidates=ordered_candidates,
                recommendation=None,
                recommended_result=None,
                failures=tuple(failures),
            )

        logger.info("Recommended candidate: %s", winner_id)

        if (
            len(ordered_candidates) < generation_result.requested_candidate_count
            or failures
        ):
            status = OptimisationStatus.PARTIAL_SUCCESS
        else:
            status = OptimisationStatus.SUCCESS
    else:
        if not evaluated_scenarios:
            # Everything execution-failed, this means FAILED workflow
            status = OptimisationStatus.FAILED
        else:
            status = OptimisationStatus.NO_FEASIBLE_CANDIDATE

    logger.info("Optimisation completed with status: %s", status.value)

    return OptimisationWorkflowResult(
        status=status,
        generation_result=generation_result,
        candidates=ordered_candidates,
        recommendation=recommendation,
        recommended_result=recommended_result,
        failures=tuple(failures),
    )
