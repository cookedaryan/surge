"""Admission-deadline guard. Owned by L2 (WP4-4).

Stage 0 stub: no deadline is configured, so the guard never stops a run.
"""

from app.optimisation.run_guard import NULL_RUN_GUARD, RunGuard, RunGuardContext


def build_deadline_guard(context: RunGuardContext) -> RunGuard:
    return NULL_RUN_GUARD
