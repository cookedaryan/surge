import math

import networkx as nx
import numpy as np
import pyproj
import pytest
from affine import Affine
from shapely.geometry import LineString, Point

from app.algorithms.physical_routing import (
    PhysicalRoute,
    PhysicalRoutingResult,
    route_collector_topology,
)
from app.algorithms.route_refinement import (
    RefinedPhysicalRoute,
    refine_physical_route,
    refine_routing_result,
    remove_collinear_points,
    remove_duplicate_points,
    segment_is_traversable,
    segment_supercover_cells,
)
from app.algorithms.topology import CollectorTopologyResult, FeederTopology
from app.gis.cost_surface import CostSurface, grid_to_world


@pytest.fixture
def surface() -> CostSurface:
    return CostSurface(
        costs=np.ones((5, 5), dtype=np.float32),
        transform=Affine.translation(0, 50) * Affine.scale(10, -10),
        crs=pyproj.CRS("EPSG:32630"),
        width=5,
        height=5,
        resolution_m=10.0,
    )


def make_route(
    coordinates: tuple[tuple[float, float], ...],
    *,
    feeder_id: str = "F1",
    start_node_id: str = "S",
    end_node_id: str = "G",
    traversal_cost: float | None = None,
) -> PhysicalRoute:
    geometry = LineString(coordinates)
    return PhysicalRoute(
        feeder_id=feeder_id,
        start_node_id=start_node_id,
        end_node_id=end_node_id,
        geometry=geometry,
        length_m=geometry.length,
        traversal_cost=(geometry.length if traversal_cost is None else traversal_cost),
    )


def cell_center(row: int, col: int, surface: CostSurface) -> tuple[float, float]:
    return grid_to_world(row, col, surface)


def test_collinear_points_removed() -> None:
    coordinates = ((0.0, 0.0), (10.0, 0.0), (20.0, 0.0), (30.0, 0.0))

    assert remove_collinear_points(coordinates) == ((0.0, 0.0), (30.0, 0.0))


def test_collinear_backtracking_point_is_preserved() -> None:
    coordinates = ((0.0, 0.0), (10.0, 0.0), (5.0, 0.0))

    assert remove_collinear_points(coordinates) == coordinates


def test_duplicate_points_removed() -> None:
    coordinates = ((0.0, 0.0), (0.0, 0.0), (10.0, 0.0), (10.0, 0.0))

    assert remove_duplicate_points(coordinates) == ((0.0, 0.0), (10.0, 0.0))


def test_exact_endpoints_preserved(surface: CostSurface) -> None:
    start = (6.25, 43.75)
    end = (43.25, 6.75)
    route = make_route((start, (15.0, 35.0), (25.0, 25.0), end))

    refined = refine_physical_route(route, surface)

    assert refined.geometry.coords[0] == start
    assert refined.geometry.coords[-1] == end


def test_straight_route_collapses_to_two_points(surface: CostSurface) -> None:
    route = make_route(tuple(cell_center(0, col, surface) for col in range(5)))

    refined = refine_physical_route(route, surface)

    assert tuple(refined.geometry.coords) == (
        cell_center(0, 0, surface),
        cell_center(0, 4, surface),
    )


def test_visibility_shortcut_removes_unnecessary_points(
    surface: CostSurface,
) -> None:
    route = make_route(
        (
            cell_center(0, 0, surface),
            cell_center(0, 1, surface),
            cell_center(1, 2, surface),
            cell_center(2, 3, surface),
            cell_center(3, 4, surface),
        )
    )

    refined = refine_physical_route(route, surface)

    assert len(refined.geometry.coords) == 2


def test_shortcut_does_not_cross_blocked_cell(surface: CostSurface) -> None:
    surface.costs[1, 1] = np.inf
    start = cell_center(0, 0, surface)
    end = cell_center(2, 2, surface)

    assert not segment_is_traversable(start, end, surface)


def test_route_around_obstacle_remains_valid(surface: CostSurface) -> None:
    surface.costs[1, 1] = np.inf
    route = make_route(
        (
            cell_center(0, 0, surface),
            cell_center(0, 1, surface),
            cell_center(0, 2, surface),
            cell_center(1, 2, surface),
            cell_center(2, 2, surface),
        )
    )

    refined = refine_physical_route(route, surface)
    refined_coordinates = tuple(refined.geometry.coords)

    assert len(refined_coordinates) == 3
    assert all(
        segment_is_traversable(start, end, surface)
        for start, end in zip(
            refined_coordinates, refined_coordinates[1:], strict=False
        )
    )


def test_refined_route_is_valid_linestring(surface: CostSurface) -> None:
    route = make_route((cell_center(0, 0, surface), cell_center(0, 1, surface)))

    refined = refine_physical_route(route, surface)

    assert isinstance(refined, RefinedPhysicalRoute)
    assert isinstance(refined.geometry, LineString)
    assert refined.geometry.is_valid
    assert len(refined.geometry.coords) >= 2


def test_refined_length_not_greater_than_original(surface: CostSurface) -> None:
    route = make_route(
        (
            cell_center(0, 0, surface),
            cell_center(0, 1, surface),
            cell_center(1, 2, surface),
            cell_center(2, 2, surface),
        )
    )

    refined = refine_physical_route(route, surface)

    assert refined.refined_length_m <= refined.original_length_m + 1e-9


def test_multiple_routes_refined_independently(surface: CostSurface) -> None:
    first = make_route(
        tuple(cell_center(0, col, surface) for col in range(3)),
        feeder_id="F1",
        end_node_id="A",
    )
    second = make_route(
        tuple(cell_center(row, 4, surface) for row in range(3)),
        feeder_id="F2",
        end_node_id="B",
    )
    result = PhysicalRoutingResult(
        routes=(first, second),
        total_length_m=first.length_m + second.length_m,
        total_traversal_cost=first.traversal_cost + second.traversal_cost,
    )

    refined = refine_routing_result(result, surface)

    assert len(refined.routes) == 2
    assert all(len(route.geometry.coords) == 2 for route in refined.routes)


def test_feeder_and_node_metadata_preserved(surface: CostSurface) -> None:
    route = make_route(
        (cell_center(0, 0, surface), cell_center(0, 1, surface)),
        feeder_id="FEEDER-X",
        start_node_id="WTG-7",
        end_node_id="SUB-1",
    )

    refined = refine_physical_route(route, surface)

    assert refined.feeder_id == "FEEDER-X"
    assert refined.start_node_id == "WTG-7"
    assert refined.end_node_id == "SUB-1"


def test_single_segment_route_unchanged(surface: CostSurface) -> None:
    coordinates = (cell_center(0, 0, surface), cell_center(0, 1, surface))

    refined = refine_physical_route(make_route(coordinates), surface)

    assert tuple(refined.geometry.coords) == coordinates


def test_refinement_is_deterministic(surface: CostSurface) -> None:
    route = make_route(
        (
            cell_center(0, 0, surface),
            cell_center(0, 1, surface),
            cell_center(1, 2, surface),
            cell_center(2, 3, surface),
        )
    )

    first = refine_physical_route(route, surface)
    second = refine_physical_route(route, surface)

    assert first == second


def test_segment_supercover_detects_corner_cells(surface: CostSurface) -> None:
    cells = set(
        segment_supercover_cells(
            cell_center(0, 0, surface),
            cell_center(1, 1, surface),
            surface,
        )
    )

    assert {(0, 0), (0, 1), (1, 0), (1, 1)} <= cells


def test_total_refined_length_equals_route_sum(surface: CostSurface) -> None:
    first = make_route(
        tuple(cell_center(0, col, surface) for col in range(3)),
        feeder_id="F1",
    )
    second = make_route(
        tuple(cell_center(row, 4, surface) for row in range(3)),
        feeder_id="F2",
    )
    result = PhysicalRoutingResult(
        routes=(first, second),
        total_length_m=first.length_m + second.length_m,
        total_traversal_cost=first.traversal_cost + second.traversal_cost,
    )

    refined = refine_routing_result(result, surface)

    assert math.isclose(
        refined.total_original_length_m,
        sum(route.original_length_m for route in refined.routes),
    )
    assert math.isclose(
        refined.total_refined_length_m,
        sum(route.refined_length_m for route in refined.routes),
    )


def test_refined_traversal_cost_is_recomputed(surface: CostSurface) -> None:
    surface.costs[0, 1] = 3.0
    coordinates = (cell_center(0, 0, surface), cell_center(0, 2, surface))
    route = make_route(coordinates, traversal_cost=999.0)

    refined = refine_physical_route(route, surface)

    assert refined.original_traversal_cost == 999.0
    assert math.isclose(refined.refined_traversal_cost, 40.0)


def test_refinement_does_not_shortcut_through_finite_high_cost_cell(
    surface: CostSurface,
) -> None:
    surface.costs[2, 2] = 100.0
    graph = nx.Graph(crs=surface.crs)
    graph.add_node("start", geometry=Point(cell_center(2, 0, surface)))
    graph.add_node("goal", geometry=Point(cell_center(2, 4, surface)))
    feeder = FeederTopology(
        feeder_id="F1",
        node_ids=("start", "goal"),
        total_capacity_mw=1.0,
        total_length_m=40.0,
        mst_edges=(("start", "goal"),),
        mst_graph=nx.Graph(),
    )
    topology = CollectorTopologyResult(feeders=(feeder,))

    physical = route_collector_topology(topology, graph, surface)
    refined = refine_routing_result(physical, surface).routes[0]

    assert len(refined.geometry.coords) > 2
    assert refined.refined_traversal_cost <= physical.routes[0].traversal_cost + 1e-9


def test_segment_on_outer_surface_boundary_is_traversable(
    surface: CostSurface,
) -> None:
    start = tuple(surface.transform * (0.0, 0.5))
    end = tuple(surface.transform * (0.0, 4.5))

    cells = segment_supercover_cells(start, end, surface)

    assert cells
    assert all(row >= 0 and col >= 0 for row, col in cells)
    assert segment_is_traversable(start, end, surface)


def test_segment_with_endpoint_outside_surface_is_rejected(
    surface: CostSurface,
) -> None:
    start = tuple(surface.transform * (-0.1, 0.5))
    end = tuple(surface.transform * (1.5, 0.5))

    assert not segment_is_traversable(start, end, surface)


def test_outer_boundary_cost_uses_only_existing_interior_cells(
    surface: CostSurface,
) -> None:
    surface.costs[:, -1] = 100.0
    start = tuple(surface.transform * (0.0, 0.5))
    end = tuple(surface.transform * (0.0, 4.5))

    refined = refine_physical_route(make_route((start, end)), surface)

    assert math.isclose(refined.refined_traversal_cost, 40.0)
