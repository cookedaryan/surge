"""Effective profile, hashes and flag echo for the V1 response. Owned by L3 (WP3-7a).

Stage 0 stub: produces nothing, so the ``effective_profile`` block stays absent.
"""

from app.contracts.resolution import ResponseContext
from app.contracts.response import EffectiveProfile
from app.optimisation.workflow_models import OptimisationWorkflowResult


def build_effective_profile(
    workflow_result: OptimisationWorkflowResult,
    context: ResponseContext,
) -> EffectiveProfile | None:
    return None
