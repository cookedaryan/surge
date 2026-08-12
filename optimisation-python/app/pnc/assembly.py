"""PNC Network Assembly orchestrator.

Two public entry points
-----------------------
``build_pnc_network``
    Full pipeline: WTG grouping → graph → MST topology → A* routing →
    route refinement → PNC assembly.  Use when starting from raw project data.

``assemble_pnc_network``
    Assembly only: validates pre-computed topology and refined routes, then
    constructs and returns the ``ProjectPNCNetwork``.  No routing algorithms
    are executed.  Use when topology and routing have already been performed,
    for example inside ``OptimisationService``, to avoid repeating A* and
    refinement on data that is already available.

Separation of concerns
-----------------------
``build_pnc_network``    = algorithm orchestration  +  PNC assembly
``assemble_pnc_network`` = input validation          +  domain object construction

These are distinct responsibilities.  Mixing them into a single function with
an optional ``RefinedRoutingResult`` parameter creates ambiguity about which
stages run, whether ``cost_surface`` is still required, and whether the
supplied routes must originate from the internally generated topology.

Provenance limitation
----------------------
``RefinedRoutingResult`` currently carries no CRS, topology fingerprint, or
cost-surface identifier.  ``assemble_pnc_network`` therefore validates
structural compatibility (exact topology ↔ route correspondence, endpoint
membership, geometry integrity, aggregate totals) but cannot prove that routes
were produced from a specific cost surface.  This is acceptable and documented;
if reproducibility or caching later requires provenance, introduce a
``RoutingProvenance`` dataclass at the result level rather than burdening the
assembly boundary.
"""

import math
from typing import Any

import networkx as nx
from shapely.geometry import LineString, Point

from app.algorithms.physical_routing import route_collector_topology
from app.algorithms.route_graph import (
    build_project_graph,
    substation_node_id,
    turbine_node_id,
)
from app.algorithms.route_refinement import (
    RefinedPhysicalRoute,
    RefinedRoutingResult,
    refine_routing_result,
)
from app.algorithms.topology import (
    CollectorTopologyResult,
    build_feeder_mst,
)
from app.algorithms.wtg_grouping import group_wtgs
from app.gis.cost_surface import CostSurface
from app.models.spatial import ProjectSpatialData
from app.pnc.errors import PNCAssemblyError, PNCAssemblyErrorCode
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork

# Tolerance used when comparing geometry.length against refined_length_m.
# Matches the tolerance used in feeder_validation.py.
_LENGTH_TOLERANCE_M = 1e-3


# ---------------------------------------------------------------------------
# Public entry point 1 — full pipeline
# ---------------------------------------------------------------------------


def build_pnc_network(
    project_id: str,
    project: ProjectSpatialData,
    feeder_capacity_mw: float,
    cost_surface: CostSurface,
    graph: nx.Graph | None = None,
) -> ProjectPNCNetwork:
    """Run the complete pipeline and return a validated PNC network.

    Executes WTG grouping, MST topology, A* physical routing, route
    refinement, and then delegates to ``assemble_pnc_network``.

    Use this when starting from raw project data with no pre-computed
    intermediate results.  If topology and routing have already been executed,
    use ``assemble_pnc_network`` directly to avoid repeating those stages.

    Parameters
    ----------
    project_id:
        Caller-supplied identifier stored on the returned network.
    project:
        Spatial data (WTGs + substation) in a projected CRS.
    feeder_capacity_mw:
        Maximum electrical capacity per feeder used for WTG grouping.
    cost_surface:
        Raster cost surface used by A* physical routing.
    graph:
        Optional pre-built topology graph.  When *None* a complete candidate
        graph is built from ``project`` via ``build_project_graph``.

    Returns
    -------
    ProjectPNCNetwork

    Raises
    ------
    ValueError
        Raised by the underlying algorithm modules for invalid inputs.
    RouteNotFoundError
        Raised when A* cannot find a physical route for a topology edge.
    PNCAssemblyError
        Raised when the assembled network fails structural integrity checks.
    """
    grouping = group_wtgs(project, feeder_capacity_mw)

    if graph is None:
        graph = build_project_graph(project)

    topology = build_feeder_mst(graph, grouping)
    physical_routes = route_collector_topology(topology, graph, cost_surface)
    refined_routes = refine_routing_result(physical_routes, cost_surface)

    return assemble_pnc_network(
        project_id=project_id,
        project=project,
        topology=topology,
        refined_routes=refined_routes,
    )


# ---------------------------------------------------------------------------
# Public entry point 2 — assembly from pre-computed results
# ---------------------------------------------------------------------------


def assemble_pnc_network(
    project_id: str,
    project: ProjectSpatialData,
    topology: CollectorTopologyResult,
    refined_routes: RefinedRoutingResult,
) -> ProjectPNCNetwork:
    """Validate pre-computed topology and routes, then assemble a PNC network.

    No routing algorithms are executed.  The caller is responsible for ensuring
    that ``topology`` and ``refined_routes`` are compatible — that is, routes
    were produced from the same graph and cost surface used to build the
    topology.  Structural compatibility is verified; provenance cannot be
    proven without additional metadata at the result level.

    This is the entry point ``OptimisationService`` should use so that A* and
    route refinement are not repeated on already-computed data.

    Parameters
    ----------
    project_id:
        Caller-supplied identifier stored on the returned network.
    project:
        Spatial data (WTGs + substation).  Used to resolve WTG coordinates
        and validate topology coverage against the authoritative turbine list.
    topology:
        Collector topology produced by ``build_feeder_mst``.
    refined_routes:
        Physical routes produced by ``route_collector_topology`` and refined
        by ``refine_routing_result``.

    Returns
    -------
    ProjectPNCNetwork

    Raises
    ------
    PNCAssemblyError
        Raised when topology or routes fail structural or geometric validation.
    ValueError
        Raised for fundamentally malformed inputs (e.g. empty feeder list).
    """
    _validate_precomputed_routes(topology, refined_routes, project)
    return _build_pnc_network(project_id, project, topology, refined_routes)


# ---------------------------------------------------------------------------
# Pre-assembly validation
# ---------------------------------------------------------------------------


def _validate_precomputed_routes(
    topology: CollectorTopologyResult,
    refined: RefinedRoutingResult,
    project: ProjectSpatialData,
) -> None:
    """Exhaustively validate topology ↔ route correspondence before assembly.

    Checks performed
    ----------------
    Coverage
        All project WTGs appear in exactly one feeder (orphan + duplicate).
        Each feeder contains the project substation.

    Exact correspondence
        ``expected_edges == actual_edges`` using canonical keys
        ``(feeder_id, *sorted((u, v)))``.
        Missing, extra, wrong-feeder, and reversed-duplicate routes are all
        rejected.

    Endpoint membership
        Route start and end nodes must both appear in the feeder's node list.

    Geometry integrity
        Non-empty, valid, ≥ 2 coordinates, all coordinates finite.

    Length consistency
        ``refined_length_m`` must be positive, finite, and match
        ``geometry.length`` within ``_LENGTH_TOLERANCE_M``.

    Aggregate totals
        ``RefinedRoutingResult.total_refined_length_m`` must match the sum of
        individual route lengths within ``_LENGTH_TOLERANCE_M``.

    Raises ``PNCAssemblyError`` or ``ValueError`` on first failure.
    """
    if not topology.feeders:
        raise ValueError("Collector topology must contain at least one feeder")

    substation_id = substation_node_id(project.substation.substation_id)

    # --- 1. Feeder-level checks: no blank/duplicate IDs, substation present, --
    # ---    WTG coverage (orphan + duplicate assignment) ----------------------

    expected_wtg_ids = {
        turbine_node_id(t.turbine_id) for t in project.turbines
    }
    assigned_wtgs: set[str] = set()
    feeder_ids: set[str] = set()
    feeder_nodes: dict[str, set[str]] = {}

    for feeder in topology.feeders:
        if not feeder.feeder_id.strip():
            raise ValueError("Feeder ID cannot be blank")
        if feeder.feeder_id in feeder_ids:
            raise ValueError(
                f"Duplicate feeder ID in topology: {feeder.feeder_id!r}"
            )
        feeder_ids.add(feeder.feeder_id)

        node_set = set(feeder.node_ids)
        feeder_nodes[feeder.feeder_id] = node_set

        if substation_id not in node_set:
            raise PNCAssemblyError(
                PNCAssemblyErrorCode.FEEDER_WITHOUT_SUBSTATION_CONNECTION,
                f"Feeder {feeder.feeder_id!r} does not contain the substation "
                f"node {substation_id!r}.",
            )

        wtg_nodes = node_set - {substation_id}
        overlap = wtg_nodes & assigned_wtgs
        if overlap:
            raise PNCAssemblyError(
                PNCAssemblyErrorCode.DUPLICATE_WTG_ASSIGNMENT,
                f"WTG(s) {sorted(overlap)} appear in multiple feeders; "
                f"most recent offending feeder: {feeder.feeder_id!r}.",
            )
        assigned_wtgs.update(wtg_nodes)

    orphans = expected_wtg_ids - assigned_wtgs
    if orphans:
        raise PNCAssemblyError(
            PNCAssemblyErrorCode.ORPHAN_WTG,
            f"WTG(s) {sorted(orphans)} from the project are not assigned "
            f"to any feeder in the topology.",
        )

    # --- 2. Build expected canonical edge set --------------------------------

    expected_keys: set[tuple[str, str, str]] = set()
    for feeder in topology.feeders:
        for u, v in feeder.mst_edges:
            low, high = sorted((u, v))
            expected_keys.add((feeder.feeder_id, low, high))

    # --- 3. Validate each route and build actual canonical key set -----------

    # Maps canonical key → human-readable route identity string (for errors).
    actual_keys: dict[tuple[str, str, str], str] = {}

    for route in refined.routes:
        identity = (
            f"{route.feeder_id}/{route.start_node_id}-{route.end_node_id}"
        )

        # Geometry validity
        if not isinstance(route.geometry, LineString) or route.geometry.is_empty:
            raise PNCAssemblyError(
                PNCAssemblyErrorCode.UNROUTED_TOPOLOGY_EDGE,
                f"Route {identity}: geometry must be a non-empty LineString.",
            )
        coords = list(route.geometry.coords)
        if not route.geometry.is_valid or len(coords) < 2:
            raise PNCAssemblyError(
                PNCAssemblyErrorCode.UNROUTED_TOPOLOGY_EDGE,
                f"Route {identity}: geometry is invalid or has fewer than "
                f"2 coordinates.",
            )
        if any(
            not all(math.isfinite(c) for c in coord) for coord in coords
        ):
            raise PNCAssemblyError(
                PNCAssemblyErrorCode.UNROUTED_TOPOLOGY_EDGE,
                f"Route {identity}: geometry contains non-finite coordinates.",
            )

        # Length validity
        if (
            not math.isfinite(route.refined_length_m)
            or route.refined_length_m <= 0
        ):
            raise PNCAssemblyError(
                PNCAssemblyErrorCode.UNROUTED_TOPOLOGY_EDGE,
                f"Route {identity}: refined_length_m must be positive and "
                f"finite, got {route.refined_length_m}.",
            )
        if not math.isclose(
            route.geometry.length,
            route.refined_length_m,
            rel_tol=0.0,
            abs_tol=_LENGTH_TOLERANCE_M,
        ):
            raise PNCAssemblyError(
                PNCAssemblyErrorCode.UNROUTED_TOPOLOGY_EDGE,
                f"Route {identity}: geometry.length "
                f"({route.geometry.length:.6f} m) is inconsistent with "
                f"refined_length_m ({route.refined_length_m:.6f} m).",
            )

        # Route feeder must be known
        if route.feeder_id not in feeder_ids:
            raise PNCAssemblyError(
                PNCAssemblyErrorCode.UNKNOWN_FEEDER_SEGMENT,
                f"Route {identity}: feeder_id {route.feeder_id!r} does not "
                f"exist in the topology.",
            )

        # Endpoint membership
        nodes = feeder_nodes[route.feeder_id]
        if route.start_node_id not in nodes:
            raise PNCAssemblyError(
                PNCAssemblyErrorCode.UNKNOWN_FEEDER_SEGMENT,
                f"Route {identity}: start_node_id {route.start_node_id!r} "
                f"is not in feeder {route.feeder_id!r} topology.",
            )
        if route.end_node_id not in nodes:
            raise PNCAssemblyError(
                PNCAssemblyErrorCode.UNKNOWN_FEEDER_SEGMENT,
                f"Route {identity}: end_node_id {route.end_node_id!r} "
                f"is not in feeder {route.feeder_id!r} topology.",
            )

        # Duplicate detection — catches both same-order and reversed duplicates
        low, high = sorted((route.start_node_id, route.end_node_id))
        key = (route.feeder_id, low, high)
        if key in actual_keys:
            raise PNCAssemblyError(
                PNCAssemblyErrorCode.DUPLICATE_SEGMENT_ID,
                f"Duplicate route for feeder edge {key}: "
                f"already have {actual_keys[key]!r}, "
                f"also got {identity!r}.",
            )
        actual_keys[key] = identity

    # --- 4. Missing routes (topology edge with no route) --------------------

    missing = expected_keys - set(actual_keys)
    if missing:
        fid, low, high = sorted(missing)[0]
        raise PNCAssemblyError(
            PNCAssemblyErrorCode.UNROUTED_TOPOLOGY_EDGE,
            f"Feeder {fid!r}: topology edge ({low!r} → {high!r}) has no "
            f"corresponding physical route.",
        )

    # --- 5. Extra routes (route with no matching topology edge) -------------

    extra = set(actual_keys) - expected_keys
    if extra:
        fid, low, high = sorted(extra)[0]
        raise PNCAssemblyError(
            PNCAssemblyErrorCode.UNKNOWN_FEEDER_SEGMENT,
            f"Extra physical route not present in topology: feeder {fid!r}, "
            f"edge ({low!r} → {high!r}).",
        )

    # --- 6. Aggregate total consistency ------------------------------------

    computed_total = math.fsum(r.refined_length_m for r in refined.routes)
    if not math.isfinite(refined.total_refined_length_m) or not math.isclose(
        computed_total,
        refined.total_refined_length_m,
        rel_tol=0.0,
        abs_tol=_LENGTH_TOLERANCE_M,
    ):
        raise ValueError(
            f"RefinedRoutingResult.total_refined_length_m "
            f"({refined.total_refined_length_m:.6f}) does not match the sum "
            f"of individual route lengths ({computed_total:.6f}).",
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalise_feeder_id(raw_feeder_id: str, index: int) -> str:
    """Convert an algorithm feeder ID (e.g. 'F1') to 'FDR-001'."""
    return f"FDR-{index + 1:03d}"


def _feeder_suffix(normalised_feeder_id: str) -> str:
    """Extract the zero-padded numeric suffix, e.g. 'FDR-001' → 'FDR001'."""
    return normalised_feeder_id.replace("-", "")


def _bfs_ordered_nodes(
    mst_graph: nx.Graph, substation_id: str
) -> tuple[str, ...]:
    """Return a deterministic BFS traversal from *substation_id*.

    Neighbours are sorted lexicographically at every level so that the output
    is stable given identical topology.  The graph itself is never modified.
    """
    visited: list[str] = []
    queue: list[str] = [substation_id]
    seen: set[str] = {substation_id}
    while queue:
        node = queue.pop(0)
        visited.append(node)
        for neighbour in sorted(mst_graph.neighbors(node)):
            if neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    return tuple(visited)


def _segment_type(from_node_id: str, to_node_id: str, substation_id: str) -> str:
    """Derive segment_type from the participating node IDs."""
    if from_node_id == substation_id or to_node_id == substation_id:
        return "substation_to_wtg"
    return "wtg_to_wtg"


def _build_route_lookup(
    refined: RefinedRoutingResult,
) -> dict[tuple[str, str, str], RefinedPhysicalRoute]:
    """Index routes by (feeder_id, canonical_low_node, canonical_high_node).

    Canonical order is lexicographic so lookups are direction-agnostic.
    Assumes ``_validate_precomputed_routes`` has already confirmed there are
    no duplicates; asserts the invariant defensively.
    """
    lookup: dict[tuple[str, str, str], RefinedPhysicalRoute] = {}
    for route in refined.routes:
        key = (route.feeder_id, *sorted((route.start_node_id, route.end_node_id)))
        assert key not in lookup, (
            f"Duplicate route key {key} reached _build_route_lookup — "
            "this should have been caught by _validate_precomputed_routes."
        )
        lookup[key] = route
    return lookup


def _reverse_linestring(line: Any) -> LineString:
    """Return a new LineString with coordinate order reversed."""
    return LineString(list(reversed(list(line.coords))))


def _collect_wtg_coordinates(
    wtg_node_ids: tuple[str, ...],
    project: ProjectSpatialData,
    wtg_coordinates: dict[str, Point],
) -> None:
    """Populate *wtg_coordinates* from the project turbine list."""
    turbine_map = {
        turbine_node_id(t.turbine_id): t.location for t in project.turbines
    }
    for node_id in wtg_node_ids:
        if node_id not in wtg_coordinates:
            # _validate_precomputed_routes has already verified coverage;
            # this branch is a defensive guard only.
            if node_id not in turbine_map:
                raise PNCAssemblyError(
                    PNCAssemblyErrorCode.ORPHAN_WTG,
                    f"WTG node {node_id!r} is in the topology but has no "
                    f"matching turbine in the project spatial data.",
                )
            wtg_coordinates[node_id] = turbine_map[node_id]


def _build_pnc_network(
    project_id: str,
    project: ProjectSpatialData,
    topology: CollectorTopologyResult,
    refined: RefinedRoutingResult,
) -> ProjectPNCNetwork:
    """Construct and return a ``ProjectPNCNetwork`` from validated inputs.

    Callers must invoke ``_validate_precomputed_routes`` before calling this
    function.  This function does not re-validate inputs; it constructs domain
    objects and performs a final post-assembly sanity check only.
    """
    substation_id = substation_node_id(project.substation.substation_id)
    route_lookup = _build_route_lookup(refined)

    sorted_topology_feeders = sorted(topology.feeders, key=lambda f: f.feeder_id)

    feeder_id_map: dict[str, str] = {
        ft.feeder_id: _normalise_feeder_id(ft.feeder_id, idx)
        for idx, ft in enumerate(sorted_topology_feeders)
    }

    pnc_feeders: list[PNCFeeder] = []
    all_segment_ids: list[str] = []
    wtg_coordinates: dict[str, Point] = {}

    for ft in sorted_topology_feeders:
        normalised_id = feeder_id_map[ft.feeder_id]
        suffix = _feeder_suffix(normalised_id)

        wtg_ids = tuple(sorted(n for n in ft.node_ids if n != substation_id))
        _collect_wtg_coordinates(wtg_ids, project, wtg_coordinates)

        sorted_edges = sorted(ft.mst_edges, key=lambda e: (e[0], e[1]))

        segments: list[PNCSegment] = []
        for seg_idx, (u, v) in enumerate(sorted_edges):
            canonical_key = (ft.feeder_id, *sorted((u, v)))
            route = route_lookup[canonical_key]

            seg_id = f"SEG-{suffix}-{seg_idx + 1:04d}"
            all_segment_ids.append(seg_id)

            seg_type = _segment_type(u, v, substation_id)
            geom = (
                route.geometry
                if route.start_node_id == u
                else _reverse_linestring(route.geometry)
            )

            segments.append(
                PNCSegment(
                    segment_id=seg_id,
                    feeder_id=normalised_id,
                    from_node_id=u,
                    to_node_id=v,
                    route_geometry=geom,
                    route_length_m=route.refined_length_m,
                    segment_type=seg_type,  # type: ignore[arg-type]
                )
            )

        ordered_nodes = _bfs_ordered_nodes(ft.mst_graph, substation_id)
        total_feeder_length = math.fsum(s.route_length_m for s in segments)

        pnc_feeders.append(
            PNCFeeder(
                feeder_id=normalised_id,
                substation_id=substation_id,
                wtg_ids=wtg_ids,
                ordered_node_ids=ordered_nodes,
                segments=tuple(segments),
                total_length_m=total_feeder_length,
                mst_graph=ft.mst_graph,
            )
        )

    substation_geometry = project.substation.location
    total_length = math.fsum(f.total_length_m for f in pnc_feeders)
    route_length_by_feeder = {f.feeder_id: f.total_length_m for f in pnc_feeders}
    wtg_count_by_feeder = {f.feeder_id: len(f.wtg_ids) for f in pnc_feeders}

    return ProjectPNCNetwork(
        project_id=project_id,
        substation_id=substation_id,
        substation_geometry=substation_geometry,
        feeders=tuple(pnc_feeders),
        wtg_coordinates=wtg_coordinates,
        total_route_length_m=total_length,
        feeder_count=len(pnc_feeders),
        wtg_count=len(wtg_coordinates),
        segment_count=len(all_segment_ids),
        crs=project.projected_crs,
        route_length_by_feeder=route_length_by_feeder,
        wtg_count_by_feeder=wtg_count_by_feeder,
    )
