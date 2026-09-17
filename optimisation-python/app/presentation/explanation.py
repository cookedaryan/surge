"""Scoring explanation for the V1 response. Owned by L3 (WP2-7).

Stage 0 stub: produces nothing, so the ``scoring_explanation`` block stays absent.
"""

from app.contracts.resolution import ResponseContext
from app.contracts.response import ScoringExplanation
from app.optimisation.workflow_models import OptimisationWorkflowResult


def build_scoring_explanation(
    workflow_result: OptimisationWorkflowResult,
    context: ResponseContext,
) -> ScoringExplanation | None:
    return None
