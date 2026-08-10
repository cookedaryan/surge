import math

import pyproj
import pytest
from shapely.geometry import Point

from app.algorithms.wtg_grouping import group_wtgs
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine


@pytest.fixture
def mock_crs() -> pyproj.CRS:
    return pyproj.CRS.from_epsg(32631)


def _make_project(wtgs: list[WindTurbine], mock_crs: pyproj.CRS) -> ProjectSpatialData:
    sub = Substation(
        substation_id="SUB-1",
        location=Point(0.0, 0.0),
        capacity_mw=100.0,
    )
    return ProjectSpatialData(
        turbines=tuple(wtgs),
        substation=sub,
        projected_crs=mock_crs,
    )


def test_single_feeder_assignment(mock_crs: pyproj.CRS) -> None:
    wtgs = [
        WindTurbine(turbine_id="W1", location=Point(10, 10), capacity_mw=2.0),
        WindTurbine(turbine_id="W2", location=Point(20, 20), capacity_mw=3.0),
    ]
    project = _make_project(wtgs, mock_crs)
    result = group_wtgs(project, feeder_capacity_mw=10.0)

    assert result.feeder_count == 1
    assert len(result.assignments) == 1
    assert set(result.assignments[0].turbine_ids) == {"W1", "W2"}
    assert result.assignments[0].total_capacity_mw == 5.0


def test_multiple_feeders_required(mock_crs: pyproj.CRS) -> None:
    wtgs = [
        WindTurbine(turbine_id="W1", location=Point(0, 10), capacity_mw=5.0),
        WindTurbine(turbine_id="W2", location=Point(0, 20), capacity_mw=6.0),
        WindTurbine(turbine_id="W3", location=Point(0, 30), capacity_mw=4.0),
    ]
    project = _make_project(wtgs, mock_crs)
    result = group_wtgs(project, feeder_capacity_mw=10.0)

    assert result.feeder_count == 2
    assert len(result.assignments) == 2
    # One cluster has 10 (6+4), one has 5. Total 15.
    capacities = sorted([a.total_capacity_mw for a in result.assignments])
    assert capacities == [5.0, 10.0]


def test_exact_capacity_boundary(mock_crs: pyproj.CRS) -> None:
    wtgs = [
        WindTurbine(turbine_id="W1", location=Point(0, 10), capacity_mw=5.0),
        WindTurbine(turbine_id="W2", location=Point(0, 20), capacity_mw=5.0),
    ]
    project = _make_project(wtgs, mock_crs)
    result = group_wtgs(project, feeder_capacity_mw=10.0)

    assert result.feeder_count == 1
    assert result.assignments[0].total_capacity_mw == 10.0


def test_no_feeder_exceeds_capacity(mock_crs: pyproj.CRS) -> None:
    wtgs = [
        WindTurbine(turbine_id=f"W{i}", location=Point(i * 10, 0), capacity_mw=4.0)
        for i in range(10)
    ]
    # Total capacity = 40 MW. Max feeder = 9 MW.
    # Theoretical min = ceil(40/9) = 5 feeders.
    project = _make_project(wtgs, mock_crs)
    result = group_wtgs(project, feeder_capacity_mw=9.0)

    assert result.feeder_count >= 5
    for a in result.assignments:
        assert a.total_capacity_mw <= 9.0


def test_every_turbine_assigned_once(mock_crs: pyproj.CRS) -> None:
    wtgs = [
        WindTurbine(turbine_id=f"W{i}", location=Point(i * 10, i * 10), capacity_mw=3.0)
        for i in range(5)
    ]
    project = _make_project(wtgs, mock_crs)
    result = group_wtgs(project, feeder_capacity_mw=5.0)

    assigned_turbines: list[str] = []
    for a in result.assignments:
        assigned_turbines.extend(a.turbine_ids)

    assert len(assigned_turbines) == 5
    assert set(assigned_turbines) == {f"W{i}" for i in range(5)}


def test_total_capacity_preserved(mock_crs: pyproj.CRS) -> None:
    wtgs = [
        WindTurbine(turbine_id="W1", location=Point(0, 10), capacity_mw=2.5),
        WindTurbine(turbine_id="W2", location=Point(0, 20), capacity_mw=3.5),
        WindTurbine(turbine_id="W3", location=Point(0, 30), capacity_mw=4.5),
    ]
    project = _make_project(wtgs, mock_crs)
    result = group_wtgs(project, feeder_capacity_mw=5.0)

    total = sum(a.total_capacity_mw for a in result.assignments)
    assert math.isclose(total, 10.5)


def test_single_wtg_exceeds_capacity_rejected(mock_crs: pyproj.CRS) -> None:
    wtgs = [
        WindTurbine(turbine_id="W1", location=Point(0, 10), capacity_mw=15.0),
    ]
    project = _make_project(wtgs, mock_crs)
    with pytest.raises(ValueError, match="exceeds feeder max"):
        group_wtgs(project, feeder_capacity_mw=10.0)


def test_missing_capacity_rejected(mock_crs: pyproj.CRS) -> None:
    wtgs = [
        WindTurbine(turbine_id="W1", location=Point(0, 10), capacity_mw=None),
    ]
    project = _make_project(wtgs, mock_crs)
    with pytest.raises(ValueError, match="invalid capacity"):
        group_wtgs(project, feeder_capacity_mw=10.0)


def test_zero_capacity_rejected(mock_crs: pyproj.CRS) -> None:
    wtgs = [
        WindTurbine(turbine_id="W1", location=Point(0, 10), capacity_mw=0.0),
    ]
    project = _make_project(wtgs, mock_crs)
    with pytest.raises(ValueError, match="invalid capacity"):
        group_wtgs(project, feeder_capacity_mw=10.0)


def test_grouping_is_deterministic(mock_crs: pyproj.CRS) -> None:
    wtgs = [
        WindTurbine(
            turbine_id=f"W{i}", location=Point(i * 10, (i % 3) * 10), capacity_mw=4.0
        )
        for i in range(20)
    ]
    project = _make_project(wtgs, mock_crs)

    result1 = group_wtgs(project, feeder_capacity_mw=15.0)
    result2 = group_wtgs(project, feeder_capacity_mw=15.0)

    # Check that both produce identical assignments in identical order
    assert result1.feeder_count == result2.feeder_count
    for a1, a2 in zip(result1.assignments, result2.assignments, strict=True):
        assert a1.turbine_ids == a2.turbine_ids


def test_feeder_count_respects_theoretical_minimum(mock_crs: pyproj.CRS) -> None:
    # 4 WTGs, 5MW each = 20MW
    # Feeder max = 10MW. Minimum feeders = 20/10 = 2.
    wtgs = [
        WindTurbine(turbine_id="W1", location=Point(0, 10), capacity_mw=5.0),
        WindTurbine(turbine_id="W2", location=Point(0, 20), capacity_mw=5.0),
        WindTurbine(turbine_id="W3", location=Point(100, 10), capacity_mw=5.0),
        WindTurbine(turbine_id="W4", location=Point(100, 20), capacity_mw=5.0),
    ]
    project = _make_project(wtgs, mock_crs)
    result = group_wtgs(project, feeder_capacity_mw=10.0)

    assert result.feeder_count == 2


def test_spatially_close_turbines_preferred(mock_crs: pyproj.CRS) -> None:
    # Create two distinct spatial groups
    # Group A: x=0 (needs 1 feeder of max 10MW)
    wtgs_a = [
        WindTurbine(turbine_id="A1", location=Point(0, 1), capacity_mw=4.0),
        WindTurbine(turbine_id="A2", location=Point(0, 2), capacity_mw=4.0),
    ]
    # Group B: x=1000 (needs 1 feeder of max 10MW)
    wtgs_b = [
        WindTurbine(turbine_id="B1", location=Point(1000, 1), capacity_mw=4.0),
        WindTurbine(turbine_id="B2", location=Point(1000, 2), capacity_mw=4.0),
    ]
    project = _make_project(wtgs_a + wtgs_b, mock_crs)
    result = group_wtgs(project, feeder_capacity_mw=10.0)

    assert result.feeder_count == 2

    # We expect A1, A2 together and B1, B2 together
    clusters = [set(a.turbine_ids) for a in result.assignments]
    assert {"A1", "A2"} in clusters
    assert {"B1", "B2"} in clusters


def test_non_finite_feeder_limit_rejected(mock_crs: pyproj.CRS) -> None:
    wtgs = [WindTurbine(turbine_id="W1", location=Point(0, 0), capacity_mw=1.0)]
    project = _make_project(wtgs, mock_crs)
    with pytest.raises(ValueError, match="positive and finite"):
        group_wtgs(project, float("inf"))
    with pytest.raises(ValueError, match="positive and finite"):
        group_wtgs(project, float("nan"))
    with pytest.raises(ValueError, match="positive and finite"):
        group_wtgs(project, -10.0)


def test_input_order_invariance(mock_crs: pyproj.CRS) -> None:
    wtgs_forward = [
        WindTurbine(turbine_id=f"W{i}", location=Point(i * 10, i * 10), capacity_mw=4.0)
        for i in range(6)
    ]
    wtgs_reversed = wtgs_forward[::-1]

    res1 = group_wtgs(_make_project(wtgs_forward, mock_crs), 10.0)
    res2 = group_wtgs(_make_project(wtgs_reversed, mock_crs), 10.0)

    assert res1.feeder_count == res2.feeder_count
    for a1, a2 in zip(res1.assignments, res2.assignments, strict=True):
        assert a1.turbine_ids == a2.turbine_ids


def test_five_bin_counterexample(mock_crs: pyproj.CRS) -> None:
    # Capacities: 2, 8, 4, 8, 7, 6, 3, 2, 3, 7
    # Total = 50. Limit = 10. Minimum = 50/10 = 5.
    capacities = [2.0, 8.0, 4.0, 8.0, 7.0, 6.0, 3.0, 2.0, 3.0, 7.0]
    wtgs = [
        WindTurbine(turbine_id=f"W{i}", location=Point(i, i), capacity_mw=cap)
        for i, cap in enumerate(capacities)
    ]
    project = _make_project(wtgs, mock_crs)
    result = group_wtgs(project, 10.0)

    # Using the exact MILP solver should nail this in exactly 5 feeders!
    assert result.feeder_count == 5


def test_fractional_boundary_without_leakage(mock_crs: pyproj.CRS) -> None:
    # 3 decimal precision
    wtgs = [
        WindTurbine(turbine_id="W1", location=Point(0, 0), capacity_mw=5.001),
        WindTurbine(turbine_id="W2", location=Point(1, 1), capacity_mw=4.999),
    ]
    project = _make_project(wtgs, mock_crs)
    result = group_wtgs(project, 10.0)
    assert result.feeder_count == 1

    wtgs_exceed = [
        WindTurbine(turbine_id="W1", location=Point(0, 0), capacity_mw=5.001),
        WindTurbine(turbine_id="W2", location=Point(1, 1), capacity_mw=5.0),
    ]
    result2 = group_wtgs(_make_project(wtgs_exceed, mock_crs), 10.0)
    assert result2.feeder_count == 2


def test_four_decimals_rejected(mock_crs: pyproj.CRS) -> None:
    wtgs = [WindTurbine(turbine_id="W1", location=Point(0, 0), capacity_mw=5.0004)]
    project = _make_project(wtgs, mock_crs)
    with pytest.raises(ValueError, match="more than 3 decimal places"):
        group_wtgs(project, 10.0)


def test_duplicate_coordinates_fewer_points(mock_crs: pyproj.CRS) -> None:
    # 5 turbines all at exactly (0,0), each 5MW. Max 10MW per feeder.
    # Needs ceil(25/10) = 3 feeders.
    # KMeans with k=3 but only 1 distinct point handled gracefully.
    wtgs = [
        WindTurbine(turbine_id=f"W{i}", location=Point(0, 0), capacity_mw=5.0)
        for i in range(5)
    ]
    project = _make_project(wtgs, mock_crs)
    result = group_wtgs(project, 10.0)
    assert result.feeder_count == 3


def test_empty_project_behavior(mock_crs: pyproj.CRS) -> None:
    project = _make_project([], mock_crs)
    result = group_wtgs(project, 10.0)
    assert result.feeder_count == 0
    assert len(result.assignments) == 0


def test_final_invariant_checks(mock_crs: pyproj.CRS) -> None:
    wtgs = [
        WindTurbine(turbine_id=f"W{i}", location=Point(i * 2, i * 3), capacity_mw=2.5)
        for i in range(15)
    ]
    project = _make_project(wtgs, mock_crs)
    feeder_cap = 10.0

    result = group_wtgs(project, feeder_cap)

    # 1. Total capacity constraint
    assigned_turbines: set[str] = set()
    for assignment in result.assignments:
        # Feeder cap
        assert assignment.total_capacity_mw <= feeder_cap
        # Mutually exclusive and collectively exhaustive
        for t_id in assignment.turbine_ids:
            assert t_id not in assigned_turbines
            assigned_turbines.add(t_id)

    assert assigned_turbines == {f"W{i}" for i in range(15)}
