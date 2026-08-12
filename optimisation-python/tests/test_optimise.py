from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.legacy_mapping import legacy_to_workflow_invocation
from app.schemas.optimise import OptimisationRequest

client = TestClient(app)


def create_payload() -> dict[str, Any]:
    return {
        "request_id": "request-001",
        "project_id": "project-123",
        "scenario": "Balanced",
        "wtg_geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [0.0, 50.0]},
                    "properties": {"id": "WTG1", "capacity_mw": 5.0},
                }
            ],
        },
        "substation_geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [0.0, 50.1]},
                    "properties": {"id": "SUB1"},
                }
            ],
        },
        "electrical_params": {
            "feeder_capacity_mw": 20.0,
            "max_voltage_drop_pct": 5.0,
            "row_width_m": 18.0,
        },
    }


def test_optimise_stub() -> None:
    response = client.post(
        "/api/v1/optimise",
        json=create_payload(),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"
    assert body["request_id"] == "request-001"
    assert body["scenario"] == "Balanced"
    assert body["metrics"]["feeder_count"] == 1
    properties = body["feeder_routes_geojson"]["features"][0]["properties"]
    assert properties["length_m"] == properties["refined_length_m"]
    assert properties["traversal_cost"] == properties["refined_traversal_cost"]
    assert properties["refined_length_m"] <= properties["original_length_m"]
    assert body["metrics"]["message"].startswith("Pipeline completed.")
    assert body["workflow_status"] in {"SUCCESS", "PARTIAL_SUCCESS"}
    assert body["generation"]["requested_candidate_count"] == 3
    assert body["candidates"]
    assert body["recommendation"]["recommended_scenario_id"]
    assert body["recommended_result"]["network_summary"]["wtg_count"] == 1
    assert body["recommended_result"]["feature_collection"]["type"] == (
        "FeatureCollection"
    )


def test_coincident_route_endpoints_return_422() -> None:
    payload = create_payload()
    payload["wtg_geojson"]["features"][0]["geometry"]["coordinates"] = [
        0.0,
        50.1,
    ]

    response = client.post("/api/v1/optimise", json=payload)

    assert response.status_code == 422
    assert "coincident endpoints" in response.json()["detail"]


def test_v1_feeder_capacity_remains_authoritative_with_explicit_cable() -> None:
    payload = create_payload()
    payload["cable_config"] = {
        "nominal_voltage_kv": 66.0,
        "cable_types": [
            {
                "cable_type_id": "HIGH_CAPACITY",
                "resistance_ohm_per_km": 0.03,
                "reactance_ohm_per_km": 0.1,
                "capacitance_nf_per_km": 200.0,
                "max_current_a": 900.0,
            }
        ],
        "default_cable_type_id": "HIGH_CAPACITY",
    }

    invocation = legacy_to_workflow_invocation(
        OptimisationRequest.model_validate(payload)
    )

    assert invocation.project_input.feeder_capacity_mw == 20.0


def test_invalid_scenario() -> None:
    payload = create_payload()
    payload["scenario"] = "Invalid Scenario"

    response = client.post(
        "/api/v1/optimise",
        json=payload,
    )

    assert response.status_code == 422


def test_negative_feeder_capacity() -> None:
    payload = create_payload()
    payload["electrical_params"]["feeder_capacity_mw"] = -10

    response = client.post(
        "/api/v1/optimise",
        json=payload,
    )

    assert response.status_code == 422


def test_empty_wtg_collection() -> None:
    payload = create_payload()
    payload["wtg_geojson"]["features"] = []

    response = client.post("/api/v1/optimise", json=payload)

    assert response.status_code == 422
    assert "WTG FeatureCollection is empty" in response.json()["detail"]


def test_invalid_wtg_geometry() -> None:
    payload = create_payload()
    payload["wtg_geojson"]["features"][0]["geometry"] = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
    }

    response = client.post("/api/v1/optimise", json=payload)

    assert response.status_code == 422
    assert "WTG geometry must be Point" in response.json()["detail"]


def test_missing_substation() -> None:
    payload = create_payload()
    payload["substation_geojson"]["features"] = []

    response = client.post("/api/v1/optimise", json=payload)

    assert response.status_code == 422
    assert "Substation GeoJSON is empty or missing" in response.json()["detail"]


def test_multiple_substations() -> None:
    payload = create_payload()
    payload["substation_geojson"]["features"].append(
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0.0, 50.2]},
            "properties": {"id": "SUB2"},
        }
    )

    response = client.post("/api/v1/optimise", json=payload)

    assert response.status_code == 422
    assert "exactly one Substation feature" in response.json()["detail"]


def test_malformed_feature_collection() -> None:
    payload = create_payload()
    payload["wtg_geojson"]["features"] = {"not": "a list"}

    response = client.post("/api/v1/optimise", json=payload)

    assert response.status_code == 422
    assert "must be a list" in response.json()["detail"]
