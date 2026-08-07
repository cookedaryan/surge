# Reference Journal: obsidian-vault/journal/2026-08-07.md
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

def validate_geometry(geom: BaseGeometry) -> BaseGeometry:
    """
    Validates a shapely geometry. If it's invalid (e.g., self-intersecting polygon),
    it attempts to make it valid.
    Raises ValueError if it cannot be fixed.
    """
    if not geom.is_valid:
        geom = make_valid(geom)
        if not geom.is_valid:
            raise ValueError("Geometry is invalid and cannot be automatically fixed.")
    return geom
