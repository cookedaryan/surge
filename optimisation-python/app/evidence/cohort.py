"""Controlled comparison-cohort runner. Owned by L3 (WP0B-11).

Unions fully evaluated candidates, deduplicates by final-design fingerprint
(keeping the lowest sorted candidate ID and recording discarded lineages),
applies identical feasibility rules, excludes candidates missing any required
metric with ``CohortExclusionCode`` counts, and reports distinct eligible
topologies. Fingerprinters are injected through ``app.contracts.evidence``.

Rules, runner version 1 (draft 0.6 §4.2)
----------------------------------------
Each input candidate is excluded by the first rule it meets, in this order:

1. ``EVALUATION_FAILED``: no design was produced, so nothing can be
   fingerprinted.
2. ``DUPLICATE_FINAL_DESIGN``: another candidate has the same final-design
   fingerprint and a lower candidate ID. The pair ``(discarded, kept)`` is
   recorded. The kept representative then meets rules 3–6 alone, so a design
   is judged once, by its representative's evidence.
3. ``INELIGIBLE``: not engineering-feasible.
4. ``INCOMPLETE_LIFECYCLE_COST``: the evaluator reported that failure code.
   This comes before the generic eligibility rule so that a ``k+1`` candidate
   losing its lifecycle cost is counted under its own code (R2-C8).
5. ``INELIGIBLE``: feasible but not eligible.
6. ``MISSING_REQUIRED_METRIC``: a metric required by any profile is absent or
   null.

Candidate IDs must be unique across the union. Callers running several
generation configurations namespace the IDs first, because ``SCN-001`` from two
runs is not the same design.

The exclusion rate is the share of non-duplicate candidates excluded for any
other reason. Deduplication is not a loss, so it does not count. The cohort is
rejected, with the result attached, when that rate exceeds the maximum or no
member remains.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from app.contracts.canonical_json import canonical_sha256
from app.contracts.codes import CohortExclusionCode
from app.contracts.evidence import (
    CandidateEvidence,
    ExclusionCount,
    Fingerprinter,
)

COHORT_RUNNER_VERSION = "1"


@dataclass(frozen=True)
class CohortCandidate:
    """One fully or partly evaluated candidate from any generation run.

    ``design`` is passed unchanged to both injected fingerprinters; it is
    ``None`` when evaluation produced no design.
    """

    evidence: CandidateEvidence
    design: object | None


@dataclass(frozen=True)
class CohortResult:
    cohort_hash: str
    members: tuple[CandidateEvidence, ...]
    exclusions: tuple[ExclusionCount, ...]
    discarded_duplicate_lineages: tuple[tuple[str, str], ...]
    distinct_eligible_topologies: int
    excluded_candidates: tuple[tuple[str, CohortExclusionCode], ...]
    exclusion_rate: float


class CohortRejectedError(ValueError):
    """The cohort cannot be used for comparison; ``result`` still carries counts."""

    def __init__(self, message: str, result: CohortResult) -> None:
        super().__init__(message)
        self.result = result


class FingerprintMismatchError(ValueError):
    """A recorded fingerprint differs from the one computed now."""


def _fingerprint(fingerprinter: Fingerprinter, candidate: CohortCandidate) -> str:
    value = fingerprinter(candidate.design)
    prefix = f"{fingerprinter.kind}:{fingerprinter.version}:"
    if not value.startswith(prefix):
        raise FingerprintMismatchError(
            f"{candidate.evidence.candidate_id}: {fingerprinter.kind} fingerprinter "
            f"returned {value!r}, expected the prefix {prefix!r}"
        )
    recorded = getattr(candidate.evidence.fingerprints, fingerprinter.kind)
    if recorded is not None and recorded != value:
        raise FingerprintMismatchError(
            f"{candidate.evidence.candidate_id}: recorded {fingerprinter.kind} "
            f"fingerprint {recorded} is not the computed {value}"
        )
    return value


def _rule_exclusion(
    evidence: CandidateEvidence, required_metrics: frozenset[str]
) -> CohortExclusionCode | None:
    if not evidence.feasible:
        return CohortExclusionCode.INELIGIBLE
    if CohortExclusionCode.INCOMPLETE_LIFECYCLE_COST.value in evidence.failure_codes:
        return CohortExclusionCode.INCOMPLETE_LIFECYCLE_COST
    if not evidence.eligible:
        return CohortExclusionCode.INELIGIBLE
    if any(evidence.raw_metrics.get(metric) is None for metric in required_metrics):
        return CohortExclusionCode.MISSING_REQUIRED_METRIC
    return None


def _with_fingerprints(
    evidence: CandidateEvidence,
    fingerprinters: Sequence[Fingerprinter],
    values: Sequence[str],
) -> CandidateEvidence:
    update: dict[str, object] = {}
    versions = dict(evidence.fingerprints.canonicaliser_versions)
    for fingerprinter, value in zip(fingerprinters, values, strict=True):
        update[fingerprinter.kind] = value
        versions[fingerprinter.kind] = fingerprinter.version
    update["canonicaliser_versions"] = versions
    fingerprints = evidence.fingerprints.model_copy(update=update)
    return evidence.model_copy(update={"fingerprints": fingerprints})


def build_cohort(
    candidates: Sequence[CohortCandidate],
    *,
    required_metrics: frozenset[str],
    maximum_exclusion_rate: float,
    topology_fingerprinter: Fingerprinter,
    final_design_fingerprinter: Fingerprinter,
) -> CohortResult:
    if not candidates:
        raise ValueError("a cohort needs at least one candidate")
    if not (
        math.isfinite(maximum_exclusion_rate) and 0.0 <= maximum_exclusion_rate <= 1.0
    ):
        raise ValueError("maximum_exclusion_rate must be within [0, 1]")
    if topology_fingerprinter.kind != "topology":
        raise ValueError("topology_fingerprinter must have kind 'topology'")
    if final_design_fingerprinter.kind != "final_design":
        raise ValueError("final_design_fingerprinter must have kind 'final_design'")
    ids = [candidate.evidence.candidate_id for candidate in candidates]
    if len(set(ids)) != len(ids):
        raise ValueError("candidate IDs must be unique across the cohort union")

    excluded: dict[str, CohortExclusionCode] = {}
    representatives: dict[str, CohortCandidate] = {}
    lineages: list[tuple[str, str]] = []

    for candidate in sorted(candidates, key=lambda c: c.evidence.candidate_id):
        candidate_id = candidate.evidence.candidate_id
        if candidate.design is None:
            excluded[candidate_id] = CohortExclusionCode.EVALUATION_FAILED
            continue
        final_design = _fingerprint(final_design_fingerprinter, candidate)
        kept = representatives.get(final_design)
        if kept is not None:
            excluded[candidate_id] = CohortExclusionCode.DUPLICATE_FINAL_DESIGN
            lineages.append((candidate_id, kept.evidence.candidate_id))
            continue
        representatives[final_design] = candidate

    members: list[CandidateEvidence] = []
    for final_design, candidate in representatives.items():
        code = _rule_exclusion(candidate.evidence, required_metrics)
        if code is not None:
            excluded[candidate.evidence.candidate_id] = code
            continue
        topology = _fingerprint(topology_fingerprinter, candidate)
        members.append(
            _with_fingerprints(
                candidate.evidence,
                (topology_fingerprinter, final_design_fingerprinter),
                (topology, final_design),
            )
        )
    members.sort(key=lambda evidence: evidence.candidate_id)

    counts = {code: 0 for code in CohortExclusionCode}
    for code in excluded.values():
        counts[code] += 1
    duplicates = counts[CohortExclusionCode.DUPLICATE_FINAL_DESIGN]
    considered = len(candidates) - duplicates
    lost = sum(counts.values()) - duplicates
    exclusion_rate = lost / considered

    result = CohortResult(
        cohort_hash=canonical_sha256(
            {
                "cohort_runner_version": COHORT_RUNNER_VERSION,
                "required_metrics": sorted(required_metrics),
                "final_design_fingerprints": sorted(
                    str(m.fingerprints.final_design) for m in members
                ),
            }
        ),
        members=tuple(members),
        exclusions=tuple(
            ExclusionCount(code=code, count=count)
            for code, count in counts.items()
            if count
        ),
        discarded_duplicate_lineages=tuple(lineages),
        distinct_eligible_topologies=len({m.fingerprints.topology for m in members}),
        excluded_candidates=tuple(sorted(excluded.items())),
        exclusion_rate=exclusion_rate,
    )
    if exclusion_rate > maximum_exclusion_rate:
        raise CohortRejectedError(
            f"exclusion rate {exclusion_rate:.3f} exceeds the maximum "
            f"{maximum_exclusion_rate:.3f}",
            result,
        )
    if not members:
        raise CohortRejectedError("no candidate is eligible for the cohort", result)
    return result
