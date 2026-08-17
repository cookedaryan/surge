import datetime
import math
from dataclasses import asdict, dataclass, replace
from decimal import Decimal

from app.algorithms.pole_placement import PolePlacementConfig
from app.costing.models import (
    ConductorCostItem,
    EngineeringCostCatalogue,
    LandCostPolicy,
    LandPricingBasis,
    LifecycleCostConfig,
    PoleCostItem,
)
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import WTGOperatingPoint
from app.gis.constraints import ingest_avoidance_constraints
from app.gis.cost_surface import build_project_cost_surface
from app.gis.preprocessing import (
    process_project_data,
    validate_project_routing_endpoints,
)
from app.land.models import (
    CandidateLandAssessment,
    LandAvailabilityStatus,
    LandCommercialContext,
    LandPriceStatus,
    LandTransactionMode,
    LandTransactionTerms,
    ParcelCommercialProfile,
)
from app.optimisation.scenario_models import ScenarioGenerationConfig
from app.optimisation.scoring_models import (
    CandidateScoringConfig,
    CostAwareRecommendationConfig,
    ElectricalScoringWeights,
    ScoringPolicyMode,
    SpatialScoringWeights,
)
from app.optimisation.workflow_models import (
    CostingConfig,
    OptimisationConfig,
    OptimisationInputError,
    OptimisationWorkflowResult,
    ProjectInput,
)
from app.schemas.v2.optimise import (
    CandidateCostSummary,
    CandidateLandSummary,
    CandidateSummary,
    CostFailureSummary,
    CostLineItemSummary,
    EngineeringMetricsSummary,
    FailuresSummary,
    GenerationSummary,
    GroupScoreSummary,
    LandParcelDecisionSummary,
    OptimiseProjectRequest,
    OptimiseProjectResponse,
    RecommendationReasonSummary,
    RecommendationSummary,
)

MAX_WTGS = 500
MAX_RASTER_CELLS = 15_000_000


@dataclass(frozen=True)
class WorkflowInvocation:
    project_input: ProjectInput
    config: OptimisationConfig


def _to_land_summary(
    assessment: "CandidateLandAssessment | None",
) -> CandidateLandSummary | None:
    """Expose the per-parcel land decisions, not only the totals."""
    if assessment is None:
        return None
    return CandidateLandSummary(
        parcel_count=assessment.parcel_count,
        owner_interaction_count=assessment.owner_interaction_count,
        owner_interaction_basis=assessment.owner_interaction_basis.value,
        unknown_owner_count=assessment.unknown_owner_count,
        unavailable_parcel_ids=list(assessment.unavailable_parcel_ids),
        land_cost_basis=assessment.land_cost_basis.value,
        is_feasible=assessment.is_feasible,
        parcel_decisions=[
            LandParcelDecisionSummary(
                parcel_id=d.parcel_id,
                owner_id=d.owner_id,
                availability_status=d.availability_status.value,
                selected_mode=d.selected_mode.value if d.selected_mode else None,
                # Money crosses the wire as a float like every other cost in this
                # response. The Decimal is authoritative inside the engine.
                selected_present_value=(
                    float(d.selected_present_value)
                    if d.selected_present_value is not None
                    else None
                ),
                cost_basis=d.cost_basis.value,
                price_date=d.price_date.isoformat() if d.price_date else None,
                affected_area_m2=d.affected_area_m2,
            )
            for d in assessment.parcel_decisions
        ],
    )


def _to_land_context(
    request: OptimiseProjectRequest,
) -> LandCommercialContext | None:
    context = request.land_context
    if context is None:
        return None
    return LandCommercialContext(
        currency=context.currency,
        as_of_date=context.as_of_date,
        parcel_profiles=tuple(
            ParcelCommercialProfile(
                parcel_id=profile.parcel_id,
                owner_id=profile.owner_id,
                availability_status=LandAvailabilityStatus(profile.availability_status),
                transaction_options=tuple(
                    LandTransactionTerms(
                        mode=LandTransactionMode(option.mode),
                        price_status=LandPriceStatus(option.price_status),
                        upfront_cost=option.upfront_cost,
                        annual_cost=option.annual_cost,
                        term_years=option.term_years,
                        price_date=option.price_date,
                    )
                    for option in profile.transaction_options
                ),
            )
            for profile in context.parcel_profiles
        ),
    )


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
        if active_power_mw > 0 and op_config.power_factor < 1.0:
            apparent_power = active_power_mw / op_config.power_factor
            reactive_magnitude = (apparent_power**2 - active_power_mw**2) ** 0.5
        else:
            reactive_magnitude = 0.0

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
    scenario_config = ScenarioGenerationConfig(
        project_id=request.project_id,
        candidate_count=request.scenario_config.candidate_count,
        base_seed=42,
    )

    try:
        if request.engineering_scoring_weights is not None:
            ew = request.engineering_scoring_weights
            scoring_config = CandidateScoringConfig(
                policy_mode=ScoringPolicyMode.UNIFIED_ENGINEERING,
                physical_weight=ew.physical_weight,
                spatial_weight=ew.spatial_weight,
                infrastructure_weight=ew.infrastructure_weight,
                electrical_weight=ew.electrical_weight,
                spatial_subweights=SpatialScoringWeights(
                    traversal_cost=ew.spatial_subweights.traversal_cost,
                    affected_parcels=ew.spatial_subweights.affected_parcels,
                    road_crossings=ew.spatial_subweights.road_crossings,
                    soft_overlap_length=ew.spatial_subweights.soft_overlap_length,
                    owner_interactions=ew.spatial_subweights.owner_interactions,
                ),
                electrical_subweights=ElectricalScoringWeights(
                    active_loss=ew.electrical_subweights.active_loss,
                    cable_loading=ew.electrical_subweights.cable_loading,
                    voltage_margin=ew.electrical_subweights.voltage_margin,
                ),
            )
        else:
            lw = request.scoring_weights
            elec_weight = (
                lw.electrical_loss_weight
                + lw.cable_loading_weight
                + lw.voltage_margin_weight
            )

            e_loss_sub = (
                lw.electrical_loss_weight / elec_weight if elec_weight > 0 else 0.0
            )
            e_cable_sub = (
                lw.cable_loading_weight / elec_weight if elec_weight > 0 else 0.0
            )
            e_volt_sub = (
                lw.voltage_margin_weight / elec_weight if elec_weight > 0 else 0.0
            )

            scoring_config = CandidateScoringConfig(
                policy_mode=ScoringPolicyMode.LEGACY_COMPATIBILITY,
                physical_weight=lw.route_length_weight,
                spatial_weight=0.0,
                infrastructure_weight=0.0,
                electrical_weight=elec_weight,
                spatial_subweights=SpatialScoringWeights(
                    traversal_cost=0.0,
                    affected_parcels=0.0,
                    road_crossings=0.0,
                    soft_overlap_length=0.0,
                ),
                electrical_subweights=ElectricalScoringWeights(
                    active_loss=e_loss_sub,
                    cable_loading=e_cable_sub,
                    voltage_margin=e_volt_sub,
                ),
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

    try:
        land_context = _to_land_context(request)
    except ValueError as exc:
        raise OptimisationInputError(f"Land context error: {exc}") from exc

    project_input = ProjectInput(
        project_id=request.project_id,
        project_data=project_data,
        cost_surface=cost_surface,
        feeder_capacity_mw=feeder_capacity_mw,
        operating_points=tuple(operating_points),
        constraint_layers=constraint_application.layers,
        land_context=land_context,
        row_width_m=request.routing_config.row_width_m,
    )

    pole_cfg = None
    if request.pole_config is not None:
        pole_cfg = PolePlacementConfig(
            target_span_m=request.pole_config.target_span_m,
            min_span_m=request.pole_config.min_span_m,
            max_span_m=request.pole_config.max_span_m,
            angle_pole_threshold_deg=request.pole_config.angle_pole_threshold_deg,
        )

    costing_cfg = None
    if request.costing_config is not None:
        cat_req = request.costing_config.catalogue
        try:
            catalogue = EngineeringCostCatalogue(
                catalogue_id=cat_req.catalogue_id,
                version=cat_req.version,
                currency=cat_req.currency,
                price_basis_date=datetime.date.fromisoformat(cat_req.price_basis_date),
                conductor_items=tuple(
                    ConductorCostItem(
                        cable_type_id=c.cable_type_id,
                        installed_cost_per_km_per_parallel_circuit=Decimal(
                            str(c.installed_cost_per_km_per_parallel_circuit)
                        ),
                    )
                    for c in cat_req.conductor_items
                ),
                pole_items=tuple(
                    PoleCostItem(
                        pole_type=p.pole_type,
                        installed_cost_each=Decimal(str(p.installed_cost_each)),
                    )
                    for p in cat_req.pole_items
                ),
                land_policy=LandCostPolicy(
                    fixed_cost_per_affected_parcel=Decimal(
                        str(cat_req.land_policy.fixed_cost_per_affected_parcel)
                    ),
                    variable_basis=LandPricingBasis(cat_req.land_policy.variable_basis),
                    variable_rate=Decimal(str(cat_req.land_policy.variable_rate)),
                ),
            )

            life_req = request.costing_config.lifecycle
            lifecycle = LifecycleCostConfig(
                currency=life_req.currency,
                energy_price_basis_date=datetime.date.fromisoformat(
                    life_req.energy_price_basis_date
                ),
                analysis_period_years=life_req.analysis_period_years,
                discount_rate=Decimal(str(life_req.discount_rate)),
                annual_operating_hours=life_req.annual_operating_hours,
                loss_load_factor=Decimal(str(life_req.loss_load_factor)),
                energy_price_per_mwh=Decimal(str(life_req.energy_price_per_mwh)),
            )
            if land_context and (
                land_context.currency.casefold() != lifecycle.currency.casefold()
            ):
                raise ValueError(
                    "Land commercial context currency must match lifecycle currency"
                )
            costing_cfg = CostingConfig(catalogue=catalogue, lifecycle=lifecycle)
        except Exception as exc:
            raise OptimisationInputError(f"Costing configuration error: {exc}") from exc

    cost_aware_cfg = None
    if request.cost_aware_config is not None:
        cost_aware_cfg = CostAwareRecommendationConfig(
            engineering_weight=request.cost_aware_config.engineering_weight,
            lifecycle_cost_weight=request.cost_aware_config.lifecycle_cost_weight,
        )
        scoring_config = replace(
            scoring_config,
            policy_mode=ScoringPolicyMode.COST_AWARE,
        )

    config = OptimisationConfig(
        scenario=scenario_config,
        electrical=load_flow_config,
        scoring=scoring_config,
        pole=pole_cfg,
        costing=costing_cfg,
        cost_aware=cost_aware_cfg,
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

        raw_metrics = None
        engineering_metrics = None
        group_scores = None
        if eval_result and eval_result.assessment.metrics:
            m = eval_result.assessment.metrics
            raw_metrics = {
                "total_route_length_m": m.total_route_length_m,
                "total_active_loss_mw": m.total_active_loss_mw,
                "maximum_loading_percent": m.maximum_loading_percent,
                "voltage_margin_pu": m.voltage_margin_pu,
            }
            engineering_metrics = EngineeringMetricsSummary(
                total_route_length_m=m.total_route_length_m,
                total_traversal_cost=m.total_traversal_cost,
                affected_parcel_count=m.affected_parcel_count,
                owner_interaction_count=m.owner_interaction_count,
                road_crossing_count=m.road_crossing_count,
                soft_constraint_overlap_length_m=m.soft_constraint_overlap_length_m,
                environmental_overlap_m2=m.environmental_overlap_m2,
                physical_pole_count=m.physical_pole_count,
                total_active_loss_mw=m.total_active_loss_mw,
                maximum_loading_percent=m.maximum_loading_percent,
                voltage_margin_pu=m.voltage_margin_pu,
            )
        if eval_result and eval_result.group_scores:
            group_scores = [
                GroupScoreSummary(
                    group=g.group.value,
                    group_score=g.group_score,
                    group_weight=g.group_weight,
                    weighted_score=g.weighted_score,
                )
                for g in eval_result.group_scores
            ]

        cost_summary = None
        if c.cost_assessment:
            ca = c.cost_assessment
            complete_cost = ca.cost
            cost_summary = CandidateCostSummary(
                conductor_capex=(
                    float(ca.conductor_capex_amount)
                    if ca.conductor_capex_amount is not None
                    else None
                ),
                pole_capex=(
                    float(ca.pole_capex_amount)
                    if ca.pole_capex_amount is not None
                    else None
                ),
                land_capex=(
                    float(ca.land_purchase_capex_amount)
                    if ca.land_purchase_capex_amount is not None
                    else None
                ),
                land_purchase_capex=(
                    float(ca.land_purchase_capex_amount)
                    if ca.land_purchase_capex_amount is not None
                    else None
                ),
                land_recurring_cost_pv=(
                    float(ca.land_recurring_cost_pv_amount)
                    if ca.land_recurring_cost_pv_amount is not None
                    else None
                ),
                land_access_present_value=(
                    float(ca.land_access_present_value_amount)
                    if ca.land_access_present_value_amount is not None
                    else None
                ),
                total_capex=(
                    float(ca.total_capex_amount)
                    if ca.total_capex_amount is not None
                    else None
                ),
                annual_loss_energy_mwh=(
                    float(ca.annual_loss_energy_mwh)
                    if ca.annual_loss_energy_mwh is not None
                    else None
                ),
                annual_loss_cost=(
                    float(ca.annual_loss_cost_amount)
                    if ca.annual_loss_cost_amount is not None
                    else None
                ),
                present_value_factor=(
                    float(ca.present_value_factor)
                    if ca.present_value_factor is not None
                    else None
                ),
                present_value_opex=(
                    float(ca.present_value_opex_amount)
                    if ca.present_value_opex_amount is not None
                    else None
                ),
                lifecycle_cost=(
                    float(complete_cost.lifecycle_cost) if complete_cost else None
                ),
                line_items=[
                    CostLineItemSummary(
                        category=li.category,
                        item_id=li.item_id,
                        quantity=float(li.quantity),
                        unit=li.unit,
                        unit_rate=float(li.unit_rate),
                        amount=float(li.amount),
                    )
                    for li in ca.line_items
                ],
                currency=ca.currency,
                catalogue_id=ca.catalogue_id,
                catalogue_version=ca.catalogue_version,
                catalogue_price_basis_date=(
                    ca.catalogue_price_basis_date.isoformat()
                    if ca.catalogue_price_basis_date
                    else None
                ),
                energy_price_basis_date=(
                    ca.energy_price_basis_date.isoformat()
                    if ca.energy_price_basis_date
                    else None
                ),
                cost_model_version=ca.cost_model_version,
                failures=[
                    CostFailureSummary(
                        code=f.code.value,
                        component=f.component,
                        message=f.message,
                        item_id=f.item_id,
                        segment_id=f.segment_id,
                        pole_id=f.pole_id,
                    )
                    for f in ca.failures
                ],
            )

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
                engineering_benefit_score=eval_result.engineering_benefit_score
                if eval_result
                else None,
                economic_benefit_score=eval_result.economic_benefit_score
                if eval_result
                else None,
                final_benefit_score=eval_result.final_benefit_score
                if eval_result
                else None,
                total_benefit_score=eval_result.total_benefit_score
                if eval_result
                else None,
                raw_metrics=raw_metrics,
                engineering_metrics=engineering_metrics,
                cost=cost_summary,
                group_scores=group_scores,
                disqualifications=[
                    d.message for d in eval_result.assessment.disqualifications
                ]
                if eval_result
                else None,
                execution_failure={
                    "code": c.execution_failure.code,
                    "message": c.execution_failure.message,
                    # Structured evidence, so a caller can say which segment
                    # and which limit defeated the run instead of relaying a
                    # status code and sending someone to the server logs.
                    **(
                        {"details": dict(c.execution_failure.details)}
                        if c.execution_failure.details
                        else {}
                    ),
                }
                if c.execution_failure
                else None,
                cable_sizing=asdict(c.cable_sizing) if c.cable_sizing else None,
                land=_to_land_summary(c.land_assessment),
            )
        )

    recommendation = None
    if workflow_result.recommendation:
        recommendation = RecommendationSummary(
            recommended_scenario_id=workflow_result.recommendation.recommended_scenario_id,
            engineering_best_scenario_id=workflow_result.recommendation.engineering_best_scenario_id,
            lowest_cost_scenario_id=workflow_result.recommendation.lowest_cost_scenario_id,
            policy=workflow_result.recommendation.policy,
            economic_context_id=workflow_result.recommendation.economic_context_id,
            normalization_ranges={
                r.metric.value: {"minimum": r.minimum, "maximum": r.maximum}
                for r in workflow_result.recommendation.normalization_ranges
            },
            reasons=[r.message for r in workflow_result.recommendation.reasons],
            reason_details=[
                RecommendationReasonSummary(
                    code=r.code.value,
                    message=r.message,
                    metric=r.metric.value if r.metric else None,
                    candidate_value=r.candidate_value,
                    comparison_value=r.comparison_value,
                )
                for r in workflow_result.recommendation.reasons
            ],
            baseline_comparisons={
                c.metric_name: c.absolute_delta
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
