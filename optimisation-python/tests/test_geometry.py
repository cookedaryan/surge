import pytest
from shapely.geometry import Polygon
from app.gis.geometry import validate_geometry

def test_validate_valid_geometry():
    # Valid square
    poly = Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)])
    validated = validate_geometry(poly)
    assert validated.is_valid
    assert validated.equals(poly)

def test_validate_invalid_geometry():
    # Bowtie polygon (self-intersecting)
    poly = Polygon([(0, 0), (0, 1), (1, 0), (1, 1), (0, 0)])
    assert not poly.is_valid
    
    validated = validate_geometry(poly)
    assert validated.is_valid
    # The bowtie typically gets converted into a MultiPolygon
    assert validated.geom_type == "MultiPolygon"
