"""End-to-End Optimisation package for Surge.

Public API
----------
optimise_project
    Run the complete pipeline from project input to final recommended PNC result.

ProjectInput
    Top-level model for orchestration inputs.

OptimisationConfig
    Top-level configuration for scenario generation, load flow, and scoring.

OptimisationWorkflowResult
    Return type encapsulating statuses, candidates, and recommended network packaging.

OptimisationStatus
    Enum for workflow status representation.
"""

from app.algorithms.wtg_grouping import GroupingObjective
from app.optimisation.orchestrator import optimise_project
from app.optimisation.scenario_models import (
    AttemptOutcome,
    InvalidScenarioConfigError,
    NoValidScenarioError,
    PNCScenario,
    ScenarioAttempt,
    ScenarioGenerationConfig,
    ScenarioGenerationError,
    ScenarioGenerationResult,
    ScenarioParameters,
    ScenarioStrategy,
    TopologyWeightProfile,
)
from app.optimisation.scenarios import generate_pnc_scenarios, scenario_fingerprint
from app.optimisation.scoring import evaluate_cohort
from app.optimisation.scoring_models import (
    CandidateAssessment,
    CandidateEvaluation,
    CandidateMetrics,
    CandidateScoringConfig,
    ElectricallyEvaluatedScenario,
    MetricComparison,
    MetricScore,
    OptimizationRecommendation,
    OptimizationRecommendationStatus,
    RecommendationReason,
)
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

__all__ = [
    "AttemptOutcome",
    "GroupingObjective",
    "InvalidScenarioConfigError",
    "NoValidScenarioError",
    "PNCScenario",
    "ScenarioAttempt",
    "ScenarioGenerationConfig",
    "ScenarioGenerationError",
    "ScenarioGenerationResult",
    "ScenarioParameters",
    "ScenarioStrategy",
    "TopologyWeightProfile",
    "generate_pnc_scenarios",
    "scenario_fingerprint",
    # PY-018 Scoring
    "CandidateScoringConfig",
    "ElectricallyEvaluatedScenario",
    "OptimizationRecommendation",
    "OptimizationRecommendationStatus",
    "CandidateEvaluation",
    "CandidateAssessment",
    "CandidateMetrics",
    "MetricScore",
    "MetricComparison",
    "RecommendationReason",
    "evaluate_cohort",
    # PY-019 Orchestrator
    "CandidateFailure",
    "CandidateWorkflowResult",
    "OptimisationConfig",
    "OptimisationInputError",
    "OptimisationStatus",
    "OptimisationWorkflowResult",
    "ProjectInput",
    "WorkflowFailureCode",
    "WorkflowStage",
    "optimise_project",
]
