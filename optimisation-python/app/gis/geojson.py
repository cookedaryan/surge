# Reference Journal: obsidian-vault/journal/2026-08-07.md
from typing import Any, cast

from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry


def parse_geojson(geojson_dict: dict[str, Any]) -> BaseGeometry:
    """
    Parse a GeoJSON dictionary (Feature or Geometry) into a Shapely geometry.
    If it's a Feature, extracts the geometry block.
    """
    if geojson_dict.get("type") == "Feature":
        geom_dict = geojson_dict.get("geometry")
        if geom_dict is None:
            raise ValueError("GeoJSON Feature missing 'geometry' key.")
        try:
            return shape(geom_dict)
        except Exception as e:
            raise ValueError(f"Invalid GeoJSON geometry: {e}") from e

    # Otherwise assume it's a bare geometry dictionary
    try:
        return shape(geojson_dict)
    except Exception as e:
        raise ValueError(f"Invalid GeoJSON geometry: {e}") from e


def serialize_geometry(geom: BaseGeometry) -> dict[str, Any]:
    """
    Serialize a Shapely geometry back into a GeoJSON geometry dictionary.
    """
    return cast(dict[str, Any], mapping(geom))
