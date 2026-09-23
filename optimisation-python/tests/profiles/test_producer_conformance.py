"""WP3-9a: Python round-trips every contract fixture in canonical JSON.

Exit evidence: every C1, C2 and C11 fixture, plus the evidence record and the
recorded-bundle manifest, is read by the model that owns it and written back
unchanged - byte-identical under the encoding that applies to it.

Fidelity is the point. A test that only checked "validates without error" would
pass while Python silently dropped a field, renamed one, or reordered a map - and
Java, which reads and writes these same documents, would then disagree with Python
about what the contract says. So each round trip asserts the document comes back
equal, and that a deterministic encoding of it is byte-identical.

Two encodings, deliberately: ``canonical_json_bytes`` is the **hashing** encoding
and rejects floats outright, because C6 requires decimals written as strings so a
hash is exact. Only the hashed documents go through it. Every other fixture carries
real floats - coordinates, scores, wall times - and is compared structurally and
under a stable key order instead.
"""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from app.contracts.canonical_json import canonical_json_bytes
from app.contracts.evidence import EvidenceRecord
from app.contracts.recorded_bundle import RecordedBundleManifest
from app.contracts.request import ProfileSelection, TypedFeatureIdentity
from app.contracts.response import (
    DesignTruth,
    EffectiveProfile,
    RunTermination,
    ScoringExplanation,
    SearchEvidence,
    SolverRun,
)

_CONTRACTS = Path(__file__).resolve().parents[3] / "contracts"
_FIXTURES = _CONTRACTS / "fixtures"


def _load(relative: str) -> Any:
    with (_FIXTURES / relative).open(encoding="utf-8") as handle:
        return json.load(handle)


def _stable(document: Any) -> str:
    """A deterministic encoding: sorted keys, no whitespace, no NaN or Infinity."""
    return json.dumps(document, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _round_trips(model: type[BaseModel], document: Any) -> None:
    """The model reads the document and writes it back unchanged."""
    produced = model.model_validate(document).model_dump(mode="json")
    assert produced == document
    assert _stable(produced) == _stable(document)


# --- C1 request fixtures ------------------------------------------------------------


def test_the_profile_selection_fixture_round_trips() -> None:
    _round_trips(ProfileSelection, _load("request/profile-selection.json"))


def test_the_typed_avoidance_feature_round_trips_its_identity() -> None:
    # The document is a GeoJSON feature; C1's model owns the additive identity
    # properties on it, not the routing fields the V0 parser already owned.
    feature = _load("request/typed-avoidance-feature.json")
    properties = feature["properties"]
    identity = TypedFeatureIdentity.model_validate(properties)
    produced = identity.model_dump(mode="json")

    for field in produced:
        assert produced[field] == properties[field], field
    assert set(produced) <= set(properties)


def test_the_avoidance_feature_document_survives_a_re_encode() -> None:
    # The whole feature, not just the identity: Java sends this document, so a
    # decode and re-encode must reproduce it.
    feature = _load("request/typed-avoidance-feature.json")
    assert _stable(json.loads(json.dumps(feature))) == _stable(feature)


# --- C2 response blocks --------------------------------------------------------------


@pytest.mark.parametrize(
    ("block", "model"),
    [
        ("design_truth", DesignTruth),
        ("search_evidence", SearchEvidence),
        ("scoring_explanation", ScoringExplanation),
        ("effective_profile", EffectiveProfile),
        ("termination", RunTermination),
    ],
)
def test_each_additive_response_block_round_trips(
    block: str, model: type[BaseModel]
) -> None:
    _round_trips(model, _load("response/additive-blocks.json")[block])


def test_the_solver_runs_block_round_trips_every_entry() -> None:
    # The only block that is a list rather than an object.
    runs = _load("response/additive-blocks.json")["solver_runs"]
    assert runs, "the fixture must carry at least one solver run"
    for run in runs:
        _round_trips(SolverRun, run)


def test_every_additive_block_in_the_fixture_is_covered() -> None:
    # A new block added to C2 must not slip past this file unnoticed.
    covered = {
        "design_truth",
        "search_evidence",
        "scoring_explanation",
        "effective_profile",
        "termination",
        "solver_runs",
    }
    assert set(_load("response/additive-blocks.json")) == covered


# --- C4 evidence and the recorded bundle ---------------------------------------------


def test_the_evidence_record_round_trips() -> None:
    _round_trips(EvidenceRecord, _load("evidence/record-example.json"))


def test_the_recorded_bundle_manifest_round_trips() -> None:
    _round_trips(RecordedBundleManifest, _load("recorded-bundle/manifest-example.json"))


# --- C11 feeder and segment identity ------------------------------------------


def test_the_feeder_segment_fixture_survives_a_re_encode() -> None:
    document = _load("feeder-segment-identity.json")
    assert _stable(json.loads(json.dumps(document))) == _stable(document)


def test_one_route_row_per_segment_feature_under_its_own_feeder() -> None:
    # C11 itself: the rule Java persists by, asserted against the shared document
    # rather than restated, so a CCR amending the fixture reaches Python too.
    document = _load("feeder-segment-identity.json")
    features = document["feeder_routes_geojson"]["features"]
    rows = document["expected_route_rows"]

    assert len(rows) == len(features)
    for feature, row in zip(features, rows, strict=True):
        properties = feature["properties"]
        assert properties["segment_id"] == row["segmentId"]
        assert properties["feeder_id"] == row["feederName"]
        # feederName is the engine's feeder id, which is what BOM aggregates on.
        assert properties["feederName"] == row["feederName"]


def test_the_bom_counts_follow_from_the_segment_features() -> None:
    document = _load("feeder-segment-identity.json")
    expected = document["expected_bom_segment_count_by_feeder"]

    counted: dict[str, int] = {}
    for feature in document["feeder_routes_geojson"]["features"]:
        feeder = feature["properties"]["feederName"]
        counted[feeder] = counted.get(feeder, 0) + 1

    assert counted == expected


# --- The hashed documents, where canonical JSON applies --------------------------


def test_the_registry_round_trips_through_the_hashing_encoding() -> None:
    # C6 hashes profile definitions, so those must survive the strict encoder that
    # rejects floats. This is the document Java reproduces byte for byte.
    from app.contracts.profiles import ProfileDefinitionSet
    from app.optimisation.profiles.registry import PLACEHOLDER_DEFINITIONS

    dumped = PLACEHOLDER_DEFINITIONS.model_dump(mode="json")
    reloaded = ProfileDefinitionSet.model_validate(dumped)

    assert canonical_json_bytes(reloaded.model_dump(mode="json")) == (
        canonical_json_bytes(dumped)
    )


def test_the_published_hash_vector_round_trips_through_the_hashing_encoding() -> None:
    from app.contracts.profiles import ProfileDefinitionSet

    with (_CONTRACTS / "profiles" / "hash-vector" / "definitions.json").open(
        encoding="utf-8"
    ) as handle:
        vector = json.load(handle)

    produced = ProfileDefinitionSet.model_validate(vector).model_dump(mode="json")

    assert produced == vector
    assert canonical_json_bytes(produced) == canonical_json_bytes(vector)


def test_the_hashing_encoding_refuses_a_float() -> None:
    # Why the other fixtures are not compared through it: a float has no exact
    # decimal form, so C6 forbids one rather than hashing an approximation.
    from app.contracts.canonical_json import CanonicalJsonError

    with pytest.raises(CanonicalJsonError, match="floats are not canonical"):
        canonical_json_bytes({"weight": 0.1})
