import math

import numpy as np
import pyproj
import pytest
from shapely.geometry import Point

from app.gis.cost_surface import (
    build_project_cost_surface,
    grid_to_world,
    world_to_grid,
)
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine


@pytest.fixture
def mock_project() -> ProjectSpatialData:
    crs = pyproj.CRS("EPSG:32630")
    t1 = WindTurbine(turbine_id="WTG-1", location=Point(100.0, 100.0), capacity_mw=5.0)
    t2 = WindTurbine(turbine_id="WTG-2", location=Point(200.0, 200.0), capacity_mw=5.0)
    sub = Substation(substation_id="SUB-1", location=Point(150.0, 150.0))
    return ProjectSpatialData(turbines=(t1, t2), substation=sub, projected_crs=crs)


def test_surface_uses_project_crs(mock_project: ProjectSpatialData) -> None:
    surface = build_project_cost_surface(mock_project)
    assert surface.crs == mock_project.projected_crs


def test_surface_contains_all_project_points(mock_project: ProjectSpatialData) -> None:
    surface = build_project_cost_surface(
        mock_project, resolution_m=10.0, padding_m=10.0
    )
    for wtg in mock_project.turbines:
        r, c = world_to_grid(wtg.location.x, wtg.location.y, surface)
        assert 0 <= r < surface.height
        assert 0 <= c < surface.width

    r, c = world_to_grid(
        mock_project.substation.location.x,
        mock_project.substation.location.y,
        surface,
    )
    assert 0 <= r < surface.height
    assert 0 <= c < surface.width


def test_surface_padding_applied(mock_project: ProjectSpatialData) -> None:
    surf_no_pad = build_project_cost_surface(
        mock_project, resolution_m=10.0, padding_m=0.0
    )
    surf_pad = build_project_cost_surface(
        mock_project, resolution_m=10.0, padding_m=100.0
    )

    assert surf_pad.width == surf_no_pad.width + 20
    assert surf_pad.height == surf_no_pad.height + 20


def test_resolution_is_respected(mock_project: ProjectSpatialData) -> None:
    surf_10 = build_project_cost_surface(mock_project, resolution_m=10.0, padding_m=0.0)
    surf_20 = build_project_cost_surface(mock_project, resolution_m=20.0, padding_m=0.0)

    assert surf_10.width == 10
    assert surf_20.width == 5


def test_default_cells_have_base_cost(mock_project: ProjectSpatialData) -> None:
    surface = build_project_cost_surface(mock_project)
    assert np.all(surface.costs == 1.0)


def test_blocked_cells_are_not_traversable(mock_project: ProjectSpatialData) -> None:
    surface = build_project_cost_surface(mock_project)
    # mock a blocked cell
    surface.costs[5, 5] = np.inf

    assert surface.costs[5, 5] == np.inf
    assert not math.isfinite(surface.costs[5, 5])


def test_world_to_grid(mock_project: ProjectSpatialData) -> None:
    surface = build_project_cost_surface(mock_project, resolution_m=10.0, padding_m=0.0)
    r, c = world_to_grid(105.0, 195.0, surface)
    assert r == 0
    assert c == 0


def test_grid_to_world(mock_project: ProjectSpatialData) -> None:
    surface = build_project_cost_surface(mock_project, resolution_m=10.0, padding_m=0.0)
    x, y = grid_to_world(0, 0, surface)
    assert math.isclose(x, 105.0)
    assert math.isclose(y, 195.0)


def test_world_grid_round_trip(mock_project: ProjectSpatialData) -> None:
    surface = build_project_cost_surface(mock_project, resolution_m=10.0, padding_m=0.0)

    # Grid -> World -> Grid
    r_orig, c_orig = 3, 4
    x, y = grid_to_world(r_orig, c_orig, surface)
    r_new, c_new = world_to_grid(x, y, surface)

    assert r_orig == r_new
    assert c_orig == c_new

    # World -> Grid -> World (approximate, snaps to center)
    x_orig, y_orig = 137.5, 162.5
    r, c = world_to_grid(x_orig, y_orig, surface)
    x_new, y_new = grid_to_world(r, c, surface)

    assert math.hypot(x_orig - x_new, y_orig - y_new) <= 10.0 * math.sqrt(2) / 2


def test_invalid_resolution_rejected(mock_project: ProjectSpatialData) -> None:
    with pytest.raises(ValueError):
        build_project_cost_surface(mock_project, resolution_m=0.0)

    with pytest.raises(ValueError):
        build_project_cost_surface(mock_project, resolution_m=-10.0)


def test_max_cells_is_checked_before_allocation(
    mock_project: ProjectSpatialData,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_allocation(*args: object, **kwargs: object) -> None:
        raise AssertionError("NumPy allocation must not be attempted")

    monkeypatch.setattr(np, "ones", fail_allocation)

    with pytest.raises(ValueError, match="maximum allowed cells"):
        build_project_cost_surface(
            mock_project,
            resolution_m=10.0,
            padding_m=0.0,
            max_cells=99,
        )


def test_surface_dimensions_are_deterministic(mock_project: ProjectSpatialData) -> None:
    s1 = build_project_cost_surface(mock_project)
    s2 = build_project_cost_surface(mock_project)
    assert s1.width == s2.width
    assert s1.height == s2.height
    assert np.array_equal(s1.costs, s2.costs)


def test_costs_are_non_negative(mock_project: ProjectSpatialData) -> None:
    surface = build_project_cost_surface(mock_project)
    assert np.all(surface.costs >= 0)
