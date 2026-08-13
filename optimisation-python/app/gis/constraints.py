"""Typed spatial constraints and deterministic cost-surface rasterization."""

import hashlib
import json
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import numpy as np
from pyproj import CRS
from rasterio.features import rasterize
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from app.gis.cost_surface import CostSurface
from app.gis.crs import WGS84_CRS, get_transformer, transform_geometry
from app.gis.geojson import parse_geojson
from app.gis.geometry import validate_geometry

_SUPPORTED_TYPES = (LineString, MultiLineString, Polygon, MultiPolygon)
_LINEAR_TYPES = (LineString, MultiLineString)


class ConstraintMode(StrEnum):
    """Routing treatment applied to one spatial constraint."""

    HARD_EXCLUSION = "hard_exclusion"
    SOFT_PENALTY = "soft_penalty"


class ConstraintType(StrEnum):
    """Supported reviewed project-feature classifications."""

    ROAD = "road"
    HT_LINE = "ht_line"
    WATERCOURSE = "watercourse"
    PARCEL = "parcel"
    RESTRICTED_AREA = "restricted_area"


@dataclass(frozen=True)
class ConstraintLayer:
    """One validated projected constraint with an explicit routing policy."""

    layer_id: str
    layer_type: ConstraintType
    mode: ConstraintMode
    geometry: BaseGeometry
    buffer_m: float
    cost_weight: float | None
    crs: CRS

    def __post_init__(self) -> None:
        if not self.layer_id.strip():
            raise ValueError("Constraint layer_id must not be empty")
        if not math.isfinite(self.buffer_m) or self.buffer_m < 0:
            raise ValueError("Constraint buffer_m must be finite and non-negative")
        if self.mode == ConstraintMode.SOFT_PENALTY:
            if self.cost_weight is None:
                raise ValueError("Soft constraints require cost_weight")
            if not math.isfinite(self.cost_weight) or self.cost_weight <= 0:
                raise ValueError(
                    "Soft constraint cost_weight must be positive and finite"
                )
        elif self.cost_weight is not None:
            raise ValueError("Hard constraints must not define cost_weight")
        if not self.crs.is_projected:
            raise ValueError("Constraint CRS must be projected")
        if self.geometry.is_empty:
            raise ValueError(f"Constraint {self.layer_id} geometry is empty")
        if not isinstance(self.geometry, _SUPPORTED_TYPES):
            raise ValueError(
                f"Constraint {self.layer_id} has unsupported geometry type "
                f"{self.geometry.geom_type}"
            )


@dataclass(frozen=True)
class ConstraintApplication:
    """The rasterized surface and the typed vector constraints used to build it."""

    surface: CostSurface
    layers: tuple[ConstraintLayer, ...]


def parse_constraint_layers(
    geojson: dict[str, Any] | None,
    *,
    target_crs: CRS,
    default_buffer_m: float,
    default_soft_cost_weight: float,
) -> tuple[ConstraintLayer, ...]:
    """Parse WGS-84 constraint features into projected typed layers."""
    _validate_non_negative_finite(default_buffer_m, "default_buffer_m")
    _validate_positive_finite(default_soft_cost_weight, "default_soft_cost_weight")
    if geojson is None:
        return ()
    if geojson.get("type") != "FeatureCollection":
        raise ValueError("avoidance_geojson must be a GeoJSON FeatureCollection")
    features = geojson.get("features")
    if not isinstance(features, list):
        raise ValueError("avoidance_geojson.features must be a list")

    transformer = get_transformer(WGS84_CRS, target_crs)
    layers: list[ConstraintLayer] = []
    seen_ids: set[str] = set()
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError(f"Avoidance feature at index {index} must be a Feature")
        properties = feature.get("properties", {})
        if not isinstance(properties, dict):
            raise ValueError(
                f"Avoidance feature at index {index} properties must be an object"
            )

        geometry = parse_geojson(feature)
        if geometry.is_empty:
            raise ValueError(f"Avoidance feature at index {index} is empty")
        if not isinstance(geometry, _SUPPORTED_TYPES):
            raise ValueError(
                "Avoidance geometries must be LineString, MultiLineString, "
                f"Polygon, or MultiPolygon; got {geometry.geom_type}"
            )
        projected = validate_geometry(transform_geometry(geometry, transformer))
        if projected.is_empty or not isinstance(projected, _SUPPORTED_TYPES):
            raise ValueError(f"Avoidance feature at index {index} is invalid")
        if any(not math.isfinite(value) for value in projected.bounds):
            raise ValueError(
                f"Avoidance feature at index {index} has non-finite coordinates"
            )

        layer_id = _layer_id(feature, properties, index)
        if layer_id in seen_ids:
            raise ValueError(f"Duplicate constraint layer_id: {layer_id}")
        seen_ids.add(layer_id)
        layer_type = _constraint_type(properties, projected)
        mode = _constraint_mode(properties, layer_type, projected)
        buffer_m = _numeric_property(
            properties,
            "buffer_m",
            default=default_buffer_m,
            positive=False,
        )
        raw_cost = properties.get("cost_weight", properties.get("cost_multiplier"))
        if mode == ConstraintMode.SOFT_PENALTY:
            cost_weight = (
                default_soft_cost_weight
                if raw_cost is None
                else _as_finite_number(raw_cost, "cost_weight")
            )
        else:
            if raw_cost is not None:
                raise ValueError(
                    f"Hard constraint {layer_id} must not define cost_weight"
                )
            cost_weight = None

        layers.append(
            ConstraintLayer(
                layer_id=layer_id,
                layer_type=layer_type,
                mode=mode,
                geometry=projected,
                buffer_m=buffer_m,
                cost_weight=cost_weight,
                crs=target_crs,
            )
        )

    return tuple(sorted(layers, key=lambda layer: layer.layer_id))


def effective_constraint_geometry(layer: ConstraintLayer) -> BaseGeometry:
    """Return the buffered geometry used by routing and compliance checks."""
    geometry = (
        layer.geometry.buffer(layer.buffer_m) if layer.buffer_m > 0 else layer.geometry
    )
    geometry = validate_geometry(geometry)
    if geometry.is_empty:
        raise ValueError(f"Constraint {layer.layer_id} is empty after buffering")
    return geometry


def apply_constraint_layers(
    surface: CostSurface,
    layers: tuple[ConstraintLayer, ...],
) -> CostSurface:
    """Return a copy of ``surface`` with hard blocks and soft costs applied."""
    seen_ids: set[str] = set()
    ordered_layers = sorted(layers, key=lambda layer: layer.layer_id)
    costs = np.array(surface.costs, dtype=np.float64, copy=True)

    for layer in ordered_layers:
        if layer.layer_id in seen_ids:
            raise ValueError(f"Duplicate constraint layer_id: {layer.layer_id}")
        seen_ids.add(layer.layer_id)
        if not layer.crs.equals(surface.crs):
            raise ValueError(
                f"Constraint {layer.layer_id} CRS does not match cost surface CRS"
            )
        geometry = effective_constraint_geometry(layer)
        mask = rasterize(
            ((geometry, 1),),
            out_shape=(surface.height, surface.width),
            transform=surface.transform,
            fill=0,
            all_touched=True,
            dtype=np.uint8,
        ).astype(bool)
        if layer.mode == ConstraintMode.HARD_EXCLUSION:
            costs[mask] = np.inf
        else:
            if layer.cost_weight is None:  # Protected by ConstraintLayer validation.
                raise AssertionError("Soft constraint is missing cost_weight")
            finite_mask = mask & np.isfinite(costs)
            costs[finite_mask] += layer.cost_weight

    return CostSurface(
        costs=costs,
        transform=surface.transform,
        crs=surface.crs,
        width=surface.width,
        height=surface.height,
        resolution_m=surface.resolution_m,
    )


def ingest_avoidance_constraints(
    surface: CostSurface,
    geojson: dict[str, Any] | None,
    *,
    buffer_m: float,
    soft_cost_weight: float,
) -> ConstraintApplication:
    """Parse and rasterize the additive avoidance compatibility input."""
    layers = parse_constraint_layers(
        geojson,
        target_crs=surface.crs,
        default_buffer_m=buffer_m,
        default_soft_cost_weight=soft_cost_weight,
    )
    return ConstraintApplication(
        surface=apply_constraint_layers(surface, layers),
        layers=layers,
    )


def apply_avoidance_constraints(
    surface: CostSurface,
    geojson: dict[str, Any] | None,
    *,
    buffer_m: float,
    soft_cost_weight: float = 20.0,
) -> CostSurface:
    """Compatibility wrapper returning only the rasterized cost surface."""
    return ingest_avoidance_constraints(
        surface,
        geojson,
        buffer_m=buffer_m,
        soft_cost_weight=soft_cost_weight,
    ).surface


def _layer_id(feature: dict[str, Any], properties: dict[str, Any], index: int) -> str:
    raw_value = properties.get(
        "constraint_id", properties.get("layer_id", properties.get("id"))
    )
    if raw_value is None:
        try:
            canonical_feature = json.dumps(
                feature,
                allow_nan=False,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Avoidance feature at index {index} is not JSON-serializable"
            ) from exc
        digest = hashlib.sha256(canonical_feature.encode("utf-8")).hexdigest()[:16]
        raw_value = f"constraint-{digest}"
    layer_id = str(raw_value).strip()
    if not layer_id:
        raise ValueError(f"Avoidance feature at index {index} has an empty ID")
    return layer_id


def _constraint_type(
    properties: dict[str, Any], geometry: BaseGeometry
) -> ConstraintType:
    raw_value = properties.get("constraint_type", properties.get("layer_type"))
    if raw_value is None:
        return (
            ConstraintType.ROAD
            if isinstance(geometry, _LINEAR_TYPES)
            else ConstraintType.RESTRICTED_AREA
        )
    normalized = _normalize_token(raw_value)
    aliases = {
        "road": ConstraintType.ROAD,
        "track": ConstraintType.ROAD,
        "reference_line": ConstraintType.ROAD,
        "ht_line": ConstraintType.HT_LINE,
        "ehv_line": ConstraintType.HT_LINE,
        "power_line": ConstraintType.HT_LINE,
        "watercourse": ConstraintType.WATERCOURSE,
        "stream": ConstraintType.WATERCOURSE,
        "water": (
            ConstraintType.WATERCOURSE
            if isinstance(geometry, _LINEAR_TYPES)
            else ConstraintType.RESTRICTED_AREA
        ),
        "parcel": ConstraintType.PARCEL,
        "cadastral_parcel": ConstraintType.PARCEL,
        "land": ConstraintType.PARCEL,
        "restricted": ConstraintType.RESTRICTED_AREA,
        "restricted_area": ConstraintType.RESTRICTED_AREA,
        "restricted_land": ConstraintType.RESTRICTED_AREA,
        "no_go": ConstraintType.RESTRICTED_AREA,
        "sanctuary": ConstraintType.RESTRICTED_AREA,
        "settlement_exclusion": ConstraintType.RESTRICTED_AREA,
        "forest": ConstraintType.RESTRICTED_AREA,
        "environmental": ConstraintType.RESTRICTED_AREA,
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported constraint_type: {raw_value!r}") from exc


def _constraint_mode(
    properties: dict[str, Any],
    layer_type: ConstraintType,
    geometry: BaseGeometry,
) -> ConstraintMode:
    if properties.get("no_go") is True:
        return ConstraintMode.HARD_EXCLUSION
    raw_value = properties.get(
        "routing_mode", properties.get("mode", properties.get("severity"))
    )
    if raw_value is not None:
        normalized = _normalize_token(raw_value)
        aliases = {
            "hard": ConstraintMode.HARD_EXCLUSION,
            "hard_exclusion": ConstraintMode.HARD_EXCLUSION,
            "soft": ConstraintMode.SOFT_PENALTY,
            "soft_penalty": ConstraintMode.SOFT_PENALTY,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"Unsupported routing_mode: {raw_value!r}") from exc

    if layer_type in {
        ConstraintType.ROAD,
        ConstraintType.HT_LINE,
        ConstraintType.WATERCOURSE,
        ConstraintType.PARCEL,
    }:
        return ConstraintMode.SOFT_PENALTY
    if isinstance(geometry, _LINEAR_TYPES):
        return ConstraintMode.SOFT_PENALTY
    return ConstraintMode.HARD_EXCLUSION


def _numeric_property(
    properties: dict[str, Any],
    name: str,
    *,
    default: float,
    positive: bool,
) -> float:
    raw_value = properties.get(name)
    value = default if raw_value is None else _as_finite_number(raw_value, name)
    if positive:
        _validate_positive_finite(value, name)
    else:
        _validate_non_negative_finite(value, name)
    return value


def _as_finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number, not a boolean")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a valid number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _validate_non_negative_finite(value: float, name: str) -> None:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")


def _validate_positive_finite(value: float, name: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite")


def _normalize_token(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")
