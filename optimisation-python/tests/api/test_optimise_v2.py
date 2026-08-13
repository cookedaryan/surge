import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.electrical.errors import CandidateElectricalEvaluationError
from app.main import app
from app.schemas.v2.optimise import OptimiseProjectResponse

client = TestClient(app)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def mvp_v2_payload() -> dict:
    fixture_path = FIXTURES_DIR / "mvp_demo_project_v2.json"
    with open(fixture_path) as f:
        return json.load(f)


def test_v2_optimise_endpoint_success(mvp_v2_payload: dict) -> None:
    response = client.post("/api/v2/optimise", json=mvp_v2_payload)

    assert response.status_code == 200, response.text
    data = response.json()

    # Validate against our Pydantic model
    validated = OptimiseProjectResponse.model_validate(data)

    assert validated.status == "SUCCESS"
    assert validated.request_id == "REQ-MVP-001"
    assert validated.project_id == "MVP-DEMO"

    assert validated.generation is not None
    assert validated.generation.requested_candidate_count == 3
    assert validated.generation.accepted_candidate_count == 3
    assert validated.generation.attempts == 3

    assert len(validated.candidates) == validated.generation.accepted_candidate_count
    assert all(c.electrical_status == "VALID" for c in validated.candidates)
    assert all(c.eligible is True for c in validated.candidates)
    assert len({c.topology_fingerprint for c in validated.candidates}) == 3
    assert sorted(c.rank for c in validated.candidates if c.rank is not None) == [
        1,
        2,
        3,
    ]

    assert validated.recommendation is not None
    assert validated.recommendation.recommended_scenario_id is not None

    assert validated.recommended_result is not None
    assert validated.recommended_result.network_summary.wtg_count == 8
    assert validated.recommended_result.pole_summary is not None
    assert validated.recommended_result.pole_summary.total_poles > 0
    assert len(validated.recommended_result.feeders) > 0
    features = validated.recommended_result.feature_collection["features"]
    wtg_features = [
        feature
        for feature in features
        if feature["properties"]["feature_type"] == "pnc_wtg"
    ]
    segment_features = [
        feature
        for feature in features
        if feature["properties"]["feature_type"] == "pnc_segment"
    ]
    pole_features = [
        feature
        for feature in features
        if feature["properties"]["feature_type"] == "pnc_pole"
    ]
    assert len(wtg_features) == 8
    assert (
        len(segment_features)
        == validated.recommended_result.network_summary.segment_count
    )
    assert len(pole_features) == validated.recommended_result.pole_summary.total_poles
    assert {
        feature["properties"]["recommended_pole_type"] for feature in pole_features
    }.issubset(
        {
            "33kV terminal/dead-end pole",
            "33kV angle/tension pole",
            "33kV tangent/suspension pole",
        }
    )

    repeated = client.post("/api/v2/optimise", json=mvp_v2_payload)
    assert repeated.status_code == 200
    assert repeated.json() == data


def test_v2_constraint_fixture_reports_soft_impacts() -> None:
    fixture_path = FIXTURES_DIR / "constraint_demo_project_v2.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    response = client.post("/api/v2/optimise", json=payload)

    assert response.status_code == 200, response.text
    result = OptimiseProjectResponse.model_validate(response.json()).recommended_result
    assert result is not None
    summary = result.spatial_constraint_summary
    assert summary is not None
    assert summary.hard_exclusion_violation_count == 0
    assert summary.soft_constraint_intersection_count >= 1
    assert summary.soft_constraint_overlap_length_m > 0
    assert summary.road_crossing_count >= 1

    repeated = client.post("/api/v2/optimise", json=payload)
    assert repeated.status_code == 200
    assert repeated.json() == response.json()


@pytest.mark.parametrize(
    "mutation",
    [
        "resolution",
        "weights",
        "duplicate_cable",
        "voltage_order",
        "missing_capacity",
    ],
)
def test_v2_optimise_endpoint_invalid_input(
    mvp_v2_payload: dict,
    mutation: str,
) -> None:
    payload = copy.deepcopy(mvp_v2_payload)
    if mutation == "resolution":
        payload["routing_config"]["resolution_m"] = 0.5
    elif mutation == "weights":
        payload["scoring_weights"]["route_length_weight"] = 0.5
    elif mutation == "duplicate_cable":
        payload["cable_config"]["cable_types"].append(
            copy.deepcopy(payload["cable_config"]["cable_types"][0])
        )
    elif mutation == "voltage_order":
        payload["cable_config"]["min_voltage_pu"] = 1.1
    else:
        del payload["wtg_geojson"]["features"][0]["properties"]["capacity_mw"]

    response = client.post("/api/v2/optimise", json=payload)

    assert response.status_code == 422


def test_v1_endpoint_remains_supported() -> None:
    openapi_response = client.get("/api/v1/openapi.json")
    assert openapi_response.status_code == 200
    spec = openapi_response.json()

    post_op = spec["paths"]["/api/v1/optimise"]["post"]
    assert post_op.get("deprecated") is not True


def test_v2_reports_partial_success(mvp_v2_payload: dict) -> None:
    payload = copy.deepcopy(mvp_v2_payload)
    payload["scenario_config"]["candidate_count"] = 2
    payload["cable_config"]["nominal_voltage_kv"] = 66.0
    payload["cable_config"]["cable_types"][0]["max_current_a"] = 900.0

    response = client.post("/api/v2/optimise", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PARTIAL_SUCCESS"
    assert body["generation"]["requested_candidate_count"] == 2
    assert body["generation"]["accepted_candidate_count"] == 1


def test_v2_reports_no_feasible_candidate(mvp_v2_payload: dict) -> None:
    payload = copy.deepcopy(mvp_v2_payload)
    payload["cable_config"]["min_voltage_pu"] = 1.01
    payload["cable_config"]["max_voltage_pu"] = 1.10

    response = client.post("/api/v2/optimise", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NO_FEASIBLE_CANDIDATE"
    assert "recommended_scenario_id" not in body["recommendation"]
    assert "recommended_result" not in body


def test_v2_reports_failed_workflow(
    mvp_v2_payload: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.optimisation import orchestrator

    def fail_load_flow(*args: object, **kwargs: object) -> None:
        raise CandidateElectricalEvaluationError("candidate evaluation failed")

    monkeypatch.setattr(orchestrator, "run_load_flow", fail_load_flow)

    response = client.post("/api/v2/optimise", json=mvp_v2_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert len(body["failures"]) == 3
    assert "recommendation" not in body
    assert "recommended_result" not in body
