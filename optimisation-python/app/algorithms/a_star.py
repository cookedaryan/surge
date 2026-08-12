import heapq
import math
from dataclasses import dataclass

import numpy as np

from app.gis.cost_surface import CostSurface

GridCell = tuple[int, int]


@dataclass(frozen=True)
class AStarResult:
    path: tuple[GridCell, ...]
    traversal_cost: float


def a_star(
    surface: CostSurface,
    start: GridCell,
    goal: GridCell,
    min_cost: float | None = None,
) -> AStarResult | None:
    start_r, start_c = start
    goal_r, goal_c = goal

    if not (0 <= start_r < surface.height and 0 <= start_c < surface.width):
        return None
    if not (0 <= goal_r < surface.height and 0 <= goal_c < surface.width):
        return None

    if math.isinf(surface.costs[start_r, start_c]) or math.isinf(
        surface.costs[goal_r, goal_c]
    ):
        return None

    if min_cost is None:
        valid_costs = surface.costs[np.isfinite(surface.costs)]
        if valid_costs.size == 0:
            min_cost = 1.0
        else:
            min_cost = float(np.min(valid_costs))

    def heuristic(r: int, c: int) -> float:
        return math.hypot(goal_r - r, goal_c - c) * surface.resolution_m * min_cost

    tie_breaker_counter = 0
    open_heap: list[tuple[float, float, int, GridCell]] = []

    g_score: dict[GridCell, float] = {start: 0.0}
    came_from: dict[GridCell, GridCell] = {}

    h_start = heuristic(start_r, start_c)
    heapq.heappush(open_heap, (h_start, h_start, tie_breaker_counter, start))

    closed_set: set[GridCell] = set()

    directions = [
        (-1, 0, False),
        (1, 0, False),
        (0, -1, False),
        (0, 1, False),
        (-1, -1, True),
        (-1, 1, True),
        (1, -1, True),
        (1, 1, True),
    ]

    while open_heap:
        _, _, _, current = heapq.heappop(open_heap)

        if current in closed_set:
            continue

        closed_set.add(current)

        if current == goal:
            path = []
            curr = current
            while curr in came_from:
                path.append(curr)
                curr = came_from[curr]
            path.append(start)
            path.reverse()
            return AStarResult(path=tuple(path), traversal_cost=g_score[goal])

        r, c = current
        current_g = g_score[current]

        for dr, dc, is_diagonal in directions:
            nr, nc = r + dr, c + dc

            if not (0 <= nr < surface.height and 0 <= nc < surface.width):
                continue

            neighbor = (nr, nc)
            dest_cost = float(surface.costs[nr, nc])

            if math.isinf(dest_cost):
                continue

            if is_diagonal:
                if math.isinf(surface.costs[r + dr, c]) or math.isinf(
                    surface.costs[r, c + dc]
                ):
                    continue

            dist = math.sqrt(2) if is_diagonal else 1.0
            move_cost = dist * surface.resolution_m * dest_cost

            tentative_g = current_g + move_cost

            if tentative_g < g_score.get(neighbor, math.inf):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h = heuristic(nr, nc)
                f = tentative_g + h

                tie_breaker_counter += 1
                heapq.heappush(open_heap, (f, h, tie_breaker_counter, neighbor))

    return None
