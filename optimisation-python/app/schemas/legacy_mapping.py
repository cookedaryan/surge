import math
from dataclasses import replace
from typing import Any, Literal

from app.optimisation.workflow_models import OptimisationWorkflowResult
from app.schemas.optimise import (
    OptimisationMetrics,
    OptimisationRequest,
    OptimisationResponse,
)
from app.schemas.v2.domain_mapping import (
    WorkflowInvocation,
    to_api_response,
    to_workflow_invocation,
)
from app.schemas.v2.optimise import (
    CableConfigRequest,
    CableTypeRequest,
    OptimiseProjectRequest,
)

_COMPATIBILITY_CABLE_ID = "MVP-COMPATIBILITY-CABLE"


def legacy_to_workflow_invocation(payload: OptimisationRequest) -> WorkflowInvocation:
    """Map the Java-compatible V1 request into the canonical workflow input."""

    cable_config = payload.cable_config or _compatibility_cable_config(payload)
    request = OptimiseProjectRequest(
        request_id=payload.request_id,
        project_id=payload.project_id,
        wtg_geojson=payload.wtg_geojson,
        substation_geojson=payload.substation_geojson,
        avoidance_geojson=payload.avoidance_geojson,
        routing_config=payload.routing_config.model_copy(
            update={"row_width_m": payload.electrical_params.row_width_m}
        ),
        pole_config=payload.pole_config,
        operating_point_config=payload.operating_point_config,
        cable_config=cable_config,
        scenario_config=payload.scenario_config,
        scoring_weights=payload.scoring_weights,
    )
    invocation = to_workflow_invocation(request)
    return WorkflowInvocation(
        project_input=replace(
            invocation.project_input,
            feeder_capacity_mw=payload.electrical_params.feeder_capacity_mw,
        ),
        config=invocation.config,
    )


def to_legacy_api_response(
    workflow_result: OptimisationWorkflowResult,
    payload: OptimisationRequest,
) -> OptimisationResponse:
    """Build the additive V1 response while preserving its legacy fields."""

    rich_response = to_api_response(
        workflow_result,
        request_id=payload.request_id,
        project_id=payload.project_id,
    )
    presentation = workflow_result.recommended_result
    routes = (
        _legacy_route_collection(presentation.feature_collection)
        if presentation
        else None
    )
    poles = (
        _legacy_pole_collection(presentation.feature_collection)
        if presentation
        else None
    )
    network_summary = presentation.network_summary if presentation else None
    status: Literal["success", "failed"] = (
        "success"
        if workflow_result.status.value in {"SUCCESS", "PARTIAL_SUCCESS"}
        else "failed"
    )

    return OptimisationResponse(
        request_id=payload.request_id,
        status=status,
        scenario=payload.scenario,
        feeder_routes_geojson=routes,
        poles_geojson=poles,
        metrics=OptimisationMetrics(
            feeder_count=network_summary.feeder_count if network_summary else 0,
            total_length_m=(
                network_summary.total_route_length_m if network_summary else 0.0
            ),
            estimated_cost=None,
            message=_legacy_message(
                workflow_result,
                presentation.source_crs if presentation else None,
            ),
        ),
        workflow_status=rich_response.status,
        generation=rich_response.generation,
        candidates=rich_response.candidates,
        recommendation=rich_response.recommendation,
        recommended_result=rich_response.recommended_result,
        failures=rich_response.failures,
    )


def _compatibility_cable_config(payload: OptimisationRequest) -> CableConfigRequest:
    """Derive the cable ampacity needed to retain the legacy feeder-capacity input."""

    nominal_voltage_kv = payload.electrical_params.nominal_voltage_kv
    power_factor = payload.operating_point_config.power_factor
    max_current_a = (
        payload.electrical_params.feeder_capacity_mw
        * 1000.0
        / (math.sqrt(3.0) * nominal_voltage_kv * power_factor)
    )
    voltage_tolerance = payload.electrical_params.max_voltage_drop_pct / 100.0
    return CableConfigRequest(
        nominal_voltage_kv=nominal_voltage_kv,
        min_voltage_pu=max(0.001, 1.0 - voltage_tolerance),
        max_voltage_pu=1.0 + voltage_tolerance,
        cable_types=[
            CableTypeRequest(
                cable_type_id=_COMPATIBILITY_CABLE_ID,
                resistance_ohm_per_km=0.03,
                reactance_ohm_per_km=0.10,
                capacitance_nf_per_km=200.0,
                max_current_a=max_current_a,
            )
        ],
        default_cable_type_id=_COMPATIBILITY_CABLE_ID,
    )


def _legacy_route_collection(feature_collection: dict[str, Any]) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for feature in feature_collection.get("features", []):
        properties = feature.get("properties", {})
        if properties.get("feature_type") != "pnc_segment":
            continue
        length_m = properties["length_m"]
        legacy_properties = dict(properties)
        legacy_properties.update(
            {
                "feederName": properties["feeder_id"],
                "edge": f"{properties['from_node']}-{properties['to_node']}",
                "traversal_cost": length_m,
                "original_length_m": length_m,
                "refined_length_m": length_m,
                "original_traversal_cost": length_m,
                "refined_traversal_cost": length_m,
            }
        )
        features.append(
            {
                "type": "Feature",
                "id": feature.get("id"),
                "properties": legacy_properties,
                "geometry": feature["geometry"],
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _legacy_pole_collection(feature_collection: dict[str, Any]) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for feature in feature_collection.get("features", []):
        properties = feature.get("properties", {})
        if properties.get("feature_type") != "pnc_pole":
            continue
        feeder_ids = properties.get("connected_feeder_ids") or []
        legacy_properties = dict(properties)
        legacy_properties.update(
            {
                "poleId": properties.get("pole_id"),
                "feederName": feeder_ids[0] if feeder_ids else None,
                "feederIds": feeder_ids,
                "poleRole": properties.get("pole_role"),
                "recommendedPoleType": properties.get("recommended_pole_type"),
            }
        )
        features.append(
            {
                "type": "Feature",
                "id": feature.get("id"),
                "properties": legacy_properties,
                "geometry": feature["geometry"],
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _legacy_message(
    result: OptimisationWorkflowResult,
    source_crs: str | None,
) -> str:
    if result.recommended_result is None:
        return f"Optimisation completed with workflow status {result.status.value}."
    return (
        "Pipeline completed. Recommended candidate selected by the end-to-end "
        f"workflow. Projected from {source_crs}."
    )
