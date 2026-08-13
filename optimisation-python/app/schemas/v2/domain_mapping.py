import dataclasses
import math
from dataclasses import dataclass

from app.algorithms.pole_placement import PolePlacementConfig
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import WTGOperatingPoint
from app.gis.constraints import ingest_avoidance_constraints
from app.gis.cost_surface import build_project_cost_surface
from app.gis.preprocessing import (
    process_project_data,
    validate_project_routing_endpoints,
)
from app.optimisation.scenario_models import ScenarioGenerationConfig
from app.optimisation.scoring_models import CandidateScoringConfig
from app.optimisation.workflow_models import (
    OptimisationConfig,
    OptimisationInputError,
    OptimisationWorkflowResult,
    ProjectInput,
)
from app.schemas.v2.optimise import (
    CandidateSummary,
    FailuresSummary,
    GenerationSummary,
    OptimiseProjectRequest,
    OptimiseProjectResponse,
    RecommendationSummary,
)

MAX_WTGS = 50
MAX_RASTER_CELLS = 1_000_000


@dataclass(frozen=True)
class WorkflowInvocation:
    project_input: ProjectInput
    config: OptimisationConfig


def to_workflow_invocation(request: OptimiseProjectRequest) -> WorkflowInvocation:
    """Explicitly map the API request to Surge domain models."""

    # 1. Parse and project GeoJSON
    try:
        project_data = process_project_data(
            wtg_geojson=request.wtg_geojson,
            substation_geojson=request.substation_geojson,
        )
    except ValueError as exc:
        raise OptimisationInputError(
            f"Project GeoJSON validation failed: {exc}"
        ) from exc

    if len(project_data.turbines) > MAX_WTGS:
        raise OptimisationInputError(
            "Maximum WTG limit exceeded: "
            f"found {len(project_data.turbines)}, maximum is {MAX_WTGS}."
        )

    missing_capacity_ids = [
        turbine.turbine_id
        for turbine in project_data.turbines
        if turbine.capacity_mw is None
    ]
    if missing_capacity_ids:
        raise OptimisationInputError(
            "Every WTG requires capacity_mw; missing for "
            + ", ".join(sorted(missing_capacity_ids))
        )

    # 2. Build bounded surface and burn road/land exclusions into it.
    try:
        cost_surface = build_project_cost_surface(
            project_data,
            resolution_m=request.routing_config.resolution_m,
            padding_m=request.routing_config.padding_m,
            max_cells=MAX_RASTER_CELLS,
        )
        constraint_application = ingest_avoidance_constraints(
            cost_surface,
            request.avoidance_geojson,
            buffer_m=request.routing_config.avoidance_buffer_m,
            soft_cost_weight=request.routing_config.avoidance_cost_weight,
        )
        cost_surface = constraint_application.surface
        validate_project_routing_endpoints(
            project_data,
            cost_surface,
            constraint_application.layers,
        )
    except ValueError as exc:
        raise OptimisationInputError(str(exc)) from exc

    # 3. Derive normalized WTG operating points
    operating_points = []
    op_config = request.operating_point_config
    for turbine in project_data.turbines:
        if turbine.capacity_mw is None:  # Narrowed above; protects future callers.
            raise OptimisationInputError(
                f"WTG {turbine.turbine_id} is missing capacity_mw"
            )
        active_power_mw = turbine.capacity_mw * op_config.operating_factor
        # Simplified: Active power factor math.
        # pf = P / S => S = P / pf => Q = sqrt(S^2 - P^2)
        if active_power_mw > 0 and op_config.power_factor < 1.0:
            apparent_power = active_power_mw / op_config.power_factor
            reactive_magnitude = (apparent_power**2 - active_power_mw**2) ** 0.5
        else:
            reactive_magnitude = 0.0

        # Generation sign convention: lagging operation injects positive Q.
        reactive_power_mvar = (
            reactive_magnitude
            if op_config.power_factor_mode == "lagging"
            else -reactive_magnitude
        )

        operating_points.append(
            WTGOperatingPoint(
                node_id=f"wtg:{turbine.turbine_id}",
                active_power_mw=active_power_mw,
                reactive_power_mvar=reactive_power_mvar,
            )
        )

    # 4. Build load-flow cable configuration
    cable_types = []
    for c in request.cable_config.cable_types:
        cable_types.append(
            LoadFlowCableType(
                cable_type_id=c.cable_type_id,
                resistance_ohm_per_km=c.resistance_ohm_per_km,
                reactance_ohm_per_km=c.reactance_ohm_per_km,
                capacitance_nf_per_km=c.capacitance_nf_per_km,
                max_current_a=c.max_current_a,
                parallel_count=c.parallel_count,
                derating_factor=c.derating_factor,
            )
        )

    try:
        load_flow_config = LoadFlowConfig(
            nominal_voltage_kv=request.cable_config.nominal_voltage_kv,
            slack_voltage_pu=request.cable_config.slack_voltage_pu,
            min_voltage_pu=request.cable_config.min_voltage_pu,
            max_voltage_pu=request.cable_config.max_voltage_pu,
            system_base_mva=request.cable_config.system_base_mva,
            cable_types=tuple(cable_types),
            default_cable_type_id=request.cable_config.default_cable_type_id,
            segment_cable_type_ids={},
        )
    except ValueError as exc:
        raise OptimisationInputError(str(exc)) from exc

    # 5. Build scenario and scoring configuration
    # Note: base_seed is omitted from public API to avoid misinterpretation
    scenario_config = ScenarioGenerationConfig(
        project_id=request.project_id,
        candidate_count=request.scenario_config.candidate_count,
        base_seed=42,
    )

    try:
        scoring_config = CandidateScoringConfig(
            route_length_weight=request.scoring_weights.route_length_weight,
            electrical_loss_weight=request.scoring_weights.electrical_loss_weight,
            cable_loading_weight=request.scoring_weights.cable_loading_weight,
            voltage_margin_weight=request.scoring_weights.voltage_margin_weight,
        )
    except ValueError as exc:
        raise OptimisationInputError(str(exc)) from exc

    default_cable_id = request.cable_config.default_cable_type_id
    try:
        default_cable = next(
            c
            for c in request.cable_config.cable_types
            if c.cable_type_id == default_cable_id
        )
    except StopIteration as exc:
        raise OptimisationInputError(
            f"Default cable type {default_cable_id} not found in cable_types."
        ) from exc

    s_mva = (
        (
            math.sqrt(3)
            * request.cable_config.nominal_voltage_kv
            * default_cable.max_current_a
            / 1000.0
        )
        * default_cable.parallel_count
        * default_cable.derating_factor
    )
    feeder_capacity_mw = round(s_mva * request.operating_point_config.power_factor, 3)

    project_input = ProjectInput(
        project_id=request.project_id,
        project_data=project_data,
        cost_surface=cost_surface,
        feeder_capacity_mw=feeder_capacity_mw,
        operating_points=tuple(operating_points),
        constraint_layers=constraint_application.layers,
    )

    config = OptimisationConfig(
        scenario=scenario_config,
        electrical=load_flow_config,
        scoring=scoring_config,
        pole=PolePlacementConfig(
            target_span_m=request.pole_config.target_span_m,
            min_span_m=request.pole_config.min_span_m,
            max_span_m=request.pole_config.max_span_m,
            angle_pole_threshold_deg=request.pole_config.angle_pole_threshold_deg,
        ),
    )

    return WorkflowInvocation(project_input=project_input, config=config)


def to_api_response(
    workflow_result: OptimisationWorkflowResult,
    *,
    request_id: str,
    project_id: str,
) -> OptimiseProjectResponse:
    """Map domain workflow results securely back to API boundaries."""
    generation = None
    if workflow_result.generation_result:
        generation = GenerationSummary(
            requested_candidate_count=workflow_result.generation_result.requested_candidate_count,
            accepted_candidate_count=len(workflow_result.generation_result.candidates),
            attempts=len(workflow_result.generation_result.attempts),
        )

    candidates = []
    for c in workflow_result.candidates:
        eval_result = c.evaluation
        candidates.append(
            CandidateSummary(
                scenario_id=c.scenario.scenario_id,
                parameter_set_id=c.scenario.parameters.parameter_set_id,
                strategy=c.scenario.strategy,
                topology_fingerprint=c.scenario.topology_fingerprint,
                electrical_status="VALID"
                if c.load_flow_result and c.load_flow_result.is_valid
                else ("INVALID" if c.load_flow_result else None),
                eligible=eval_result.assessment.eligible if eval_result else None,
                rank=eval_result.rank if eval_result else None,
                total_benefit_score=eval_result.total_benefit_score
                if eval_result
                else None,
                raw_metrics=dataclasses.asdict(eval_result.assessment.metrics)
                if eval_result and eval_result.assessment.metrics
                else None,
                disqualifications=[
                    d.message for d in eval_result.assessment.disqualifications
                ]
                if eval_result
                else None,
                execution_failure={
                    "code": c.execution_failure.code,
                    "message": c.execution_failure.message,
                }
                if c.execution_failure
                else None,
            )
        )

    recommendation = None
    if workflow_result.recommendation:
        recommendation = RecommendationSummary(
            recommended_scenario_id=workflow_result.recommendation.recommended_scenario_id,
            normalization_ranges={
                r.metric.value: {"minimum": r.minimum, "maximum": r.maximum}
                for r in workflow_result.recommendation.normalization_ranges
            },
            reasons=[r.message for r in workflow_result.recommendation.reasons],
            baseline_comparisons={
                c.metric.value: c.absolute_delta
                for c in workflow_result.recommendation.baseline_comparisons
            },
        )

    failures = []
    for f in workflow_result.failures:
        failures.append(
            FailuresSummary(
                stage=f.stage.value,
                code=f.code.value,
                message=f.message,
                scenario_id=f.scenario_id,
            )
        )

    return OptimiseProjectResponse(
        request_id=request_id,
        project_id=project_id,
        status=workflow_result.status.value,
        generation=generation,
        candidates=candidates,
        recommendation=recommendation,
        recommended_result=workflow_result.recommended_result,
        failures=failures,
    )
