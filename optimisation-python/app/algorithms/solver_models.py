"""Grouping MILP options and telemetry (S5).

Owned by L2 after Stage 0. Stage 0 records status, wall time and gap for every
solve but applies no limits, so behaviour is unchanged.

When limits are applied (WP4-6) note the hazard in ``group_wtgs``: a solve that
returns no assignment currently makes the loop try the next feeder count. A
``LIMIT_REACHED`` solve is not proof of infeasibility and must not be treated as
one.
"""

import math
from dataclasses import dataclass

from app.contracts.codes import SolverStatus

# scipy.optimize.milp status codes.
_SCIPY_STATUS = {
    0: SolverStatus.OPTIMAL,
    1: SolverStatus.LIMIT_REACHED,
    2: SolverStatus.INFEASIBLE,
    3: SolverStatus.UNBOUNDED,
    4: SolverStatus.ERROR,
}


@dataclass(frozen=True)
class SolverOptions:
    """Limits for one grouping MILP solve; ``None`` means unlimited."""

    time_limit_s: float | None = None
    node_limit: int | None = None

    def __post_init__(self) -> None:
        if self.time_limit_s is not None and (
            not math.isfinite(self.time_limit_s) or self.time_limit_s <= 0
        ):
            raise ValueError("time_limit_s must be positive and finite")
        if self.node_limit is not None and (
            isinstance(self.node_limit, bool) or self.node_limit <= 0
        ):
            raise ValueError("node_limit must be a positive integer")


@dataclass(frozen=True)
class SolverTelemetry:
    """What happened in one MILP solve."""

    objective: str
    feeder_count: int
    status: SolverStatus
    wall_time_s: float
    mip_gap: float | None
    time_limit_s: float | None
    node_limit: int | None
    limit_reached: bool


def solver_status_from_scipy(status: int) -> SolverStatus:
    return _SCIPY_STATUS.get(status, SolverStatus.ERROR)
