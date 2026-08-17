import logging
from typing import Any

from app.algorithms.pole_micro_siting import PoleMicroSitingContext, optimize_poles
from app.costing.lifecycle import evaluate_candidate_cost
from app.electrical.errors import CandidateElectricalEvaluationError
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.repair import (
    ClosedLoopRepairResult,
    RepairExhaustionReason,
    RepairStatus,
    repair_electrical_design,
)
from app.land.decision import assess_candidate_land
from app.optimisation import engineering_metrics as _engineering_metrics
from app.optimisation.engineering_metric_models import (
    CandidateEngineeringAssessment,
    EngineeringMetricFailure,
    EngineeringMetricFailureCode,
)
from app.optimisation.engineering_metrics import (
    build_candidate_engineering_metrics,
    extract_spatial_metrics,
)
from app.optimisation.scenario_models import PNCScenario
from app.optimisation.workflow_models import (
    CandidateFailure,
    CandidateWorkflowResult,
    OptimisationConfig,
    ProjectInput,
    WorkflowFailureCode,
    WorkflowStage,
)

logger = logging.getLogger(__name__)


def _effective_ampacity_a(cable: LoadFlowCableType) -> float:
    return cable.max_current_a * cable.derating_factor * cable.parallel_count


def _describe_repair_failure(
    repair_result: ClosedLoopRepairResult,
    electrical: LoadFlowConfig,
) -> dict[str, Any]:
    """
    Explain why electrical repair gave up, in terms a reader can act on.

    The caller used to receive only ``Electrical repair failed:
    REPAIR_EXHAUSTED``, which says something was wrong without saying what,
    where, or by how much -- so diagnosing it meant reading server logs.
    Everything needed is already on the repair result: the violations still
    outstanding when it stopped, every upgrade it tried on the way, and the
    catalogue it had to work with.

    The headline names the binding violation with its measured value against
    its limit, because "voltage 0.912 pu against a 0.950 limit" tells an
    engineer what to change and a status code does not. Where the largest
    conductor available was still not enough, that is said explicitly: it is
    usually the actual finding, and it points at the catalogue rather than the
    route.
    """
    violations = (
        list(repair_result.load_flow_result.violations)
        if repair_result.load_flow_result
        else []
    )
    ordered_cables = sorted(electrical.cable_types, key=_effective_ampacity_a)
    largest = ordered_cables[-1] if ordered_cables else None

    unresolved = [
        {
            "code": v.code.value,
            "message": v.message,
            "segment_id": v.segment_id,
            "node_id": v.node_id,
            "feeder_id": v.feeder_id,
            "measured_value": v.measured_value,
            "limit_value": v.limit_value,
        }
        for v in violations
    ]

    attempts = [
        {
            "segment_id": a.segment_id,
            "iteration": a.repair_iteration,
            "from_cable_type_id": a.original_cable_type_id,
            "to_cable_type_id": a.upgraded_cable_type_id,
            "trigger_violation_type": a.trigger_violation_type,
            "reason_code": a.reason_code.value,
            "pre_repair_loading_pct": a.pre_repair_loading_pct,
            "post_repair_loading_pct": a.post_repair_loading_pct,
            "pre_repair_voltage_pu": a.pre_repair_voltage_pu,
            "post_repair_voltage_pu": a.post_repair_voltage_pu,
        }
        for a in repair_result.repair_log
    ]

    summary = _summarise_repair_failure(
        repair_result.status.value, unresolved, attempts, largest
    )

    return {
        "status": repair_result.status.value,
        "summary": summary,
        "no_upgrade_reason_code": (
            repair_result.exhaustion_reason.value
            if repair_result.exhaustion_reason
            else None
        ),
        "no_upgrade_reason": _describe_exhaustion_reason(
            repair_result.exhaustion_reason
        ),
        "unresolved_violations": unresolved,
        "repair_attempts": attempts,
        "largest_cable_available": (
            {
                "cable_type_id": largest.cable_type_id,
                "effective_ampacity_a": round(_effective_ampacity_a(largest), 2),
                "parallel_count": largest.parallel_count,
            }
            if largest
            else None
        ),
        "catalogue_size": len(ordered_cables),
    }


_EXHAUSTION_REASONS: dict[RepairExhaustionReason, str] = {
    RepairExhaustionReason.CABLE_SIZING_FAILED: (
        "Initial cable sizing failed, so no repair was attempted at all."
    ),
    RepairExhaustionReason.NO_LARGER_CONDUCTOR_FOR_OVERLOAD: (
        "No conductor in the catalogue carries the required current, so the "
        "overload cannot be cleared by upgrading. The catalogue is the limit."
    ),
    RepairExhaustionReason.NO_CONDUCTOR_REDUCES_VOLTAGE_DROP: (
        "No conductor in the catalogue has lower impedance than the one already "
        "assigned, so the voltage drop cannot be reduced by upgrading."
    ),
    RepairExhaustionReason.NO_CONDUCTOR_REDUCES_VOLTAGE_RISE: (
        "No conductor upgrade can reduce this voltage rise: the search considers "
        "only conductors of at least equal ampacity and requires no more "
        "capacitance, and larger conductors carry more. Voltage rise on a "
        "lightly loaded feeder is a design question -- reactive compensation, "
        "tap settings or a wider voltage band -- not a conductor choice."
    ),
    RepairExhaustionReason.VIOLATION_HAS_NO_BUS: (
        "The voltage violation named no bus, so there was no path to upgrade along."
    ),
    RepairExhaustionReason.BUS_NOT_IN_ANY_FEEDER: (
        "The offending bus belongs to no feeder in the network, so no path to it "
        "could be identified."
    ),
    RepairExhaustionReason.NO_PATH_FROM_SUBSTATION_TO_BUS: (
        "No path connects the substation to the offending bus, so there were no "
        "segments to upgrade."
    ),
    RepairExhaustionReason.UNSUPPORTED_VIOLATION: (
        "The network is invalid for a reason repair has no strategy for -- "
        "neither an overload nor a voltage violation."
    ),
}


def _describe_exhaustion_reason(reason: RepairExhaustionReason | None) -> str | None:
    """
    Say why no conductor upgrade was made, where the loop knows and the reader
    cannot tell.

    An empty ``repair_attempts`` list looks the same whether the catalogue ran
    out, the violation was one repair cannot address by changing conductors, or
    the network was malformed -- and those call for opposite responses. The loop
    distinguishes all of them internally; without this the distinction died at
    the return statement.
    """
    if reason is None:
        return None
    return _EXHAUSTION_REASONS.get(reason)


def _summarise_repair_failure(
    status: str,
    unresolved: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
    largest: LoadFlowCableType | None,
) -> str:
    """One sentence naming the binding constraint, not the status code."""
    if not unresolved:
        return f"Electrical repair failed ({status}) with no violation reported."

    # Overloads first: an overload has a definite fix (a bigger conductor)
    # whereas a voltage violation may need a different design entirely, so it
    # is the more actionable headline.
    binding = next(
        (v for v in unresolved if v["code"] == "CABLE_OVERLOAD"),
        unresolved[0],
    )
    where = (
        binding["segment_id"]
        or binding["node_id"]
        or binding["feeder_id"]
        or "the network"
    )
    measured = binding["measured_value"]
    limit = binding["limit_value"]

    parts = [f"Electrical repair exhausted: {binding['code']} at {where}"]
    if measured is not None and limit is not None:
        parts.append(f"measured {measured:.3g} against a limit of {limit:.3g}")
    if attempts:
        parts.append(f"after {len(attempts)} conductor upgrade(s)")
    if largest is not None:
        parts.append(
            f"the largest conductor available was {largest.cable_type_id} "
            f"at {_effective_ampacity_a(largest):.0f} A effective"
        )
    return "; ".join(parts) + "."


def evaluate_candidate(
    scenario: PNCScenario,
    project_input: ProjectInput,
    config: OptimisationConfig,
) -> CandidateWorkflowResult:
    """Evaluate one candidate's electrical, engineering, and lifecycle results."""
    wtg_active_power_mw = {
        op.node_id: op.active_power_mw for op in project_input.operating_points
    }
    wtg_reactive_power_mvar = {
        op.node_id: op.reactive_power_mvar for op in project_input.operating_points
    }

    # 1. Electrical Validation
    try:
        repair_result = repair_electrical_design(
            network=scenario.network,
            operating_points=project_input.operating_points,
            config=config.electrical,
            wtg_active_power_mw=wtg_active_power_mw,
            wtg_reactive_power_mvar=wtg_reactive_power_mvar,
            max_iterations=10,
        )
        if repair_result.status != RepairStatus.VALID:
            logger.warning(
                "%s electrical repair stopped with status: %s",
                scenario.scenario_id,
                repair_result.status.value,
            )
            diagnostics = _describe_repair_failure(repair_result, config.electrical)
            failure = CandidateFailure(
                stage=WorkflowStage.ELECTRICAL_VALIDATION,
                code=WorkflowFailureCode.ELECTRICAL_VALIDATION_FAILED,
                message=diagnostics["summary"],
                scenario_id=scenario.scenario_id,
                details=diagnostics,
            )
            return CandidateWorkflowResult(
                scenario=scenario,
                load_flow_result=repair_result.load_flow_result,
                evaluation=None,
                execution_failure=failure,
                cable_sizing=repair_result.initial_cable_sizing,
                repair_log=repair_result.repair_log,
            )
        assert repair_result.load_flow_result is not None
        logger.info("%s electrical validation completed", scenario.scenario_id)
    except CandidateElectricalEvaluationError as e:
        logger.warning(
            "%s electrical execution failed: %s", scenario.scenario_id, str(e)
        )
        failure = CandidateFailure(
            stage=WorkflowStage.ELECTRICAL_VALIDATION,
            code=WorkflowFailureCode.ELECTRICAL_EXECUTION_ERROR,
            message=str(e),
            scenario_id=scenario.scenario_id,
        )
        return CandidateWorkflowResult(
            scenario=scenario,
            load_flow_result=None,
            evaluation=None,
            execution_failure=failure,
        )
    except Exception as e:
        logger.exception(
            "%s unexpected global failure during load flow", scenario.scenario_id
        )
        failure = CandidateFailure(
            stage=WorkflowStage.ELECTRICAL_VALIDATION,
            code=WorkflowFailureCode.UNEXPECTED_EXCEPTION,
            message=str(e),
            scenario_id=scenario.scenario_id,
        )
        return CandidateWorkflowResult(
            scenario=scenario,
            load_flow_result=None,
            evaluation=None,
            execution_failure=failure,
        )

    # 1.5 Spatial Extraction
    spatial_result = None
    try:
        spatial_result = extract_spatial_metrics(
            network=scenario.network,
            constraint_layers=project_input.constraint_layers,
            row_corridor_width_m=project_input.row_width_m,
        )
    except Exception as exc:
        logger.warning("%s spatial analysis failed: %s", scenario.scenario_id, str(exc))

    # 1.6 Initial Pole Placement and Micro-Siting
    pole_result = None
    if config.pole:
        try:
            pole_result = _engineering_metrics.place_poles_on_network(
                scenario.network, config.pole
            )

            if config.pole.micro_siting and config.pole.micro_siting.enabled:
                micro_context = PoleMicroSitingContext(
                    route_geometries={
                        route.route_id: route.geometry for route in pole_result.routes
                    },
                    constraint_layers=project_input.constraint_layers,
                    land_context=project_input.land_context,
                    pole_config=config.pole,
                )
                pole_result, _ = optimize_poles(
                    pole_result, micro_context, config.pole.micro_siting
                )
        except Exception as exc:
            logger.warning(
                "%s pole placement/micro-siting failed: %s",
                scenario.scenario_id,
                str(exc),
            )
            pole_result = None

    # 1.7 Land Assessment
    lifecycle_config = config.costing.lifecycle if config.costing else None
    land_assessment = assess_candidate_land(
        scenario_id=scenario.scenario_id,
        parcel_exposures=(
            spatial_result.parcel_exposures if spatial_result is not None else ()
        ),
        land_context=project_input.land_context,
        lifecycle_config=lifecycle_config,
    )

    # 2. Canonical Engineering Metrics
    assessment = build_candidate_engineering_metrics(
        scenario=scenario,
        load_flow_result=repair_result.load_flow_result,
        load_flow_config=repair_result.final_electrical_config,
        pole_config=config.pole,
        owner_interaction_count=land_assessment.owner_interaction_count,
        spatial_result=spatial_result,
        pole_result=pole_result,
    )

    if not land_assessment.is_feasible:
        logger.warning("%s crosses unavailable land parcel(s)", scenario.scenario_id)
        assessment = CandidateEngineeringAssessment(
            scenario_id=scenario.scenario_id,
            metrics=None,
            engineering_metrics_available=False,
            hard_violation_ids=assessment.hard_violation_ids,
            extraction_failures=(
                EngineeringMetricFailure(
                    code=EngineeringMetricFailureCode.LAND_PARCEL_UNAVAILABLE,
                    message="Candidate crosses one or more unavailable parcels.",
                ),
            ),
            pole_result=pole_result,
            parcel_exposures=assessment.parcel_exposures,
        )
        return CandidateWorkflowResult(
            scenario=scenario,
            load_flow_result=repair_result.load_flow_result,
            evaluation=None,
            execution_failure=None,
            land_assessment=land_assessment,
            engineering_assessment=assessment,
            cable_sizing=repair_result.initial_cable_sizing,
            repair_log=repair_result.repair_log,
        )

    if assessment.engineering_metrics_available:
        logger.info("%s engineering metrics extracted", scenario.scenario_id)
    else:
        logger.warning(
            "%s engineering metrics unavailable: %s",
            scenario.scenario_id,
            ", ".join(f.code for f in assessment.extraction_failures),
        )

    # 3. Optional Lifecycle Cost Evaluation
    cost_assessment = None
    if config.costing is not None:
        cost_assessment = evaluate_candidate_cost(
            scenario=scenario,
            load_flow_result=repair_result.load_flow_result,
            electrical_config=repair_result.final_electrical_config,
            engineering_assessment=assessment,
            catalogue=config.costing.catalogue,
            config=config.costing.lifecycle,
            land_assessment=land_assessment,
        )
        if cost_assessment.cost is not None:
            logger.info("%s lifecycle cost evaluated", scenario.scenario_id)
        else:
            logger.info(
                "%s lifecycle cost unavailable: %s",
                scenario.scenario_id,
                ", ".join(f.code for f in cost_assessment.failures),
            )

    return CandidateWorkflowResult(
        scenario=scenario,
        load_flow_result=repair_result.load_flow_result,
        evaluation=None,
        execution_failure=None,
        land_assessment=land_assessment,
        engineering_assessment=assessment,
        cost_assessment=cost_assessment,
        cable_sizing=repair_result.initial_cable_sizing,
        repair_log=repair_result.repair_log,
    )
