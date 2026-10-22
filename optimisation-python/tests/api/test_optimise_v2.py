import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from app.electrical.errors import CandidateElectricalEvaluationError
from app.main import app
from app.schemas.v2.domain_mapping import to_workflow_invocation
from app.schemas.v2.optimise import (
    EngineeringScoringWeightsRequest,
    OptimiseProjectRequest,
    OptimiseProjectResponse,
)

client = TestClient(app)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
JsonObject = dict[str, Any]


@pytest.fixture
def mvp_v2_payload() -> JsonObject:
    fixture_path = FIXTURES_DIR / "mvp_demo_project_v2.json"
    with open(fixture_path) as f:
        return cast(JsonObject, json.load(f))


def _costing_config(*, include_conductor: bool = True) -> JsonObject:
    conductor_items = (
        [
            {
                "cable_type_id": "66kV_800mm2",
                "installed_cost_per_km_per_parallel_circuit": 100_000.0,
            }
        ]
        if include_conductor
        else []
    )
    return {
        "catalogue": {
            "catalogue_id": "CAT-TEST",
            "version": "1.0",
            "currency": "USD",
            "price_basis_date": "2026-01-01",
            "conductor_items": conductor_items,
            "pole_items": [
                {"pole_type": "terminal", "installed_cost_each": 5_000.0},
                {"pole_type": "angle", "installed_cost_each": 6_000.0},
                {"pole_type": "intermediate", "installed_cost_each": 3_000.0},
                {"pole_type": "junction", "installed_cost_each": 7_000.0},
            ],
            "land_policy": {
                "fixed_cost_per_affected_parcel": 0.0,
                "variable_basis": "NONE",
                "variable_rate": 0.0,
            },
        },
        "lifecycle": {
            "currency": "USD",
            "energy_price_basis_date": "2026-01-01",
            "analysis_period_years": 25,
            "discount_rate": 0.08,
            "annual_operating_hours": 8_760,
            "loss_load_factor": 0.3,
            "energy_price_per_mwh": 50.0,
        },
    }


def test_v2_optimise_endpoint_success(mvp_v2_payload: JsonObject) -> None:
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
    assert all(c.engineering_metrics is not None for c in validated.candidates)
    assert all(c.group_scores is not None for c in validated.candidates)
    assert all(c.cable_sizing is not None for c in validated.candidates)
    assert all(
        c.engineering_metrics is not None
        and c.engineering_metrics.environmental_overlap_m2 >= 0.0
        for c in validated.candidates
    )
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
            "33kV shared junction pole",
        }
    )

    repeated = client.post("/api/v2/optimise", json=mvp_v2_payload)
    assert repeated.status_code == 200
    assert repeated.json() == data


def test_v2_accepts_unified_policy_with_inactive_groups(
    mvp_v2_payload: JsonObject,
) -> None:
    payload = copy.deepcopy(mvp_v2_payload)
    payload.pop("scoring_weights")
    payload["engineering_scoring_weights"] = {
        "physical_weight": 1.0,
        "spatial_weight": 0.0,
        "infrastructure_weight": 0.0,
        "electrical_weight": 0.0,
        "spatial_subweights": {
            "traversal_cost": 0.0,
            "affected_parcels": 0.0,
            "road_crossings": 0.0,
            "soft_overlap_length": 0.0,
        },
        "electrical_subweights": {
            "active_loss": 0.0,
            "cable_loading": 0.0,
            "voltage_margin": 0.0,
        },
    }

    response = client.post("/api/v2/optimise", json=payload)

    assert response.status_code == 200, response.text
    result = OptimiseProjectResponse.model_validate(response.json())
    assert result.status == "SUCCESS"
    assert result.recommendation is not None
    assert all(
        candidate.group_scores is not None and len(candidate.group_scores) == 4
        for candidate in result.candidates
    )


def test_v2_maps_land_commercial_context(mvp_v2_payload: JsonObject) -> None:
    payload = copy.deepcopy(mvp_v2_payload)
    payload["land_context"] = {
        "currency": "USD",
        "as_of_date": "2026-01-01",
        "parcel_profiles": [
            {
                "parcel_id": "P1",
                "owner_id": "OWNER-1",
                "availability_status": "NEGOTIABLE",
                "transaction_options": [
                    {
                        "mode": "LEASE",
                        "price_status": "QUOTED",
                        "upfront_cost": "1000",
                        "annual_cost": "250",
                        "term_years": 10,
                        "price_date": "2026-01-01",
                    }
                ],
            }
        ],
    }

    request = OptimiseProjectRequest.model_validate(payload)
    invocation = to_workflow_invocation(request)

    context = invocation.project_input.land_context
    assert context is not None
    assert context.currency == "USD"
    assert context.parcel_profiles[0].parcel_id == "P1"
    assert context.parcel_profiles[0].transaction_options[0].annual_cost == 250


def test_response_reports_the_decision_taken_for_each_parcel(
    mvp_v2_payload: JsonObject,
) -> None:
    """
    The land engine's conclusions have to leave the process.

    Only ``owner_interaction_count`` used to reach the response, with the
    per-parcel decisions dropped. A consumer could report how many owners had to
    be approached but not which instrument was chosen for which parcel, nor
    whether any price behind that figure was a real quote.
    """
    payload = copy.deepcopy(mvp_v2_payload)
    payload["land_context"] = {
        "currency": "USD",
        "as_of_date": "2026-01-01",
        "parcel_profiles": [
            {
                "parcel_id": "P1",
                "owner_id": "OWNER-1",
                "availability_status": "NEGOTIABLE",
                "transaction_options": [
                    {
                        "mode": "PURCHASE",
                        "price_status": "QUOTED",
                        "upfront_cost": "9000",
                        "annual_cost": "0",
                        "term_years": None,
                        "price_date": "2026-01-01",
                    },
                    {
                        # Cheaper in present value, so this is the one the engine
                        # should pick -- and the response has to say so.
                        "mode": "EASEMENT",
                        "price_status": "QUOTED",
                        "upfront_cost": "500",
                        "annual_cost": "0",
                        "term_years": None,
                        "price_date": "2026-01-01",
                    },
                ],
            }
        ],
    }

    response = client.post("/api/v2/optimise", json=payload)
    assert response.status_code == 200

    result = OptimiseProjectResponse.model_validate(response.json())
    assessed = [c for c in result.candidates if c.land is not None]
    assert assessed, "at least one candidate must report a land assessment"

    land = assessed[0].land
    assert land is not None
    assert land.owner_interaction_basis in {"CONFIRMED_OWNER_IDS", "PARCEL_PROXY"}
    assert land.land_cost_basis in {"QUOTED", "ESTIMATED", "MIXED", "UNKNOWN"}

    # Whether this candidate's route happens to touch P1 depends on the geometry,
    # so assert the shape of whatever decisions it did make rather than a count.
    for decision in land.parcel_decisions:
        assert decision.parcel_id
        assert decision.availability_status
        if decision.selected_mode is not None:
            assert decision.selected_mode in {"PURCHASE", "LEASE", "EASEMENT"}
            assert decision.selected_present_value is not None


def test_v2_returns_partial_cost_components_with_failure_details(
    mvp_v2_payload: JsonObject,
) -> None:
    payload = copy.deepcopy(mvp_v2_payload)
    payload["costing_config"] = _costing_config(include_conductor=False)

    response = client.post("/api/v2/optimise", json=payload)

    assert response.status_code == 200, response.text
    result = OptimiseProjectResponse.model_validate(response.json())
    for candidate in result.candidates:
        assert candidate.cost is not None
        assert candidate.cost.conductor_capex is None
        assert candidate.cost.pole_capex is not None
        assert candidate.cost.land_capex == 0.0
        assert candidate.cost.land_purchase_capex == 0.0
        assert candidate.cost.land_recurring_cost_pv == 0.0
        assert candidate.cost.land_access_present_value == 0.0
        assert candidate.cost.total_capex is None
        assert candidate.cost.present_value_opex is not None
        assert candidate.cost.lifecycle_cost is None
        assert candidate.cost.currency == "USD"
        assert any(
            failure.code == "CABLE_COST_NOT_FOUND"
            for failure in candidate.cost.failures
        )


def test_v2_rejects_mixed_costing_currencies(
    mvp_v2_payload: JsonObject,
) -> None:
    payload = copy.deepcopy(mvp_v2_payload)
    payload["costing_config"] = _costing_config()
    payload["costing_config"]["lifecycle"]["currency"] = "EUR"

    response = client.post("/api/v2/optimise", json=payload)

    assert response.status_code == 422
    assert "currency must match" in response.text


def test_v2_rejects_unresolvable_catalogue_reference(
    mvp_v2_payload: JsonObject,
) -> None:
    payload = copy.deepcopy(mvp_v2_payload)
    payload["costing_config"] = _costing_config()
    payload["costing_config"]["catalogue"] = "CAT-TEST"

    response = client.post("/api/v2/optimise", json=payload)

    assert response.status_code == 422


def test_unified_policy_rejects_nonzero_subweights_for_inactive_group() -> None:
    with pytest.raises(ValueError, match="inactive spatial group"):
        EngineeringScoringWeightsRequest.model_validate(
            {
                "physical_weight": 1.0,
                "spatial_weight": 0.0,
                "infrastructure_weight": 0.0,
                "electrical_weight": 0.0,
                "electrical_subweights": {
                    "active_loss": 0.0,
                    "cable_loading": 0.0,
                    "voltage_margin": 0.0,
                },
            },
        )


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
    mvp_v2_payload: JsonObject,
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


def test_v2_reports_partial_success(mvp_v2_payload: JsonObject) -> None:
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


def test_v2_reports_no_feasible_candidate(mvp_v2_payload: JsonObject) -> None:
    payload = copy.deepcopy(mvp_v2_payload)
    payload["cable_config"]["min_voltage_pu"] = 1.01
    payload["cable_config"]["max_voltage_pu"] = 1.10

    response = client.post("/api/v2/optimise", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "NO_FEASIBLE_CANDIDATE"
    if "recommendation" in body and body["recommendation"] is not None:
        assert "recommended_scenario_id" not in body["recommendation"]
    assert "recommended_result" not in body


def test_exhausted_repair_reports_what_defeated_it(
    mvp_v2_payload: JsonObject,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A caller must be able to diagnose REPAIR_EXHAUSTED from the response alone.

    It used to return ``Electrical repair failed: REPAIR_EXHAUSTED`` and nothing
    else, so working out which segment and which limit had defeated the run meant
    reading server logs on the machine that produced it.
    """
    from app.electrical.load_flow.models import (
        LoadFlowNetworkResult,
        LoadFlowViolation,
        LoadFlowViolationCode,
    )
    from app.electrical.repair import (
        ClosedLoopRepairResult,
        RepairExhaustionReason,
        RepairStatus,
    )

    def exhausted(*args: object, **kwargs: object) -> ClosedLoopRepairResult:
        config = kwargs["config"]
        return ClosedLoopRepairResult(
            status=RepairStatus.REPAIR_EXHAUSTED,
            final_electrical_config=config,  # type: ignore[arg-type]
            load_flow_result=LoadFlowNetworkResult(
                converged=True,
                is_valid=False,
                solver_algorithm="nr",
                total_generation_mw=10.0,
                slack_power_mw=-10.0,
                total_active_loss_mw=0.1,
                total_reactive_loss_mvar=0.1,
                minimum_voltage_pu=0.91,
                maximum_voltage_pu=1.0,
                maximum_loading_percent=140.0,
                buses=(),
                segments=(),
                feeders=(),
                violations=(
                    LoadFlowViolation(
                        code=LoadFlowViolationCode.CABLE_OVERLOAD,
                        message="segment overloaded",
                        segment_id="SEG-UNDER-TEST",
                        measured_value=700.0,
                        limit_value=500.0,
                    ),
                ),
            ),
            repair_log=(),
            initial_cable_sizing=None,
            exhaustion_reason=(RepairExhaustionReason.NO_LARGER_CONDUCTOR_FOR_OVERLOAD),
        )

    monkeypatch.setattr(
        "app.optimisation.candidate_evaluation.repair_electrical_design", exhausted
    )

    response = client.post("/api/v2/optimise", json=mvp_v2_payload)
    assert response.status_code == 200

    failed = [
        c
        for c in response.json()["candidates"]
        if c.get("execution_failure") is not None
    ]
    assert failed, "an exhausted repair must be reported on the candidate"

    failure = failed[0]["execution_failure"]
    assert "details" in failure, "the diagnostics must survive to the response"

    details = failure["details"]
    assert details["status"] == "REPAIR_EXHAUSTED"
    assert details["unresolved_violations"][0]["segment_id"] == "SEG-UNDER-TEST"
    assert details["unresolved_violations"][0]["measured_value"] == 700.0
    assert details["unresolved_violations"][0]["limit_value"] == 500.0
    # Naming the biggest conductor available points at the catalogue rather than
    # the route when nothing in it could have carried the load.
    assert details["largest_cable_available"] is not None
    assert "SEG-UNDER-TEST" in failure["message"]

    # An empty repair log is ambiguous on its own: the catalogue running out and a
    # violation no conductor can fix produce the identical list.
    assert details["repair_attempts"] == []
    assert details["no_upgrade_reason_code"] == "NO_LARGER_CONDUCTOR_FOR_OVERLOAD"
    assert "catalogue" in details["no_upgrade_reason"]


def test_v2_reports_failed_workflow(
    mvp_v2_payload: JsonObject,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_repair(*args: object, **kwargs: object) -> None:
        raise CandidateElectricalEvaluationError("candidate evaluation failed")

    monkeypatch.setattr(
        "app.optimisation.candidate_evaluation.repair_electrical_design", fail_repair
    )

    response = client.post("/api/v2/optimise", json=mvp_v2_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FAILED"
    assert len(body["failures"]) == 3
    assert "recommendation" not in body
    assert "recommended_result" not in body
