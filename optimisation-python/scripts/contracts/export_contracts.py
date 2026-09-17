"""Export the Stage 0 contract pack to ``contracts/`` at the repository root.

Every JSON artefact under ``contracts/`` except hand-written Markdown is
generated here from the Python contract modules, so the two cannot drift
silently. ``tests/contracts/test_contract_pack.py`` fails when a committed
artefact differs from what this script would write.

Usage (from optimisation-python/):
    python -m scripts.contracts.export_contracts          # write
    python -m scripts.contracts.export_contracts --check  # verify only
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.contracts import CONTRACT_PACK_VERSION
from app.contracts.canonical_json import canonical_sha256
from app.contracts.codes import (
    CODE_REGISTRY,
    CohortExclusionCode,
    JobStatus,
    RunTerminationReason,
    SizingBasis,
    SolverStatus,
)
from app.contracts.evidence import (
    EVIDENCE_SCHEMA_VERSION,
    CandidateEvidence,
    CandidateFingerprints,
    CatalogueBasis,
    EvidenceRecord,
    ExclusionCount,
    HostEnvironment,
    RunState,
    SourceRevisions,
    Timings,
)
from app.contracts.metric_registry_version import METRIC_REGISTRY_VERSION
from app.contracts.profiles import (
    ALLOWED_PROFILE_VERSIONS,
    PROFILE_SCENARIO_LABELS,
    MetricTerm,
    ProfileDefinition,
    ProfileDefinitionSet,
    ProfileId,
    definition_set_hash,
)
from app.contracts.recorded_bundle import (
    RECORDED_BUNDLE_SCHEMA_VERSION,
    BundleHashes,
    DemoMode,
    RecordedBundleManifest,
)
from app.contracts.request import (
    JAVA_GENERATION_SETTING_KEYS,
    MAX_V1_REQUEST_BYTES,
    CanonicalFeatureType,
    ProfileSelection,
    TypedFeatureIdentity,
)
from app.contracts.response import (
    ADDITIVE_RESPONSE_BLOCKS,
    GOLDEN_COMPARISON_EXCLUSIONS,
    CandidateExplanation,
    DesignTruth,
    EffectiveProfile,
    GenerationPenalty,
    InstalledSegment,
    LineageEntry,
    MetricContribution,
    RepairActionRecord,
    RunTermination,
    ScoringExplanation,
    SearchCaps,
    SearchCounts,
    SearchEvidence,
    SolverRun,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = REPO_ROOT / "contracts"


def _json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _model(value: BaseModel) -> Any:
    return value.model_dump(mode="json")


def _schema(model: type[BaseModel]) -> Any:
    return model.model_json_schema(mode="serialization")


def _example_counts() -> SearchCounts:
    # 20 proposals: 4 duplicates, 2 structural rejects, 14 routed.
    # Routed: 3 cache hits, 1 routing failure, 10 evaluated.
    return SearchCounts(
        requested_seeds=3,
        seed_evaluations=3,
        child_proposals=20,
        duplicates=4,
        structural_rejects=2,
        routed_proposals=14,
        routed_not_evaluated=1,
        cache_hits=3,
        child_evaluations=10,
        executed_evaluations=13,
        successful_evaluations=11,
        evaluation_failures=2,
        feasible=14,
        eligible=9,
        archive_size=17,
        rounds_completed=2,
    )


def _example_solver_run() -> SolverRun:
    return SolverRun(
        objective="minimize_distance",
        feeder_count=2,
        status=SolverStatus.OPTIMAL,
        wall_time_s=0.042,
        mip_gap=0.0,
        time_limit_s=None,
        node_limit=None,
        limit_reached=False,
    )


def _example_effective_profile() -> EffectiveProfile:
    return EffectiveProfile(
        profile_id=ProfileId.BALANCED.value,
        profile_version="1",
        policy_hash="0" * 64,
        definition_hash="1" * 64,
        metric_registry_version=METRIC_REGISTRY_VERSION,
        generation_settings_hash="2" * 64,
        profiles_enabled=True,
        search_enabled=True,
    )


def _response_blocks_example() -> dict[str, Any]:
    return {
        "design_truth": _model(
            DesignTruth(
                candidate_id="SCN-001",
                candidate_sizing_basis=SizingBasis.INITIAL_ONLY,
                segments=[
                    InstalledSegment(
                        segment_id="SEG-F1-001",
                        feeder_id="F1",
                        initial_cable_type_id="SMALL",
                        final_cable_type_id="LARGE",
                        repaired=True,
                    )
                ],
                repair_actions=[
                    RepairActionRecord(
                        segment_id="SEG-F1-001",
                        original_cable_type_id="SMALL",
                        upgraded_cable_type_id="LARGE",
                        reason_code="VOLTAGE_VIOLATION",
                        trigger_violation_type="OVERVOLTAGE",
                        repair_iteration=1,
                    )
                ],
            )
        ),
        "search_evidence": _model(
            SearchEvidence(
                enabled=True,
                caps=SearchCaps(
                    seeds=5,
                    children=40,
                    archive=60,
                    proposals=200,
                    routed_proposals=60,
                    evaluations=40,
                    rounds=2,
                ),
                counts=_example_counts(),
                lineage=[
                    LineageEntry(
                        candidate_id="SCN-S1-001",
                        parent_id="SCN-001",
                        round=1,
                        mutation_type="FEEDER_SWAP",
                    )
                ],
                admission_deadline_s=45.0,
                admission_deadline_reached=False,
                routing_time_s=3.2,
            )
        ),
        "solver_runs": [_model(_example_solver_run())],
        "scoring_explanation": _model(
            ScoringExplanation(
                profile_id=ProfileId.BALANCED.value,
                reference_ranges_version="1",
                candidates=[
                    CandidateExplanation(
                        candidate_id="SCN-001",
                        eligible=True,
                        rank=1,
                        total_score=0.74,
                        contributions=[
                            MetricContribution(
                                metric="affected_parcel_row_area_m2",
                                direction="minimise",
                                raw_value=1250.0,
                                reference_min=0.0,
                                reference_max=5000.0,
                                normalised_value=0.75,
                                weight=0.2,
                                weighted_contribution=0.15,
                            )
                        ],
                    )
                ],
                generation_penalties=[
                    GenerationPenalty(name="parcel_cost_weight", value=20.0, unit="1")
                ],
            )
        ),
        "effective_profile": _model(_example_effective_profile()),
        "termination": _model(
            RunTermination(reason=RunTerminationReason.MAX_ROUNDS_REACHED)
        ),
    }


def _evidence_example() -> EvidenceRecord:
    return EvidenceRecord(
        record_id="EVD-EXAMPLE-0001",
        request_variant="balanced",
        project_input_sha256="3" * 64,
        serialised_request_sha256="4" * 64,
        blinded=True,
        revisions=SourceRevisions(
            python_revision="a313d2f",
            java_revision="a313d2f",
            frontend_revision="a313d2f",
            clean_worktree=True,
            lockfile_sha256={"requirements.lock.txt": "5" * 64},
            image_digests={"optimizer": "sha256:" + "6" * 64},
        ),
        environment=HostEnvironment(
            os="linux",
            python_version="3.11.9",
            java_version="21",
            node_version="20",
            cpu="example",
            memory_gb=16.0,
            cold_run=True,
            cold_definition="clean Compose start, empty application caches",
        ),
        effective_profile=_example_effective_profile(),
        profile_version_count=1,
        catalogue=CatalogueBasis(
            catalogue_id="IN-33KV-INDICATIVE",
            version="1",
            currency="INR",
            price_basis_date="2026-09-01",
            cost_assumptions={"discount_rate": "0.08"},
        ),
        counts=_example_counts(),
        exclusions=[
            ExclusionCount(code=CohortExclusionCode.INCOMPLETE_LIFECYCLE_COST, count=1)
        ],
        solver_runs=[_example_solver_run()],
        candidates=[
            CandidateEvidence(
                candidate_id="SCN-001",
                parent_id=None,
                mutation_type=None,
                fingerprints=CandidateFingerprints(
                    topology="topology:1:" + "7" * 64,
                    geometry="geometry:1:" + "8" * 64,
                    final_design="final_design:1:" + "9" * 64,
                    canonicaliser_versions={
                        "topology": "1",
                        "geometry": "1",
                        "final_design": "1",
                    },
                ),
                feasible=True,
                eligible=True,
                failure_codes=[],
                raw_metrics={"ROUTE_LENGTH": 12500.0},
                contributions=None,
            )
        ],
        cohort_hash=None,
        run_state=RunState(
            job_status=JobStatus.COMPLETED,
            termination_reason=RunTerminationReason.MAX_ROUNDS_REACHED,
            admission_deadline_reached=False,
            outer_timeout_reached=False,
            repeatability_matched=None,
        ),
        timings=Timings(
            total_wall_time_s=38.5,
            routing_time_s=3.2,
            stage_timings_s={"generation": 12.0},
        ),
    )


def _hash_vector_definitions() -> ProfileDefinitionSet:
    """A synthetic set whose only job is to pin the hash algorithm across languages."""
    return ProfileDefinitionSet(
        definitions=[
            ProfileDefinition(
                profile_id=ProfileId.MINIMUM_LAND_IMPACT,
                version="1",
                policy_mode="UNIFIED_ENGINEERING",
                terms=[
                    MetricTerm(
                        metric="affected_parcel_row_area_m2",
                        direction="minimise",
                        weight="0.6",
                        reference_min="0",
                        reference_max="5000.5",
                        lexicographic_rank=1,
                        tolerance="25",
                    ),
                    MetricTerm(
                        metric="AFFECTED_PARCEL_COUNT",
                        direction="minimise",
                        weight="0.4",
                        reference_min="0",
                        reference_max="40",
                        lexicographic_rank=2,
                    ),
                ],
                tie_breaks=["ROUTE_LENGTH", "candidate_id"],
                generation_settings={"note": "vector only — café"},
                placeholder=True,
            ),
            ProfileDefinition(
                profile_id=ProfileId.BALANCED,
                version="1",
                policy_mode="UNIFIED_ENGINEERING",
                terms=[
                    MetricTerm(
                        metric="ROUTE_LENGTH",
                        direction="minimise",
                        weight="1",
                        reference_min="-1.25",
                        reference_max="90000",
                    )
                ],
            ),
        ]
    )


def _feeder_segment_fixture() -> dict[str, Any]:
    """C11: one Feature is one routed segment under one feeder (WP0A-3)."""

    def feature(segment: str, feeder: str, a: str, b: str) -> dict[str, Any]:
        return {
            "type": "Feature",
            "id": segment,
            "properties": {
                "feature_type": "pnc_segment",
                "segment_id": segment,
                "feeder_id": feeder,
                "feederName": feeder,
                "from_node": a,
                "to_node": b,
                "edge": f"{a}-{b}",
                "length_m": 1000.0,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[77.10, 14.30], [77.11, 14.31]],
            },
        }

    return {
        "description": (
            "V1 feeder_routes_geojson segment features and how Java must persist "
            "and aggregate them."
        ),
        "feeder_routes_geojson": {
            "type": "FeatureCollection",
            "features": [
                feature("SEG-F1-001", "F1", "substation:SS", "wtg:T1"),
                feature("SEG-F1-002", "F1", "wtg:T1", "wtg:T2"),
                feature("SEG-F2-001", "F2", "substation:SS", "wtg:T3"),
            ],
        },
        "expected_route_rows": [
            {"feederName": "F1", "segmentId": "SEG-F1-001"},
            {"feederName": "F1", "segmentId": "SEG-F1-002"},
            {"feederName": "F2", "segmentId": "SEG-F2-001"},
        ],
        "expected_bom_segment_count_by_feeder": {"F1": 2, "F2": 1},
    }


def build_artefacts() -> dict[str, str]:
    """Map repository-relative path to exact file content."""
    definitions = _hash_vector_definitions()
    artefacts: dict[str, Any] = {
        "codes.json": {
            "contract_pack_version": CONTRACT_PACK_VERSION,
            "codes": {
                name: [member.value for member in enum]
                for name, enum in CODE_REGISTRY.items()
            },
        },
        "request-rules.json": {
            "max_v1_request_bytes": MAX_V1_REQUEST_BYTES,
            "java_generation_setting_keys": list(JAVA_GENERATION_SETTING_KEYS),
            "canonical_feature_types": [item.value for item in CanonicalFeatureType],
            "typed_identity_properties": ["source_id", "feature_type", "routing_mode"],
            "absent_profile_means": "V0",
            "run_id_header": "X-Surge-Run-Id",
        },
        "response-rules.json": {
            "additive_blocks": list(ADDITIVE_RESPONSE_BLOCKS),
            "absent_when_not_produced": True,
            "golden_comparison_exclusions": list(GOLDEN_COMPARISON_EXCLUSIONS),
            "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
            "metric_registry_version": METRIC_REGISTRY_VERSION,
        },
        "profiles/allow-list.json": {
            "profiles": [
                {
                    "id": profile_id.value,
                    "scenario_label": PROFILE_SCENARIO_LABELS[profile_id],
                    "versions": list(ALLOWED_PROFILE_VERSIONS[profile_id]),
                }
                for profile_id in ProfileId
            ]
        },
        "profiles/hash-vector/definitions.json": _model(definitions),
        "recorded-mode.json": {
            "schema_version": RECORDED_BUNDLE_SCHEMA_VERSION,
            "demo_modes": [item.value for item in DemoMode],
        },
        "schemas/v1-request-profile.schema.json": _schema(ProfileSelection),
        "schemas/v1-request-typed-identity.schema.json": _schema(
            TypedFeatureIdentity
        ),
        "schemas/v1-response-design-truth.schema.json": _schema(DesignTruth),
        "schemas/v1-response-search-evidence.schema.json": _schema(SearchEvidence),
        "schemas/v1-response-solver-run.schema.json": _schema(SolverRun),
        "schemas/v1-response-scoring-explanation.schema.json": _schema(
            ScoringExplanation
        ),
        "schemas/v1-response-effective-profile.schema.json": _schema(
            EffectiveProfile
        ),
        "schemas/v1-response-termination.schema.json": _schema(RunTermination),
        "schemas/evidence-v1.schema.json": _schema(EvidenceRecord),
        "schemas/profile-definition-set.schema.json": _schema(ProfileDefinitionSet),
        "schemas/recorded-bundle-v1.schema.json": _schema(RecordedBundleManifest),
        "fixtures/request/profile-selection.json": _model(
            ProfileSelection(id=ProfileId.BALANCED.value, version="1")
        ),
        "fixtures/request/typed-avoidance-feature.json": {
            "type": "Feature",
            "id": "restricted-3f0c",
            "properties": {
                "constraint_id": "restricted-3f0c",
                "constraint_type": "restricted_area",
                "routing_mode": "hard",
                "buffer_m": 30.0,
                "source_id": "3f0c9a52-1b8e-4a57-9d8e-0f3f4e6f2a10",
                "feature_type": CanonicalFeatureType.FOREST.value,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[77.2, 14.38], [77.21, 14.38], [77.21, 14.39], [77.2, 14.38]]
                ],
            },
        },
        "fixtures/response/additive-blocks.json": _response_blocks_example(),
        "fixtures/evidence/record-example.json": _model(_evidence_example()),
        "fixtures/recorded-bundle/manifest-example.json": _model(
            RecordedBundleManifest(
                bundle_id="BUNDLE-EXAMPLE",
                recorded_at="2026-09-17T00:00:00Z",
                release_candidate_tag="demo-opt-rc1",
                hashes=BundleHashes(
                    request_sha256={"balanced": "a" * 64},
                    profile_definition_sha256="b" * 64,
                    code_revisions={"python": "a313d2f"},
                    image_digests={"optimizer": "sha256:" + "c" * 64},
                    catalogue_sha256="d" * 64,
                    response_schema_version="2.0",
                    evidence_schema_version=EVIDENCE_SCHEMA_VERSION,
                ),
                winner_final_design_fingerprints={
                    "balanced": "final_design:1:" + "e" * 64
                },
                cohort_hash=None,
                on_screen_label="Recorded run",
            )
        ),
        "fixtures/feeder-segment-identity.json": _feeder_segment_fixture(),
    }
    files = {path: _json(value) for path, value in artefacts.items()}
    files["profiles/hash-vector/expected.sha256"] = (
        definition_set_hash(definitions) + "\n"
    )
    files["profiles/hash-vector/canonical.json"] = (
        canonical_sha256_input(definitions) + "\n"
    )
    return files


def canonical_sha256_input(definitions: ProfileDefinitionSet) -> str:
    """The exact canonical text that is hashed, for cross-language debugging."""
    from app.contracts.canonical_json import canonical_json_bytes

    ordered = sorted(
        definitions.definitions, key=lambda item: (item.profile_id.value, item.version)
    )
    payload = {"definitions": [item.model_dump(mode="json") for item in ordered]}
    assert canonical_sha256(payload) == definition_set_hash(definitions)
    return canonical_json_bytes(payload).decode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for relative, content in build_artefacts().items():
        path = CONTRACTS / relative
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == content:
            continue
        stale.append(relative)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    if args.check and stale:
        print("Stale contract artefacts:\n  " + "\n  ".join(stale))
        return 1
    print(f"{'Checked' if args.check else 'Wrote'} contract pack; changed: {stale}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
