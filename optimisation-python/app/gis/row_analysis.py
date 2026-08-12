"""Right-of-way corridor generation and constraint intersection analysis.

SURGE-PY-011 is intentionally a domain-level spatial analysis module.  It
operates on projected refined routes and projected constraint geometries, but
does not parse API payloads or serialize GeoJSON.
"""

import logging
import math
from dataclasses import dataclass
from typing import Literal, TypeAlias

from pyproj import CRS
from shapely import BufferCapStyle, BufferJoinStyle
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from shapely.strtree import STRtree

from app.algorithms.route_refinement import RefinedPhysicalRoute
from app.gis.geometry import validate_geometry

logger = logging.getLogger(__name__)

ConstraintLayerType: TypeAlias = Literal[
    "parcel",
    "restricted",
    "forest",
    "road",
    "water",
    "environmental",
]
ConstraintSeverity: TypeAlias = Literal["hard", "soft"]
BufferCapStyleName: TypeAlias = Literal["flat", "round", "square"]
BufferJoinStyleName: TypeAlias = Literal["round", "mitre", "bevel"]
AreaGeometry: TypeAlias = Polygon | MultiPolygon

_LAYER_TYPES = {
    "parcel",
    "restricted",
    "forest",
    "road",
    "water",
    "environmental",
}
_SEVERITIES = {"hard", "soft"}
_AREAL_LAYER_TYPES = {"parcel", "restricted", "forest", "environmental"}
_LINEAR_TYPES = (LineString, MultiLineString)
_AREAL_TYPES = (Polygon, MultiPolygon)
_CAP_STYLES = {
    "flat": BufferCapStyle.flat,
    "round": BufferCapStyle.round,
    "square": BufferCapStyle.square,
}
_JOIN_STYLES = {
    "round": BufferJoinStyle.round,
    "mitre": BufferJoinStyle.mitre,
    "bevel": BufferJoinStyle.bevel,
}


@dataclass(frozen=True)
class RowConfig:
    """Configuration for metric right-of-way corridor generation."""

    corridor_width_m: float
    cap_style: BufferCapStyleName = "flat"
    join_style: BufferJoinStyleName = "round"
    minimum_overlap_area_m2: float = 0.0
    minimum_overlap_length_m: float = 0.0
    crossing_tolerance_m: float = 1e-7


@dataclass(frozen=True)
class ConstraintFeature:
    """One projected project constraint with stable domain metadata."""

    feature_id: str
    layer_type: ConstraintLayerType
    geometry: BaseGeometry
    severity: ConstraintSeverity | None = None


@dataclass(frozen=True)
class ProjectConstraintLayers:
    """Constraint features sharing one projected metric CRS."""

    features: tuple[ConstraintFeature, ...]
    crs: CRS


@dataclass(frozen=True)
class RouteRowCorridor:
    """A refined route and its buffered right-of-way footprint."""

    feeder_id: str
    start_node_id: str
    end_node_id: str
    route_geometry: LineString
    row_geometry: AreaGeometry
    corridor_width_m: float
    route_length_m: float
    row_area_m2: float


@dataclass(frozen=True)
class RowIntersection:
    """One route-segment/constraint intersection event."""

    feeder_id: str
    start_node_id: str
    end_node_id: str
    feature_id: str
    layer_type: ConstraintLayerType
    severity: ConstraintSeverity | None
    geometry: BaseGeometry
    intersection_area_m2: float
    route_overlap_length_m: float
    constraint_length_within_corridor_m: float
    touches_only: bool

    @property
    def intersection_length_m(self) -> float:
        """Length of the route centreline inside/on the constraint."""

        return self.route_overlap_length_m


@dataclass(frozen=True)
class SkippedConstraint:
    """A non-critical empty feature omitted from the spatial index."""

    feature_id: str
    layer_type: ConstraintLayerType
    reason: str


@dataclass(frozen=True)
class RowAnalysisResult:
    """Corridors, intersection events, and deterministic aggregates."""

    corridors: tuple[RouteRowCorridor, ...]
    intersections: tuple[RowIntersection, ...]
    total_row_area_m2: float
    unique_row_footprint_area_m2: float
    unique_parcel_count: int
    road_crossing_count: int
    restricted_intersection_count: int
    unique_restricted_feature_count: int
    has_hard_violation: bool
    skipped_constraints: tuple[SkippedConstraint, ...]


def analyse_row_corridors(
    routes: tuple[RefinedPhysicalRoute, ...],
    route_crs: CRS,
    constraints: ProjectConstraintLayers,
    config: RowConfig,
) -> RowAnalysisResult:
    """Build ROW corridors and analyse projected constraint intersections.

    ``route_crs`` is explicit spatial provenance for Shapely route geometries,
    which do not carry CRS metadata themselves.  Both route and constraint CRS
    values must describe the same projected coordinate system with metre axes.
    Empty non-critical constraints are reported in ``skipped_constraints``;
    empty hard/restricted constraints and all other invalid features fail the
    analysis rather than silently weakening compliance results.
    """

    _validate_config(config)
    normalized_route_crs = _validate_analysis_crs(route_crs, constraints.crs)
    validated_features, skipped_constraints = _validate_and_repair_constraints(
        constraints, normalized_route_crs
    )
    corridors = _build_corridors(routes, config)

    intersections: list[RowIntersection] = []
    road_crossing_count = 0

    if corridors and validated_features:
        tree = STRtree([feature.geometry for feature in validated_features])
        for corridor in corridors:
            candidate_indices = sorted(
                (int(index) for index in tree.query(corridor.row_geometry)),
                key=lambda index: (
                    validated_features[index].layer_type,
                    validated_features[index].feature_id,
                    index,
                ),
            )
            for index in candidate_indices:
                feature = validated_features[index]
                intersection = _intersect_corridor(corridor, feature, config)
                if intersection is None:
                    continue
                intersections.append(intersection)
                if feature.layer_type == "road":
                    road_crossing_count += _count_road_crossings(
                        corridor.route_geometry,
                        feature.geometry,
                        config.crossing_tolerance_m,
                    )

    ordered_intersections = tuple(
        sorted(
            intersections,
            key=lambda item: (
                item.feeder_id,
                item.start_node_id,
                item.end_node_id,
                item.layer_type,
                item.feature_id,
            ),
        )
    )
    total_row_area = math.fsum(corridor.row_area_m2 for corridor in corridors)
    unique_row_area = (
        float(unary_union([corridor.row_geometry for corridor in corridors]).area)
        if corridors
        else 0.0
    )
    parcel_keys = {
        (item.layer_type, item.feature_id)
        for item in ordered_intersections
        if item.layer_type == "parcel"
    }
    restricted_events = tuple(
        item for item in ordered_intersections if item.layer_type == "restricted"
    )
    restricted_keys = {(item.layer_type, item.feature_id) for item in restricted_events}

    return RowAnalysisResult(
        corridors=corridors,
        intersections=ordered_intersections,
        total_row_area_m2=total_row_area,
        unique_row_footprint_area_m2=unique_row_area,
        unique_parcel_count=len(parcel_keys),
        road_crossing_count=road_crossing_count,
        restricted_intersection_count=len(restricted_events),
        unique_restricted_feature_count=len(restricted_keys),
        has_hard_violation=any(
            item.severity == "hard" for item in ordered_intersections
        ),
        skipped_constraints=skipped_constraints,
    )


def _validate_config(config: RowConfig) -> None:
    numeric_values = {
        "corridor_width_m": config.corridor_width_m,
        "minimum_overlap_area_m2": config.minimum_overlap_area_m2,
        "minimum_overlap_length_m": config.minimum_overlap_length_m,
        "crossing_tolerance_m": config.crossing_tolerance_m,
    }
    for name, value in numeric_values.items():
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if config.corridor_width_m <= 0:
        raise ValueError("corridor_width_m must be greater than zero")
    if config.minimum_overlap_area_m2 < 0:
        raise ValueError("minimum_overlap_area_m2 must be non-negative")
    if config.minimum_overlap_length_m < 0:
        raise ValueError("minimum_overlap_length_m must be non-negative")
    if config.crossing_tolerance_m < 0:
        raise ValueError("crossing_tolerance_m must be non-negative")
    if config.cap_style not in _CAP_STYLES:
        raise ValueError(f"Unsupported ROW cap style: {config.cap_style}")
    if config.join_style not in _JOIN_STYLES:
        raise ValueError(f"Unsupported ROW join style: {config.join_style}")


def _validate_analysis_crs(route_crs: CRS, constraint_crs: CRS) -> CRS:
    try:
        normalized_route_crs = CRS.from_user_input(route_crs)
        normalized_constraint_crs = CRS.from_user_input(constraint_crs)
    except Exception as exc:
        raise ValueError("Route and constraint CRS values must be valid") from exc

    if not normalized_route_crs.equals(normalized_constraint_crs):
        raise ValueError(
            "Route and constraint CRS values do not match: "
            f"{normalized_route_crs.to_string()} != "
            f"{normalized_constraint_crs.to_string()}"
        )
    if not normalized_route_crs.is_projected:
        raise ValueError("ROW analysis requires a projected CRS")
    if len(normalized_route_crs.axis_info) < 2 or any(
        not math.isclose(axis.unit_conversion_factor, 1.0, rel_tol=0.0, abs_tol=1e-12)
        for axis in normalized_route_crs.axis_info[:2]
    ):
        raise ValueError("ROW analysis requires projected CRS axes measured in metres")
    return normalized_route_crs


def _validate_and_repair_constraints(
    constraints: ProjectConstraintLayers,
    normalized_crs: CRS,
) -> tuple[tuple[ConstraintFeature, ...], tuple[SkippedConstraint, ...]]:
    if not normalized_crs.equals(CRS.from_user_input(constraints.crs)):
        raise ValueError("Constraint CRS changed during validation")

    validated: list[ConstraintFeature] = []
    skipped: list[SkippedConstraint] = []
    seen_keys: set[tuple[str, str]] = set()

    for feature in constraints.features:
        feature_id = feature.feature_id.strip()
        if not feature_id:
            raise ValueError("Constraint feature_id must not be empty")
        if feature.layer_type not in _LAYER_TYPES:
            raise ValueError(
                f"Constraint {feature_id} has unsupported layer type "
                f"{feature.layer_type!r}"
            )
        if feature.severity is not None and feature.severity not in _SEVERITIES:
            raise ValueError(
                f"Constraint {feature_id} has unsupported severity {feature.severity!r}"
            )
        key = (feature.layer_type, feature_id)
        if key in seen_keys:
            raise ValueError(
                f"Duplicate constraint identity: {feature.layer_type}/{feature_id}"
            )
        seen_keys.add(key)

        if feature.geometry.is_empty:
            if feature.severity == "hard" or feature.layer_type == "restricted":
                raise ValueError(
                    f"Critical constraint {feature.layer_type}/{feature_id} is empty"
                )
            reason = "empty geometry"
            logger.warning(
                "Skipping constraint %s/%s: %s",
                feature.layer_type,
                feature_id,
                reason,
            )
            skipped.append(
                SkippedConstraint(
                    feature_id=feature_id,
                    layer_type=feature.layer_type,
                    reason=reason,
                )
            )
            continue

        try:
            repaired_geometry = validate_geometry(feature.geometry)
        except ValueError as exc:
            raise ValueError(
                f"Constraint {feature.layer_type}/{feature_id} is invalid: {exc}"
            ) from exc
        if repaired_geometry.is_empty:
            raise ValueError(
                f"Constraint {feature.layer_type}/{feature_id} "
                "became empty after repair"
            )
        if any(not math.isfinite(value) for value in repaired_geometry.bounds):
            raise ValueError(
                f"Constraint {feature.layer_type}/{feature_id} has non-finite bounds"
            )
        _validate_constraint_geometry_type(
            feature_id, feature.layer_type, repaired_geometry
        )
        validated.append(
            ConstraintFeature(
                feature_id=feature_id,
                layer_type=feature.layer_type,
                geometry=repaired_geometry,
                severity=feature.severity,
            )
        )

    return tuple(validated), tuple(skipped)


def _validate_constraint_geometry_type(
    feature_id: str,
    layer_type: ConstraintLayerType,
    geometry: BaseGeometry,
) -> None:
    if layer_type in _AREAL_LAYER_TYPES:
        supported = isinstance(geometry, _AREAL_TYPES)
    else:
        supported = isinstance(geometry, _LINEAR_TYPES + _AREAL_TYPES)
    if not supported:
        raise ValueError(
            f"Constraint {layer_type}/{feature_id} has unsupported geometry type "
            f"{geometry.geom_type}"
        )


def _build_corridors(
    routes: tuple[RefinedPhysicalRoute, ...],
    config: RowConfig,
) -> tuple[RouteRowCorridor, ...]:
    corridors: list[RouteRowCorridor] = []
    seen_route_keys: set[tuple[str, str, str]] = set()

    for route in routes:
        route_key = (route.feeder_id, route.start_node_id, route.end_node_id)
        if route_key in seen_route_keys:
            raise ValueError(
                "Duplicate refined route identity: "
                f"{route.feeder_id}/{route.start_node_id}/{route.end_node_id}"
            )
        seen_route_keys.add(route_key)
        corridors.append(_build_corridor(route, config))

    return tuple(corridors)


def _build_corridor(
    route: RefinedPhysicalRoute,
    config: RowConfig,
) -> RouteRowCorridor:
    geometry = route.geometry
    if not isinstance(geometry, LineString):
        raise ValueError("Refined route geometry must be a LineString")
    if geometry.is_empty or not geometry.is_valid or not geometry.is_simple:
        raise ValueError(
            f"Refined route {route.start_node_id}-{route.end_node_id} "
            "must be non-empty, valid, and simple"
        )
    if len(geometry.coords) < 2 or geometry.length <= 0:
        raise ValueError("Refined route must contain a non-degenerate line")
    if any(
        not math.isfinite(float(value))
        for coordinate in geometry.coords
        for value in coordinate[:2]
    ):
        raise ValueError("Refined route coordinates must be finite")
    if not math.isfinite(route.refined_length_m) or not math.isclose(
        route.refined_length_m,
        geometry.length,
        rel_tol=1e-9,
        abs_tol=1e-6,
    ):
        raise ValueError("Refined route length metadata does not match its geometry")

    row_geometry = geometry.buffer(
        config.corridor_width_m / 2.0,
        cap_style=_CAP_STYLES[config.cap_style],
        join_style=_JOIN_STYLES[config.join_style],
    )
    if not isinstance(row_geometry, _AREAL_TYPES):
        raise ValueError("ROW buffering did not produce an areal geometry")
    if row_geometry.is_empty or not row_geometry.is_valid:
        raise ValueError("ROW buffering produced an empty or invalid geometry")

    return RouteRowCorridor(
        feeder_id=route.feeder_id,
        start_node_id=route.start_node_id,
        end_node_id=route.end_node_id,
        route_geometry=geometry,
        row_geometry=row_geometry,
        corridor_width_m=config.corridor_width_m,
        route_length_m=float(geometry.length),
        row_area_m2=float(row_geometry.area),
    )


def _intersect_corridor(
    corridor: RouteRowCorridor,
    feature: ConstraintFeature,
    config: RowConfig,
) -> RowIntersection | None:
    geometry = corridor.row_geometry.intersection(feature.geometry)
    if geometry.is_empty:
        return None

    route_intersection = corridor.route_geometry.intersection(feature.geometry)
    area = float(geometry.area)
    route_overlap_length = float(route_intersection.length)
    constraint_length = (
        float(geometry.length) if isinstance(feature.geometry, _LINEAR_TYPES) else 0.0
    )
    touches_only = corridor.row_geometry.touches(feature.geometry)
    if (
        area < config.minimum_overlap_area_m2
        and max(route_overlap_length, constraint_length)
        < config.minimum_overlap_length_m
    ):
        return None

    return RowIntersection(
        feeder_id=corridor.feeder_id,
        start_node_id=corridor.start_node_id,
        end_node_id=corridor.end_node_id,
        feature_id=feature.feature_id,
        layer_type=feature.layer_type,
        severity=feature.severity,
        geometry=geometry,
        intersection_area_m2=area,
        route_overlap_length_m=route_overlap_length,
        constraint_length_within_corridor_m=constraint_length,
        touches_only=touches_only,
    )


def _count_road_crossings(
    route_geometry: LineString,
    road_geometry: BaseGeometry,
    tolerance_m: float,
) -> int:
    point_coordinates: list[tuple[float, float]] = []

    if isinstance(road_geometry, _LINEAR_TYPES):
        if not route_geometry.crosses(road_geometry):
            return 0
        intersection = route_geometry.intersection(road_geometry)
        point_coordinates.extend(_point_coordinates(intersection))
        return len(_deduplicate_coordinates(point_coordinates, tolerance_m))

    if isinstance(road_geometry, _AREAL_TYPES):
        interior_intersection = route_geometry.intersection(road_geometry)
        return sum(
            road_geometry.contains(part.interpolate(0.5, normalized=True))
            for part in _positive_length_line_parts(interior_intersection)
        )

    return 0


def _count_point_geometries(geometry: BaseGeometry) -> int:
    """Count Point members recursively, including MultiPoint collections."""

    return len(_point_coordinates(geometry))


def _point_coordinates(geometry: BaseGeometry) -> list[tuple[float, float]]:
    if isinstance(geometry, Point):
        return [(float(geometry.x), float(geometry.y))]
    if isinstance(geometry, MultiPoint | GeometryCollection):
        coordinates: list[tuple[float, float]] = []
        for part in geometry.geoms:
            coordinates.extend(_point_coordinates(part))
        return coordinates
    return []


def _positive_length_line_parts(
    geometry: BaseGeometry,
) -> tuple[LineString, ...]:
    if isinstance(geometry, LineString):
        return (geometry,) if geometry.length > 0 else ()
    if isinstance(geometry, MultiLineString | GeometryCollection):
        return tuple(
            line
            for part in geometry.geoms
            for line in _positive_length_line_parts(part)
        )
    return ()


def _deduplicate_coordinates(
    coordinates: list[tuple[float, float]],
    tolerance_m: float,
) -> tuple[tuple[float, float], ...]:
    unique: list[tuple[float, float]] = []
    for coordinate in sorted(coordinates):
        if any(math.dist(coordinate, existing) <= tolerance_m for existing in unique):
            continue
        unique.append(coordinate)
    return tuple(unique)
