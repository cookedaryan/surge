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

def test_v1_costing_config_produces_real_candidate_costs(
    constraint_v1_payload: dict[str, Any],
) -> None:
    """
    Costs only exist when the caller asks for them, and V1 could not ask.

    ``evaluate_candidate_cost`` runs only when a request carries a
    ``costing_config``. V1 had no such field, and this model ignores unknown
    keys, so a caller sending one had it dropped without complaint and received
    ``cost: null`` on every candidate -- no CAPEX, no loss valuation, nothing to
    compare scenarios on -- with no error to explain why.
    """
    payload = copy.deepcopy(constraint_v1_payload)
    payload["costing_config"] = {
        "catalogue": {
            "catalogue_id": "TEST-CATALOGUE",
            "version": "1",
            "currency": "INR",
            "price_basis_date": "2026-01-01",
            # Rates are keyed on the conductor ids cable sizing actually selects.
            # This fixture carries its own cable_config, so the rate has to name
            # that conductor -- a catalogue that misses one gets no conductor
            # CAPEX at all, as the test below shows.
            "conductor_items": [
                {
                    "cable_type_id": "33kV-demo",
                    "installed_cost_per_km_per_parallel_circuit": 1_200_000.0,
                }
            ],
            "pole_items": [
                {"pole_type": "terminal", "installed_cost_each": 45_000.0},
                {"pole_type": "angle", "installed_cost_each": 38_000.0},
                {"pole_type": "intermediate", "installed_cost_each": 22_000.0},
                {"pole_type": "junction", "installed_cost_each": 52_000.0},
            ],
            "land_policy": {
                "fixed_cost_per_affected_parcel": 25_000.0,
                "variable_basis": "ROUTE_OVERLAP_LENGTH_M",
                "variable_rate": 400.0,
            },
        },
        "lifecycle": {
            "currency": "INR",
            "energy_price_basis_date": "2026-01-01",
            "analysis_period_years": 25,
            "discount_rate": 0.08,
            "annual_operating_hours": 8760,
            "loss_load_factor": 0.35,
            "energy_price_per_mwh": 3_500.0,
        },
    }

    response = client.post("/api/v1/optimise", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()

    costed = [c for c in body["candidates"] if c.get("cost") is not None]
    assert costed, "a request carrying a costing_config must come back costed"

    cost = costed[0]["cost"]
    assert cost["currency"] == "INR"
    assert cost["total_capex"] > 0, "conductor and pole CAPEX must be summed"
    assert cost["conductor_capex"] > 0
    assert cost["pole_capex"] > 0
    # The whole point of a lifecycle figure: losses valued over the analysis
    # period, not just the money spent on day one.
    assert cost["annual_loss_energy_mwh"] > 0
    assert cost["lifecycle_cost"] > cost["total_capex"]
    assert cost["catalogue_id"] == "TEST-CATALOGUE"


def test_v1_without_costing_config_stays_uncosted(
    constraint_v1_payload: dict[str, Any],
) -> None:
    """
    Absent rates must read as absent, not as zero.

    A run with no catalogue has no cost, and inventing one would put fabricated
    money in front of an engineer who cannot tell it from a real quote.
    """
    response = client.post("/api/v1/optimise", json=constraint_v1_payload)

    assert response.status_code == 200, response.text
    assert all(c.get("cost") is None for c in response.json()["candidates"])

def test_v1_reports_an_uncovered_conductor_rather_than_costing_it_at_zero(
    constraint_v1_payload: dict[str, Any],
) -> None:
    """
    A cost catalogue that misses a conductor must say so.

    Conductor rates are keyed on the ids cable sizing selects, so a catalogue can
    be complete on paper and still not cover the conductor a run chose. Treating
    the gap as zero would understate CAPEX by the largest line in the estimate
    while looking like a finished number.
    """
    payload = copy.deepcopy(constraint_v1_payload)
    payload["costing_config"] = {
        "catalogue": {
            "catalogue_id": "TEST-CATALOGUE",
            "version": "1",
            "currency": "INR",
            "price_basis_date": "2026-01-01",
            "conductor_items": [
                {
                    "cable_type_id": "A-CONDUCTOR-THIS-RUN-DOES-NOT-USE",
                    "installed_cost_per_km_per_parallel_circuit": 1_200_000.0,
                }
            ],
            "pole_items": [
                {"pole_type": "terminal", "installed_cost_each": 45_000.0},
                {"pole_type": "angle", "installed_cost_each": 38_000.0},
                {"pole_type": "intermediate", "installed_cost_each": 22_000.0},
                {"pole_type": "junction", "installed_cost_each": 52_000.0},
            ],
            "land_policy": {
                "fixed_cost_per_affected_parcel": 0.0,
                "variable_basis": "NONE",
                "variable_rate": 0.0,
            },
        },
        "lifecycle": {
            "currency": "INR",
            "energy_price_basis_date": "2026-01-01",
            "analysis_period_years": 25,
            "discount_rate": 0.08,
            "annual_operating_hours": 8760,
            "loss_load_factor": 0.35,
            "energy_price_per_mwh": 3_500.0,
        },
    }

    response = client.post("/api/v1/optimise", json=payload)
    assert response.status_code == 200, response.text
    cost = response.json()["candidates"][0]["cost"]

    failures = cost["failures"]
    assert [f["code"] for f in failures] == ["CABLE_COST_NOT_FOUND"]
    assert failures[0]["component"] == "conductor_capex"
    # No conductor rate means no conductor CAPEX and therefore no total -- absent,
    # not zero, and not a total that silently omits a line.
    assert cost.get("conductor_capex") is None
    assert cost.get("total_capex") is None
    # Poles were priced, and reporting that is not the same as reporting a total.
    assert cost["pole_capex"] > 0
