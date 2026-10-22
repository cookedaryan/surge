"""Executable count-reconciliation equations (C4, draft 0.6 §8).

Routing failures count as ``routed_not_evaluated``: the proposal was routed, or
routing was attempted, but no evaluation ran and no cache entry was restored.
"""

from collections.abc import Collection
from dataclasses import dataclass

from app.contracts.response import SearchCounts


@dataclass(frozen=True)
class ReconciliationViolation:
    equation: str
    left: int
    right: int


def reconcile_counts(
    counts: SearchCounts,
    *,
    eligible_ids: Collection[str] | None = None,
    complete_feasible_ids: Collection[str] | None = None,
) -> tuple[ReconciliationViolation, ...]:
    """Return every equation that does not hold; empty means reconciled."""
    violations: list[ReconciliationViolation] = []

    def check(equation: str, left: int, right: int) -> None:
        if left != right:
            violations.append(ReconciliationViolation(equation, left, right))

    check(
        "child_proposals = duplicates + structural_rejects + cache_hits"
        " + routed_not_evaluated + child_evaluations",
        counts.child_proposals,
        counts.duplicates
        + counts.structural_rejects
        + counts.cache_hits
        + counts.routed_not_evaluated
        + counts.child_evaluations,
    )
    check(
        "routed_proposals = cache_hits + routed_not_evaluated + child_evaluations",
        counts.routed_proposals,
        counts.cache_hits + counts.routed_not_evaluated + counts.child_evaluations,
    )
    check(
        "seed_evaluations + child_evaluations = executed_evaluations",
        counts.seed_evaluations + counts.child_evaluations,
        counts.executed_evaluations,
    )
    check(
        "executed_evaluations = successful_evaluations + evaluation_failures",
        counts.executed_evaluations,
        counts.successful_evaluations + counts.evaluation_failures,
    )
    if counts.eligible > counts.feasible:
        violations.append(
            ReconciliationViolation(
                "eligible <= feasible", counts.eligible, counts.feasible
            )
        )
    if eligible_ids is not None and complete_feasible_ids is not None:
        outside = set(eligible_ids) - set(complete_feasible_ids)
        if outside:
            violations.append(
                ReconciliationViolation(
                    "eligible ⊆ complete feasible (fully evaluated or cache-restored)",
                    len(outside),
                    0,
                )
            )
    return tuple(violations)
