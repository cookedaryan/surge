from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.electrical.repair import RepairAction

from app.algorithms.pole_placement import CollectorPoleResult, PolePlacementConfig
from app.costing.failures import CostConfigurationError
from app.costing.models import (
    CandidateCostAssessment,
    EngineeringCostCatalogue,
    LifecycleCostConfig,
)
from app.electrical.cable_sizing import CableSizingResult
from app.electrical.load_flow.config import LoadFlowConfig
from app.electrical.load_flow.models import LoadFlowNetworkResult, WTGOperatingPoint
from app.gis.constraints import ConstraintLayer
from app.gis.cost_surface import CostSurface
from app.land.models import CandidateLandAssessment, LandCommercialContext
from app.models.spatial import ProjectSpatialData
from app.optimisation.engineering_metric_models import (
    CandidateEngineeringAssessment,
)
from app.optimisation.scenario_models import (
    PNCScenario,
    ScenarioGenerationConfig,
    ScenarioGenerationResult,
)
from app.optimisation.scoring_models import (
    CandidateEvaluation,
    CandidateScoringConfig,
    CostAwareRecommendationConfig,
    OptimizationRecommendation,
)
from app.optimisation.search_models import CandidateSearchConfig, CandidateSearchResult
from app.presentation.models import ProjectOptimizationResult


class OptimisationStatus(StrEnum):
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    NO_FEASIBLE_CANDIDATE = "NO_FEASIBLE_CANDIDATE"
    FAILED = "FAILED"


class OptimisationInputError(Exception):
    """Raised when project data or configuration is invalid before pipeline starts."""

    pass


@dataclass(frozen=True)
class ProjectInput:
    project_id: str
    project_data: ProjectSpatialData
    cost_surface: CostSurface
    feeder_capacity_mw: float
    operating_points: tuple[WTGOperatingPoint, ...]
    constraint_layers: tuple[ConstraintLayer, ...] = ()
    land_context: LandCommercialContext | None = None
    row_width_m: float = 18.0


@dataclass(frozen=True)
class CostingConfig:
    catalogue: EngineeringCostCatalogue
    lifecycle: LifecycleCostConfig

    def __post_init__(self) -> None:
        if self.catalogue.currency.upper() != self.lifecycle.currency.upper():
            raise CostConfigurationError(
                "Cost catalogue currency must match lifecycle configuration currency"
            )


@dataclass(frozen=True)
class OptimisationConfig:
    scenario: ScenarioGenerationConfig
    electrical: LoadFlowConfig
    scoring: CandidateScoringConfig
    pole: PolePlacementConfig | None = None
    costing: CostingConfig | None = None
    cost_aware: CostAwareRecommendationConfig | None = None
    search: CandidateSearchConfig = CandidateSearchConfig()


class WorkflowStage(StrEnum):
    PNC_GENERATION = "PNC_GENERATION"
    ELECTRICAL_VALIDATION = "ELECTRICAL_VALIDATION"
    SCORING = "SCORING"
    POLE_PLACEMENT = "POLE_PLACEMENT"
    PACKAGING = "PACKAGING"


class WorkflowFailureCode(StrEnum):
    GENERATION_FAILED = "GENERATION_FAILED"
    ELECTRICAL_EXECUTION_ERROR = "ELECTRICAL_EXECUTION_ERROR"
    ELECTRICAL_VALIDATION_FAILED = "ELECTRICAL_VALIDATION_FAILED"
    SCORING_FAILED = "SCORING_FAILED"
    LAND_PARCEL_UNAVAILABLE = "LAND_PARCEL_UNAVAILABLE"
    POLE_NETWORK_GENERATION_FAILED = "POLE_NETWORK_GENERATION_FAILED"
    PACKAGING_FAILED = "PACKAGING_FAILED"
    UNEXPECTED_EXCEPTION = "UNEXPECTED_EXCEPTION"


@dataclass(frozen=True)
class CandidateFailure:
    stage: WorkflowStage
    code: WorkflowFailureCode
    message: str
    scenario_id: str | None = None
    parameter_set_id: str | None = None


@dataclass(frozen=True)
class CandidateWorkflowResult:
    scenario: PNCScenario
    load_flow_result: LoadFlowNetworkResult | None
    evaluation: CandidateEvaluation | None
    execution_failure: CandidateFailure | None
    land_assessment: CandidateLandAssessment | None = None
    engineering_assessment: CandidateEngineeringAssessment | None = None
    cost_assessment: CandidateCostAssessment | None = None
    presentation_result: ProjectOptimizationResult | None = None
    pole_failure: CandidateFailure | None = None
    packaging_failure: CandidateFailure | None = None
    cable_sizing: CableSizingResult | None = None
    repair_log: tuple["RepairAction", ...] = ()

    def __post_init__(self) -> None:
        if self.execution_failure is not None:
            valid_stages = (
                WorkflowStage.ELECTRICAL_VALIDATION,
                WorkflowStage.SCORING,
            )
            if self.execution_failure.stage not in valid_stages:
                raise ValueError(
                    "Execution failure must use the ELECTRICAL_VALIDATION "
                    "or SCORING stage."
                )
            if self.execution_failure.code not in (
                WorkflowFailureCode.ELECTRICAL_EXECUTION_ERROR,
                WorkflowFailureCode.ELECTRICAL_VALIDATION_FAILED,
                WorkflowFailureCode.LAND_PARCEL_UNAVAILABLE,
                WorkflowFailureCode.UNEXPECTED_EXCEPTION,
            ):
                raise ValueError("Execution failure has an invalid failure code.")
            if (
                self.execution_failure.code
                == WorkflowFailureCode.ELECTRICAL_EXECUTION_ERROR
                and self.load_flow_result is not None
            ):
                raise ValueError(
                    "ELECTRICAL_EXECUTION_ERROR cannot have a load-flow result."
                )
            if self.evaluation is not None:
                raise ValueError("Execution failure cannot have an evaluation.")
            if self.engineering_assessment is not None:
                raise ValueError(
                    "Execution failure cannot have an engineering assessment."
                )
            if self.cost_assessment is not None:
                raise ValueError("Execution failure cannot have a cost assessment.")
            if self.presentation_result is not None:
                raise ValueError("Execution failure cannot have a presentation result.")
            if self.pole_failure is not None:
                raise ValueError("Execution failure cannot have a pole failure.")
            if self.packaging_failure is not None:
                raise ValueError("Execution failure cannot have a packaging failure.")
        if self.evaluation is not None:
            if self.load_flow_result is None:
                raise ValueError("Evaluation requires a load-flow result.")
            if self.evaluation.assessment.scenario_id != self.scenario.scenario_id:
                raise ValueError(
                    "Evaluation scenario_id must match the candidate scenario."
                )
        if self.engineering_assessment is not None:
            if self.load_flow_result is None:
                raise ValueError("Engineering assessment requires a load-flow result.")
            if self.engineering_assessment.scenario_id != self.scenario.scenario_id:
                raise ValueError(
                    "Engineering assessment scenario_id must match the candidate "
                    "scenario."
                )
        if self.cost_assessment is not None:
            if self.cost_assessment.scenario_id != self.scenario.scenario_id:
                raise ValueError(
                    "Cost assessment scenario_id must match the candidate scenario."
                )
        if self.presentation_result is not None and self.evaluation is None:
            raise ValueError("Presentation result requires a candidate evaluation.")
        if self.pole_failure is not None:
            if self.load_flow_result is None or self.evaluation is None:
                raise ValueError(
                    "Pole failure requires load-flow and evaluation results."
                )
            if self.presentation_result is not None:
                raise ValueError(
                    "Pole failure cannot coexist with a presentation result."
                )
            if self.packaging_failure is not None:
                raise ValueError(
                    "Pole failure cannot coexist with a packaging failure."
                )
            if self.pole_failure.stage != WorkflowStage.POLE_PLACEMENT:
                raise ValueError("Pole failure must use the POLE_PLACEMENT stage.")
            if (
                self.pole_failure.code
                != WorkflowFailureCode.POLE_NETWORK_GENERATION_FAILED
            ):
                raise ValueError(
                    "Pole failure must use POLE_NETWORK_GENERATION_FAILED."
                )
        if self.packaging_failure is not None:
            if self.load_flow_result is None or self.evaluation is None:
                raise ValueError(
                    "Packaging failure requires load-flow and evaluation results."
                )
            if self.presentation_result is not None:
                raise ValueError(
                    "Packaging failure cannot coexist with a presentation result."
                )
            if self.packaging_failure.stage != WorkflowStage.PACKAGING:
                raise ValueError("Packaging failure must use the PACKAGING stage.")
            if self.packaging_failure.code != WorkflowFailureCode.PACKAGING_FAILED:
                raise ValueError("Packaging failure must use PACKAGING_FAILED.")
        if (
            self.execution_failure
            and self.execution_failure.scenario_id
            and self.execution_failure.scenario_id != self.scenario.scenario_id
        ):
            raise ValueError(
                "Execution failure scenario_id must match the candidate scenario."
            )
        if (
            self.pole_failure
            and self.pole_failure.scenario_id
            and self.pole_failure.scenario_id != self.scenario.scenario_id
        ):
            raise ValueError(
                "Pole failure scenario_id must match the candidate scenario."
            )
        if (
            self.packaging_failure
            and self.packaging_failure.scenario_id
            and self.packaging_failure.scenario_id != self.scenario.scenario_id
        ):
            raise ValueError(
                "Packaging failure scenario_id must match the candidate scenario."
            )


@dataclass(frozen=True)
class OptimisationWorkflowResult:
    status: OptimisationStatus
    generation_result: ScenarioGenerationResult | None
    candidates: tuple[CandidateWorkflowResult, ...]
    recommendation: OptimizationRecommendation | None
    recommended_result: ProjectOptimizationResult | None
    failures: tuple[CandidateFailure, ...]
    pole_network: CollectorPoleResult | None = None
    search_result: CandidateSearchResult | None = None

    def __post_init__(self) -> None:
        candidate_failures = tuple(
            failure
            for candidate in self.candidates
            for failure in (
                candidate.execution_failure,
                candidate.pole_failure,
                candidate.packaging_failure,
            )
            if failure is not None
        )
        if any(failure not in self.failures for failure in candidate_failures):
            raise ValueError(
                "Candidate failures must be included in workflow failures."
            )

        for candidate in self.candidates:
            if candidate.execution_failure is None:
                if candidate.load_flow_result is None or candidate.evaluation is None:
                    raise ValueError(
                        "Completed candidates require load-flow and evaluation results."
                    )
                if candidate.engineering_assessment is None:
                    raise ValueError(
                        "Completed candidates require an engineering assessment."
                    )

        if self.status in (
            OptimisationStatus.SUCCESS,
            OptimisationStatus.PARTIAL_SUCCESS,
        ):
            self._validate_success_result()
            if self.status == OptimisationStatus.SUCCESS:
                if self.failures:
                    raise ValueError("SUCCESS status cannot have failures.")
                if (
                    self.generation_result is not None
                    and len(self.candidates)
                    < self.generation_result.requested_candidate_count
                ):
                    raise ValueError(
                        "SUCCESS requires the requested number of candidates."
                    )
            elif not self.failures and (
                self.generation_result is None
                or len(self.candidates)
                >= self.generation_result.requested_candidate_count
            ):
                raise ValueError(
                    "PARTIAL_SUCCESS requires a failure or candidate shortfall."
                )
        elif self.status == OptimisationStatus.NO_FEASIBLE_CANDIDATE:
            if not self.candidates:
                raise ValueError("NO_FEASIBLE_CANDIDATE requires evaluated candidates.")
            if (
                self.recommendation is not None
                and self.recommendation.recommended_scenario_id is not None
            ):
                raise ValueError(
                    "NO_FEASIBLE_CANDIDATE must have recommended_scenario_id=None."
                )
            if self.recommended_result is not None:
                raise ValueError(
                    "NO_FEASIBLE_CANDIDATE cannot have a recommended_result."
                )
            if self.pole_network is not None:
                raise ValueError("NO_FEASIBLE_CANDIDATE cannot have a pole network.")
        elif self.status == OptimisationStatus.FAILED:
            if self.recommendation is not None:
                raise ValueError("FAILED status cannot have a recommendation.")
            if self.recommended_result is not None:
                raise ValueError("FAILED status cannot have a recommended_result.")
            if self.pole_network is not None:
                raise ValueError("FAILED status cannot have a pole network.")
            if not self.failures:
                raise ValueError("FAILED status requires failure diagnostics.")

    def _validate_success_result(self) -> None:
        if self.generation_result is None:
            raise ValueError("Successful workflow requires a generation result.")
        if not self.recommendation or not self.recommended_result:
            raise ValueError(
                "Successful workflow requires recommendation and recommended_result."
            )
        winner_id = self.recommendation.recommended_scenario_id
        if winner_id is None:
            raise ValueError("Successful workflow requires a recommended scenario ID.")
        winner = next(
            (
                candidate
                for candidate in self.candidates
                if candidate.scenario.scenario_id == winner_id
            ),
            None,
        )
        if winner is None or winner.presentation_result is not self.recommended_result:
            raise ValueError(
                "recommended_result must be the recommended candidate presentation."
            )
        if self.pole_network is not None:
            self._validate_pole_network(winner)

    def _validate_pole_network(self, winner: CandidateWorkflowResult) -> None:
        assert self.pole_network is not None
        segments = {
            segment.segment_id: segment
            for feeder in winner.scenario.network.feeders
            for segment in feeder.segments
        }
        routes = {route.route_id: route for route in self.pole_network.routes}
        if set(routes) != set(segments):
            raise ValueError(
                "pole_network routes must exactly cover recommended PNC segments."
            )
        for segment_id, route in routes.items():
            segment = segments[segment_id]
            if (
                route.feeder_id != segment.feeder_id
                or route.start_node_id != segment.from_node_id
                or route.end_node_id != segment.to_node_id
                or not route.geometry.equals_exact(segment.route_geometry, 0.0)
            ):
                raise ValueError(
                    "pole_network must be generated from the recommended PNC geometry."
                )
