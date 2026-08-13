from dataclasses import dataclass
from enum import StrEnum

from app.algorithms.pole_placement import PolePlacementConfig
from app.electrical.load_flow.config import LoadFlowConfig
from app.electrical.load_flow.models import LoadFlowNetworkResult, WTGOperatingPoint
from app.gis.constraints import ConstraintLayer
from app.gis.cost_surface import CostSurface
from app.models.spatial import ProjectSpatialData
from app.optimisation.scenario_models import (
    PNCScenario,
    ScenarioGenerationConfig,
    ScenarioGenerationResult,
)
from app.optimisation.scoring_models import (
    CandidateEvaluation,
    CandidateScoringConfig,
    OptimizationRecommendation,
)
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


@dataclass(frozen=True)
class OptimisationConfig:
    scenario: ScenarioGenerationConfig
    electrical: LoadFlowConfig
    scoring: CandidateScoringConfig
    pole: PolePlacementConfig | None = None


class WorkflowStage(StrEnum):
    PNC_GENERATION = "PNC_GENERATION"
    ELECTRICAL_VALIDATION = "ELECTRICAL_VALIDATION"
    SCORING = "SCORING"
    PACKAGING = "PACKAGING"


class WorkflowFailureCode(StrEnum):
    GENERATION_FAILED = "GENERATION_FAILED"
    ELECTRICAL_EXECUTION_ERROR = "ELECTRICAL_EXECUTION_ERROR"
    SCORING_FAILED = "SCORING_FAILED"
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
    presentation_result: ProjectOptimizationResult | None = None
    packaging_failure: CandidateFailure | None = None

    def __post_init__(self) -> None:
        if self.execution_failure is not None:
            if self.execution_failure.stage != WorkflowStage.ELECTRICAL_VALIDATION:
                raise ValueError(
                    "Execution failure must use the ELECTRICAL_VALIDATION stage."
                )
            if (
                self.execution_failure.code
                != WorkflowFailureCode.ELECTRICAL_EXECUTION_ERROR
            ):
                raise ValueError(
                    "Execution failure must use ELECTRICAL_EXECUTION_ERROR."
                )
            if self.load_flow_result is not None:
                raise ValueError("Execution failure cannot have a load-flow result.")
            if self.evaluation is not None:
                raise ValueError("Execution failure cannot have an evaluation.")
            if self.presentation_result is not None:
                raise ValueError("Execution failure cannot have a presentation result.")
            if self.packaging_failure is not None:
                raise ValueError("Execution failure cannot have a packaging failure.")
        if self.evaluation is not None:
            if self.load_flow_result is None:
                raise ValueError("Evaluation requires a load-flow result.")
            if self.evaluation.assessment.scenario_id != self.scenario.scenario_id:
                raise ValueError(
                    "Evaluation scenario_id must match the candidate scenario."
                )
        if self.presentation_result is not None and self.evaluation is None:
            raise ValueError("Presentation result requires a candidate evaluation.")
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

    def __post_init__(self) -> None:
        candidate_failures = tuple(
            failure
            for candidate in self.candidates
            for failure in (candidate.execution_failure, candidate.packaging_failure)
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
            if not self.recommendation:
                raise ValueError(
                    "NO_FEASIBLE_CANDIDATE requires a recommendation object."
                )
            if self.recommendation.recommended_scenario_id is not None:
                raise ValueError(
                    "NO_FEASIBLE_CANDIDATE must have recommended_scenario_id=None."
                )
            if self.recommended_result is not None:
                raise ValueError(
                    "NO_FEASIBLE_CANDIDATE cannot have a recommended_result."
                )
        elif self.status == OptimisationStatus.FAILED:
            if self.recommendation is not None:
                raise ValueError("FAILED status cannot have a recommendation.")
            if self.recommended_result is not None:
                raise ValueError("FAILED status cannot have a recommended_result.")
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
