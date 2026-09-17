"""Run cancellation guard. Owned by L3 (WP4-9a).

Stage 0 stub: nothing can be cancelled yet, so the guard never stops a run.
"""

from app.optimisation.run_guard import NULL_RUN_GUARD, RunGuard, RunGuardContext


def build_cancellation_guard(context: RunGuardContext) -> RunGuard:
    return NULL_RUN_GUARD
