"""Search provenance, solver telemetry and termination for the V1 response.

Owned by L2 (WP4-6, WP4-7). Stage 0 stubs produce nothing, so the
``search_evidence``, ``solver_runs`` and ``termination`` blocks stay absent.
"""

from app.contracts.resolution import ResponseContext
from app.contracts.response import RunTermination, SearchEvidence, SolverRun
from app.optimisation.workflow_models import OptimisationWorkflowResult


def build_search_evidence(
    workflow_result: OptimisationWorkflowResult,
    context: ResponseContext,
) -> SearchEvidence | None:
    return None


def build_solver_runs(
    workflow_result: OptimisationWorkflowResult,
    context: ResponseContext,
) -> list[SolverRun] | None:
    return None


def build_termination(
    workflow_result: OptimisationWorkflowResult,
    context: ResponseContext,
) -> RunTermination | None:
    return None
