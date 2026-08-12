import math
from dataclasses import dataclass

from shapely.geometry import LineString

from app.algorithms.physical_routing import (
    PhysicalRoute,
    PhysicalRoutingResult,
    validate_cost_surface,
)
from app.gis.cost_surface import CostSurface

Coordinate = tuple[float, float]
GridCell = tuple[int, int]

_GRID_TOLERANCE = 1e-12
_LENGTH_TOLERANCE = 1e-9
_COST_TOLERANCE = 1e-9


@dataclass(frozen=True)
class RefinedPhysicalRoute:
    feeder_id: str
    start_node_id: str
    end_node_id: str
    geometry: LineString
    original_length_m: float
    refined_length_m: float
    original_traversal_cost: float
    refined_traversal_cost: float


@dataclass(frozen=True)
class RefinedRoutingResult:
    routes: tuple[RefinedPhysicalRoute, ...]
    total_original_length_m: float
    total_refined_length_m: float


def remove_duplicate_points(
    coordinates: tuple[Coordinate, ...],
) -> tuple[Coordinate, ...]:
    """Remove consecutive duplicate coordinates without changing the path."""
    if not coordinates:
        return ()

    result = [coordinates[0]]
    for coordinate in coordinates[1:]:
        if coordinate != result[-1]:
            result.append(coordinate)
    return tuple(result)


def remove_collinear_points(
    coordinates: tuple[Coordinate, ...],
    tolerance: float = 1e-9,
) -> tuple[Coordinate, ...]:
    """Remove intermediate points on a straight, forward-moving segment."""
    if tolerance < 0:
        raise ValueError("Collinearity tolerance must be non-negative")
    if len(coordinates) < 3:
        return coordinates

    result: list[Coordinate] = []
    for coordinate in coordinates:
        while len(result) >= 2 and _is_redundant_collinear_point(
            result[-2], result[-1], coordinate, tolerance
        ):
            result.pop()
        result.append(coordinate)
    return tuple(result)


def segment_supercover_cells(
    start: Coordinate,
    end: Coordinate,
    surface: CostSurface,
) -> tuple[GridCell, ...]:
    """Return every raster cell touched by a world-coordinate segment."""
    start_col, start_row = _world_to_grid_coordinates(start, surface)
    end_col, end_row = _world_to_grid_coordinates(end, surface)
    breakpoints = _segment_breakpoints(start_col, start_row, end_col, end_row)

    cells: list[GridCell] = []
    seen: set[GridCell] = set()

    def add_cells_at(parameter: float) -> None:
        col = start_col + (end_col - start_col) * parameter
        row = start_row + (end_row - start_row) * parameter
        for cell in _existing_cells_touching_grid_point(col, row, surface):
            if cell not in seen:
                seen.add(cell)
                cells.append(cell)

    for index, parameter in enumerate(breakpoints):
        add_cells_at(parameter)
        if index + 1 < len(breakpoints):
            midpoint = (parameter + breakpoints[index + 1]) / 2.0
            add_cells_at(midpoint)

    return tuple(cells)


def segment_is_traversable(
    start: Coordinate,
    end: Coordinate,
    surface: CostSurface,
) -> bool:
    """Return whether a segment stays in bounds and touches no blocked cell."""
    validate_cost_surface(surface)
    return _segment_is_traversable(start, end, surface)


def refine_physical_route(
    route: PhysicalRoute,
    cost_surface: CostSurface,
) -> RefinedPhysicalRoute:
    """Simplify a physical route while retaining obstacle-safe geometry."""
    validate_cost_surface(cost_surface)
    return _refine_physical_route(route, cost_surface)


def refine_routing_result(
    result: PhysicalRoutingResult,
    cost_surface: CostSurface,
) -> RefinedRoutingResult:
    """Refine every physical route and aggregate original/refined lengths."""
    validate_cost_surface(cost_surface)
    routes = tuple(
        _refine_physical_route(route, cost_surface) for route in result.routes
    )
    return RefinedRoutingResult(
        routes=routes,
        total_original_length_m=sum(route.original_length_m for route in routes),
        total_refined_length_m=sum(route.refined_length_m for route in routes),
    )


def _refine_physical_route(
    route: PhysicalRoute,
    cost_surface: CostSurface,
) -> RefinedPhysicalRoute:
    coordinates = tuple(
        (float(coordinate[0]), float(coordinate[1]))
        for coordinate in route.geometry.coords
    )
    if len(coordinates) < 2:
        raise ValueError("Physical route geometry must contain at least two points")
    if any(not all(math.isfinite(value) for value in point) for point in coordinates):
        raise ValueError("Physical route coordinates must be finite")

    for start, end in zip(coordinates, coordinates[1:], strict=False):
        if not _segment_is_traversable(start, end, cost_surface):
            raise ValueError(
                f"Physical route {route.start_node_id}-{route.end_node_id} "
                "contains a non-traversable segment"
            )

    without_duplicates = remove_duplicate_points(coordinates)
    if len(without_duplicates) < 2:
        raise ValueError("Cannot refine a route with coincident endpoints")

    without_collinear = remove_collinear_points(without_duplicates)
    original_integrated_cost = _polyline_traversal_cost(without_collinear, cost_surface)
    refined_coordinates = _shortcut_visible_points(without_collinear, cost_surface)
    refined_geometry = LineString(refined_coordinates)

    if not refined_geometry.is_valid or len(refined_geometry.coords) < 2:
        raise ValueError("Refinement did not produce a valid LineString")
    if refined_coordinates[0] != coordinates[0]:
        raise AssertionError("Route refinement changed the start coordinate")
    if refined_coordinates[-1] != coordinates[-1]:
        raise AssertionError("Route refinement changed the end coordinate")
    if refined_geometry.length > route.length_m + _LENGTH_TOLERANCE:
        raise ValueError("Refined route length exceeds the original route length")

    refined_cost = _polyline_traversal_cost(refined_coordinates, cost_surface)
    if not _cost_is_not_greater(refined_cost, original_integrated_cost):
        raise ValueError("Refined route traversal cost exceeds the original route cost")

    return RefinedPhysicalRoute(
        feeder_id=route.feeder_id,
        start_node_id=route.start_node_id,
        end_node_id=route.end_node_id,
        geometry=refined_geometry,
        original_length_m=route.length_m,
        refined_length_m=refined_geometry.length,
        original_traversal_cost=route.traversal_cost,
        refined_traversal_cost=refined_cost,
    )


def _is_redundant_collinear_point(
    start: Coordinate,
    middle: Coordinate,
    end: Coordinate,
    tolerance: float,
) -> bool:
    first_dx = middle[0] - start[0]
    first_dy = middle[1] - start[1]
    second_dx = end[0] - middle[0]
    second_dy = end[1] - middle[1]
    cross_product = first_dx * second_dy - first_dy * second_dx
    direction_dot_product = first_dx * second_dx + first_dy * second_dy
    return (
        math.isclose(cross_product, 0.0, rel_tol=0.0, abs_tol=tolerance)
        and direction_dot_product >= -tolerance
    )


def _world_to_grid_coordinates(
    coordinate: Coordinate,
    surface: CostSurface,
) -> Coordinate:
    col, row = ~surface.transform * coordinate
    return float(col), float(row)


def _segment_breakpoints(
    start_col: float,
    start_row: float,
    end_col: float,
    end_row: float,
) -> tuple[float, ...]:
    parameters = [0.0, 1.0]
    parameters.extend(_axis_breakpoints(start_col, end_col))
    parameters.extend(_axis_breakpoints(start_row, end_row))
    parameters.sort()

    unique_parameters: list[float] = []
    for parameter in parameters:
        if not unique_parameters or not math.isclose(
            parameter,
            unique_parameters[-1],
            rel_tol=0.0,
            abs_tol=_GRID_TOLERANCE,
        ):
            unique_parameters.append(parameter)
    return tuple(unique_parameters)


def _axis_breakpoints(start: float, end: float) -> list[float]:
    delta = end - start
    if math.isclose(delta, 0.0, rel_tol=0.0, abs_tol=_GRID_TOLERANCE):
        return []

    lower = min(start, end)
    upper = max(start, end)
    parameters = []
    for boundary in range(math.floor(lower), math.ceil(upper) + 1):
        parameter = (boundary - start) / delta
        if _GRID_TOLERANCE < parameter < 1.0 - _GRID_TOLERANCE:
            parameters.append(parameter)
    return parameters


def _cells_touching_grid_point(col: float, row: float) -> tuple[GridCell, ...]:
    columns = _indices_touching_axis_coordinate(col)
    rows = _indices_touching_axis_coordinate(row)
    return tuple((row_index, col_index) for row_index in rows for col_index in columns)


def _indices_touching_axis_coordinate(value: float) -> tuple[int, ...]:
    nearest_integer = round(value)
    if math.isclose(value, nearest_integer, rel_tol=0.0, abs_tol=_GRID_TOLERANCE):
        return nearest_integer - 1, nearest_integer
    return (math.floor(value),)


def _existing_cells_touching_grid_point(
    col: float,
    row: float,
    surface: CostSurface,
) -> tuple[GridCell, ...]:
    return tuple(
        (cell_row, cell_col)
        for cell_row, cell_col in _cells_touching_grid_point(col, row)
        if 0 <= cell_row < surface.height and 0 <= cell_col < surface.width
    )


def _segment_is_traversable(
    start: Coordinate,
    end: Coordinate,
    surface: CostSurface,
) -> bool:
    if not _coordinate_is_within_surface(start, surface):
        return False
    if not _coordinate_is_within_surface(end, surface):
        return False

    for row, col in segment_supercover_cells(start, end, surface):
        if not math.isfinite(float(surface.costs[row, col])):
            return False
    return True


def _coordinate_is_within_surface(
    coordinate: Coordinate,
    surface: CostSurface,
) -> bool:
    col, row = _world_to_grid_coordinates(coordinate, surface)
    return (
        -_GRID_TOLERANCE <= col <= surface.width + _GRID_TOLERANCE
        and -_GRID_TOLERANCE <= row <= surface.height + _GRID_TOLERANCE
    )


def _shortcut_visible_points(
    coordinates: tuple[Coordinate, ...],
    surface: CostSurface,
) -> tuple[Coordinate, ...]:
    refined = [coordinates[0]]
    anchor_index = 0
    segment_costs = tuple(
        _segment_traversal_cost(start, end, surface)
        for start, end in zip(coordinates, coordinates[1:], strict=False)
    )
    cumulative_costs = [0.0]
    for segment_cost in segment_costs:
        cumulative_costs.append(cumulative_costs[-1] + segment_cost)

    while anchor_index < len(coordinates) - 1:
        for candidate_index in range(len(coordinates) - 1, anchor_index, -1):
            start = coordinates[anchor_index]
            end = coordinates[candidate_index]
            if not _segment_is_traversable(start, end, surface):
                continue

            shortcut_cost = _segment_traversal_cost(start, end, surface)
            replaced_cost = (
                cumulative_costs[candidate_index] - cumulative_costs[anchor_index]
            )
            if not _cost_is_not_greater(shortcut_cost, replaced_cost):
                continue

            refined.append(end)
            anchor_index = candidate_index
            break
        else:
            raise ValueError(
                "Route refinement could not find a traversable, cost-preserving segment"
            )

    return tuple(refined)


def _segment_traversal_cost(
    start: Coordinate,
    end: Coordinate,
    surface: CostSurface,
) -> float:
    start_col, start_row = _world_to_grid_coordinates(start, surface)
    end_col, end_row = _world_to_grid_coordinates(end, surface)
    breakpoints = _segment_breakpoints(start_col, start_row, end_col, end_row)
    segment_length = math.dist(start, end)
    traversal_cost = 0.0

    for interval_start, interval_end in zip(breakpoints, breakpoints[1:], strict=False):
        midpoint = (interval_start + interval_end) / 2.0
        col = start_col + (end_col - start_col) * midpoint
        row = start_row + (end_row - start_row) * midpoint
        touched_cells = _existing_cells_touching_grid_point(col, row, surface)
        interval_cost = max(
            float(surface.costs[cell_row, cell_col])
            for cell_row, cell_col in touched_cells
        )
        traversal_cost += (
            segment_length * (interval_end - interval_start) * interval_cost
        )

    return traversal_cost


def _polyline_traversal_cost(
    coordinates: tuple[Coordinate, ...],
    surface: CostSurface,
) -> float:
    return sum(
        _segment_traversal_cost(start, end, surface)
        for start, end in zip(coordinates, coordinates[1:], strict=False)
    )


def _cost_is_not_greater(candidate: float, baseline: float) -> bool:
    return candidate <= baseline or math.isclose(
        candidate,
        baseline,
        rel_tol=1e-12,
        abs_tol=_COST_TOLERANCE,
    )
