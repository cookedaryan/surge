from typing import Any

from fastapi.testclient import TestClient

from app.main import app

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
                    "properties": {"id": "WTG1"}
                }
            ],
        },
        "substation_geojson": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [0.0, 50.1]},
                    "properties": {"id": "SUB1"}
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
