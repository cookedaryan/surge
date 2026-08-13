import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from app.main import app

client = TestClient(app)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def constraint_v1_payload() -> dict[str, Any]:
    fixture_path = FIXTURES_DIR / "constraint_demo_project_v2.json"
    payload = cast(
        dict[str, Any],
        json.loads(fixture_path.read_text(encoding="utf-8")),
    )
    payload["scenario"] = "Balanced"
    return payload


def _route_geometry(response_body: dict[str, Any]) -> BaseGeometry:
    route_features = response_body["feeder_routes_geojson"]["features"]
    return unary_union([shape(feature["geometry"]) for feature in route_features])


def test_v1_constraint_fixture_routes_around_hard_exclusion(
    constraint_v1_payload: dict[str, Any],
) -> None:
    response = client.post("/api/v1/optimise", json=constraint_v1_payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["workflow_status"] == "SUCCESS"

    summary = body["recommended_result"]["spatial_constraint_summary"]
    assert summary["road_crossing_count"] == 1
    assert summary["soft_constraint_overlap_length_m"] > 0
    assert summary["hard_exclusion_violation_count"] == 0

    route_geometry = _route_geometry(body)
    hard_exclusions = [
        shape(feature["geometry"])
        for feature in constraint_v1_payload["avoidance_geojson"]["features"]
        if feature["properties"]["routing_mode"] == "HARD_EXCLUSION"
    ]
    assert hard_exclusions
    assert all(route_geometry.disjoint(exclusion) for exclusion in hard_exclusions)


def test_v1_constraint_fixture_is_deterministic(
    constraint_v1_payload: dict[str, Any],
) -> None:
    first = client.post("/api/v1/optimise", json=constraint_v1_payload)
    second = client.post("/api/v1/optimise", json=constraint_v1_payload)

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.content == first.content


def test_v1_rejects_endpoint_inside_hard_exclusion_buffer(
    constraint_v1_payload: dict[str, Any],
) -> None:
    payload = copy.deepcopy(constraint_v1_payload)
    hard_exclusion = payload["avoidance_geojson"]["features"][0]
    hard_exclusion["properties"]["buffer_m"] = 20.0
    payload["wtg_geojson"]["features"][0]["geometry"]["coordinates"] = [
        -1.0,
        52.0006,
    ]
    wtg_point = Point(-1.0, 52.0006)

    assert not shape(hard_exclusion["geometry"]).covers(wtg_point)

    response = client.post("/api/v1/optimise", json=payload)

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "WTG T01" in detail
    assert "restricted-1" in detail


def test_v1_without_constraints_preserves_uniform_cost_routing(
    constraint_v1_payload: dict[str, Any],
) -> None:
    payload = copy.deepcopy(constraint_v1_payload)
    del payload["avoidance_geojson"]

    response = client.post("/api/v1/optimise", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["workflow_status"] == "SUCCESS"
    assert "spatial_constraint_summary" not in body["recommended_result"]

    wtg_coordinates = payload["wtg_geojson"]["features"][0]["geometry"]["coordinates"]
    substation_coordinates = payload["substation_geojson"]["features"][0]["geometry"][
        "coordinates"
    ]
    direct_route = LineString([wtg_coordinates, substation_coordinates])
    route_geometry = _route_geometry(body)

    assert route_geometry.geom_type == "LineString"
    assert len(route_geometry.coords) == 2
    assert route_geometry.hausdorff_distance(direct_route) < 1e-9
