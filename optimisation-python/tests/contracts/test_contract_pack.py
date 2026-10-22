"""Stage 0 contract pack (CON-1): artefacts, codes, fixtures and hashing."""

import json
import subprocess
import sys
from pathlib import Path
from typing import get_args

import pytest

from app.contracts.canonical_json import (
    CanonicalJsonError,
    canonical_json_bytes,
    canonical_sha256,
)
from app.contracts.codes import RunTerminationReason
from app.contracts.evidence import EvidenceRecord
from app.contracts.profiles import (
    ALLOWED_PROFILE_VERSIONS,
    PROFILE_SCENARIO_LABELS,
    ProfileDefinitionSet,
    ProfileId,
    definition_set_hash,
)
from app.contracts.reconcile import reconcile_counts
from app.contracts.recorded_bundle import RecordedBundleManifest
from app.contracts.request import ProfileSelection, TypedFeatureIdentity
from app.contracts.response import (
    ADDITIVE_RESPONSE_BLOCKS,
    DesignTruth,
    EffectiveProfile,
    RunTermination,
    ScoringExplanation,
    SearchEvidence,
    SolverRun,
)
from app.optimisation.search_models import SearchTerminationReason
from app.schemas.optimise import OptimisationResponse, OptimisationScenario
from scripts.contracts.export_contracts import CONTRACTS, build_artefacts


def _load(relative: str) -> object:
    return json.loads((CONTRACTS / relative).read_text(encoding="utf-8"))


def test_committed_artefacts_match_the_python_contract() -> None:
    stale = [
        relative
        for relative, content in build_artefacts().items()
        if not (CONTRACTS / relative).exists()
        or (CONTRACTS / relative).read_text(encoding="utf-8") != content
    ]
    assert stale == [], (
        "Regenerate with `python -m scripts.contracts.export_contracts` "
        f"through a contract change request: {stale}"
    )


def test_artefacts_match_from_a_fresh_interpreter() -> None:
    # Guards against schema output that depends on which modules were imported
    # first (typing caches Literal types regardless of value order).
    completed = subprocess.run(
        [sys.executable, "-m", "scripts.contracts.export_contracts", "--check"],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_run_termination_reasons_cover_every_search_termination_reason() -> None:
    published = {member.value for member in RunTerminationReason}
    assert {member.value for member in SearchTerminationReason} <= published


def test_every_profile_maps_to_a_v1_scenario_label_and_a_version() -> None:
    labels = set(get_args(OptimisationScenario))
    for profile_id in ProfileId:
        assert PROFILE_SCENARIO_LABELS[profile_id] in labels
        assert ALLOWED_PROFILE_VERSIONS[profile_id]


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
def test_response_fixture_blocks_validate(block: str, model: type) -> None:
    fixture = _load("fixtures/response/additive-blocks.json")
    assert isinstance(fixture, dict)
    model.model_validate(fixture[block])


def test_response_fixture_covers_every_additive_block() -> None:
    fixture = _load("fixtures/response/additive-blocks.json")
    assert isinstance(fixture, dict)
    assert set(fixture) == set(ADDITIVE_RESPONSE_BLOCKS)
    for run in fixture["solver_runs"]:
        SolverRun.model_validate(run)


def test_additive_blocks_are_absent_from_a_v0_response() -> None:
    response = OptimisationResponse(
        request_id="r", status="success", scenario="Balanced"
    )
    body = response.model_dump(mode="json", exclude_none=True)
    assert not set(ADDITIVE_RESPONSE_BLOCKS) & set(body)


def test_request_fixtures_validate() -> None:
    ProfileSelection.model_validate(_load("fixtures/request/profile-selection.json"))
    feature = _load("fixtures/request/typed-avoidance-feature.json")
    assert isinstance(feature, dict)
    identity = TypedFeatureIdentity.model_validate(feature["properties"])
    assert identity.source_id and identity.feature_type and identity.routing_mode


def test_evidence_and_bundle_fixtures_validate() -> None:
    record = EvidenceRecord.model_validate(
        _load("fixtures/evidence/record-example.json")
    )
    RecordedBundleManifest.model_validate(
        _load("fixtures/recorded-bundle/manifest-example.json")
    )
    assert reconcile_counts(record.counts) == ()


def test_reconciliation_names_the_broken_equation() -> None:
    record = EvidenceRecord.model_validate(
        _load("fixtures/evidence/record-example.json")
    )
    broken = record.counts.model_copy(update={"cache_hits": 4})
    equations = {violation.equation for violation in reconcile_counts(broken)}
    assert any(eq.startswith("child_proposals") for eq in equations)
    assert any(eq.startswith("routed_proposals") for eq in equations)


def test_reconciliation_rejects_eligible_outside_complete_feasible() -> None:
    record = EvidenceRecord.model_validate(
        _load("fixtures/evidence/record-example.json")
    )
    violations = reconcile_counts(
        record.counts,
        eligible_ids={"A", "B"},
        complete_feasible_ids={"A"},
    )
    assert len(violations) == 1


def test_canonical_json_rules() -> None:
    assert canonical_json_bytes({"b": 1, "a": ["é", None, True]}) == (
        '{"a":["é",null,true],"b":1}'.encode()
    )
    with pytest.raises(CanonicalJsonError):
        canonical_json_bytes({"weight": 0.25})


def test_definition_hash_vector_reproduces() -> None:
    definitions = ProfileDefinitionSet.model_validate(
        _load("profiles/hash-vector/definitions.json")
    )
    expected = (CONTRACTS / "profiles/hash-vector/expected.sha256").read_text()
    canonical = (CONTRACTS / "profiles/hash-vector/canonical.json").read_text(
        encoding="utf-8"
    )
    assert definition_set_hash(definitions) == expected.strip()
    assert canonical_sha256(json.loads(canonical)) == expected.strip()


def test_definition_hash_ignores_definition_order() -> None:
    definitions = ProfileDefinitionSet.model_validate(
        _load("profiles/hash-vector/definitions.json")
    )
    reversed_set = ProfileDefinitionSet(
        definitions=list(reversed(definitions.definitions))
    )
    assert definition_set_hash(reversed_set) == definition_set_hash(definitions)


def test_feeder_segment_fixture_is_internally_consistent() -> None:
    fixture = _load("fixtures/feeder-segment-identity.json")
    assert isinstance(fixture, dict)
    features = fixture["feeder_routes_geojson"]["features"]
    rows = [
        {
            "feederName": feature["properties"]["feederName"],
            "segmentId": feature["properties"]["segment_id"],
        }
        for feature in features
    ]
    assert rows == fixture["expected_route_rows"]
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["feederName"]] = counts.get(row["feederName"], 0) + 1
    assert counts == fixture["expected_bom_segment_count_by_feeder"]


def test_contracts_directory_is_the_repository_root_one() -> None:
    assert CONTRACTS == Path(__file__).resolve().parents[3] / "contracts"
