# Reference Journal: obsidian-vault/journal/2026-08-07.md
from typing import Dict, Any, List
from shapely.geometry import Point
from app.gis.geojson import parse_geojson
from app.gis.crs import WGS84_CRS, get_utm_crs, get_transformer, transform_geometry
from app.models.spatial import WindTurbine, Substation, ProjectSpatialData

def _extract_features(geojson: Dict[str, Any]) -> List[Dict[str, Any]]:
    if geojson.get("type") == "FeatureCollection":
        return geojson.get("features", [])
    elif geojson.get("type") == "Feature":
        return [geojson]
    else:
        raise ValueError("Expected FeatureCollection or Feature")

def process_project_data(wtg_geojson: Dict[str, Any], substation_geojson: Dict[str, Any]) -> ProjectSpatialData:
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
    for i, feat in enumerate(wtg_features):
        geom = parse_geojson(feat)
        if not isinstance(geom, Point):
            raise ValueError(f"WTG geometry must be Point, got {geom.geom_type}")
        props = feat.get("properties", {})
        raw_wtgs.append({
            "geom": geom,
            "id": str(props.get("id", props.get("turbine_id", f"WTG-{i+1}"))),
            "capacity": props.get("capacity_mw")
        })
        
    sub_geom = parse_geojson(sub_feature)
    if not isinstance(sub_geom, Point):
        raise ValueError(f"Substation geometry must be Point, got {sub_geom.geom_type}")
    sub_props = sub_feature.get("properties", {})
    raw_sub = {
        "geom": sub_geom,
        "id": str(sub_props.get("id", sub_props.get("substation_id", "SUB-1"))),
        "capacity": sub_props.get("capacity_mw")
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
                turbine_id=raw_wtg["id"],
                location=proj_geom,  # type: ignore
                capacity_mw=raw_wtg["capacity"]
            )
        )

    proj_sub_geom = transform_geometry(raw_sub["geom"], transformer)
    substation = Substation(
        substation_id=raw_sub["id"],
        location=proj_sub_geom,  # type: ignore
        capacity_mw=raw_sub["capacity"]
    )

    return ProjectSpatialData(
        turbines=tuple(turbines),
        substation=substation,
        projected_crs=projected_crs
    )
