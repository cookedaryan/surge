import math

import numpy as np
import pyproj
import pytest
from affine import Affine

from app.algorithms.a_star import a_star
from app.gis.cost_surface import CostSurface


@pytest.fixture
def empty_surface() -> CostSurface:
    return CostSurface(
        costs=np.ones((10, 10), dtype=np.float32),
        transform=Affine.identity(),
        crs=pyproj.CRS("EPSG:32630"),
        width=10,
        height=10,
        resolution_m=10.0,
    )


def test_straight_path_on_uniform_grid(empty_surface: CostSurface) -> None:
    res = a_star(empty_surface, (0, 0), (0, 5))
    assert res is not None
    assert len(res.path) == 6
    assert res.path == ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5))
    assert res.traversal_cost == 50.0


def test_diagonal_path_on_uniform_grid(empty_surface: CostSurface) -> None:
    res = a_star(empty_surface, (0, 0), (5, 5))
    assert res is not None
    assert len(res.path) == 6
    assert res.path == ((0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5))
    assert math.isclose(res.traversal_cost, 5 * 10.0 * math.sqrt(2))


def test_path_avoids_blocked_cells(empty_surface: CostSurface) -> None:
    surface = empty_surface
    surface.costs[0:5, 2] = np.inf

    res = a_star(surface, (2, 0), (2, 4))
    assert res is not None
    for r, c in res.path:
        assert not math.isinf(surface.costs[r, c])


def test_no_path_returns_none(empty_surface: CostSurface) -> None:
    surface = empty_surface
    surface.costs[:, 5] = np.inf

    res = a_star(surface, (5, 0), (5, 9))
    assert res is None


def test_start_equals_goal(empty_surface: CostSurface) -> None:
    res = a_star(empty_surface, (3, 3), (3, 3))
    assert res is not None
    assert res.path == ((3, 3),)
    assert res.traversal_cost == 0.0


def test_path_stays_inside_grid(empty_surface: CostSurface) -> None:
    res = a_star(empty_surface, (0, 0), (-1, -1))
    assert res is None


def test_expensive_cells_are_avoided(empty_surface: CostSurface) -> None:
    surface = empty_surface
    surface.costs[5, 5] = 9.0

    res = a_star(surface, (5, 4), (5, 6))
    assert res is not None
    assert (5, 5) not in res.path


def test_diagonal_distance_cost(empty_surface: CostSurface) -> None:
    res = a_star(empty_surface, (0, 0), (1, 1))
    assert res is not None
    assert math.isclose(res.traversal_cost, 10.0 * math.sqrt(2))


def test_corner_cutting_prevented(empty_surface: CostSurface) -> None:
    surface = empty_surface
    surface.costs[0, 1] = np.inf
    surface.costs[1, 0] = np.inf

    res = a_star(surface, (0, 0), (1, 1))
    assert res is None


def test_astar_is_deterministic(empty_surface: CostSurface) -> None:
    res1 = a_star(empty_surface, (0, 0), (9, 9))
    res2 = a_star(empty_surface, (0, 0), (9, 9))
    assert res1 is not None and res2 is not None
    assert res1.path == res2.path


def test_heuristic_remains_optimal_with_cost_below_one() -> None:
    surface = CostSurface(
        costs=np.ones((5, 5), dtype=np.float32),
        transform=Affine.identity(),
        crs=pyproj.CRS("EPSG:32630"),
        width=5,
        height=5,
        resolution_m=10.0,
    )
    surface.costs[1:4, 1:4] = 2.0
    surface.costs[0, :] = 0.4
    surface.costs[:, 4] = 0.4

    res = a_star(surface, (0, 0), (4, 4))
    assert res is not None
    assert (2, 2) not in res.path
