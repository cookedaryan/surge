"""Stable machine codes shared by Python, Java, the frontend and evidence (C3).

``contracts/codes.json`` is exported from these enums and a test fails when the
two drift. Values are persisted and compared across languages, so a published
value is never renamed; retire it and add a new one instead.
"""

from enum import StrEnum


class ContractErrorCode(StrEnum):
    """Stable request-rejection codes returned with HTTP 422 or 413."""

    PROFILE_NOT_SUPPORTED = "PROFILE_NOT_SUPPORTED"
    UNKNOWN_PROFILE = "UNKNOWN_PROFILE"
    UNKNOWN_PROFILE_VERSION = "UNKNOWN_PROFILE_VERSION"
    PROFILE_SCENARIO_MISMATCH = "PROFILE_SCENARIO_MISMATCH"
    UNKNOWN_METRIC = "UNKNOWN_METRIC"
    NON_FINITE_VALUE = "NON_FINITE_VALUE"
    VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    INVALID_TYPED_IDENTITY = "INVALID_TYPED_IDENTITY"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


class RunTerminationReason(StrEnum):
    """Why a run or its search stopped.

    A superset of ``SearchTerminationReason``; every value there must exist here
    with the same spelling.
    """

    COMPLETED = "COMPLETED"
    SEARCH_DISABLED = "SEARCH_DISABLED"
    MAX_ROUNDS_REACHED = "MAX_ROUNDS_REACHED"
    EVALUATION_BUDGET_EXHAUSTED = "EVALUATION_BUDGET_EXHAUSTED"
    PROPOSAL_BUDGET_EXHAUSTED = "PROPOSAL_BUDGET_EXHAUSTED"
    ROUTED_PROPOSAL_BUDGET_EXHAUSTED = "ROUTED_PROPOSAL_BUDGET_EXHAUSTED"
    SEED_BUDGET_EXHAUSTED = "SEED_BUDGET_EXHAUSTED"
    CHILD_BUDGET_EXHAUSTED = "CHILD_BUDGET_EXHAUSTED"
    ARCHIVE_LIMIT_REACHED = "ARCHIVE_LIMIT_REACHED"
    NO_NEW_UNIQUE_CANDIDATES = "NO_NEW_UNIQUE_CANDIDATES"
    NO_FEASIBLE_SEARCH_CANDIDATES = "NO_FEASIBLE_SEARCH_CANDIDATES"
    ADMISSION_DEADLINE_REACHED = "ADMISSION_DEADLINE_REACHED"
    SOLVER_LIMIT_REACHED = "SOLVER_LIMIT_REACHED"
    CANCELLED = "CANCELLED"
    NO_ELIGIBLE_CANDIDATE = "NO_ELIGIBLE_CANDIDATE"


class GuardPoint(StrEnum):
    """Places where a run guard is consulted before starting bounded work."""

    BEFORE_SEED_GENERATION = "BEFORE_SEED_GENERATION"
    BEFORE_SEED_EVALUATION = "BEFORE_SEED_EVALUATION"
    BEFORE_CHILD_ROUTING = "BEFORE_CHILD_ROUTING"
    BEFORE_CHILD_EVALUATION = "BEFORE_CHILD_EVALUATION"


class SolverStatus(StrEnum):
    """Outcome of one MILP solve.

    ``LIMIT_REACHED`` must never be treated as ``INFEASIBLE``: a limit that
    stops a solve says nothing about whether that feeder count is feasible.
    """

    OPTIMAL = "OPTIMAL"
    INFEASIBLE = "INFEASIBLE"
    LIMIT_REACHED = "LIMIT_REACHED"
    UNBOUNDED = "UNBOUNDED"
    ERROR = "ERROR"


class SizingBasis(StrEnum):
    """Whether published conductor sizing is the initial pass or what is installed."""

    INITIAL_ONLY = "INITIAL_ONLY"
    FINAL_INSTALLED = "FINAL_INSTALLED"


class CohortExclusionCode(StrEnum):
    """Why a candidate was left out of the shared comparison cohort."""

    EVALUATION_FAILED = "EVALUATION_FAILED"
    INELIGIBLE = "INELIGIBLE"
    MISSING_REQUIRED_METRIC = "MISSING_REQUIRED_METRIC"
    INCOMPLETE_LIFECYCLE_COST = "INCOMPLETE_LIFECYCLE_COST"
    DUPLICATE_FINAL_DESIGN = "DUPLICATE_FINAL_DESIGN"


class CatalogueIncompletenessCode(StrEnum):
    """Why an installable component cannot be priced (catalogue preflight)."""

    UNPRICED_CONDUCTOR = "UNPRICED_CONDUCTOR"
    UNPRICED_POLE_TYPE = "UNPRICED_POLE_TYPE"
    MISSING_LAND_POLICY = "MISSING_LAND_POLICY"
    CURRENCY_MISMATCH = "CURRENCY_MISMATCH"


class ExtraFeederOutcome(StrEnum):
    """Result of trying the explicit ``k+1`` feeder candidate."""

    ACCEPTED = "ACCEPTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CAPACITY_INFEASIBLE = "CAPACITY_INFEASIBLE"
    SOLVER_LIMIT_REACHED = "SOLVER_LIMIT_REACHED"
    DUPLICATE_TOPOLOGY = "DUPLICATE_TOPOLOGY"
    EVALUATION_FAILED = "EVALUATION_FAILED"


class MetricDirection(StrEnum):
    """Whether a lower or higher raw metric value is better."""

    MINIMISE = "minimise"
    MAXIMISE = "maximise"


class ProfilePolicyMode(StrEnum):
    """Scoring policy a profile definition runs under."""

    UNIFIED_ENGINEERING = "UNIFIED_ENGINEERING"
    COST_AWARE = "COST_AWARE"


class JobStatus(StrEnum):
    """Java job lifecycle states, mirrored so evidence can name them."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


CODE_REGISTRY: dict[str, type[StrEnum]] = {
    "ContractErrorCode": ContractErrorCode,
    "RunTerminationReason": RunTerminationReason,
    "GuardPoint": GuardPoint,
    "SolverStatus": SolverStatus,
    "SizingBasis": SizingBasis,
    "CohortExclusionCode": CohortExclusionCode,
    "CatalogueIncompletenessCode": CatalogueIncompletenessCode,
    "ExtraFeederOutcome": ExtraFeederOutcome,
    "MetricDirection": MetricDirection,
    "ProfilePolicyMode": ProfilePolicyMode,
    "JobStatus": JobStatus,
}
