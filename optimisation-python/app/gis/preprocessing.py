# Reference Journal: obsidian-vault/journal/2026-08-07.md
import math
from typing import Any, cast

from shapely.geometry import Point

from app.gis.constraints import (
    ConstraintLayer,
    ConstraintMode,
    effective_constraint_geometry,
)
from app.gis.cost_surface import CostSurface, world_to_grid
from app.gis.crs import WGS84_CRS, get_transformer, get_utm_crs, transform_geometry
from app.gis.geojson import parse_geojson
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine


def _extract_features(geojson: dict[str, Any]) -> list[dict[str, Any]]:
    if geojson.get("type") == "FeatureCollection":
        features = geojson.get("features", [])
        if not isinstance(features, list):
            raise ValueError("FeatureCollection 'features' must be a list")
        for f in features:
            if not isinstance(f, dict):
                raise ValueError("FeatureCollection 'features' must contain objects")
        return cast(list[dict[str, Any]], features)
    elif geojson.get("type") == "Feature":
        return [geojson]
    else:
        raise ValueError("Expected FeatureCollection or Feature")


def _validate_point_coords(geom: Point, prefix: str) -> None:
    if geom.is_empty:
        raise ValueError(f"{prefix} geometry is empty")
    if not math.isfinite(geom.x) or not math.isfinite(geom.y):
        raise ValueError(f"{prefix} coordinates must be finite")
    if not (-180.0 <= geom.x <= 180.0):
        raise ValueError(f"{prefix} longitude must be between -180 and 180")
    if not (-90.0 <= geom.y <= 90.0):
        raise ValueError(f"{prefix} latitude must be between -90 and 90")


def _validate_capacity(capacity: Any, prefix: str) -> float | None:
    if capacity is None:
        return None
    if isinstance(capacity, bool):
        raise ValueError(f"{prefix} capacity_mw must not be a boolean")
    try:
        val = float(capacity)
    except (ValueError, TypeError) as e:
        raise ValueError(f"{prefix} capacity_mw must be a valid number") from e
    if not math.isfinite(val) or val <= 0:
        raise ValueError(f"{prefix} capacity_mw must be positive and finite")
    return val


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    earth_radius_m = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * earth_radius_m * math.asin(math.sqrt(a))


def _select_primary_substation(
    sub_features: list[dict[str, Any]], wtg_features: list[dict[str, Any]]
) -> dict[str, Any]:
    """Picks the substation feeders should connect to when more than one is supplied.

    Prefers the highest-capacity substation when at least one reports a positive capacity.
    Survey KMZ files typically carry no capacity metadata at all, in which case every
    substation ties at zero; falling back to feature order in that case can silently pick a
    connection point many kilometres from the actual site. When capacity gives no signal,
    pick whichever substation sits closest to the WTG cluster instead.
    """
    if len(sub_features) == 1:
        return sub_features[0]

    def capacity_of(f: dict[str, Any]) -> float:
        val = (f.get("properties", {}) or {}).get("capacity_mw")
        try:
            return float(val) if val is not None else 0.0
        except (TypeError, ValueError):
            return 0.0

    if any(capacity_of(f) > 0 for f in sub_features):
        return max(sub_features, key=capacity_of)

    wtg_coords = [
        f["geometry"]["coordinates"]
        for f in wtg_features
        if isinstance(f.get("geometry"), dict)
        and f["geometry"].get("type") == "Point"
        and isinstance(f["geometry"].get("coordinates"), (list, tuple))
        and len(f["geometry"]["coordinates"]) >= 2
    ]
    if not wtg_coords:
        return sub_features[0]

    centroid_lon = sum(c[0] for c in wtg_coords) / len(wtg_coords)
    centroid_lat = sum(c[1] for c in wtg_coords) / len(wtg_coords)

    def distance_to_centroid(f: dict[str, Any]) -> float:
        coords = (f.get("geometry", {}) or {}).get("coordinates")
        if not coords or len(coords) < 2:
            return math.inf
        return _haversine_m(centroid_lon, centroid_lat, coords[0], coords[1])

    return min(sub_features, key=distance_to_centroid)


def process_project_data(
    wtg_geojson: dict[str, Any], substation_geojson: dict[str, Any]
) -> ProjectSpatialData:
    """
    Parses WTG and Substation GeoJSON, verifies geometries, calculates a
    common projected CRS (UTM), and returns structured optimisation objects.
    """
    # 1. Parse and extract features
    wtg_features = _extract_features(wtg_geojson)
    if not wtg_features:
        raise ValueError("WTG FeatureCollection is empty")

    sub_features = _extract_features(substation_geojson)
    if not sub_features:
        raise ValueError("Substation GeoJSON is empty or missing")
    
    sub_feature = _select_primary_substation(sub_features, wtg_features)

    # 2. Parse and Validate geometries (must be Points)
    raw_wtgs = []
    seen_ids = set()
    for i, feat in enumerate(wtg_features):
        geom = parse_geojson(feat)
        if not isinstance(geom, Point):
            raise ValueError(f"WTG geometry must be Point, got {geom.geom_type}")

        _validate_point_coords(geom, "WTG")

        props = feat.get("properties", {})
        raw_id = props.get("id", props.get("turbine_id"))
        if not raw_id or str(raw_id).strip() == "":
            raise ValueError(f"WTG feature at index {i} is missing a valid ID")

        wtg_id = str(raw_id).strip()
        if wtg_id in seen_ids:
            raise ValueError(f"Duplicate ID found: {wtg_id}")
        seen_ids.add(wtg_id)

        cap = _validate_capacity(props.get("capacity_mw"), f"WTG {wtg_id}")
        raw_wtgs.append({"geom": geom, "id": wtg_id, "capacity": cap})

    sub_geom = parse_geojson(sub_feature)
    if not isinstance(sub_geom, Point):
        raise ValueError(f"Substation geometry must be Point, got {sub_geom.geom_type}")

    _validate_point_coords(sub_geom, "Substation")

    sub_props = sub_feature.get("properties", {})
    raw_sub_id = sub_props.get("id", sub_props.get("substation_id"))
    if not raw_sub_id or str(raw_sub_id).strip() == "":
        raise ValueError("Substation feature is missing a valid ID")

    sub_id = str(raw_sub_id).strip()
    if sub_id in seen_ids:
        raise ValueError(f"Duplicate ID found: {sub_id}")

    sub_cap = _validate_capacity(sub_props.get("capacity_mw"), f"Substation {sub_id}")
    raw_sub = {"geom": sub_geom, "id": sub_id, "capacity": sub_cap}

    # 3. Calculate project geographic centre
    all_geoms = [w["geom"] for w in raw_wtgs] + [raw_sub["geom"]]
    avg_lon = sum(g.x for g in all_geoms) / len(all_geoms)
    avg_lat = sum(g.y for g in all_geoms) / len(all_geoms)

    # 4. Select one common projected CRS
    projected_crs = get_utm_crs(avg_lon, avg_lat)
    transformer = get_transformer(WGS84_CRS, projected_crs)

    # 5. Transform every geometry into that CRS and construct internal models
    turbines = []
    for raw_wtg in raw_wtgs:
        proj_geom = transform_geometry(raw_wtg["geom"], transformer)
        # Ensure it's typed as a Point explicitly for the dataclass
        turbines.append(
            WindTurbine(
                turbine_id=str(raw_wtg["id"]),
                location=cast(Point, proj_geom),
                capacity_mw=raw_wtg["capacity"],
            )
        )

    proj_sub_geom = transform_geometry(raw_sub["geom"], transformer)
    substation = Substation(
        substation_id=str(raw_sub["id"]),
        location=cast(Point, proj_sub_geom),
        capacity_mw=raw_sub["capacity"],
    )

    return ProjectSpatialData(
        turbines=tuple(turbines), substation=substation, projected_crs=projected_crs
    )


def validate_project_routing_endpoints(
    project: ProjectSpatialData,
    surface: CostSurface,
    constraints: tuple[ConstraintLayer, ...],
) -> None:
    """Reject project endpoints covered by a hard exclusion or blocked cell."""
    endpoints = [
        ("WTG", turbine.turbine_id, turbine.location) for turbine in project.turbines
    ]
    endpoints.append(
        ("Substation", project.substation.substation_id, project.substation.location)
    )
    hard_layers = tuple(
        layer for layer in constraints if layer.mode == ConstraintMode.HARD_EXCLUSION
    )

    for endpoint_type, endpoint_id, point in endpoints:
        covering_ids = sorted(
            layer.layer_id
            for layer in hard_layers
            if effective_constraint_geometry(layer).covers(point)
        )
        if covering_ids:
            raise ValueError(
                f"{endpoint_type} {endpoint_id} lies inside hard exclusion(s): "
                + ", ".join(covering_ids)
            )

        row, col = world_to_grid(point.x, point.y, surface)
        if not (0 <= row < surface.height and 0 <= col < surface.width):
            raise ValueError(
                f"{endpoint_type} {endpoint_id} lies outside the routing surface"
            )
        if math.isinf(float(surface.costs[row, col])):
            raise ValueError(
                f"{endpoint_type} {endpoint_id} lies in a hard-exclusion raster cell"
            )
