"""Map-ready WGS-84 GeoJSON enrichment with electrical telemetry."""

import math
from typing import Any

import pyproj

from app.algorithms.pole_placement import CollectorPoleResult
from app.electrical.load_flow.models import (
    LoadFlowNetworkResult,
    LoadFlowViolationCode,
)
from app.gis.crs import WGS84_CRS
from app.pnc.geojson import network_to_feature_collection
from app.pnc.models import ProjectPNCNetwork
from app.presentation.exceptions import PresentationDataMismatchError

_VOLTAGE_CODES = {
    LoadFlowViolationCode.BUS_UNDERVOLTAGE,
    LoadFlowViolationCode.BUS_OVERVOLTAGE,
}


def build_enriched_geojson(
    pnc_network: ProjectPNCNetwork,
    load_flow_result: LoadFlowNetworkResult,
    pole_result: CollectorPoleResult | None = None,
) -> dict[str, Any]:
    """Return deterministic WGS-84 PNC features with optional LF telemetry.

    The PNC converter creates a new collection, so enrichment can happen in
    place without copying the complete coordinate tree. Stable feature IDs and
    nullable electrical keys are present even when load flow did not converge.
    """

    collection = network_to_feature_collection(
        network=pnc_network,
        output_crs=WGS84_CRS,
    )
    features = _validate_feature_collection(collection)

    bus_map = (
        {bus.node_id: bus for bus in load_flow_result.buses}
        if load_flow_result.converged
        else {}
    )
    segment_map = (
        {segment.segment_id: segment for segment in load_flow_result.segments}
        if load_flow_result.converged
        else {}
    )
    voltage_violations = {
        violation.node_id
        for violation in load_flow_result.violations
        if violation.node_id is not None and violation.code in _VOLTAGE_CODES
    }
    overloads = {
        violation.segment_id
        for violation in load_flow_result.violations
        if violation.segment_id is not None
        and violation.code == LoadFlowViolationCode.CABLE_OVERLOAD
    }

    positions: list[tuple[float, float]] = []
    for feature in features:
        positions.extend(_validate_feature_geometry(feature))
        properties = feature["properties"]
        feature_type = properties["feature_type"]
        if feature_type == "pnc_substation":
            node_id = _require_feature_id(properties, "substation_id")
            feature["id"] = f"substation-{node_id}"
            _enrich_node(
                properties, bus_map.get(node_id), node_id in voltage_violations
            )
        elif feature_type == "pnc_wtg":
            node_id = _require_feature_id(properties, "wtg_id")
            feature["id"] = f"wtg-{node_id}"
            _enrich_node(
                properties, bus_map.get(node_id), node_id in voltage_violations
            )
        elif feature_type == "pnc_segment":
            segment_id = _require_feature_id(properties, "segment_id")
            feature["id"] = f"segment-{segment_id}"
            _enrich_segment(
                properties,
                segment_map.get(segment_id),
                bus_map,
                segment_id in overloads,
            )
        else:
            raise PresentationDataMismatchError(
                f"Unsupported PNC feature_type: {feature_type!r}"
            )
        _validate_json_value(properties, f"feature {feature['id']} properties")

    if pole_result is not None:
        transformer = pyproj.Transformer.from_crs(
            pnc_network.crs, pyproj.CRS("EPSG:4326"), always_xy=True
        )
        for pole in pole_result.physical_poles:
            longitude, latitude = transformer.transform(
                pole.geometry.x, pole.geometry.y
            )
            positions.append((longitude, latitude))
            structural_type = {
                "terminal": "33kV terminal/dead-end pole",
                "angle": "33kV angle/tension pole",
                "intermediate": "33kV tangent/suspension pole",
                "junction": "33kV shared junction pole",
            }.get(pole.pole_type, "33kV pole")
            properties = {
                "feature_type": "pnc_pole",
                "pole_id": pole.pole_id,
                "connected_feeder_ids": sorted(list(pole.feeder_ids)),
                "connected_route_ids": sorted(list(pole.route_ids)),
                "source_pole_ids": sorted(list(pole.source_pole_ids)),
                "pole_role": pole.pole_type,
                "recommended_pole_type": structural_type,
                "connected_node_ids": (
                    [pole.topology_node_id] if pole.topology_node_id else []
                ),
            }
            features.append(
                {
                    "type": "Feature",
                    "id": f"pole-{pole.pole_id}",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude],
                    },
                    "properties": properties,
                }
            )
            _validate_json_value(properties, f"feature pole-{pole.pole_id} properties")

    if not positions:
        raise PresentationDataMismatchError("FeatureCollection contains no positions")
    longitudes = [position[0] for position in positions]
    latitudes = [position[1] for position in positions]
    collection["bbox"] = [
        min(longitudes),
        min(latitudes),
        max(longitudes),
        max(latitudes),
    ]
    return collection


def _validate_feature_collection(collection: dict[str, Any]) -> list[dict[str, Any]]:
    if collection.get("type") != "FeatureCollection":
        raise PresentationDataMismatchError("Expected a GeoJSON FeatureCollection")
    features = collection.get("features")
    if not isinstance(features, list) or not features:
        raise PresentationDataMismatchError(
            "FeatureCollection.features must be a non-empty list"
        )
    for feature in features:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise PresentationDataMismatchError("Invalid GeoJSON Feature")
        if not isinstance(feature.get("properties"), dict):
            raise PresentationDataMismatchError("Feature properties must be an object")
    return features


def _validate_feature_geometry(feature: dict[str, Any]) -> list[tuple[float, float]]:
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict):
        raise PresentationDataMismatchError("Feature geometry must be an object")
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point":
        return [_validate_position(coordinates, "Point")]
    if geometry_type == "LineString":
        if not isinstance(coordinates, list) or len(coordinates) < 2:
            raise PresentationDataMismatchError(
                "LineString must contain at least two positions"
            )
        return [_validate_position(position, "LineString") for position in coordinates]
    raise PresentationDataMismatchError(
        f"Unsupported GeoJSON geometry type: {geometry_type!r}"
    )


def _validate_position(position: Any, geometry_type: str) -> tuple[float, float]:
    if not isinstance(position, (list, tuple)) or len(position) != 2:
        raise PresentationDataMismatchError(
            f"{geometry_type} positions must contain exactly longitude and latitude"
        )
    longitude, latitude = position
    if (
        isinstance(longitude, bool)
        or isinstance(latitude, bool)
        or not isinstance(longitude, (int, float))
        or not isinstance(latitude, (int, float))
        or not math.isfinite(longitude)
        or not math.isfinite(latitude)
    ):
        raise PresentationDataMismatchError(
            f"Coordinates must be finite numbers, got {position!r}"
        )
    if not -180.0 <= longitude <= 180.0:
        raise PresentationDataMismatchError(
            f"Longitude out of WGS84 bounds: {longitude}"
        )
    if not -90.0 <= latitude <= 90.0:
        raise PresentationDataMismatchError(f"Latitude out of WGS84 bounds: {latitude}")
    return float(longitude), float(latitude)


def _require_feature_id(properties: dict[str, Any], key: str) -> str:
    value = properties.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PresentationDataMismatchError(f"Feature has invalid {key}")
    return value


def _validate_json_value(value: Any, subject: str) -> None:
    """Reject values that cannot be emitted as strict interoperable JSON."""

    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise PresentationDataMismatchError(f"Non-finite value in {subject}")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item, subject)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for item in value.values():
            _validate_json_value(item, subject)
        return
    raise PresentationDataMismatchError(
        f"Unsupported JSON value {type(value).__name__} in {subject}"
    )


def _enrich_node(properties: dict[str, Any], bus: Any, violated: bool) -> None:
    properties.update(
        {
            "voltage_pu": round(bus.voltage_pu, 4) if bus is not None else None,
            "voltage_kv": round(bus.voltage_kv, 3) if bus is not None else None,
            "voltage_angle_degree": (
                round(bus.voltage_angle_degree, 2) if bus is not None else None
            ),
            "net_active_power_demand_mw": (
                round(bus.net_active_power_demand_mw, 4) if bus is not None else None
            ),
            "net_reactive_power_demand_mvar": (
                round(bus.net_reactive_power_demand_mvar, 4)
                if bus is not None
                else None
            ),
            "has_voltage_violation": violated,
        }
    )


def _enrich_segment(
    properties: dict[str, Any],
    segment: Any,
    bus_map: dict[str, Any],
    overloaded: bool,
) -> None:
    from_node = _require_feature_id(properties, "from_node")
    to_node = _require_feature_id(properties, "to_node")
    from_bus = bus_map.get(from_node)
    to_bus = bus_map.get(to_node)
    properties.update(
        {
            "current_from_a": (
                round(segment.current_from_a, 2) if segment is not None else None
            ),
            "current_to_a": (
                round(segment.current_to_a, 2) if segment is not None else None
            ),
            "maximum_current_a": (
                round(segment.maximum_current_a, 2) if segment is not None else None
            ),
            "loading_percent": (
                round(segment.loading_percent, 2) if segment is not None else None
            ),
            "active_loss_mw": (
                round(segment.active_loss_mw, 6) if segment is not None else None
            ),
            # Same quantity in kilowatts. Emitted alongside the megawatt figure rather than
            # replacing it: consumers reading `active_loss_mw` keep working, while a caller that
            # reports losses in kW no longer has to convert (or, as the backend did, silently fall
            # back to a distance heuristic because no field with a kW name was ever present).
            "electrical_losses_kw": (
                round(segment.active_loss_mw * 1000.0, 4)
                if segment is not None and segment.active_loss_mw is not None
                else None
            ),
            "reactive_loss_mvar": (
                round(segment.reactive_loss_mvar, 6) if segment is not None else None
            ),
            "from_voltage_pu": (
                round(from_bus.voltage_pu, 4) if from_bus is not None else None
            ),
            "to_voltage_pu": (
                round(to_bus.voltage_pu, 4) if to_bus is not None else None
            ),
            "has_cable_overload": overloaded,
        }
    )
