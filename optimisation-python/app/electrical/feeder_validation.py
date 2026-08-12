"""Deterministic radial-collector electrical feasibility screening."""

import math
from collections.abc import Iterable
from typing import TypeAlias

import networkx as nx
from pyproj import CRS
from shapely.geometry import LineString, Point

from app.algorithms.route_graph import substation_node_id, turbine_node_id
from app.algorithms.route_refinement import RefinedPhysicalRoute, RefinedRoutingResult
from app.algorithms.topology import CollectorTopologyResult, FeederTopology
from app.electrical.models import (
    ElectricalDesignConfig,
    ElectricalSegmentResult,
    ElectricalValidationResult,
    ElectricalViolation,
    FeederElectricalResult,
    TurbineElectricalResult,
)
from app.electrical.voltage_drop import (
    calculate_segment_impedance,
    calculate_three_phase_current_a,
    calculate_voltage_change,
)
from app.models.spatial import ProjectSpatialData

EdgeKey: TypeAlias = tuple[str, str]
RouteKey: TypeAlias = tuple[str, EdgeKey]

_LENGTH_TOLERANCE_M = 1e-3
_ENDPOINT_TOLERANCE_M = 1e-6
_LIMIT_TOLERANCE = 1e-9
_CAPACITY_TOLERANCE_MW = 1e-6


def _edge_key(first: str, second: str) -> EdgeKey:
    """Return a canonical key for one undirected topology edge."""

    low, high = sorted((first, second))
    return low, high


def calculate_downstream_active_power_mw(
    tree: nx.DiGraph,
    wtg_capacities: dict[str, float],
) -> dict[EdgeKey, float]:
    """Return downstream active power for every edge in a rooted arborescence."""

    if tree.number_of_nodes() == 0 or not nx.is_arborescence(tree):
        raise ValueError("tree must be a non-empty rooted arborescence")
    unknown_capacity_nodes = set(wtg_capacities).difference(tree.nodes)
    if unknown_capacity_nodes:
        unknown = ", ".join(sorted(unknown_capacity_nodes))
        raise ValueError(f"Capacity supplied for node outside tree: {unknown}")
    for node_id, capacity_mw in wtg_capacities.items():
        if (
            isinstance(capacity_mw, bool)
            or not isinstance(capacity_mw, (int, float))
            or not math.isfinite(capacity_mw)
            or capacity_mw < 0
        ):
            raise ValueError(f"WTG {node_id} capacity must be finite and non-negative")

    edge_power: dict[EdgeKey, float] = {}
    node_power: dict[str, float] = {}
    postorder = reversed(list(nx.lexicographical_topological_sort(tree, key=str)))
    for node in postorder:
        power = wtg_capacities.get(str(node), 0.0)
        for child in tree.successors(node):
            power += node_power[str(child)]
        node_id = str(node)
        node_power[node_id] = power
        predecessors = list(tree.predecessors(node))
        if predecessors:
            edge_power[(str(predecessors[0]), node_id)] = power
    return edge_power


def validate_collector_network(
    topology: CollectorTopologyResult,
    routing: RefinedRoutingResult,
    project: ProjectSpatialData,
    electrical_config: ElectricalDesignConfig,
) -> ElectricalValidationResult:
    """Validate one complete radial collector network at a fixed operating point.

    Malformed or mutually inconsistent inputs raise ``ValueError``. Valid inputs
    that exceed an electrical design limit return explicit violations instead.
    This is a linear screening proxy, not a nonlinear load-flow calculation.
    """

    _validate_metric_crs(project.projected_crs)
    substation_id = substation_node_id(project.substation.substation_id)
    capacities, node_locations = _project_nodes(project, substation_id)
    route_map = _build_route_map(routing, node_locations)
    feeders = tuple(sorted(topology.feeders, key=lambda feeder: feeder.feeder_id))
    if not feeders:
        raise ValueError("Collector topology must contain at least one feeder")

    expected_routes, installed_feeder_power = _validate_topology(
        feeders,
        substation_id,
        capacities,
    )
    _validate_route_coverage(expected_routes, route_map)

    operating_capacities = {
        node_id: capacity * electrical_config.operating_factor
        for node_id, capacity in capacities.items()
    }
    feeder_results = tuple(
        _evaluate_feeder(
            feeder,
            substation_id,
            installed_feeder_power[feeder.feeder_id],
            operating_capacities,
            route_map,
            electrical_config,
        )
        for feeder in feeders
    )
    violations = [
        violation
        for feeder_result in feeder_results
        for violation in feeder_result.violations
    ]

    total_operating_power_mw = math.fsum(operating_capacities.values())
    capacity_mw = project.substation.capacity_mw
    if capacity_mw is not None:
        _validate_positive_capacity("Substation", capacity_mw)
        if total_operating_power_mw - capacity_mw > _LIMIT_TOLERANCE:
            violations.append(
                ElectricalViolation(
                    code="SUBSTATION_CAPACITY_EXCEEDED",
                    feeder_id="",
                    node_id=substation_id,
                    edge=None,
                    measured_value=total_operating_power_mw,
                    limit_value=capacity_mw,
                )
            )

    return ElectricalValidationResult(
        feeders=feeder_results,
        maximum_voltage_deviation_percent=max(
            (feeder.maximum_voltage_deviation_percent for feeder in feeder_results),
            default=0.0,
        ),
        maximum_loading_percent=max(
            (feeder.maximum_loading_percent for feeder in feeder_results),
            default=0.0,
        ),
        is_valid=not violations,
        violations=tuple(violations),
    )


def _validate_metric_crs(crs: CRS) -> None:
    try:
        normalized = CRS.from_user_input(crs)
    except Exception as exc:
        raise ValueError("Project CRS must be valid") from exc
    if not normalized.is_projected:
        raise ValueError("Electrical route lengths require a projected CRS")
    if len(normalized.axis_info) < 2 or any(
        not math.isclose(
            axis.unit_conversion_factor,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        for axis in normalized.axis_info[:2]
    ):
        raise ValueError("Electrical route lengths require CRS axes in metres")


def _project_nodes(
    project: ProjectSpatialData,
    substation_id: str,
) -> tuple[dict[str, float], dict[str, Point]]:
    if not project.turbines:
        raise ValueError("Project must contain at least one WTG")
    locations = {substation_id: project.substation.location}
    _validate_point(substation_id, project.substation.location)
    capacities: dict[str, float] = {}
    for turbine in project.turbines:
        node_id = turbine_node_id(turbine.turbine_id)
        if node_id in capacities:
            raise ValueError(f"Duplicate WTG node ID: {node_id}")
        if turbine.capacity_mw is None:
            raise ValueError(f"WTG {turbine.turbine_id} capacity is missing")
        _validate_positive_capacity(f"WTG {turbine.turbine_id}", turbine.capacity_mw)
        _validate_point(node_id, turbine.location)
        capacities[node_id] = turbine.capacity_mw
        locations[node_id] = turbine.location
    return capacities, locations


def _validate_positive_capacity(subject: str, capacity_mw: float) -> None:
    if (
        isinstance(capacity_mw, bool)
        or not isinstance(capacity_mw, (int, float))
        or not math.isfinite(capacity_mw)
        or capacity_mw <= 0
    ):
        raise ValueError(f"{subject} capacity must be finite and positive")


def _validate_point(node_id: str, point: Point) -> None:
    if not isinstance(point, Point) or point.is_empty:
        raise ValueError(f"Node {node_id} must have a non-empty Point location")
    if any(not math.isfinite(value) for value in point.coords[0]):
        raise ValueError(f"Node {node_id} coordinates must be finite")


def _build_route_map(
    routing: RefinedRoutingResult,
    node_locations: dict[str, Point],
) -> dict[RouteKey, RefinedPhysicalRoute]:
    routes: dict[RouteKey, RefinedPhysicalRoute] = {}
    for route in routing.routes:
        _validate_route(route, node_locations)
        key = (route.feeder_id, _edge_key(route.start_node_id, route.end_node_id))
        if key in routes:
            raise ValueError(f"Duplicate physical route for feeder/edge {key}")
        routes[key] = route

    total_refined_length = math.fsum(
        route.refined_length_m for route in routes.values()
    )
    if not math.isfinite(routing.total_refined_length_m) or not math.isclose(
        total_refined_length,
        routing.total_refined_length_m,
        rel_tol=0.0,
        abs_tol=_LENGTH_TOLERANCE_M,
    ):
        raise ValueError("Routing total_refined_length_m does not match its routes")
    return routes


def _validate_route(
    route: RefinedPhysicalRoute,
    node_locations: dict[str, Point],
) -> None:
    identity = f"{route.start_node_id}-{route.end_node_id}"
    if not route.feeder_id.strip():
        raise ValueError(f"Route {identity} has a blank feeder ID")
    if route.start_node_id == route.end_node_id:
        raise ValueError(f"Route {identity} is a self-loop")
    if (
        route.start_node_id not in node_locations
        or route.end_node_id not in node_locations
    ):
        raise ValueError(f"Route {identity} references an unknown project node")
    if not isinstance(route.geometry, LineString) or route.geometry.is_empty:
        raise ValueError(f"Route {identity} geometry must be a non-empty LineString")
    if not route.geometry.is_valid or len(route.geometry.coords) < 2:
        raise ValueError(f"Route {identity} geometry is invalid")
    if any(
        not all(math.isfinite(value) for value in coordinate)
        for coordinate in route.geometry.coords
    ):
        raise ValueError(f"Route {identity} coordinates must be finite")
    if not math.isfinite(route.refined_length_m) or route.refined_length_m <= 0:
        raise ValueError(f"Route {identity} has invalid refined length")
    if not math.isclose(
        route.geometry.length,
        route.refined_length_m,
        rel_tol=0.0,
        abs_tol=_LENGTH_TOLERANCE_M,
    ):
        raise ValueError(f"Route {identity} geometry length mismatch")

    start = Point(route.geometry.coords[0])
    end = Point(route.geometry.coords[-1])
    if start.distance(node_locations[route.start_node_id]) > _ENDPOINT_TOLERANCE_M:
        raise ValueError(f"Route {identity} start does not match its project node")
    if end.distance(node_locations[route.end_node_id]) > _ENDPOINT_TOLERANCE_M:
        raise ValueError(f"Route {identity} end does not match its project node")


def _validate_topology(
    feeders: tuple[FeederTopology, ...],
    substation_id: str,
    capacities: dict[str, float],
) -> tuple[set[RouteKey], dict[str, float]]:
    feeder_ids: set[str] = set()
    assigned_wtgs: set[str] = set()
    expected_routes: set[RouteKey] = set()
    installed_power: dict[str, float] = {}

    for feeder in feeders:
        if not feeder.feeder_id.strip():
            raise ValueError("Feeder ID cannot be blank")
        if feeder.feeder_id in feeder_ids:
            raise ValueError(f"Duplicate feeder ID: {feeder.feeder_id}")
        feeder_ids.add(feeder.feeder_id)
        node_ids = tuple(feeder.node_ids)
        if len(node_ids) != len(set(node_ids)):
            raise ValueError(f"Feeder {feeder.feeder_id} contains duplicate node IDs")
        if node_ids.count(substation_id) != 1:
            raise ValueError(
                f"Feeder {feeder.feeder_id} must contain exactly one substation node"
            )
        graph = feeder.mst_graph
        if graph.is_directed() or graph.number_of_nodes() == 0 or not nx.is_tree(graph):
            raise ValueError(
                f"Feeder {feeder.feeder_id} graph must be an undirected tree"
            )
        if set(graph.nodes) != set(node_ids):
            raise ValueError(
                f"Feeder {feeder.feeder_id} node_ids do not match graph nodes"
            )
        graph_edges = {_edge_key(str(u), str(v)) for u, v in graph.edges}
        declared_edges = {_edge_key(*edge) for edge in feeder.mst_edges}
        if (
            len(declared_edges) != len(feeder.mst_edges)
            or declared_edges != graph_edges
        ):
            raise ValueError(
                f"Feeder {feeder.feeder_id} mst_edges do not match its graph"
            )

        turbine_nodes = set(node_ids).difference({substation_id})
        unknown = turbine_nodes.difference(capacities)
        if unknown:
            raise ValueError(
                f"Feeder {feeder.feeder_id} contains unknown WTG nodes: "
                f"{', '.join(sorted(unknown))}"
            )
        duplicate_assignments = turbine_nodes.intersection(assigned_wtgs)
        if duplicate_assignments:
            raise ValueError(
                "WTGs appear in multiple feeders: "
                f"{', '.join(sorted(duplicate_assignments))}"
            )
        assigned_wtgs.update(turbine_nodes)

        capacity_mw = math.fsum(capacities[node] for node in turbine_nodes)
        if not math.isfinite(feeder.total_capacity_mw) or not math.isclose(
            capacity_mw,
            feeder.total_capacity_mw,
            rel_tol=0.0,
            abs_tol=_CAPACITY_TOLERANCE_MW,
        ):
            raise ValueError(f"Feeder {feeder.feeder_id} capacity mismatch")
        installed_power[feeder.feeder_id] = capacity_mw
        expected_routes.update((feeder.feeder_id, edge) for edge in graph_edges)

    if assigned_wtgs != set(capacities):
        missing = set(capacities).difference(assigned_wtgs)
        raise ValueError(
            f"Project WTGs missing from topology: {', '.join(sorted(missing))}"
        )
    return expected_routes, installed_power


def _validate_route_coverage(
    expected: set[RouteKey],
    actual: dict[RouteKey, RefinedPhysicalRoute],
) -> None:
    missing = expected.difference(actual)
    if missing:
        raise ValueError(f"Missing physical route for feeder/edge {sorted(missing)[0]}")
    extra = set(actual).difference(expected)
    if extra:
        raise ValueError(
            f"Extra physical route not present in topology: {sorted(extra)[0]}"
        )


def _root_tree(feeder: FeederTopology, substation_id: str) -> nx.DiGraph:
    rooted = nx.bfs_tree(
        feeder.mst_graph,
        source=substation_id,
        sort_neighbors=lambda nodes: sorted(nodes, key=str),
    )
    return nx.DiGraph(rooted)


def _evaluate_feeder(
    feeder: FeederTopology,
    substation_id: str,
    installed_power_mw: float,
    operating_capacities: dict[str, float],
    route_map: dict[RouteKey, RefinedPhysicalRoute],
    config: ElectricalDesignConfig,
) -> FeederElectricalResult:
    rooted = _root_tree(feeder, substation_id)
    feeder_capacities = {
        node: operating_capacities[node]
        for node in feeder.node_ids
        if node != substation_id
    }
    edge_power = calculate_downstream_active_power_mw(rooted, feeder_capacities)
    segments: list[ElectricalSegmentResult] = []
    violations: list[ElectricalViolation] = []
    edge_voltage_change: dict[EdgeKey, float] = {}

    for parent, child in rooted.edges:
        parent_id, child_id = str(parent), str(child)
        route = route_map[(feeder.feeder_id, _edge_key(parent_id, child_id))]
        downstream_mw = edge_power[(parent_id, child_id)]
        current_a = calculate_three_phase_current_a(
            downstream_mw,
            config.nominal_line_voltage_kv,
            config.power_factor,
        )
        impedance = calculate_segment_impedance(
            route.refined_length_m,
            config.conductor.resistance_ohm_per_km,
            config.conductor.reactance_ohm_per_km,
        )
        voltage = calculate_voltage_change(
            current_a,
            impedance,
            config.power_factor,
            config.power_factor_mode,
            config.nominal_line_voltage_kv,
        )
        loading_percent = current_a / config.conductor.ampacity_a * 100.0
        exceeded = current_a - config.conductor.ampacity_a > _LIMIT_TOLERANCE
        edge = (parent_id, child_id)
        if exceeded:
            violations.append(
                ElectricalViolation(
                    code="AMPACITY_EXCEEDED",
                    feeder_id=feeder.feeder_id,
                    node_id=None,
                    edge=edge,
                    measured_value=current_a,
                    limit_value=config.conductor.ampacity_a,
                )
            )
        segments.append(
            ElectricalSegmentResult(
                feeder_id=feeder.feeder_id,
                parent_node_id=parent_id,
                child_node_id=child_id,
                route_length_m=route.refined_length_m,
                downstream_active_power_mw=downstream_mw,
                current_a=current_a,
                impedance=impedance,
                voltage_change_v=voltage.voltage_change_v,
                voltage_change_percent=voltage.voltage_change_percent,
                ampacity_a=config.conductor.ampacity_a,
                loading_percent=loading_percent,
                ampacity_exceeded=exceeded,
            )
        )
        edge_voltage_change[edge] = voltage.voltage_change_v

    turbines = _evaluate_turbines(
        feeder,
        rooted,
        substation_id,
        operating_capacities,
        edge_voltage_change,
        config,
        violations,
    )
    worst_turbine = max(
        turbines,
        key=lambda turbine: (
            abs(turbine.cumulative_voltage_change_percent),
            turbine.turbine_node_id,
        ),
        default=None,
    )
    most_loaded_segment = max(
        segments,
        key=lambda segment: (
            segment.loading_percent,
            segment.parent_node_id,
            segment.child_node_id,
        ),
        default=None,
    )
    return FeederElectricalResult(
        feeder_id=feeder.feeder_id,
        substation_node_id=substation_id,
        total_active_power_mw=installed_power_mw * config.operating_factor,
        segments=tuple(segments),
        turbines=turbines,
        maximum_voltage_deviation_percent=(
            abs(worst_turbine.cumulative_voltage_change_percent)
            if worst_turbine is not None
            else 0.0
        ),
        maximum_loading_percent=(
            most_loaded_segment.loading_percent
            if most_loaded_segment is not None
            else 0.0
        ),
        worst_voltage_turbine_id=(
            worst_turbine.turbine_node_id if worst_turbine is not None else None
        ),
        most_loaded_edge=(
            (
                most_loaded_segment.parent_node_id,
                most_loaded_segment.child_node_id,
            )
            if most_loaded_segment is not None
            else None
        ),
        is_valid=not violations,
        violations=tuple(violations),
    )


def _evaluate_turbines(
    feeder: FeederTopology,
    rooted: nx.DiGraph,
    substation_id: str,
    operating_capacities: dict[str, float],
    edge_voltage_change: dict[EdgeKey, float],
    config: ElectricalDesignConfig,
    violations: list[ElectricalViolation],
) -> tuple[TurbineElectricalResult, ...]:
    results: list[TurbineElectricalResult] = []
    nominal_voltage_v = config.nominal_line_voltage_kv * 1000.0
    turbine_nodes: Iterable[str] = sorted(
        set(feeder.node_ids).difference({substation_id})
    )
    for node_id in turbine_nodes:
        path = tuple(nx.shortest_path(rooted, substation_id, node_id))
        cumulative_change_v = math.fsum(
            edge_voltage_change[(path[index], path[index + 1])]
            for index in range(len(path) - 1)
        )
        cumulative_percent = cumulative_change_v / nominal_voltage_v * 100.0
        deviation = abs(cumulative_percent)
        exceeded = deviation - config.max_voltage_deviation_percent > _LIMIT_TOLERANCE
        if exceeded:
            violations.append(
                ElectricalViolation(
                    code="VOLTAGE_LIMIT_EXCEEDED",
                    feeder_id=feeder.feeder_id,
                    node_id=node_id,
                    edge=None,
                    measured_value=deviation,
                    limit_value=config.max_voltage_deviation_percent,
                )
            )
        results.append(
            TurbineElectricalResult(
                feeder_id=feeder.feeder_id,
                turbine_node_id=node_id,
                active_power_mw=operating_capacities[node_id],
                path_from_substation=path,
                cumulative_voltage_change_v=cumulative_change_v,
                cumulative_voltage_change_percent=cumulative_percent,
                estimated_terminal_voltage_v=nominal_voltage_v - cumulative_change_v,
                voltage_limit_exceeded=exceeded,
            )
        )
    return tuple(results)
