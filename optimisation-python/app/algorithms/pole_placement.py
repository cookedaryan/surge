"""
SURGE-PY-010/PY-023 — Route-Local Placement and Network Endpoint Deduplication

Converts each RefinedPhysicalRoute into an ordered sequence of physical pole
structures suitable for an overhead collector network.

Pipeline position:
    Refined LineString  →  Pole Placement Engine  →  PoleRouteResult

Design decisions
----------------
* Pole IDs use the raw feeder_id string as supplied by upstream (e.g. "F1").
  Within a single route they are ``{feeder_id}-P{sequence:03d}``.  When
  multiple routes share the same feeder_id, place_poles_on_routes() maintains
  a continuous per-feeder sequence so that IDs remain unique across all routes
  in the CollectorPoleResult (e.g. F1-P001…F1-P005 for route A, F1-P006…
  F1-P009 for route B of the same feeder).  place_poles_on_route() accepts an
  optional sequence_offset keyword argument (default 0) for callers that need
  to chain sequences manually.
* Route-level pole generation is independent.  ``deduplicate_pole_endpoints``
  is an additive network-level pass over ``CollectorPoleResult``.  It merges
  only terminal records from different routes that declare the same topology
  node and lie within ``coordinate_tolerance_m``.  Route-local records remain
  unchanged so their pole/span traceability is preserved.
* A merged terminal is classified as ``junction`` and retains the sorted union
  of contributing feeder, route, and source-pole IDs.  Its stable ID is derived
  from the topology node plus sorted feeder/route identities, not input order.
* Endpoint clusters use deterministic strict-pairwise membership: a candidate
  may join a cluster only when it lies within tolerance of every member.  Thus
  A-B and B-C proximity does not merge A-C when A and C exceed the tolerance.
  The canonical output coordinate is an existing member coordinate selected by
  deterministic sort order rather than an off-route centroid.
* max_span_m is a hard constraint.  min_span_m is a soft subdivision
  threshold: a section at or below it receives no fill pole.  Mandatory angle
  poles can still give a short route more than two poles.
* PoleSpan.span_length_m is the Euclidean chord distance between the two pole
  Points (i.e. start.geometry.distance(end.geometry)), not the arc-length
  difference along the LineString.  The two values coincide for poles that
  lie on the same straight segment; they diverge when a non-mandatory route
  vertex falls between two consecutive fill poles.
* Span count is chosen as the integer nearest to (L / target) rather than
  always ceiling-rounding, so that a section of length 101 m with target
  100 m correctly produces one 101 m span rather than two 50.5 m spans.
  The while-loop still enforces the hard max_span_m upper bound.
"""

import hashlib
import math
from dataclasses import dataclass

from shapely.geometry import LineString, Point

from app.algorithms.route_refinement import RefinedPhysicalRoute
from app.pnc.models import ProjectPNCNetwork

# ---------------------------------------------------------------------------
# Tolerances
# ---------------------------------------------------------------------------

_DISTANCE_EPSILON = 1e-9  # metres — treat distances this close as equal


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PolePlacementConfig:
    """
    Immutable configuration for the pole placement engine.

    All numeric fields must be finite (non-NaN, non-infinite); validation
    raises ValueError for any non-finite or out-of-range value.

    Parameters
    ----------
    target_span_m:
        Preferred pole-to-pole distance in metres.  The span-count algorithm
        starts with Python's rounded value of ``L / target`` and then increases
        it when required by ``max_span_m``.  This is a deterministic heuristic;
        it does not minimize actual span-length deviation in every tie case.
    min_span_m:
        Soft subdivision threshold.  A section at or below this length receives
        no intermediate fill pole.  It is not a guaranteed lower bound on every
        resulting span, and mandatory angle poles are still retained.
    max_span_m:
        Hard upper bound.  The span-count calculation always ensures spans
        remain at or below this limit.
    angle_pole_threshold_deg:
        Deflection angle (degrees) at or above which an interior LineString
        vertex becomes a mandatory angle pole.  0° means every vertex is
        mandatory; 180° means only exact reversals are mandatory.

        Deflection is measured as the angle between the two forward direction
        vectors at the vertex (incoming → vertex, vertex → outgoing): 0° for
        a straight continuation, 90° for a right-angle turn, 180° for a full
        reversal.
    coordinate_tolerance_m:
        Maximum projected distance used by ``deduplicate_pole_endpoints`` for
        terminal records that declare the same topology node.  Route-local
        placement does not use this value.
    """

    target_span_m: float
    min_span_m: float
    max_span_m: float
    angle_pole_threshold_deg: float = 10.0
    coordinate_tolerance_m: float = 0.1

    def __post_init__(self) -> None:
        # Finiteness checks first — NaN comparisons are always False, so
        # relational checks alone cannot catch NaN or infinite values.
        _require_finite("target_span_m", self.target_span_m)
        _require_finite("min_span_m", self.min_span_m)
        _require_finite("max_span_m", self.max_span_m)
        _require_finite("angle_pole_threshold_deg", self.angle_pole_threshold_deg)
        _require_finite("coordinate_tolerance_m", self.coordinate_tolerance_m)

        if self.target_span_m <= 0:
            raise ValueError(
                f"target_span_m must be positive, got {self.target_span_m}"
            )
        if self.min_span_m <= 0:
            raise ValueError(f"min_span_m must be positive, got {self.min_span_m}")
        if self.max_span_m <= 0:
            raise ValueError(f"max_span_m must be positive, got {self.max_span_m}")
        if self.min_span_m > self.max_span_m:
            raise ValueError(
                f"min_span_m ({self.min_span_m}) must not exceed "
                f"max_span_m ({self.max_span_m})"
            )
        if self.target_span_m > self.max_span_m:
            raise ValueError(
                f"target_span_m ({self.target_span_m}) must not exceed "
                f"max_span_m ({self.max_span_m})"
            )
        if not (0.0 <= self.angle_pole_threshold_deg <= 180.0):
            raise ValueError(
                f"angle_pole_threshold_deg must be in [0, 180], "
                f"got {self.angle_pole_threshold_deg}"
            )
        if self.coordinate_tolerance_m < 0:
            raise ValueError(
                f"coordinate_tolerance_m must be non-negative, "
                f"got {self.coordinate_tolerance_m}"
            )


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pole:
    """
    An immutable physical pole structure placed on a collector route.

    Attributes
    ----------
    pole_id:
        Deterministic identifier in the form ``{feeder_id}-P{sequence:03d}``.
        Sequence numbers are continuous within a feeder across all routes when
        poles are placed via place_poles_on_routes().
    feeder_id:
        Feeder this pole belongs to, as supplied by the upstream route.
    sequence:
        Position of this pole within the feeder-wide sequence (1-based when
        called via place_poles_on_routes; 1-based within the route when called
        via place_poles_on_route with default sequence_offset=0).
    geometry:
        Exact projected coordinate of the pole (same CRS as the route),
        obtained by LineString.interpolate(distance_along_route_m).
    pole_type:
        ``"terminal"``     — start or end of a routed edge.
        ``"angle"``        — mandatory structure at a significant route bend.
        ``"intermediate"`` — fill pole between mandatory structures.
    distance_along_route_m:
        Arc-length distance from the route start to this pole, measured along
        the LineString geometry.
    """

    pole_id: str
    feeder_id: str
    sequence: int
    geometry: Point
    pole_type: str
    distance_along_route_m: float


@dataclass(frozen=True)
class PoleSpan:
    """
    A single overhead conductor span between two consecutive poles.

    Attributes
    ----------
    start_pole_id:
        ID of the pole at the near end.
    end_pole_id:
        ID of the pole at the far end.
    span_length_m:
        Euclidean chord distance between the two pole Points
        (``start.geometry.distance(end.geometry)``).  This equals the
        arc-length interval between the poles when both points lie on the same
        straight LineString segment; it is shorter than the arc-length when a
        non-mandatory route vertex falls between them.
    """

    start_pole_id: str
    end_pole_id: str
    span_length_m: float


@dataclass(frozen=True)
class PoleRouteResult:
    """
    All poles and spans for a single refined feeder route.

    Attributes
    ----------
    route_id:
        Upstream route/segment identifier when supplied, otherwise the
        composite ``{feeder_id}_{start_node_id}_{end_node_id}``.
    feeder_id:
        Feeder identifier from the upstream route.
    start_node_id:
        Topology node ID at the route start (WTG or substation).
    end_node_id:
        Topology node ID at the route end.
    geometry:
        Original projected route geometry, retained unchanged so the
        physical-pole view can be reconciled with its source segment.
    poles:
        Ordered tuple of poles from start to end.
    spans:
        Ordered tuple of spans connecting consecutive poles.
    """

    route_id: str
    feeder_id: str
    start_node_id: str
    end_node_id: str
    geometry: LineString
    poles: tuple[Pole, ...]
    spans: tuple[PoleSpan, ...]


@dataclass(frozen=True)
class PhysicalPole:
    """One distinct physical structure after network-level endpoint merging.

    ``source_pole_ids`` retains every route-local record represented by this
    structure. ``feeder_ids`` and ``route_ids`` provide deterministic
    downstream traceability. ``topology_node_id`` is present only for route
    endpoints; intermediate and angle poles remain independent structures.
    """

    pole_id: str
    geometry: Point
    pole_type: str
    feeder_ids: tuple[str, ...]
    route_ids: tuple[str, ...]
    source_pole_ids: tuple[str, ...]
    topology_node_id: str | None


@dataclass(frozen=True)
class CollectorPoleResult:
    """
    Aggregated pole and span results for all refined routes.

    Attributes
    ----------
    routes:
        One PoleRouteResult per input refined route, in deterministic order.
    total_poles:
        Sum of poles across all routes.
    total_spans:
        Sum of spans across all routes.
    physical_poles:
        Distinct physical structures. The raw batch result contains one entry
        per route-local pole. ``deduplicate_pole_endpoints`` returns a new
        result whose shared topology endpoints are represented once.

    Notes
    -----
    Pole IDs are unique within each feeder across all routes: the batch
    function place_poles_on_routes() maintains a per-feeder sequence counter
    so that route A of feeder F1 receives F1-P001…F1-P004 and route B of
    feeder F1 receives F1-P005…F1-P007.

    Shared endpoints remain in each ``PoleRouteResult`` because route spans
    refer to those local pole IDs. Distinct structure counts and downstream
    presentation should use ``physical_poles`` and ``total_poles`` from the
    result returned by ``deduplicate_pole_endpoints``.
    """

    routes: tuple[PoleRouteResult, ...]
    total_poles: int
    total_spans: int
    physical_poles: tuple[PhysicalPole, ...] = ()


@dataclass(frozen=True)
class _EndpointPoleRecord:
    pole: Pole
    route_id: str
    topology_node_id: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate_span_count(
    route_length_m: float,
    config: PolePlacementConfig,
) -> int:
    """
    Return the number of spans needed to cover *route_length_m* while
    respecting the configured span limits.

    The candidate count is the integer *nearest* to ``L / target`` (using
    Python's built-in rounding), so a section of 101 m with target 100 m
    correctly produces one 101 m span rather than two 50.5 m spans.

    The while-loop then increases the count until the arc-length interval fits
    within ``max_span_m``.  This helper does not enforce ``min_span_m``; the
    caller uses that value only to decide whether a section should be filled.

    Parameters
    ----------
    route_length_m:
        Total arc-length of the section to cover.  Must be positive.
    config:
        Span configuration.

    Returns
    -------
    int
        Number of spans (always ≥ 1).
    """
    if route_length_m <= 0:
        raise ValueError(f"route_length_m must be positive, got {route_length_m}")

    # Round to nearest integer rather than always ceiling, so the preferred
    # span is honoured when the section length is close to an integer multiple
    # of target_span_m.
    n_spans = max(1, round(route_length_m / config.target_span_m))

    # Hard upper-bound enforcement: increase until actual ≤ max_span_m.
    while route_length_m / n_spans > config.max_span_m + _DISTANCE_EPSILON:
        n_spans += 1

    return n_spans


def place_poles_on_route(
    route: RefinedPhysicalRoute,
    config: PolePlacementConfig,
    *,
    sequence_offset: int = 0,
) -> PoleRouteResult:
    """
    Place physical pole structures along a single refined feeder route.

    Parameters
    ----------
    route:
        A refined physical route from SURGE-PY-009.  Must carry a valid,
        non-degenerate LineString with finite coordinates and positive length.
    config:
        Pole placement configuration.
    sequence_offset:
        Starting sequence number is ``sequence_offset + 1``.  Pass the total
        number of poles already placed for this feeder to obtain a continuous
        per-feeder sequence.  Defaults to 0 (route-local sequence starts at 1).

    Returns
    -------
    PoleRouteResult
        Ordered poles and spans for the route.

    Raises
    ------
    ValueError
        If the route geometry is invalid, degenerate, or contains non-finite
        coordinates.

    Notes
    -----
    The placement algorithm:

    1. Validate the input geometry.
    2. Identify *mandatory* positions:
       - distance 0.0 (start terminal)
       - interior LineString vertices whose deflection angle equals or exceeds
         ``config.angle_pole_threshold_deg`` (angle poles)
       - ``route.geometry.length`` (end terminal)
    3. Divide the route into sections between consecutive mandatory positions.
    4. Fill each section longer than ``min_span_m`` with evenly-distributed
       intermediate poles.  ``max_span_m`` is enforced on arc-length intervals;
       ``min_span_m`` is only the subdivision threshold.
    5. Classify each pole as ``"terminal"``, ``"angle"``, or
       ``"intermediate"``.
    6. Build PoleSpan objects whose ``span_length_m`` is the Euclidean chord
       distance between adjacent pole Points.
    """
    # ------------------------------------------------------------------
    # Input validation (caller errors → ValueError, not AssertionError)
    # ------------------------------------------------------------------
    geometry = route.geometry
    if not isinstance(geometry, LineString):
        raise ValueError(
            f"route.geometry must be a LineString, got {type(geometry).__name__}"
        )
    if not geometry.is_valid:
        raise ValueError(
            "route.geometry is not a valid LineString (Shapely validity check failed)"
        )
    coords = list(geometry.coords)
    if len(coords) < 2:
        raise ValueError("route.geometry must contain at least two distinct points")
    if any(not all(math.isfinite(v) for v in pt) for pt in coords):
        raise ValueError("route.geometry contains non-finite coordinates")
    total_length = geometry.length
    if total_length <= 0:
        raise ValueError(f"route.geometry has zero or negative length: {total_length}")

    # ------------------------------------------------------------------
    # Step 1: identify mandatory pole distances
    # ------------------------------------------------------------------
    mandatory_distances: set[float] = {0.0, total_length}
    mandatory_angle_distances: set[float] = set()

    if len(coords) >= 3:
        cumulative = 0.0
        for i in range(1, len(coords) - 1):
            dx_prev = coords[i][0] - coords[i - 1][0]
            dy_prev = coords[i][1] - coords[i - 1][1]
            dx_next = coords[i + 1][0] - coords[i][0]
            dy_next = coords[i + 1][1] - coords[i][1]
            # Advance cumulative arc-length to vertex i
            seg_len = math.hypot(dx_prev, dy_prev)
            cumulative += seg_len

            deflection = _deflection_angle_deg(dx_prev, dy_prev, dx_next, dy_next)
            if deflection >= config.angle_pole_threshold_deg:
                d = min(cumulative, total_length)
                mandatory_distances.add(d)
                mandatory_angle_distances.add(d)

    sorted_mandatory = sorted(mandatory_distances)

    # ------------------------------------------------------------------
    # Step 2 & 3: fill each section with intermediate poles
    # ------------------------------------------------------------------
    all_distances: list[float] = list(sorted_mandatory)

    for section_start, section_end in zip(
        sorted_mandatory, sorted_mandatory[1:], strict=False
    ):
        section_length = section_end - section_start
        if section_length <= config.min_span_m + _DISTANCE_EPSILON:
            # Short section — mandatory endpoints suffice.
            continue

        n_spans = calculate_span_count(section_length, config)
        if n_spans <= 1:
            continue

        interval = section_length / n_spans
        for k in range(1, n_spans):
            d = section_start + k * interval
            # Clamp to avoid floating-point overshoot past section_end
            d = min(d, section_end - _DISTANCE_EPSILON)
            all_distances.append(d)

    # ------------------------------------------------------------------
    # Step 4: sort, deduplicate, interpolate, classify
    # ------------------------------------------------------------------
    all_distances_sorted = _deduplicate_distances(sorted(all_distances))

    poles: list[Pole] = []
    for local_seq, dist in enumerate(all_distances_sorted, start=1):
        seq = local_seq + sequence_offset
        point: Point = geometry.interpolate(dist)
        pole_type = _classify_pole(dist, total_length, mandatory_angle_distances)
        pole_id = f"{route.feeder_id}-P{seq:03d}"
        poles.append(
            Pole(
                pole_id=pole_id,
                feeder_id=route.feeder_id,
                sequence=seq,
                geometry=point,
                pole_type=pole_type,
                distance_along_route_m=dist,
            )
        )

    # ------------------------------------------------------------------
    # Step 5: build spans — span_length_m is the Euclidean chord distance
    # ------------------------------------------------------------------
    spans: list[PoleSpan] = []
    for a, b in zip(poles, poles[1:], strict=False):
        chord = a.geometry.distance(b.geometry)
        spans.append(
            PoleSpan(
                start_pole_id=a.pole_id,
                end_pole_id=b.pole_id,
                span_length_m=chord,
            )
        )

    route_id = route.route_id or (
        f"{route.feeder_id}_{route.start_node_id}_{route.end_node_id}"
    )
    result = PoleRouteResult(
        route_id=route_id,
        feeder_id=route.feeder_id,
        start_node_id=route.start_node_id,
        end_node_id=route.end_node_id,
        geometry=geometry,
        poles=tuple(poles),
        spans=tuple(spans),
    )

    _validate_pole_route_result(result, config)
    return result


def place_poles_on_routes(
    routes: tuple[RefinedPhysicalRoute, ...],
    config: PolePlacementConfig,
) -> CollectorPoleResult:
    """
    Place poles on every refined route and aggregate results.

    Pole IDs are unique per feeder across all routes: this function maintains
    a per-feeder sequence counter and passes it as ``sequence_offset`` to each
    call of place_poles_on_route(), so that routes sharing the same feeder_id
    receive a continuous, non-colliding sequence.

    Routes are processed in the order supplied; callers should ensure a
    deterministic input ordering for deterministic pole IDs.

    Parameters
    ----------
    routes:
        Refined physical routes from SURGE-PY-009.
    config:
        Pole placement configuration.

    Returns
    -------
    CollectorPoleResult
        All route results and aggregate pole / span counts.
    """
    feeder_offsets: dict[str, int] = {}
    route_results: list[PoleRouteResult] = []

    for route in routes:
        offset = feeder_offsets.get(route.feeder_id, 0)
        result = place_poles_on_route(route, config, sequence_offset=offset)
        feeder_offsets[route.feeder_id] = offset + len(result.poles)
        route_results.append(result)

    physical_poles = _route_local_physical_poles(tuple(route_results))
    total_poles = len(physical_poles)
    total_spans = sum(len(r.spans) for r in route_results)
    return CollectorPoleResult(
        routes=tuple(route_results),
        total_poles=total_poles,
        total_spans=total_spans,
        physical_poles=physical_poles,
    )


def place_poles_on_network(
    network: ProjectPNCNetwork,
    config: PolePlacementConfig,
) -> CollectorPoleResult:
    """Build the canonical pole network for an assembled project PNC.

    Pole placement consumes each segment's routed geometry and preserves the
    upstream segment ID as route provenance. The network-level PY-023 endpoint
    deduplication pass is always applied before the result is returned.
    """
    segments = tuple(
        sorted(
            (segment for feeder in network.feeders for segment in feeder.segments),
            key=lambda segment: (segment.feeder_id, segment.segment_id),
        )
    )
    if not segments:
        raise ValueError("Project PNC network has no routed segments.")

    routes = tuple(
        RefinedPhysicalRoute(
            feeder_id=segment.feeder_id,
            start_node_id=segment.from_node_id,
            end_node_id=segment.to_node_id,
            geometry=segment.route_geometry,
            original_length_m=segment.route_length_m,
            refined_length_m=segment.route_length_m,
            original_traversal_cost=segment.route_length_m,
            refined_traversal_cost=segment.route_length_m,
            route_id=segment.segment_id,
        )
        for segment in segments
    )
    route_result = place_poles_on_routes(routes, config)
    return deduplicate_pole_endpoints(
        route_result,
        coordinate_tolerance_m=config.coordinate_tolerance_m,
    )


def deduplicate_pole_endpoints(
    result: CollectorPoleResult,
    coordinate_tolerance_m: float,
) -> CollectorPoleResult:
    """Return a network view with coincident shared endpoints represented once.

    Only terminal poles attached to the same declared topology node on
    different routes are eligible. Intermediate/angle poles and geometrically
    close endpoints with different node IDs remain distinct. Clustering is
    deterministic and strict-pairwise: a record joins a cluster only when its
    coordinate is within ``coordinate_tolerance_m`` of every existing member.

    Multi-route clusters are classified as ``junction``. Route-local poles and
    spans are deliberately retained unchanged for conductor-span traceability;
    ``total_spans`` therefore remains the number of route conductor spans while
    ``total_poles`` becomes the number of distinct physical structures.
    """

    _require_finite("coordinate_tolerance_m", coordinate_tolerance_m)
    if coordinate_tolerance_m < 0:
        raise ValueError(
            f"coordinate_tolerance_m must be non-negative, got {coordinate_tolerance_m}"
        )

    endpoint_records = _endpoint_pole_records(result.routes)
    endpoint_source_ids = {
        (record.route_id, record.pole.pole_id) for record in endpoint_records
    }
    independent = [
        physical
        for physical in _route_local_physical_poles(result.routes)
        if (physical.route_ids[0], physical.source_pole_ids[0])
        not in endpoint_source_ids
    ]

    clusters: list[list[_EndpointPoleRecord]] = []
    for record in endpoint_records:
        matching_cluster = next(
            (
                cluster
                for cluster in clusters
                if _can_join_endpoint_cluster(
                    record,
                    cluster,
                    coordinate_tolerance_m,
                )
            ),
            None,
        )
        if matching_cluster is None:
            clusters.append([record])
        else:
            matching_cluster.append(record)

    physical_poles = independent + [
        _physical_pole_from_endpoint_cluster(cluster) for cluster in clusters
    ]
    physical_poles.sort(key=_physical_pole_sort_key)
    return CollectorPoleResult(
        routes=result.routes,
        total_poles=len(physical_poles),
        total_spans=result.total_spans,
        physical_poles=tuple(physical_poles),
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _route_local_physical_poles(
    routes: tuple[PoleRouteResult, ...],
) -> tuple[PhysicalPole, ...]:
    physical_poles = [
        PhysicalPole(
            pole_id=pole.pole_id,
            geometry=pole.geometry,
            pole_type=pole.pole_type,
            feeder_ids=(route.feeder_id,),
            route_ids=(route.route_id,),
            source_pole_ids=(pole.pole_id,),
            topology_node_id=_pole_topology_node_id(route, pole_index),
        )
        for route in routes
        for pole_index, pole in enumerate(route.poles)
    ]
    physical_poles.sort(key=_physical_pole_sort_key)
    return tuple(physical_poles)


def _endpoint_pole_records(
    routes: tuple[PoleRouteResult, ...],
) -> tuple[_EndpointPoleRecord, ...]:
    records: list[_EndpointPoleRecord] = []
    for route in routes:
        endpoint_indexes = ((0, route.start_node_id), (-1, route.end_node_id))
        for pole_index, topology_node_id in endpoint_indexes:
            pole = route.poles[pole_index]
            if pole.pole_type != "terminal":
                raise ValueError(
                    f"Route {route.route_id} endpoint pole {pole.pole_id} "
                    "must be terminal"
                )
            records.append(
                _EndpointPoleRecord(
                    pole=pole,
                    route_id=route.route_id,
                    topology_node_id=topology_node_id,
                )
            )
    return tuple(
        sorted(
            records,
            key=lambda record: (
                record.topology_node_id,
                record.route_id,
                record.pole.feeder_id,
                record.pole.pole_id,
            ),
        )
    )


def _pole_topology_node_id(
    route: PoleRouteResult,
    pole_index: int,
) -> str | None:
    if pole_index == 0:
        return route.start_node_id
    if pole_index == len(route.poles) - 1:
        return route.end_node_id
    return None


def _can_join_endpoint_cluster(
    record: _EndpointPoleRecord,
    cluster: list[_EndpointPoleRecord],
    coordinate_tolerance_m: float,
) -> bool:
    return all(
        record.topology_node_id == member.topology_node_id
        and record.route_id != member.route_id
        and record.pole.geometry.distance(member.pole.geometry)
        <= coordinate_tolerance_m + _DISTANCE_EPSILON
        for member in cluster
    )


def _physical_pole_from_endpoint_cluster(
    cluster: list[_EndpointPoleRecord],
) -> PhysicalPole:
    members = sorted(
        cluster,
        key=lambda record: (
            record.route_id,
            record.pole.feeder_id,
            record.pole.pole_id,
        ),
    )
    feeder_ids = tuple(sorted({member.pole.feeder_id for member in members}))
    route_ids = tuple(sorted(member.route_id for member in members))
    source_pole_ids = tuple(sorted(member.pole.pole_id for member in members))
    topology_node_id = members[0].topology_node_id

    if len(members) == 1:
        member = members[0]
        return PhysicalPole(
            pole_id=member.pole.pole_id,
            geometry=member.pole.geometry,
            pole_type=member.pole.pole_type,
            feeder_ids=feeder_ids,
            route_ids=route_ids,
            source_pole_ids=source_pole_ids,
            topology_node_id=topology_node_id,
        )

    stable_identity = repr((topology_node_id, feeder_ids, route_ids))
    digest = hashlib.sha256(stable_identity.encode("utf-8")).hexdigest()[:12]
    return PhysicalPole(
        pole_id=f"JUNCTION-{digest}",
        geometry=members[0].pole.geometry,
        pole_type="junction",
        feeder_ids=feeder_ids,
        route_ids=route_ids,
        source_pole_ids=source_pole_ids,
        topology_node_id=topology_node_id,
    )


def _physical_pole_sort_key(physical: PhysicalPole) -> tuple[str, str, str]:
    return (
        physical.topology_node_id or "",
        physical.pole_id,
        "|".join(physical.route_ids),
    )


def _require_finite(field: str, value: float) -> None:
    """Raise ValueError if *value* is NaN or infinite."""
    if not math.isfinite(value):
        raise ValueError(f"{field} must be a finite number, got {value!r}")


def _deflection_angle_deg(
    dx_prev: float,
    dy_prev: float,
    dx_next: float,
    dy_next: float,
) -> float:
    """
    Return the deflection angle in degrees at a LineString vertex.

    Both input vectors are *forward-direction* vectors:
    - ``(dx_prev, dy_prev)`` points from the previous vertex toward the
      current vertex.
    - ``(dx_next, dy_next)`` points from the current vertex toward the next
      vertex.

    The deflection angle is the angle *between* these two vectors:

    - 0°   for a straight continuation (vectors parallel, same direction).
    - 90°  for a right-angle turn.
    - 180° for a full reversal (vectors anti-parallel).

    This is computed directly as ``arccos(dot / (|a| |b|))``.  The cosine is
    clamped to [−1, 1] to guard against floating-point noise.
    """
    len_prev = math.hypot(dx_prev, dy_prev)
    len_next = math.hypot(dx_next, dy_next)
    if len_prev < _DISTANCE_EPSILON or len_next < _DISTANCE_EPSILON:
        return 0.0

    dot = dx_prev * dx_next + dy_prev * dy_next
    cos_theta = dot / (len_prev * len_next)
    # Clamp to [-1, 1] to guard against floating-point noise in arccos
    cos_theta = max(-1.0, min(1.0, cos_theta))
    # arccos of the dot product of two forward vectors gives the deflection
    # directly: 0° straight, 90° right-angle, 180° reversal.
    return math.degrees(math.acos(cos_theta))


def _classify_pole(
    distance: float,
    total_length: float,
    angle_distances: set[float],
) -> str:
    """Return ``"terminal"``, ``"angle"``, or ``"intermediate"``."""
    if math.isclose(distance, 0.0, abs_tol=_DISTANCE_EPSILON) or math.isclose(
        distance, total_length, abs_tol=_DISTANCE_EPSILON
    ):
        return "terminal"
    for angle_d in angle_distances:
        if math.isclose(distance, angle_d, abs_tol=_DISTANCE_EPSILON):
            return "angle"
    return "intermediate"


def _deduplicate_distances(
    distances: list[float],
) -> list[float]:
    """
    Remove distances within *_DISTANCE_EPSILON* of the preceding entry.
    Input must be sorted ascending.
    """
    if not distances:
        return []
    result = [distances[0]]
    for d in distances[1:]:
        if d - result[-1] > _DISTANCE_EPSILON:
            result.append(d)
    return result


def _validate_pole_route_result(
    result: PoleRouteResult,
    config: PolePlacementConfig,
) -> None:
    """
    Assert all placement invariants for a completed PoleRouteResult.

    Raises AssertionError if any invariant is violated.  This is an internal
    consistency guard — violations indicate a bug in the placement algorithm,
    not invalid caller input (which is caught with ValueError before this
    function is reached).
    """
    poles = result.poles
    spans = result.spans

    assert len(poles) >= 2, (
        f"Route {result.route_id}: expected at least 2 poles, got {len(poles)}"
    )

    # First pole at route start
    assert math.isclose(
        poles[0].distance_along_route_m, 0.0, abs_tol=_DISTANCE_EPSILON
    ), (
        f"Route {result.route_id}: first pole distance should be 0, "
        f"got {poles[0].distance_along_route_m}"
    )

    # Terminal type on endpoints
    assert poles[0].pole_type == "terminal", (
        f"Route {result.route_id}: first pole must be terminal"
    )
    assert poles[-1].pole_type == "terminal", (
        f"Route {result.route_id}: last pole must be terminal"
    )

    # Poles strictly ordered along route
    for i in range(1, len(poles)):
        assert poles[i].distance_along_route_m > (
            poles[i - 1].distance_along_route_m + _DISTANCE_EPSILON
        ), f"Route {result.route_id}: poles not strictly ordered at index {i}"

    # Span count matches pole pairs
    assert len(spans) == len(poles) - 1, (
        f"Route {result.route_id}: expected {len(poles) - 1} spans, got {len(spans)}"
    )

    # Span connectivity, chord length, and max_span_m enforcement
    for i, span in enumerate(spans):
        assert span.start_pole_id == poles[i].pole_id, (
            f"Route {result.route_id}: span {i} start mismatch"
        )
        assert span.end_pole_id == poles[i + 1].pole_id, (
            f"Route {result.route_id}: span {i} end mismatch"
        )

        expected_chord = poles[i].geometry.distance(poles[i + 1].geometry)
        assert math.isclose(
            span.span_length_m,
            expected_chord,
            rel_tol=1e-9,
            abs_tol=_DISTANCE_EPSILON,
        ), (
            f"Route {result.route_id}: span {i} length "
            f"{span.span_length_m} != chord {expected_chord}"
        )

        assert span.span_length_m > _DISTANCE_EPSILON, (
            f"Route {result.route_id}: span {i} has zero or negative length"
        )
        assert span.span_length_m <= config.max_span_m + _DISTANCE_EPSILON, (
            f"Route {result.route_id}: span {i} chord {span.span_length_m:.3f} m "
            f"exceeds max_span_m={config.max_span_m}"
        )

    # IDs are non-empty
    for pole in poles:
        assert pole.pole_id, f"Route {result.route_id}: empty pole_id"
    for span in spans:
        assert span.start_pole_id and span.end_pole_id, (
            f"Route {result.route_id}: span has empty pole_id"
        )
