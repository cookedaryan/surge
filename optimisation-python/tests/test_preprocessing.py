from typing import Any

import pytest

from app.gis.preprocessing import process_project_data
from app.models.spatial import ProjectSpatialData, Substation


def _make_fc(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": features}


def _make_pt(
    lon: float, lat: float, props: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": props or {},
    }


def test_successful_parsing_and_transformation() -> None:
    wtgs = _make_fc(
        [
            _make_pt(-3.0, 55.0, {"id": "W1", "capacity_mw": 5.0}),
            _make_pt(-3.1, 55.1, {"id": "W2", "capacity_mw": 6.0}),
        ]
    )
    sub = _make_fc([_make_pt(-3.05, 55.05, {"id": "S1", "capacity_mw": 100.0})])

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


def test_non_point_wtg_rejected() -> None:
    wtgs = _make_fc(
        [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-3.0, 55.0], [-3.1, 55.1]],
                },
                "properties": {"id": "W1"},
            }
        ]
    )
    sub = _make_fc([_make_pt(-3.05, 55.05)])

    with pytest.raises(ValueError, match="WTG geometry must be Point"):
        process_project_data(wtgs, sub)


def test_missing_substation_rejected() -> None:
    wtgs = _make_fc([_make_pt(-3.0, 55.0)])
    sub = _make_fc([])  # Empty collection

    with pytest.raises(ValueError, match="Substation GeoJSON is empty"):
        process_project_data(wtgs, sub)


def test_multiple_substations_selects_nearest_when_capacity_missing() -> None:
    wtgs = _make_fc([_make_pt(-3.0, 55.0, {"id": "W1"})])
    substations = _make_fc(
        [
            _make_pt(-3.5, 55.5, {"id": "FAR"}),
            _make_pt(-3.01, 55.01, {"id": "NEAR"}),
        ]
    )

    project_data = process_project_data(wtgs, substations)

    assert project_data.substation.substation_id == "NEAR"


def test_empty_wtg_rejected() -> None:
    wtgs = _make_fc([])
    sub = _make_fc([_make_pt(-3.05, 55.05)])

    with pytest.raises(ValueError, match="WTG FeatureCollection is empty"):
        process_project_data(wtgs, sub)


def test_invalid_coordinates_rejected() -> None:
    # Provide coordinates that don't make a valid Point definition in GeoJSON
    wtgs = _make_fc(
        [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": []},  # Empty coordinates
                "properties": {"id": "W1"},
            }
        ]
    )
    sub = _make_fc([_make_pt(-3.05, 55.05, {"id": "S1"})])

    with pytest.raises(ValueError, match="geometry is empty"):
        process_project_data(wtgs, sub)


def test_out_of_bounds_coordinates() -> None:
    # Longitude > 180
    wtgs1 = _make_fc([_make_pt(181.0, 55.0, {"id": "W1"})])
    sub = _make_fc([_make_pt(-3.0, 55.0, {"id": "S1"})])
    with pytest.raises(ValueError, match="longitude must be between -180 and 180"):
        process_project_data(wtgs1, sub)

    # Latitude < -90
    wtgs2 = _make_fc([_make_pt(-3.0, -91.0, {"id": "W2"})])
    with pytest.raises(ValueError, match="latitude must be between -90 and 90"):
        process_project_data(wtgs2, sub)


def test_invalid_capacity() -> None:
    # Negative capacity
    wtgs = _make_fc([_make_pt(-3.0, 55.0, {"id": "W1", "capacity_mw": -5.0})])
    sub = _make_fc([_make_pt(-3.05, 55.05, {"id": "S1"})])
    with pytest.raises(ValueError, match="positive and finite"):
        process_project_data(wtgs, sub)

    # Boolean capacity
    wtgs_bool = _make_fc([_make_pt(-3.0, 55.0, {"id": "W2", "capacity_mw": True})])
    with pytest.raises(ValueError, match="must not be a boolean"):
        process_project_data(wtgs_bool, sub)

    # Zero capacity
    wtgs_zero = _make_fc([_make_pt(-3.0, 55.0, {"id": "W3", "capacity_mw": 0.0})])
    with pytest.raises(ValueError, match="positive and finite"):
        process_project_data(wtgs_zero, sub)

    # NaN capacity
    wtgs_nan = _make_fc(
        [_make_pt(-3.0, 55.0, {"id": "W4", "capacity_mw": float("nan")})]
    )
    with pytest.raises(ValueError, match="positive and finite"):
        process_project_data(wtgs_nan, sub)

    # Inf capacity
    wtgs_inf = _make_fc(
        [_make_pt(-3.0, 55.0, {"id": "W5", "capacity_mw": float("inf")})]
    )
    with pytest.raises(ValueError, match="positive and finite"):
        process_project_data(wtgs_inf, sub)

    # Negative Inf capacity
    wtgs_ninf = _make_fc(
        [_make_pt(-3.0, 55.0, {"id": "W6", "capacity_mw": float("-inf")})]
    )
    with pytest.raises(ValueError, match="positive and finite"):
        process_project_data(wtgs_ninf, sub)


def test_duplicate_ids() -> None:
    wtgs = _make_fc(
        [
            _make_pt(-3.0, 55.0, {"id": "W1"}),
            _make_pt(-3.1, 55.1, {"id": "W1"}),  # Duplicate WTG ID
        ]
    )
    sub = _make_fc([_make_pt(-3.05, 55.05, {"id": "S1"})])
    with pytest.raises(ValueError, match="Duplicate ID found: W1"):
        process_project_data(wtgs, sub)

    wtgs2 = _make_fc([_make_pt(-3.0, 55.0, {"id": "S1"})])
    with pytest.raises(ValueError, match="Duplicate ID found: S1"):
        process_project_data(wtgs2, sub)


def test_blank_ids() -> None:
    wtgs = _make_fc([_make_pt(-3.0, 55.0, {"id": "   "})])
    sub = _make_fc([_make_pt(-3.05, 55.05, {"id": "S1"})])
    with pytest.raises(ValueError, match="missing a valid ID"):
        process_project_data(wtgs, sub)


def test_shapely_parse_error() -> None:
    wtgs = _make_fc(
        [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": ["not", "a", "number"]},
                "properties": {"id": "W1"},
            }
        ]
    )
    sub = _make_fc([_make_pt(-3.05, 55.05, {"id": "S1"})])
    with pytest.raises(ValueError, match="Invalid GeoJSON geometry"):
        process_project_data(wtgs, sub)


def test_malformed_features_container() -> None:
    # features is an object instead of list
    wtgs = {"type": "FeatureCollection", "features": {"invalid": "object"}}
    sub = _make_fc([_make_pt(-3.05, 55.05, {"id": "S1"})])
    with pytest.raises(ValueError, match="must be a list"):
        process_project_data(wtgs, sub)

    # features list contains non-objects
    wtgs2 = {"type": "FeatureCollection", "features": ["string"]}
    with pytest.raises(ValueError, match="must contain objects"):
        process_project_data(wtgs2, sub)
