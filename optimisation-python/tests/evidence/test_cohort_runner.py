"""WP0B-11: controlled-cohort runner, version 1."""

import hashlib
import json
from dataclasses import dataclass
from typing import Literal

import pytest

from app.contracts.codes import CohortExclusionCode
from app.contracts.evidence import (
    CandidateEvidence,
    CandidateFingerprints,
    EvidenceRecord,
    FingerprintKind,
)
from app.evidence.cohort import (
    CohortCandidate,
    CohortRejectedError,
    CohortResult,
    FingerprintMismatchError,
    build_cohort,
)
from app.evidence.fingerprints.final_design import (
    FinalDesign,
    FinalDesignFingerprinter,
)
from scripts.contracts.export_contracts import CONTRACTS
from tests.evidence.test_final_design_fingerprint import CONDUCTORS, truth_for
from tests.evidence.test_geometry_fingerprint import build_network

Code = CohortExclusionCode


@dataclass(frozen=True)
class FakeDesign:
    topology: str
    final_design: str


class FakeFingerprinter:
    """Hashes one named field of a ``FakeDesign``; no real canonicaliser."""

    def __init__(self, kind: FingerprintKind, version: str = "9") -> None:
        self.kind: FingerprintKind = kind
        self.version = version

    def __call__(self, design: object) -> str:
        assert isinstance(design, FakeDesign)
        key = getattr(design, self.kind)
        return f"{self.kind}:{self.version}:{hashlib.sha256(key.encode()).hexdigest()}"


def evidence(
    candidate_id: str,
    *,
    feasible: bool = True,
    eligible: bool = True,
    failure_codes: tuple[str, ...] = (),
    metrics: dict[str, float | None] | None = None,
    recorded: dict[str, str | None] | None = None,
) -> CandidateEvidence:
    recorded = recorded or {}
    return CandidateEvidence(
        candidate_id=candidate_id,
        parent_id=None,
        mutation_type=None,
        fingerprints=CandidateFingerprints(
            topology=recorded.get("topology"),
            geometry=None,
            final_design=recorded.get("final_design"),
            canonicaliser_versions={},
        ),
        feasible=feasible,
        eligible=eligible,
        failure_codes=list(failure_codes),
        raw_metrics={"cost": 1.0, "land": 2.0} if metrics is None else metrics,
        contributions=None,
    )


def candidate(
    candidate_id: str,
    topology: str | None = "T1",
    final_design: str | None = None,
    **kwargs: object,
) -> CohortCandidate:
    design = (
        None
        if topology is None
        else FakeDesign(topology, final_design or f"{topology}/{candidate_id}")
    )
    return CohortCandidate(evidence(candidate_id, **kwargs), design)  # type: ignore[arg-type]


def run(
    candidates: list[CohortCandidate],
    *,
    required: frozenset[str] = frozenset({"cost", "land"}),
    maximum: float = 1.0,
) -> CohortResult:
    return build_cohort(
        candidates,
        required_metrics=required,
        maximum_exclusion_rate=maximum,
        topology_fingerprinter=FakeFingerprinter("topology"),
        final_design_fingerprinter=FakeFingerprinter("final_design"),
    )


def counts(result: CohortResult) -> dict[str, int]:
    return {e.code.value: e.count for e in result.exclusions}


# --- deduplication --------------------------------------------------------------------


def test_duplicates_keep_the_lowest_sorted_id_and_record_lineages() -> None:
    result = run(
        [
            candidate("b/SCN-002", "T1", "D1"),
            candidate("a/SCN-010", "T1", "D1"),
            candidate("c/SCN-001", "T1", "D1"),
            candidate("a/SCN-002", "T2", "D2"),
        ]
    )
    assert [m.candidate_id for m in result.members] == ["a/SCN-002", "a/SCN-010"]
    assert result.discarded_duplicate_lineages == (
        ("b/SCN-002", "a/SCN-010"),
        ("c/SCN-001", "a/SCN-010"),
    )
    assert counts(result) == {"DUPLICATE_FINAL_DESIGN": 2}
    # Deduplication is not a loss: nothing else was excluded.
    assert result.exclusion_rate == 0.0


def test_representative_is_judged_by_its_own_evidence() -> None:
    result = run(
        [
            candidate("SCN-001", "T1", "D1", eligible=False),
            candidate("SCN-002", "T1", "D1"),
            candidate("SCN-003", "T2", "D2"),
        ]
    )
    assert [m.candidate_id for m in result.members] == ["SCN-003"]
    assert dict(result.excluded_candidates) == {
        "SCN-001": Code.INELIGIBLE,
        "SCN-002": Code.DUPLICATE_FINAL_DESIGN,
    }


# --- exclusion codes and precedence ---------------------------------------------------


def test_every_exclusion_code_is_counted_in_rule_order() -> None:
    result = run(
        [
            candidate("SCN-001", None),
            candidate("SCN-002", "T1", "D1"),
            candidate("SCN-003", "T1", "D1"),
            candidate(
                "SCN-004",
                "T2",
                feasible=False,
                eligible=False,
                failure_codes=("INCOMPLETE_LIFECYCLE_COST",),
            ),
            candidate(
                "SCN-005",
                "T3",
                eligible=False,
                failure_codes=("INCOMPLETE_LIFECYCLE_COST",),
            ),
            candidate("SCN-006", "T4", eligible=False),
            candidate("SCN-007", "T5", metrics={"cost": 1.0}),
            candidate("SCN-008", "T6", metrics={"cost": 1.0, "land": None}),
        ],
    )
    assert dict(result.excluded_candidates) == {
        "SCN-001": Code.EVALUATION_FAILED,
        "SCN-003": Code.DUPLICATE_FINAL_DESIGN,
        "SCN-004": Code.INELIGIBLE,
        "SCN-005": Code.INCOMPLETE_LIFECYCLE_COST,
        "SCN-006": Code.INELIGIBLE,
        "SCN-007": Code.MISSING_REQUIRED_METRIC,
        "SCN-008": Code.MISSING_REQUIRED_METRIC,
    }
    assert counts(result) == {
        "EVALUATION_FAILED": 1,
        "INELIGIBLE": 2,
        "MISSING_REQUIRED_METRIC": 2,
        "INCOMPLETE_LIFECYCLE_COST": 1,
        "DUPLICATE_FINAL_DESIGN": 1,
    }
    # Codes are reported in registry order.
    assert [e.code for e in result.exclusions] == [
        code for code in Code if counts(result).get(code.value)
    ]
    assert result.exclusion_rate == pytest.approx(6 / 7)
    assert [m.candidate_id for m in result.members] == ["SCN-002"]


@pytest.mark.parametrize(
    ("required", "expected_members"),
    [
        (frozenset(), ["SCN-001", "SCN-002", "SCN-003"]),
        (frozenset({"cost"}), ["SCN-001", "SCN-002"]),
        (frozenset({"cost", "land"}), ["SCN-001"]),
        (frozenset({"cost", "land", "environment"}), []),
    ],
)
def test_required_metric_sets_are_injected(
    required: frozenset[str], expected_members: list[str]
) -> None:
    candidates = [
        candidate("SCN-001", "T1", metrics={"cost": 1.0, "land": 0.0}),
        candidate("SCN-002", "T2", metrics={"cost": 1.0}),
        candidate("SCN-003", "T3", metrics={}),
    ]
    if not expected_members:
        with pytest.raises(CohortRejectedError) as raised:
            run(candidates, required=required)
        assert raised.value.result.members == ()
        return
    result = run(candidates, required=required)
    assert [m.candidate_id for m in result.members] == expected_members


# --- exclusion rate -------------------------------------------------------------------


def test_exclusion_rate_above_the_maximum_rejects_with_counts_attached() -> None:
    candidates = [
        candidate("SCN-001", "T1"),
        candidate("SCN-002", "T2"),
        candidate("SCN-003", "T3", metrics={}),
        candidate("SCN-004", "T4", "D-shared"),
        candidate("SCN-005", "T4", "D-shared"),
    ]
    # 1 of 4 non-duplicate candidates is excluded.
    assert run(candidates, maximum=0.25).exclusion_rate == 0.25
    with pytest.raises(CohortRejectedError) as raised:
        run(candidates, maximum=0.2)
    assert counts(raised.value.result) == {
        "MISSING_REQUIRED_METRIC": 1,
        "DUPLICATE_FINAL_DESIGN": 1,
    }


# --- topology count and fingerprints on members ---------------------------------------


def test_distinct_topologies_count_eligible_members_only() -> None:
    result = run(
        [
            candidate("SCN-001", "T1", "D1"),
            candidate("SCN-002", "T1", "D1-larger-conductor"),
            candidate("SCN-003", "T2", "D2"),
            candidate("SCN-004", "T3", "D3", feasible=False),
        ]
    )
    assert len(result.members) == 3
    assert result.distinct_eligible_topologies == 2


def test_members_carry_both_fingerprints_and_their_versions() -> None:
    (member,) = run([candidate("SCN-001", "T1", "D1")]).members
    digest = hashlib.sha256(b"D1").hexdigest()
    assert member.fingerprints.final_design == f"final_design:9:{digest}"
    assert member.fingerprints.topology == (
        f"topology:9:{hashlib.sha256(b'T1').hexdigest()}"
    )
    assert member.fingerprints.canonicaliser_versions == {
        "topology": "9",
        "final_design": "9",
    }


def test_recorded_fingerprints_must_match_the_computed_ones() -> None:
    good = f"final_design:9:{hashlib.sha256(b'D1').hexdigest()}"
    run([candidate("SCN-001", "T1", "D1", recorded={"final_design": good})])
    with pytest.raises(FingerprintMismatchError):
        run(
            [
                candidate(
                    "SCN-001", "T1", "D1", recorded={"final_design": good[:-1] + "0"}
                )
            ]
        )


def test_fingerprinter_output_must_carry_its_own_kind_and_version() -> None:
    class Liar(FakeFingerprinter):
        def __call__(self, design: object) -> str:
            return super().__call__(design).replace(":9:", ":8:")

    with pytest.raises(FingerprintMismatchError):
        build_cohort(
            [candidate("SCN-001")],
            required_metrics=frozenset(),
            maximum_exclusion_rate=1.0,
            topology_fingerprinter=FakeFingerprinter("topology"),
            final_design_fingerprinter=Liar("final_design"),
        )


# --- cohort identity and determinism --------------------------------------------------


def _mixed() -> list[CohortCandidate]:
    return [
        candidate("SCN-003", "T2", "D2"),
        candidate("SCN-001", "T1", "D1"),
        candidate("SCN-002", "T1", "D1"),
        candidate("SCN-004", None),
    ]


def test_result_does_not_depend_on_input_order() -> None:
    forwards = run(_mixed())
    backwards = run(list(reversed(_mixed())))
    assert forwards == backwards
    assert len(forwards.cohort_hash) == 64


def test_cohort_hash_tracks_members_and_required_metrics() -> None:
    base = run(_mixed())
    renamed = run(
        [
            candidate("X-1", "T2", "D2"),
            candidate("X-0", "T1", "D1"),
        ]
    )
    assert renamed.cohort_hash == base.cohort_hash
    assert run(_mixed()[:2]).cohort_hash == base.cohort_hash
    assert run([candidate("SCN-001", "T1", "D1")]).cohort_hash != base.cohort_hash
    assert run(_mixed(), required=frozenset({"cost"})).cohort_hash != (base.cohort_hash)


# --- input validation -----------------------------------------------------------------


@pytest.mark.parametrize("maximum", [float("nan"), -0.1, 1.1, float("inf")])
def test_maximum_exclusion_rate_must_be_a_share(maximum: float) -> None:
    with pytest.raises(ValueError):
        run([candidate("SCN-001")], maximum=maximum)


def test_empty_union_and_repeated_ids_are_refused() -> None:
    with pytest.raises(ValueError):
        run([])
    with pytest.raises(ValueError):
        run([candidate("SCN-001", "T1"), candidate("SCN-001", "T2")])


@pytest.mark.parametrize(
    ("topology_kind", "final_kind"),
    [("final_design", "final_design"), ("topology", "geometry")],
)
def test_fingerprinters_must_be_of_the_right_kind(
    topology_kind: Literal["topology", "final_design"],
    final_kind: Literal["final_design", "geometry"],
) -> None:
    with pytest.raises(ValueError):
        build_cohort(
            [candidate("SCN-001")],
            required_metrics=frozenset(),
            maximum_exclusion_rate=1.0,
            topology_fingerprinter=FakeFingerprinter(topology_kind),
            final_design_fingerprinter=FakeFingerprinter(final_kind),
        )


# --- real final-design canonicaliser and the C4 record --------------------------------


class NetworkTopology:
    """Stand-in topology canonicaliser (WP0B-5 belongs to L2)."""

    kind: Literal["topology"] = "topology"
    version = "0"

    def __call__(self, design: object) -> str:
        assert isinstance(design, FinalDesign)
        feeders = sorted(
            sorted(s.from_node_id + ">" + s.to_node_id for s in feeder.segments)
            for feeder in design.network.feeders  # type: ignore[union-attr]
        )
        digest = hashlib.sha256(json.dumps(feeders).encode()).hexdigest()
        return f"topology:0:{digest}"


def test_real_final_design_fingerprints_separate_conductor_variants() -> None:
    network = build_network()
    base = FinalDesign(network, truth_for(network))
    relabelled = FinalDesign(network, truth_for(network, candidate_id="SCN-S1-004"))
    upgraded = FinalDesign(
        network, truth_for(network, {**CONDUCTORS, "SEG-FDR-002-0001": "LARGE"})
    )
    result = build_cohort(
        [
            CohortCandidate(evidence("k/SCN-001"), base),
            CohortCandidate(evidence("s/SCN-S1-004"), relabelled),
            CohortCandidate(evidence("k/SCN-002"), upgraded),
        ],
        required_metrics=frozenset({"cost"}),
        maximum_exclusion_rate=0.0,
        topology_fingerprinter=NetworkTopology(),
        final_design_fingerprinter=FinalDesignFingerprinter(),
    )
    assert [m.candidate_id for m in result.members] == ["k/SCN-001", "k/SCN-002"]
    assert result.discarded_duplicate_lineages == (("s/SCN-S1-004", "k/SCN-001"),)
    assert result.distinct_eligible_topologies == 1


def test_result_fits_the_c4_evidence_record() -> None:
    record = json.loads(
        (CONTRACTS / "fixtures" / "evidence" / "record-example.json").read_text(
            encoding="utf-8"
        )
    )
    result = run(_mixed())
    record["candidates"] = [m.model_dump(mode="json") for m in result.members]
    record["exclusions"] = [e.model_dump(mode="json") for e in result.exclusions]
    record["cohort_hash"] = result.cohort_hash
    EvidenceRecord.model_validate(record)
