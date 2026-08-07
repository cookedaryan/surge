# Reference Journal: obsidian-vault/journal/2026-08-07.md
from typing import Any, Dict
from shapely.geometry import shape, mapping
from shapely.geometry.base import BaseGeometry

def parse_geojson(geojson_dict: Dict[str, Any]) -> BaseGeometry:
    """
    Parse a GeoJSON dictionary (Feature or Geometry) into a Shapely geometry.
    If it's a Feature, extracts the geometry block.
    """
    if geojson_dict.get("type") == "Feature":
        geom_dict = geojson_dict.get("geometry")
        if geom_dict is None:
            raise ValueError("GeoJSON Feature missing 'geometry' key.")
        return shape(geom_dict)
    
    # Otherwise assume it's a bare geometry dictionary
    return shape(geojson_dict)

def serialize_geometry(geom: BaseGeometry) -> Dict[str, Any]:
    """
    Serialize a Shapely geometry back into a GeoJSON geometry dictionary.
    """
    return mapping(geom)
