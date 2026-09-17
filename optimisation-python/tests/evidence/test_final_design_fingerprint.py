"""WP0B-6: final-design fingerprint canonicaliser, version 1."""

import json
from dataclasses import replace

import pytest

from app.contracts.codes import SizingBasis
from app.contracts.response import DesignTruth, InstalledSegment, RepairActionRecord
from app.evidence.fingerprints.final_design import (
    FINAL_DESIGN_FINGERPRINT_VERSION,
    INSTALLED_FIELDS,
    FinalDesign,
    FinalDesignFingerprinter,
    FinalDesignFingerprintError,
    canonical_final_design_payload,
)
from app.evidence.fingerprints.geometry import GeometryFingerprinter
from app.pnc.models import ProjectPNCNetwork
from scripts.contracts.export_contracts import CONTRACTS
from tests.evidence.test_geometry_fingerprint import DEFAULT_FEEDERS, build_network

# Golden vectors. They change only with a new FINAL_DESIGN_FINGERPRINT_VERSION
# (or a new geometry version); a failure at the same version is a regression.
GOLDEN_V1 = (
    "final_design:1:30dced10a4c18ef8aa5083f8249c0997788891c67bd97e871d6c48f9e5f8e0af"
)
GOLDEN_V1_C2_FIXTURE = (
    "final_design:1:f0398c2a35578654bc67d2b8186c28071e9835d9179095f715dba26aef51d0fa"
)

CONDUCTORS = {
    "SEG-FDR-001-0001": "LARGE",
    "SEG-FDR-001-0002": "SMALL",
    "SEG-FDR-002-0001": "SMALL",
}

fingerprint = FinalDesignFingerprinter()


def truth_for(
    network: ProjectPNCNetwork,
    conductors: dict[str, str] | None = None,
    *,
    candidate_id: str = "SCN-001",
) -> DesignTruth:
    conductors = CONDUCTORS if conductors is None else conductors
    return DesignTruth(
        candidate_id=candidate_id,
        candidate_sizing_basis=SizingBasis.FINAL_INSTALLED,
        segments=[
            InstalledSegment(
                segment_id=segment.segment_id,
                feeder_id=segment.feeder_id,
                initial_cable_type_id=conductors[segment.segment_id],
                final_cable_type_id=conductors[segment.segment_id],
                repaired=False,
            )
            for feeder in network.feeders
            for segment in feeder.segments
        ],
        repair_actions=[],
    )


def design(conductors: dict[str, str] | None = None) -> FinalDesign:
    network = build_network()
    return FinalDesign(network=network, design_truth=truth_for(network, conductors))


# --- format, golden vectors, payload --------------------------------------------------


def test_fingerprinter_satisfies_the_c4_format() -> None:
    kind, version, digest = fingerprint(design()).split(":")
    assert (kind, version) == ("final_design", FINAL_DESIGN_FINGERPRINT_VERSION)
    assert len(digest) == 64 and digest == digest.lower()
    assert (fingerprint.kind, fingerprint.version) == ("final_design", "1")


def test_golden_vector_v1() -> None:
    assert fingerprint(design()) == GOLDEN_V1


def test_c2_design_truth_fixture_is_consumed() -> None:
    fixture = json.loads(
        (CONTRACTS / "fixtures" / "response" / "additive-blocks.json").read_text(
            encoding="utf-8"
        )
    )
    truth = DesignTruth.model_validate(fixture["design_truth"])
    (installed,) = truth.segments
    base = build_network({"F1": [DEFAULT_FEEDERS["FDR-001"][0]]})
    (feeder,) = base.feeders
    segment = replace(feeder.segments[0], segment_id=installed.segment_id)
    network = replace(base, feeders=(replace(feeder, segments=(segment,)),))

    value = fingerprint(FinalDesign(network=network, design_truth=truth))
    assert value == GOLDEN_V1_C2_FIXTURE

    downsized = truth.model_copy(
        update={
            "segments": [installed.model_copy(update={"final_cable_type_id": "SMALL"})]
        }
    )
    assert fingerprint(FinalDesign(network, downsized)) != value


def test_canonical_payload_spells_out_the_declared_rules() -> None:
    payload = canonical_final_design_payload(design())
    assert payload == {
        "canonicaliser": "final_design",
        "version": "1",
        "geometry": GeometryFingerprinter()(build_network()),
        "installed_fields": ["final_cable_type_id", "feeder_circuit"],
        "feeder_circuits": [
            [[[[499600000, 799700750], [500000000, 800000000]], "SMALL"]],
            [
                [[[500000000, 800000000], [500400250, 800150500]], "LARGE"],
                [
                    [
                        [500400250, 800150500],
                        [500650000, 800300000],
                        [500900125, 800310000],
                    ],
                    "SMALL",
                ],
            ],
        ],
    }
    assert tuple(payload["installed_fields"]) == INSTALLED_FIELDS


def test_repeat_calls_agree() -> None:
    first = fingerprint(design())
    assert all(fingerprint(design()) == first for _ in range(20))


# --- sensitivity: the strong claim's distinctions -------------------------------------


def test_changing_only_one_conductor_changes_the_fingerprint() -> None:
    base = design()
    upgraded = design({**CONDUCTORS, "SEG-FDR-002-0001": "LARGE"})
    assert GeometryFingerprinter()(base.network) == GeometryFingerprinter()(
        upgraded.network
    )
    assert fingerprint(upgraded) != fingerprint(base)


def test_swapping_conductors_between_segments_changes_the_fingerprint() -> None:
    swapped = {
        **CONDUCTORS,
        "SEG-FDR-001-0001": "SMALL",
        "SEG-FDR-001-0002": "LARGE",
    }
    assert fingerprint(design(swapped)) != fingerprint(design())


def test_changing_geometry_changes_the_fingerprint() -> None:
    moved_feeders = {
        **DEFAULT_FEEDERS,
        "FDR-002": [
            ("substation:SS", "wtg:T3", [(500000.0, 800000.0), (499600.0, 799700.0)])
        ],
    }
    network = build_network(moved_feeders)
    assert fingerprint(FinalDesign(network, truth_for(network))) != (
        fingerprint(design())
    )


def test_regrouping_segments_into_other_feeders_changes_the_fingerprint() -> None:
    regrouped_feeders = {
        "FDR-001": [DEFAULT_FEEDERS["FDR-001"][0]],
        "FDR-002": [DEFAULT_FEEDERS["FDR-002"][0], DEFAULT_FEEDERS["FDR-001"][1]],
    }
    network = build_network(regrouped_feeders)
    conductors = {
        "SEG-FDR-001-0001": "LARGE",
        "SEG-FDR-002-0001": "SMALL",
        "SEG-FDR-002-0002": "SMALL",
    }
    regrouped = FinalDesign(network, truth_for(network, conductors))
    assert GeometryFingerprinter()(network) == GeometryFingerprinter()(build_network())
    assert fingerprint(regrouped) != fingerprint(design())


# --- invariance: labels and history are not installed state ---------------------------


def test_labels_history_and_sizing_basis_are_not_hashed() -> None:
    base = design()
    truth = base.design_truth
    relabelled_truth = truth.model_copy(
        update={
            "candidate_id": "SCN-S3-017",
            "candidate_sizing_basis": SizingBasis.INITIAL_ONLY,
            "segments": [
                s.model_copy(update={"initial_cable_type_id": None, "repaired": True})
                for s in reversed(truth.segments)
            ],
            "repair_actions": [
                RepairActionRecord(
                    segment_id="SEG-FDR-001-0001",
                    original_cable_type_id="SMALL",
                    upgraded_cable_type_id="LARGE",
                    reason_code="VOLTAGE_VIOLATION",
                    trigger_violation_type="UNDERVOLTAGE",
                    repair_iteration=1,
                )
            ],
        }
    )
    assert fingerprint(FinalDesign(base.network, relabelled_truth)) == (
        fingerprint(base)
    )


def test_feeder_and_segment_ids_are_not_hashed() -> None:
    relabelled = build_network(
        {
            "FDR-777": DEFAULT_FEEDERS["FDR-002"],
            "FDR-555": list(reversed(DEFAULT_FEEDERS["FDR-001"])),
        }
    )
    conductors = {
        "SEG-FDR-777-0001": "SMALL",
        "SEG-FDR-555-0001": "SMALL",
        "SEG-FDR-555-0002": "LARGE",
    }
    assert fingerprint(FinalDesign(relabelled, truth_for(relabelled, conductors))) == (
        fingerprint(design())
    )


# --- completeness rules ---------------------------------------------------------------


def _truth_with(segments: list[InstalledSegment]) -> FinalDesign:
    base = design()
    return FinalDesign(
        base.network, base.design_truth.model_copy(update={"segments": segments})
    )


_SEGMENTS = design().design_truth.segments


@pytest.mark.parametrize(
    "broken",
    [
        _SEGMENTS[1:],
        [*_SEGMENTS, _SEGMENTS[0].model_copy(update={"segment_id": "SEG-X-0001"})],
        [*_SEGMENTS, _SEGMENTS[0]],
        [_SEGMENTS[0].model_copy(update={"feeder_id": "FDR-002"}), *_SEGMENTS[1:]],
        [
            _SEGMENTS[0].model_copy(update={"final_cable_type_id": " "}),
            *_SEGMENTS[1:],
        ],
    ],
    ids=["missing", "unknown", "duplicate", "wrong-feeder", "empty-conductor"],
)
def test_incomplete_or_inconsistent_design_truth_is_rejected(
    broken: list[InstalledSegment],
) -> None:
    with pytest.raises(FinalDesignFingerprintError):
        fingerprint(_truth_with(broken))


def test_other_design_types_are_refused() -> None:
    with pytest.raises(TypeError):
        fingerprint(build_network())
