from typing import Any

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def valid_payload() -> dict[str, Any]:
    return {
        "request_id": "request-001",
        "project_id": "proj-123",
        "scenario": "Balanced",
        "wtg_geojson": {
            "type": "FeatureCollection",
            "features": [],
        },
        "substation_geojson": {
            "type": "FeatureCollection",
            "features": [],
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
        json=valid_payload(),
    )

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "success"
    assert body["request_id"] == "request-001"
    assert body["scenario"] == "Balanced"


def test_invalid_scenario_is_rejected() -> None:
    payload = valid_payload()
    payload["scenario"] = "Unknown Scenario"

    response = client.post(
        "/api/v1/optimise",
        json=payload,
    )

    assert response.status_code == 422


def test_negative_capacity_is_rejected() -> None:
    payload = valid_payload()
    payload["electrical_params"]["feeder_capacity_mw"] = -10

    response = client.post(
        "/api/v1/optimise",
        json=payload,
    )

    assert response.status_code == 422
