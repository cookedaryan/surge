"""Request-wide validation with stable error codes. Owned by L3 (WP3-1).

Exit evidence for WP3-1: unknown profile, version or metric, non-finite,
out-of-range and oversized payload all map to stable codes, and nothing ever falls
back to Balanced.

Runs inside ``resolve_profile`` (seam S2), which the endpoint calls before it parses
any geometry, so a bad value is reported here with a C3 code instead of surfacing
later as a free-text message, a silent acceptance or a server error. Before WP3-1:

- a non-finite ``operating_factor`` crashed the request with a 500;
- an unknown ``feature_type`` or an empty ``source_id`` was accepted silently;
- out-of-range coordinates and negative buffers returned a free-text 422.

What this layer cannot reach. Pydantic validates the declared request fields before
the endpoint runs, so a field that breaks its own declared constraint still gets
FastAPI's default validation response rather than a C3 code, and the body is fully
read before any size check can run. Both need the application-level handler in
``app/main.py``, which no level owns. Stable codes here cover everything that
reaches the endpoint; the rest is recorded as a gap, not claimed.

Checks run in a fixed order, so a request with several defects always reports the
same one: size, then non-finite values, then coordinate ranges, then avoidance
feature properties.
"""

import math
from collections.abc import Iterator
from typing import Any

from app.contracts.codes import ContractErrorCode
from app.contracts.errors import ContractError
from app.contracts.request import MAX_V1_REQUEST_BYTES
from app.gis.constraints import canonical_feature_type
from app.schemas.optimise import OptimisationRequest

_GEOJSON_FIELDS = ("wtg_geojson", "substation_geojson", "avoidance_geojson")


def validate_request(payload: OptimisationRequest) -> None:
    """Raise a ``ContractError`` for the first defect found, in the fixed order."""
    _check_size(payload)
    body = payload.model_dump(mode="python")
    _check_finite(body)
    _check_coordinates(body)
    _check_avoidance_properties(body.get("avoidance_geojson"))


def _check_size(payload: OptimisationRequest) -> None:
    """Refuse a request whose canonical form exceeds the C1 limit.

    **This is not the C1 raw-body limit, and does not replace it.** The body is
    parsed before the endpoint runs, so the only size available here is the
    re-serialised payload, which is smaller than the body it came from: a 10.58 MB
    body measured 9.62 MB re-serialised and passed. A raw body over the limit can
    still be accepted, and nothing here protects the parser from reading it. Both
    need app-level middleware in ``app/main.py``, which no level owns.
    """
    size = len(payload.model_dump_json().encode("utf-8"))
    if size > MAX_V1_REQUEST_BYTES:
        raise ContractError(
            ContractErrorCode.PAYLOAD_TOO_LARGE,
            f"Request is {size} bytes; the limit is {MAX_V1_REQUEST_BYTES}.",
            http_status=413,
        )


def _check_finite(body: dict[str, Any]) -> None:
    for path, value in _walk(body, ""):
        if isinstance(value, float) and not math.isfinite(value):
            raise ContractError(
                ContractErrorCode.NON_FINITE_VALUE,
                f"{path} must be a finite number.",
            )


def _check_coordinates(body: dict[str, Any]) -> None:
    for field in _GEOJSON_FIELDS:
        collection = body.get(field)
        if not isinstance(collection, dict):
            continue
        for index, feature in enumerate(collection.get("features") or []):
            geometry = feature.get("geometry") if isinstance(feature, dict) else None
            if not isinstance(geometry, dict):
                continue
            base = f"{field}.features[{index}].geometry.coordinates"
            for path, longitude, latitude in _positions(
                geometry.get("coordinates"), base
            ):
                if not -180.0 <= longitude <= 180.0:
                    raise ContractError(
                        ContractErrorCode.VALUE_OUT_OF_RANGE,
                        f"{path} longitude {longitude} is outside [-180, 180].",
                    )
                if not -90.0 <= latitude <= 90.0:
                    raise ContractError(
                        ContractErrorCode.VALUE_OUT_OF_RANGE,
                        f"{path} latitude {latitude} is outside [-90, 90].",
                    )


def _check_avoidance_properties(collection: object) -> None:
    if not isinstance(collection, dict):
        return
    for index, feature in enumerate(collection.get("features") or []):
        properties = feature.get("properties") if isinstance(feature, dict) else None
        if not isinstance(properties, dict):
            continue
        base = f"avoidance_geojson.features[{index}].properties"
        _check_typed_identity(properties, base)
        _check_non_negative(properties, base, ("buffer_m", "cost_weight"))


def _check_typed_identity(properties: dict[str, Any], base: str) -> None:
    # Absent means V0; an explicit value must be valid. Aliases the parser resolves
    # are accepted, from the parser's own table, so validation and parsing agree.
    # ``routing_mode`` is left to the parser, which owns its legacy spellings.
    feature_type = properties.get("feature_type")
    if feature_type is not None and canonical_feature_type(feature_type) is None:
        raise ContractError(
            ContractErrorCode.INVALID_TYPED_IDENTITY,
            f"{base}.feature_type {feature_type!r} is not a recognised feature type.",
        )
    source_id = properties.get("source_id")
    if source_id is not None and (
        not isinstance(source_id, str) or not source_id.strip()
    ):
        raise ContractError(
            ContractErrorCode.INVALID_TYPED_IDENTITY,
            f"{base}.source_id must be a non-empty string when present.",
        )


def _check_non_negative(
    properties: dict[str, Any], base: str, keys: tuple[str, ...]
) -> None:
    for key in keys:
        value = properties.get(key)
        if isinstance(value, bool) or not isinstance(value, int | float):
            continue
        if value < 0:
            raise ContractError(
                ContractErrorCode.VALUE_OUT_OF_RANGE,
                f"{base}.{key} must not be negative; got {value}.",
            )


def _positions(coordinates: object, path: str) -> Iterator[tuple[str, float, float]]:
    """Every (longitude, latitude) in a GeoJSON coordinate array, at any depth."""
    if not isinstance(coordinates, list) or not coordinates:
        return
    first = coordinates[0]
    if isinstance(first, int | float) and not isinstance(first, bool):
        if len(coordinates) >= 2 and isinstance(coordinates[1], int | float):
            yield path, float(coordinates[0]), float(coordinates[1])
        return
    for index, item in enumerate(coordinates):
        yield from _positions(item, f"{path}[{index}]")


def _walk(value: object, path: str) -> Iterator[tuple[str, object]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")
    else:
        yield path, value
