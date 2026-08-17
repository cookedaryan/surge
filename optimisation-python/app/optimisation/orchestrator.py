import csv
import hashlib
import json
import logging
import math
import os
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from shapely.geometry import Point

from app.algorithms.physical_routing import validate_cost_surface
from app.algorithms.pole_placement import place_poles_on_network
from app.algorithms.route_graph import build_project_graph
from app.costing.models import LifecycleCostConfig
from app.electrical.load_flow.config import LoadFlowConfig
from app.electrical.load_flow.models import WTGOperatingPoint
from app.gis.constraints import (
    ConstraintLayer,
    ConstraintMode,
    ConstraintType,
    apply_constraint_layers,
)
from app.gis.cost_surface import world_to_grid
from app.land.decision import assess_transaction_option
from app.land.fingerprint import compute_land_economic_context_id
from app.land.models import (
    LandAvailabilityStatus,
    ParcelCommercialProfile,
)
from app.optimisation.candidate_evaluation import evaluate_candidate
from app.optimisation.candidate_search import run_candidate_beam_search
from app.optimisation.scenario_models import (
    ScenarioGenerationConfig,
    ScenarioGenerationError,
)
from app.optimisation.scenarios import generate_pnc_scenarios
from app.optimisation.search_cache import (
    CandidateEvaluationCache,
    compute_evaluation_context_id,
)
from app.optimisation.workflow_models import (
    CandidateFailure,
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

_OWNER_INTERACTION_PENALTY = 20.0
_LAND_PRESENT_VALUE_SCALE = 0.0001


def _validate_input(project_input: ProjectInput, config: OptimisationConfig) -> None:
    """Fail-fast validation of inputs before any heavy computation."""
    if not project_input.project_id or not project_input.project_id.strip():
        raise OptimisationInputError("Project ID must not be blank.")
    if not math.isfinite(project_input.row_width_m) or project_input.row_width_m <= 0:
        raise OptimisationInputError("ROW width must be positive and finite.")

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
            "Manual segment_cable_type_ids are not accepted by automatic "
            "candidate design mode."
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


def derive_land_constraint_layers(
    project_input: ProjectInput,
    lifecycle_config: LifecycleCostConfig | None = None,
) -> tuple[ConstraintLayer, ...]:
    if project_input.land_context is None:
        return project_input.constraint_layers

    profiles_by_id = {
        profile.parcel_id: profile
        for profile in project_input.land_context.parcel_profiles
    }
    effective_layers = []
    for layer in project_input.constraint_layers:
        profile = profiles_by_id.get(layer.layer_id)
        if layer.layer_type != ConstraintType.PARCEL or profile is None:
            effective_layers.append(layer)
            continue

        if profile.availability_status == LandAvailabilityStatus.UNAVAILABLE:
            effective_layers.append(
                replace(
                    layer,
                    mode=ConstraintMode.HARD_EXCLUSION,
                    cost_weight=None,
                )
            )
            continue

        if layer.mode == ConstraintMode.HARD_EXCLUSION:
            effective_layers.append(layer)
            continue

        penalty = _land_routing_penalty(profile, lifecycle_config)
        effective_layers.append(
            replace(
                layer,
                cost_weight=(layer.cost_weight or 0.0) + penalty,
            )
        )

    return tuple(effective_layers)


def _land_routing_penalty(
    profile: ParcelCommercialProfile,
    lifecycle_config: LifecycleCostConfig | None,
) -> float:
    option_values = (
        assessment.present_value
        for terms in profile.transaction_options
        if (assessment := assess_transaction_option(terms, lifecycle_config)).feasible
    )
    minimum_present_value = min(option_values, default=None)
    if minimum_present_value is None:
        return _OWNER_INTERACTION_PENALTY
    return (
        _OWNER_INTERACTION_PENALTY
        + float(minimum_present_value) * _LAND_PRESENT_VALUE_SCALE
    )


def _apply_land_routing_constraints(
    project_input: ProjectInput,
    lifecycle_config: LifecycleCostConfig | None,
) -> ProjectInput:
    effective_layers = derive_land_constraint_layers(
        project_input,
        lifecycle_config,
    )
    adjustments = []
    for original, effective in zip(
        project_input.constraint_layers,
        effective_layers,
        strict=True,
    ):
        if original is effective or original.mode == ConstraintMode.HARD_EXCLUSION:
            continue
        if effective.mode == ConstraintMode.HARD_EXCLUSION:
            adjustment = effective
        else:
            if original.cost_weight is None or effective.cost_weight is None:
                raise AssertionError("Soft land constraint is missing cost_weight")
            adjustment = replace(
                effective,
                cost_weight=effective.cost_weight - original.cost_weight,
            )
        adjustments.append(
            replace(adjustment, layer_id=f"land-routing:{original.layer_id}")
        )

    surface = (
        apply_constraint_layers(project_input.cost_surface, tuple(adjustments))
        if adjustments
        else project_input.cost_surface
    )
    return replace(
        project_input,
        constraint_layers=effective_layers,
        cost_surface=surface,
    )


def optimise_project(
    project_input: ProjectInput,
    config: OptimisationConfig,
    *,
    evaluation_cache: CandidateEvaluationCache | None = None,
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
    land_economic_context_id = compute_land_economic_context_id(
        project_input.land_context
    )

    lifecycle_config = config.costing.lifecycle if config.costing else None
    project_input = _apply_land_routing_constraints(
        project_input,
        lifecycle_config,
    )

    evaluation_context_id = compute_evaluation_context_id(
        project_input, config, electrical_context_id, land_economic_context_id
    )
    if evaluation_cache is None:
        evaluation_cache = CandidateEvaluationCache()

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

    # 4. Evaluate Seeds
    seeds = []
    for scenario in generation_result.candidates:
        eval_res = evaluate_candidate(scenario, project_input, config)
        if (
            eval_res.execution_failure
            and eval_res.execution_failure.code
            == WorkflowFailureCode.UNEXPECTED_EXCEPTION
        ):
            # Unexpected or global configuration exceptions abort the whole run
            logger.error("Unexpected global failure during load flow")
            return OptimisationWorkflowResult(
                status=OptimisationStatus.FAILED,
                generation_result=generation_result,
                candidates=(),
                recommendation=None,
                recommended_result=None,
                failures=(eval_res.execution_failure,),
            )
        seeds.append(eval_res)

    # 5. Search & Score
    base_graph = build_project_graph(project_input.project_data)
    substations = [
        n for n, d in base_graph.nodes(data=True) if d.get("type") == "substation"
    ]
    if not substations:
        raise ValueError("Project graph contains no substation node")
    substation_node_id = substations[0]

    corpus_sink = None
    if config.search.emit_training_corpus and config.search.training_corpus_path:
        path = config.search.training_corpus_path

        def _corpus_sink(row: Mapping[str, object]) -> None:
            file_exists = os.path.exists(path)
            with open(path, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(row.keys()))
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)

        corpus_sink = _corpus_sink

    try:
        all_candidates, recommendation, search_result = run_candidate_beam_search(
            seeds=tuple(seeds),
            project_input=project_input,
            config=config,
            base_graph=base_graph,
            cost_surface=project_input.cost_surface,
            substation_node_id=substation_node_id,
            electrical_context_id=electrical_context_id,
            evaluation_context_id=evaluation_context_id,
            evaluation_cache=evaluation_cache,
            corpus_sink=corpus_sink,
        )
    except Exception as exc:
        logger.exception("Candidate evaluation/search failed")
        failure = CandidateFailure(
            stage=WorkflowStage.SCORING,
            code=WorkflowFailureCode.SCORING_FAILED,
            message=str(exc),
        )
        return OptimisationWorkflowResult(
            status=OptimisationStatus.FAILED,
            generation_result=generation_result,
            candidates=(),
            recommendation=None,
            recommended_result=None,
            failures=(failure,),
        )

    failures = []
    for c in all_candidates:
        if c.execution_failure:
            failures.append(c.execution_failure)

    # Preserve seed generation order, followed by deterministic search-result order.
    candidate_map = {c.scenario.scenario_id: c for c in all_candidates}
    ordered_candidates_list = [
        candidate_map[s.scenario_id]
        for s in generation_result.candidates
        if s.scenario_id in candidate_map
    ]
    seed_ids = {s.scenario_id for s in generation_result.candidates}
    search_candidates = [
        c for c in all_candidates if c.scenario.scenario_id not in seed_ids
    ]
    search_candidates.sort(key=lambda c: c.scenario.scenario_id)
    ordered_candidates_list.extend(search_candidates)

    ordered_candidates = tuple(ordered_candidates_list)

    # 8. Recommendation and Status
    recommended_result = None
    pole_network = None
    if recommendation and recommendation.recommended_scenario_id:
        winner_id = recommendation.recommended_scenario_id
        winner_candidate = candidate_map[winner_id]

        # Verify invariants before packaging
        load_flow_result = winner_candidate.load_flow_result
        if load_flow_result is None:
            raise RuntimeError("Recommended scenario is missing a load flow result.")
        if (
            not winner_candidate.evaluation
            or not winner_candidate.evaluation.assessment.eligible
        ):
            raise RuntimeError("Recommended scenario must be eligible.")

        if config.pole is not None:
            try:
                winner_assessment = winner_candidate.engineering_assessment
                pole_network = (
                    winner_assessment.pole_result
                    if winner_assessment is not None
                    and winner_assessment.pole_result is not None
                    else place_poles_on_network(
                        winner_candidate.scenario.network,
                        config.pole,
                    )
                )
            except Exception as exc:
                logger.exception("Pole network generation failed for %s", winner_id)
                failure = CandidateFailure(
                    stage=WorkflowStage.POLE_PLACEMENT,
                    code=WorkflowFailureCode.POLE_NETWORK_GENERATION_FAILED,
                    message=str(exc),
                    scenario_id=winner_id,
                )
                failures.append(failure)
                winner_candidate = replace(winner_candidate, pole_failure=failure)
                candidate_map[winner_id] = winner_candidate

                # Rebuild ordered_candidates
                ordered_candidates = tuple(
                    candidate_map[c.scenario.scenario_id] for c in ordered_candidates
                )

                return OptimisationWorkflowResult(
                    status=OptimisationStatus.FAILED,
                    generation_result=generation_result,
                    candidates=ordered_candidates,
                    recommendation=None,
                    recommended_result=None,
                    failures=tuple(failures),
                )

        try:
            presentation = build_project_result(
                pnc_network=winner_candidate.scenario.network,
                load_flow_result=load_flow_result,
                pole_network=pole_network,
                constraint_layers=project_input.constraint_layers,
            )
            # Create a new instance with the presentation result
            winner_candidate = replace(
                winner_candidate, presentation_result=presentation
            )
            candidate_map[winner_id] = winner_candidate

            # Rebuild ordered_candidates
            ordered_candidates = tuple(
                candidate_map[c.scenario.scenario_id] for c in ordered_candidates
            )

            recommended_result = presentation
            logger.info("Recommended candidate: %s", winner_id)
        except PresentationDataMismatchError as exc:
            logger.warning("%s packaging failed: %s", winner_id, str(exc))
            failure = CandidateFailure(
                stage=WorkflowStage.PACKAGING,
                code=WorkflowFailureCode.PACKAGING_FAILED,
                message=str(exc),
                scenario_id=winner_id,
            )
            failures.append(failure)

            winner_candidate = replace(winner_candidate, packaging_failure=failure)
            candidate_map[winner_id] = winner_candidate

            # Rebuild ordered_candidates
            ordered_candidates = tuple(
                candidate_map[c.scenario.scenario_id] for c in ordered_candidates
            )

            return OptimisationWorkflowResult(
                status=OptimisationStatus.FAILED,
                generation_result=generation_result,
                candidates=ordered_candidates,
                recommendation=None,
                recommended_result=None,
                failures=tuple(failures),
            )
        except Exception as exc:
            logger.exception("Unexpected packaging failure for %s", winner_id)
            failure = CandidateFailure(
                stage=WorkflowStage.PACKAGING,
                code=WorkflowFailureCode.PACKAGING_FAILED,
                message=str(exc),
                scenario_id=winner_id,
            )
            failures.append(failure)

            winner_candidate = replace(winner_candidate, packaging_failure=failure)
            candidate_map[winner_id] = winner_candidate

            # Rebuild ordered_candidates
            ordered_candidates = tuple(
                candidate_map[c.scenario.scenario_id] for c in ordered_candidates
            )

            return OptimisationWorkflowResult(
                status=OptimisationStatus.FAILED,
                generation_result=generation_result,
                candidates=ordered_candidates,
                recommendation=None,
                recommended_result=None,
                failures=tuple(failures),
            )

    if (
        len(generation_result.candidates) < generation_result.requested_candidate_count
        or failures
    ):
        status = OptimisationStatus.PARTIAL_SUCCESS
    else:
        status = OptimisationStatus.SUCCESS

    if not (recommendation and recommendation.recommended_scenario_id):
        if all(
            c.execution_failure is not None
            and c.execution_failure.code
            == WorkflowFailureCode.ELECTRICAL_EXECUTION_ERROR
            for c in ordered_candidates
        ):
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
        pole_network=pole_network,
        search_result=search_result,
    )
