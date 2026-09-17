"""Run guard seam (S4). Frozen after Stage 0.

A run guard is consulted immediately before each unit of bounded work starts
(see ``GuardPoint``). It either returns, letting the work start, or raises a
``RunGuardStop``. Raising keeps every call site identical while each owner
decides the reaction in its own files:

* ``AdmissionDeadlineReached`` comes from ``deadline_guard.py`` (L2). L2 catches
  it inside the search/orchestration code it owns and publishes only fully
  evaluated candidates plus a termination reason (WP4-4, WP4-8).
* ``RunCancelledError`` comes from ``cancellation.py`` (L3). Nothing catches it
  below the endpoint, which answers 409 with code ``CANCELLED`` (WP4-9a).

The guard is cooperative, not pre-emptive: work already started finishes.
"""

import time
from dataclasses import dataclass, field
from typing import Protocol

from app.contracts.codes import GuardPoint, RunTerminationReason


class RunGuardStop(Exception):  # noqa: N818 - a stop signal, not an error
    """Base signal: do not start the next unit of work."""

    reason: RunTerminationReason = RunTerminationReason.COMPLETED

    def __init__(self, point: GuardPoint, message: str | None = None) -> None:
        super().__init__(message or f"{self.reason.value} at {point.value}")
        self.point = point


class AdmissionDeadlineReached(RunGuardStop):  # noqa: N818
    reason = RunTerminationReason.ADMISSION_DEADLINE_REACHED


class RunCancelledError(RunGuardStop):
    reason = RunTerminationReason.CANCELLED


class RunGuard(Protocol):
    def check(self, point: GuardPoint) -> None: ...


class NullRunGuard:
    """Never stops anything; the default everywhere a guard is optional."""

    def check(self, point: GuardPoint) -> None:
        return None


NULL_RUN_GUARD = NullRunGuard()


@dataclass(frozen=True)
class RunGuardContext:
    """What a guard may know about the run it protects."""

    run_id: str | None
    started_monotonic: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class CompositeRunGuard:
    """Cancellation is checked first, so a cancelled run never reports a deadline."""

    cancellation: RunGuard
    deadline: RunGuard

    def check(self, point: GuardPoint) -> None:
        self.cancellation.check(point)
        self.deadline.check(point)


def build_run_guard(context: RunGuardContext) -> RunGuard:
    from app.optimisation.cancellation import build_cancellation_guard
    from app.optimisation.deadline_guard import build_deadline_guard

    return CompositeRunGuard(
        cancellation=build_cancellation_guard(context),
        deadline=build_deadline_guard(context),
    )
