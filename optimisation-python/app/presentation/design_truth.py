"""Installed design truth for the V1 response. Owned by L2 (WP1-2, WP1-5).

Stage 0 stub: produces nothing, so the ``design_truth`` block stays absent.
"""

from app.contracts.resolution import ResponseContext
from app.contracts.response import DesignTruth
from app.optimisation.workflow_models import OptimisationWorkflowResult


def build_design_truth(
    workflow_result: OptimisationWorkflowResult,
    context: ResponseContext,
) -> DesignTruth | None:
    return None
