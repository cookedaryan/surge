"""Cost evaluation failure models."""

from dataclasses import dataclass
from enum import StrEnum


class CostConfigurationError(ValueError):
    """Raised when costing configuration is invalid globally or at the request level."""


class CostEvaluationFailureCode(StrEnum):
    """Stable reasons why a cost evaluation component failed for a candidate."""

    CABLE_COST_NOT_FOUND = "CABLE_COST_NOT_FOUND"
    POLE_RESULT_UNAVAILABLE = "POLE_RESULT_UNAVAILABLE"
    POLE_COST_NOT_FOUND = "POLE_COST_NOT_FOUND"
    LAND_EXPOSURE_UNAVAILABLE = "LAND_EXPOSURE_UNAVAILABLE"
    LOAD_FLOW_NOT_CONVERGED = "LOAD_FLOW_NOT_CONVERGED"
    ACTIVE_LOSS_MISSING = "ACTIVE_LOSS_MISSING"
    ACTIVE_LOSS_INVALID = "ACTIVE_LOSS_INVALID"
    COST_EVALUATION_ERROR = "COST_EVALUATION_ERROR"


@dataclass(frozen=True)
class CostEvaluationFailure:
    """One diagnostic failure encountered while evaluating a candidate's cost."""

    code: CostEvaluationFailureCode
    component: str
    message: str
    item_id: str | None = None
    segment_id: str | None = None
    pole_id: str | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Cost evaluation failure message must not be blank")
