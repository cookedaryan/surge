import pytest
from app.gis.preprocessing import process_project_data
from app.models.spatial import WindTurbine, Substation, ProjectSpatialData

def _make_fc(features):
    return {"type": "FeatureCollection", "features": features}

def _make_pt(lon, lat, props=None):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": props or {}
    }

def test_successful_parsing_and_transformation():
    wtgs = _make_fc([
        _make_pt(-3.0, 55.0, {"id": "W1", "capacity_mw": 5.0}),
        _make_pt(-3.1, 55.1, {"id": "W2", "capacity_mw": 6.0})
    ])
    sub = _make_fc([
        _make_pt(-3.05, 55.05, {"id": "S1", "capacity_mw": 100.0})
    ])

    project_data = process_project_data(wtgs, sub)

    # All objects correct types
    assert isinstance(project_data, ProjectSpatialData)
    assert len(project_data.turbines) == 2
    assert isinstance(project_data.substation, Substation)

    # FeatureCollection parses and properties preserved
    assert project_data.turbines[0].turbine_id == "W1"
    assert project_data.turbines[0].capacity_mw == 5.0
    assert project_data.turbines[1].turbine_id == "W2"
    assert project_data.turbines[1].capacity_mw == 6.0
    assert project_data.substation.substation_id == "S1"
    
    # Common projected CRS and coordinates are metre-based (UTM coordinates are large)
    assert project_data.projected_crs.is_projected
    assert project_data.turbines[0].location.x > 10000
    assert project_data.turbines[0].location.y > 10000

def test_non_point_wtg_rejected():
    wtgs = _make_fc([{
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[-3.0, 55.0], [-3.1, 55.1]]},
        "properties": {"id": "W1"}
    }])
    sub = _make_fc([_make_pt(-3.05, 55.05)])

    with pytest.raises(ValueError, match="WTG geometry must be Point"):
        process_project_data(wtgs, sub)

def test_missing_substation_rejected():
    wtgs = _make_fc([_make_pt(-3.0, 55.0)])
    sub = _make_fc([])  # Empty collection

    with pytest.raises(ValueError, match="Substation GeoJSON is empty"):
        process_project_data(wtgs, sub)

def test_empty_wtg_rejected():
    wtgs = _make_fc([])
    sub = _make_fc([_make_pt(-3.05, 55.05)])

    with pytest.raises(ValueError, match="WTG FeatureCollection is empty"):
        process_project_data(wtgs, sub)

def test_invalid_coordinates_rejected():
    # Provide coordinates that don't make a valid Point definition in GeoJSON
    wtgs = _make_fc([{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": []}, # Invalid coordinates
        "properties": {}
    }])
    sub = _make_fc([_make_pt(-3.05, 55.05)])

    with pytest.raises(Exception):  # Either ValueError or Shapely parsing error
        process_project_data(wtgs, sub)
