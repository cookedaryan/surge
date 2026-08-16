import logging

from app.costing.lifecycle import evaluate_candidate_cost
from app.electrical.errors import CandidateElectricalEvaluationError
from app.electrical.repair import RepairStatus, repair_electrical_design
from app.land.decision import assess_candidate_land
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
            failure = CandidateFailure(
                stage=WorkflowStage.ELECTRICAL_VALIDATION,
                code=WorkflowFailureCode.ELECTRICAL_VALIDATION_FAILED,
                message=f"Electrical repair failed: {repair_result.status.value}",
                scenario_id=scenario.scenario_id,
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
    spatial_result = extract_spatial_metrics(
        network=scenario.network,
        constraint_layers=project_input.constraint_layers,
        row_corridor_width_m=project_input.row_width_m,
    )

    # 1.6 Land Assessment
    lifecycle_config = config.costing.lifecycle if config.costing else None
    land_assessment = assess_candidate_land(
        scenario_id=scenario.scenario_id,
        parcel_exposures=spatial_result.parcel_exposures,
        land_context=project_input.land_context,
        lifecycle_config=lifecycle_config,
    )

    if not land_assessment.is_feasible:
        logger.warning(
            "%s crosses unavailable land parcel(s)", scenario.scenario_id
        )
        failure = CandidateFailure(
            stage=WorkflowStage.SCORING,
            code=WorkflowFailureCode.LAND_PARCEL_UNAVAILABLE,
            message="Candidate crosses one or more unavailable parcels.",
            scenario_id=scenario.scenario_id,
        )
        return CandidateWorkflowResult(
            scenario=scenario,
            load_flow_result=repair_result.load_flow_result,
            evaluation=None,
            execution_failure=failure,
            cable_sizing=repair_result.initial_cable_sizing,
            repair_log=repair_result.repair_log,
            land_assessment=land_assessment,
        )

    # 2. Canonical Engineering Metrics
    assessment = build_candidate_engineering_metrics(
        scenario=scenario,
        load_flow_result=repair_result.load_flow_result,
        load_flow_config=repair_result.final_electrical_config,
        spatial_result=spatial_result,
        owner_interaction_count=land_assessment.owner_interaction_count,
        pole_config=config.pole,
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
            land_assessment=land_assessment,
            catalogue=config.costing.catalogue,
            config=config.costing.lifecycle,
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
        engineering_assessment=assessment,
        cost_assessment=cost_assessment,
        cable_sizing=repair_result.initial_cable_sizing,
        repair_log=repair_result.repair_log,
        land_assessment=land_assessment,
    )
