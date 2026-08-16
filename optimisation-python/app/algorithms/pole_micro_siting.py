"""
PY-035 Deterministic Pole Micro-Siting Optimization.

This module implements a pole-layout refinement stage that adjusts the locations
of movable poles (intermediate poles) along their original routed corridor to
minimize landowner interactions, improve constructability, and avoid constraints.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from shapely.geometry import LineString, Point

from app.algorithms.pole_placement import (
    CollectorPoleResult,
    Pole,
    PoleMicroSitingConfig,
    PolePlacementConfig,
    PoleRouteResult,
    PoleSpan,
    deduplicate_pole_endpoints,
)
from app.gis.constraints import (
    ConstraintLayer,
    ConstraintMode,
    ConstraintType,
    effective_constraint_geometry,
)
from app.land.models import LandAvailabilityStatus, LandCommercialContext


@dataclass(frozen=True)
class PoleMicroSitingContext:
    """Immutable context required for evaluating pole candidates."""

    route_geometries: Mapping[str, LineString]
    route_owner_ids: frozenset[str]
    constraint_layers: tuple[ConstraintLayer, ...]
    land_context: LandCommercialContext | None
    pole_config: PolePlacementConfig
    route_parcel_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class PoleMoveScore:
    """Detailed evidence of why a candidate position was evaluated."""

    owner_delta: int
    parcel_delta: int
    span_quality_delta: float
    constructability_delta: float
    movement_distance_m: float

    def is_strictly_better_than(
        self, other: "PoleMoveScore", min_improvement: float
    ) -> bool:
        """
        Ranking:
        1. lower owner burden
        2. lower parcel burden
        3. better span quality
        4. lower constructability penalty
        5. smaller movement distance
        """
        if self.owner_delta < other.owner_delta:
            return True
        if self.owner_delta > other.owner_delta:
            return False

        if self.parcel_delta < other.parcel_delta:
            return True
        if self.parcel_delta > other.parcel_delta:
            return False

        # Span quality and constructability are combined or checked sequentially.
        score = self.span_quality_delta + self.constructability_delta
        other_score = other.span_quality_delta + other.constructability_delta

        if score < other_score - min_improvement:
            return True

        if abs(score - other_score) <= min_improvement:
            if self.movement_distance_m < other.movement_distance_m:
                return True

        return False


@dataclass(frozen=True)
class PoleMicroSitingMove:
    """Evidence of a single pole movement."""

    pole_id: str
    original_chainage_m: float
    selected_chainage_m: float
    movement_distance_m: float
    reason: str


@dataclass(frozen=True)
class PoleMicroSitingResult:
    """Aggregate result of the micro-siting pass."""

    moves: tuple[PoleMicroSitingMove, ...]
    moved_count: int
    unchanged_count: int


def _generate_candidates(
    chainage_m: float,
    route_length: float,
    config: PoleMicroSitingConfig,
) -> tuple[float, ...]:
    """Generate candidate chainages within the search radius of ``chainage_m``."""
    candidates = [chainage_m]

    steps = int(config.search_radius_m / config.candidate_spacing_m)
    for i in range(1, steps + 1):
        offset = i * config.candidate_spacing_m

        forward = chainage_m + offset
        if forward <= route_length:
            candidates.append(forward)

        backward = chainage_m - offset
        if backward >= 0:
            candidates.append(backward)

    return tuple(sorted(set(candidates)))


def _parcel_layers_for_point(
    point: Point,
    constraint_layers: tuple[ConstraintLayer, ...],
) -> tuple[str, ...]:
    """Return every distinct PARCEL layer containing ``point``."""
    parcel_ids: set[str] = set()
    for layer in constraint_layers:
        if layer.layer_type != ConstraintType.PARCEL:
            continue
        try:
            geometry = effective_constraint_geometry(layer)
        except ValueError:
            continue
        if geometry.covers(point):
            parcel_ids.add(layer.layer_id)
    return tuple(sorted(parcel_ids))


def _owners_for_parcels(
    parcel_ids: tuple[str, ...],
    land_context: LandCommercialContext | None,
) -> frozenset[str]:
    if not parcel_ids or land_context is None:
        return frozenset()
    parcel_id_set = set(parcel_ids)
    owners: set[str] = set()
    for profile in land_context.parcel_profiles:
        if profile.parcel_id in parcel_id_set and profile.owner_id is not None:
            owners.add(profile.owner_id)
    return frozenset(owners)


def _is_feasible(
    candidate_geom: Point,
    candidate_chainage: float,
    prev_pole: Pole,
    next_pole: Pole,
    context: PoleMicroSitingContext,
    max_span_m: float,
) -> bool:
    """Check ordering, span limits, GIS exclusions, and unavailable land."""
    # 0. Route ordering must be preserved.
    if not (
        prev_pole.distance_along_route_m
        < candidate_chainage
        < next_pole.distance_along_route_m
    ):
        return False

    # 1. Span limits
    prev_span = prev_pole.geometry.distance(candidate_geom)
    if prev_span > max_span_m:
        return False
    if prev_span < context.pole_config.min_span_m:
        return False

    next_span = candidate_geom.distance(next_pole.geometry)
    if next_span > max_span_m:
        return False
    if next_span < context.pole_config.min_span_m:
        return False

    # 2. Hard GIS constraints
    for layer in context.constraint_layers:
        if layer.mode != ConstraintMode.HARD_EXCLUSION:
            continue
        try:
            geometry = effective_constraint_geometry(layer)
        except ValueError:
            continue
        if geometry.covers(candidate_geom):
            return False

    # 3. Unavailable land
    if context.land_context:
        parcel_ids = set(
            _parcel_layers_for_point(candidate_geom, context.constraint_layers)
        )
        if any(
            profile.parcel_id in parcel_ids
            and profile.availability_status == LandAvailabilityStatus.UNAVAILABLE
            for profile in context.land_context.parcel_profiles
        ):
            return False

    return True


def _score_candidate(
    candidate_geom: Point,
    candidate_chainage: float,
    original_chainage: float,
    prev_pole: Pole,
    next_pole: Pole,
    context: PoleMicroSitingContext,
    target_span_m: float,
) -> PoleMoveScore:
    """Score a candidate position."""
    # 1. Span quality
    prev_span = prev_pole.geometry.distance(candidate_geom)
    next_span = candidate_geom.distance(next_pole.geometry)

    span_penalty = abs(prev_span - target_span_m) + abs(next_span - target_span_m)

    # 2. Landowner burden introduced by the candidate position
    candidate_parcels = _parcel_layers_for_point(
        candidate_geom, context.constraint_layers
    )
    candidate_owners = _owners_for_parcels(candidate_parcels, context.land_context)
    owner_delta = len(candidate_owners - context.route_owner_ids)
    parcel_delta = len(set(candidate_parcels).difference(context.route_parcel_ids))

    # 3. Movement distance
    movement_dist = abs(candidate_chainage - original_chainage)

    return PoleMoveScore(
        owner_delta=owner_delta,
        parcel_delta=parcel_delta,
        span_quality_delta=span_penalty,
        constructability_delta=0.0,
        movement_distance_m=movement_dist,
    )


def _network_objective(
    routes: tuple[PoleRouteResult, ...],
    context: PoleMicroSitingContext,
) -> tuple[int, float]:
    """Network-level objective: (owner interaction count, span penalty)."""
    owners = set(context.route_owner_ids)
    total_span_penalty = 0.0
    for route in routes:
        for pole in route.poles:
            parcel_ids = _parcel_layers_for_point(
                pole.geometry, context.constraint_layers
            )
            owners.update(_owners_for_parcels(parcel_ids, context.land_context))
        for i in range(len(route.poles) - 1):
            span = route.poles[i].geometry.distance(route.poles[i + 1].geometry)
            total_span_penalty += abs(span - context.pole_config.target_span_m)
    return len(owners), total_span_penalty


def _strictly_better(
    candidate: tuple[int, float],
    baseline: tuple[int, float],
) -> bool:
    """Return True when ``candidate`` strictly beats ``baseline``."""
    if candidate[0] < baseline[0]:
        return True
    if candidate[0] == baseline[0] and candidate[1] < baseline[1]:
        return True
    return False


def optimize_poles(
    initial_result: CollectorPoleResult,
    context: PoleMicroSitingContext,
    config: PoleMicroSitingConfig,
) -> tuple[CollectorPoleResult, PoleMicroSitingResult]:
    """
    Deterministically refine pole locations to improve the pole network layout.

    Candidates are always generated from the immutable original chainage of each
    pole, so repeated passes can never drift beyond ``search_radius_m``.  The
    final layout is accepted only when it strictly improves the network-level
    objective; otherwise the original layout is returned unchanged.
    """
    if not config.enabled:
        return (
            initial_result,
            PoleMicroSitingResult(
                moves=(),
                moved_count=0,
                unchanged_count=len(initial_result.physical_poles),
            ),
        )

    moves: list[PoleMicroSitingMove] = []

    # We mutate route poles locally during coordinate descent
    route_poles_map: dict[str, list[Pole]] = {
        route.route_id: list(route.poles) for route in initial_result.routes
    }
    original_positions: dict[str, float] = {
        pole.pole_id: pole.distance_along_route_m
        for route in initial_result.routes
        for pole in route.poles
    }

    max_span_m = context.pole_config.max_span_m
    target_span_m = context.pole_config.target_span_m

    for _ in range(config.max_passes):
        moved_in_pass = False

        # We must iterate deterministically
        for route in initial_result.routes:
            route_id = route.route_id
            route_geom = context.route_geometries[route_id]
            r_poles = route_poles_map[route_id]

            for idx, pole in enumerate(r_poles):
                if pole.pole_type != "intermediate":
                    continue

                prev_pole = r_poles[idx - 1]
                next_pole = r_poles[idx + 1]
                original_chainage = original_positions[pole.pole_id]

                # Candidates are generated from the immutable original chainage.
                candidates = _generate_candidates(
                    original_chainage, route_geom.length, config
                )

                best_candidate_pole = pole
                best_score = _score_candidate(
                    pole.geometry,
                    pole.distance_along_route_m,
                    original_chainage,
                    prev_pole,
                    next_pole,
                    context,
                    target_span_m,
                )

                for chainage in candidates:
                    cand_geom = route_geom.interpolate(chainage)
                    if not _is_feasible(
                        cand_geom, chainage, prev_pole, next_pole, context, max_span_m
                    ):
                        continue

                    score = _score_candidate(
                        cand_geom,
                        chainage,
                        original_chainage,
                        prev_pole,
                        next_pole,
                        context,
                        target_span_m,
                    )

                    if score.is_strictly_better_than(
                        best_score, config.min_improvement
                    ):
                        best_candidate_pole = Pole(
                            pole_id=pole.pole_id,
                            feeder_id=pole.feeder_id,
                            sequence=pole.sequence,
                            geometry=cand_geom,
                            pole_type=pole.pole_type,
                            distance_along_route_m=chainage,
                        )
                        best_score = score

                if (
                    best_candidate_pole.distance_along_route_m
                    != pole.distance_along_route_m
                ):
                    r_poles[idx] = best_candidate_pole
                    moved_in_pass = True

                    moves.append(
                        PoleMicroSitingMove(
                            pole_id=pole.pole_id,
                            original_chainage_m=original_chainage,
                            selected_chainage_m=best_candidate_pole.distance_along_route_m,
                            movement_distance_m=abs(
                                best_candidate_pole.distance_along_route_m
                                - original_chainage
                            ),
                            reason="Improved score",
                        )
                    )

        if not moved_in_pass:
            break

    # Rebuild CollectorPoleResult
    new_routes = []
    for route in initial_result.routes:
        new_poles = tuple(route_poles_map[route.route_id])
        new_spans = []
        for i in range(len(new_poles) - 1):
            p1 = new_poles[i]
            p2 = new_poles[i + 1]
            new_spans.append(
                PoleSpan(
                    start_pole_id=p1.pole_id,
                    end_pole_id=p2.pole_id,
                    span_length_m=p1.geometry.distance(p2.geometry),
                )
            )

        new_routes.append(
            PoleRouteResult(
                route_id=route.route_id,
                feeder_id=route.feeder_id,
                start_node_id=route.start_node_id,
                end_node_id=route.end_node_id,
                geometry=route.geometry,
                poles=new_poles,
                spans=tuple(new_spans),
            )
        )

    temp_result = CollectorPoleResult(
        routes=tuple(new_routes),
        total_poles=sum(len(r.poles) for r in new_routes),
        total_spans=sum(len(r.spans) for r in new_routes),
        physical_poles=(),
    )

    new_result = deduplicate_pole_endpoints(
        temp_result, context.pole_config.coordinate_tolerance_m
    )

    # Global acceptance: revert unless the new layout strictly improves the
    # network-level objective.
    baseline_objective = _network_objective(initial_result.routes, context)
    candidate_objective = _network_objective(new_result.routes, context)
    if not _strictly_better(candidate_objective, baseline_objective):
        return (
            initial_result,
            PoleMicroSitingResult(
                moves=(),
                moved_count=0,
                unchanged_count=len(initial_result.physical_poles),
            ),
        )

    moved_count = len(set(m.pole_id for m in moves))
    result = PoleMicroSitingResult(
        moves=tuple(moves),
        moved_count=moved_count,
        unchanged_count=len(new_result.physical_poles) - moved_count,
    )

    return new_result, result
