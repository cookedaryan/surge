import pytest
from shapely.geometry import Point
from app.gis.geojson import parse_geojson, serialize_geometry

def test_parse_geojson_feature():
    geojson_feature = {
        "type": "Feature",
        "properties": {"name": "Test"},
        "geometry": {
            "type": "Point",
            "coordinates": [1.0, 2.0]
        }
    }
    geom = parse_geojson(geojson_feature)
    assert isinstance(geom, Point)
    assert geom.x == 1.0
    assert geom.y == 2.0

def test_parse_geojson_geometry():
    geojson_geom = {
        "type": "Point",
        "coordinates": [1.0, 2.0]
    }
    geom = parse_geojson(geojson_geom)
    assert isinstance(geom, Point)
    assert geom.x == 1.0
    assert geom.y == 2.0

def test_serialize_geometry():
    geom = Point(1.0, 2.0)
    geojson_geom = serialize_geometry(geom)
    assert geojson_geom["type"] == "Point"
    assert geojson_geom["coordinates"] == (1.0, 2.0)
