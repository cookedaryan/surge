"""Evidence record schema v1 (WP0B-4, C4).

One record describes one measured run of one request variant. The field
dictionary follows draft 0.6 §8. Machine evidence avoids the word "generated";
use the count names in ``SearchCounts`` instead.
"""

from typing import Final, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.codes import (
    CohortExclusionCode,
    ExtraFeederOutcome,
    JobStatus,
    RunTerminationReason,
)
from app.contracts.response import EffectiveProfile, SearchCounts, SolverRun

EVIDENCE_SCHEMA_VERSION: Final = "1.0.0"

FingerprintKind = Literal["topology", "geometry", "final_design"]


class Fingerprinter(Protocol):
    """A versioned canonicaliser.

    Returns ``"<kind>:<version>:<sha256 hex>"``. Implementations live in
    ``app/evidence/fingerprints/``; consumers depend on this protocol only, so
    a test can inject a fake without importing another level's implementation.
    """

    kind: FingerprintKind
    version: str

    def __call__(self, design: object) -> str: ...


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SourceRevisions(_Record):
    python_revision: str
    java_revision: str
    frontend_revision: str
    clean_worktree: bool
    source_artifact_sha256: str | None = None
    lockfile_sha256: dict[str, str]
    image_digests: dict[str, str]


class HostEnvironment(_Record):
    os: str
    python_version: str
    java_version: str | None
    node_version: str | None
    cpu: str
    memory_gb: float = Field(gt=0)
    cold_run: bool
    cold_definition: str


class CatalogueBasis(_Record):
    catalogue_id: str
    version: str
    currency: str
    price_basis_date: str
    cost_assumptions: dict[str, str]


class CandidateFingerprints(_Record):
    topology: str | None
    geometry: str | None
    final_design: str | None
    canonicaliser_versions: dict[str, str]


class CandidateEvidence(_Record):
    candidate_id: str
    parent_id: str | None
    mutation_type: str | None
    fingerprints: CandidateFingerprints
    feasible: bool
    eligible: bool
    failure_codes: list[str]
    raw_metrics: dict[str, float | None]
    contributions: dict[str, float | None] | None
    rank: int | None = Field(default=None, ge=1)
    winner: bool = False
    extra_feeder_outcome: ExtraFeederOutcome | None = None


class ExclusionCount(_Record):
    code: CohortExclusionCode
    count: int = Field(ge=0)


class Timings(_Record):
    total_wall_time_s: float = Field(ge=0)
    routing_time_s: float | None = Field(default=None, ge=0)
    stage_timings_s: dict[str, float]
    job_submitted_to_persisted_s: float | None = Field(default=None, ge=0)
    image_pull_build_s: float | None = Field(default=None, ge=0)


class RunState(_Record):
    job_status: JobStatus
    termination_reason: RunTerminationReason
    admission_deadline_reached: bool
    outer_timeout_reached: bool
    repeatability_matched: bool | None


class EvidenceRecord(_Record):
    schema_version: Literal["1.0.0"] = EVIDENCE_SCHEMA_VERSION
    record_id: str
    request_variant: str
    project_input_sha256: str
    serialised_request_sha256: str
    blinded: bool
    revisions: SourceRevisions
    environment: HostEnvironment
    effective_profile: EffectiveProfile
    profile_version_count: int = Field(ge=0)
    catalogue: CatalogueBasis | None
    counts: SearchCounts
    exclusions: list[ExclusionCount]
    solver_runs: list[SolverRun]
    candidates: list[CandidateEvidence]
    cohort_hash: str | None
    run_state: RunState
    timings: Timings
