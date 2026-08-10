import math
from dataclasses import dataclass

import networkx as nx
from shapely.geometry import LineString

from app.algorithms.a_star import a_star
from app.algorithms.topology import CollectorTopologyResult
from app.gis.cost_surface import CostSurface, grid_to_world, world_to_grid


class RouteNotFoundError(RuntimeError):
    def __init__(self, feeder_id: str, start_node_id: str, end_node_id: str, reason: str):
        super().__init__(
            f"Route not found for feeder {feeder_id} between {start_node_id} "
            f"and {end_node_id}: {reason}"
        )
        self.feeder_id = feeder_id
        self.start_node_id = start_node_id
        self.end_node_id = end_node_id
        self.reason = reason


@dataclass(frozen=True)
class PhysicalRoute:
    feeder_id: str
    start_node_id: str
    end_node_id: str
    geometry: LineString
    length_m: float
    traversal_cost: float


@dataclass(frozen=True)
class PhysicalRoutingResult:
    routes: tuple[PhysicalRoute, ...]
    total_length_m: float
    total_traversal_cost: float


def route_collector_topology(
    topology: CollectorTopologyResult,
    graph: nx.Graph,
    cost_surface: CostSurface,
) -> PhysicalRoutingResult:
    Translates electrical MST edges into physical LineString paths using A*
    across the CostSurface.
    """
    routes = []
    
    for feeder in topology.feeders:
        for u, v in feeder.mst_edges:
            start_geom = graph.nodes[u]["geometry"]
            end_geom = graph.nodes[v]["geometry"]
            
            start_cell = world_to_grid(start_geom.x, start_geom.y, cost_surface)
            goal_cell = world_to_grid(end_geom.x, end_geom.y, cost_surface)
            
            # Check bounds for start_cell and goal_cell
            if not (
                0 <= start_cell[0] < cost_surface.height
                and 0 <= start_cell[1] < cost_surface.width
            ):
                raise RouteNotFoundError(
                    feeder.feeder_id, u, v, "start cell is out of bounds"
                )
            if not (
                0 <= goal_cell[0] < cost_surface.height
                and 0 <= goal_cell[1] < cost_surface.width
            ):
                raise RouteNotFoundError(
                    feeder.feeder_id, u, v, "goal cell is out of bounds"
                )
            
            # Pre-validate start and goal cells are traversable
            if math.isinf(cost_surface.costs[start_cell[0], start_cell[1]]):
                raise RouteNotFoundError(
                    feeder.feeder_id, u, v, "start cell is blocked"
                )
            if math.isinf(cost_surface.costs[goal_cell[0], goal_cell[1]]):
                raise RouteNotFoundError(
                    feeder.feeder_id, u, v, "goal cell is blocked"
                )
                
            res = a_star(cost_surface, start_cell, goal_cell)
            if res is None:
                raise RouteNotFoundError(feeder.feeder_id, u, v, "no path found")
                
            path_coords = []
            
            # The first point is the exact start coordinate
            path_coords.append((start_geom.x, start_geom.y))
            
            # Include intermediate grid centers
            # (skip first and last grid cell centers since we use exact coords)
            for i in range(1, len(res.path) - 1):
                r, c = res.path[i]
                wx, wy = grid_to_world(r, c, cost_surface)
                path_coords.append((wx, wy))
                
            # The last point is the exact end coordinate
            if len(res.path) > 1:
                path_coords.append((end_geom.x, end_geom.y))
                
            geometry = LineString(path_coords)
            
            routes.append(
                PhysicalRoute(
                    feeder_id=feeder.feeder_id,
                    start_node_id=u,
                    end_node_id=v,
                    geometry=geometry,
                    length_m=geometry.length,
                    traversal_cost=res.traversal_cost,
                )
            )
            
    total_len = sum(r.length_m for r in routes)
    total_cost = sum(r.traversal_cost for r in routes)
    
    return PhysicalRoutingResult(
        routes=tuple(routes),
        total_length_m=total_len,
        total_traversal_cost=total_cost,
    )
