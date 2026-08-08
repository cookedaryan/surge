# Reference Journal: obsidian-vault/journal/2026-08-07.md
import math
from typing import Any, cast

from shapely.geometry import Point

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
    if len(sub_features) > 1:
        raise ValueError("Expected exactly one Substation feature")
        
    sub_feature = sub_features[0]

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
        raw_wtgs.append({
            "geom": geom,
            "id": wtg_id,
            "capacity": cap
        })
        
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
    raw_sub = {
        "geom": sub_geom,
        "id": sub_id,
        "capacity": sub_cap
    }

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
                capacity_mw=raw_wtg["capacity"]
            )
        )

    proj_sub_geom = transform_geometry(raw_sub["geom"], transformer)
    substation = Substation(
        substation_id=str(raw_sub["id"]),
        location=cast(Point, proj_sub_geom),
        capacity_mw=raw_sub["capacity"]
    )

    return ProjectSpatialData(
        turbines=tuple(turbines),
        substation=substation,
        projected_crs=projected_crs
    )
