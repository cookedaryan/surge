"""Controlled comparison-cohort runner. Owned by L3 (WP0B-11).

Unions fully evaluated candidates, deduplicates by final-design fingerprint
(keeping the lowest sorted candidate ID and recording discarded lineages),
applies identical feasibility rules, excludes candidates missing any required
metric with ``CohortExclusionCode`` counts, and reports distinct eligible
topologies. Fingerprinters are injected through ``app.contracts.evidence``.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.contracts.evidence import (
    CandidateEvidence,
    ExclusionCount,
    Fingerprinter,
)


@dataclass(frozen=True)
class CohortResult:
    cohort_hash: str
    members: tuple[CandidateEvidence, ...]
    exclusions: tuple[ExclusionCount, ...]
    discarded_duplicate_lineages: tuple[tuple[str, str], ...]
    distinct_eligible_topologies: int


def build_cohort(
    candidates: Sequence[CandidateEvidence],
    *,
    required_metrics: frozenset[str],
    maximum_exclusion_rate: float,
    topology_fingerprinter: Fingerprinter,
    final_design_fingerprinter: Fingerprinter,
) -> CohortResult:
    raise NotImplementedError("Implemented by WP0B-11 (L3)")
