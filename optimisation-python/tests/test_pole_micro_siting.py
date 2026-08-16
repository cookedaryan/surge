import pytest
from shapely.geometry import LineString, Point

from app.algorithms.pole_micro_siting import (
    PoleMicroSitingConfig,
    PoleMicroSitingContext,
    _generate_candidates,
    _is_feasible,
    _score_candidate,
    optimize_poles,
)
from app.algorithms.pole_placement import (
    CollectorPoleResult,
    Pole,
    PolePlacementConfig,
    PoleRouteResult,
)


@pytest.fixture
def base_config():
    return PoleMicroSitingConfig(
        enabled=True,
        search_radius_m=15.0,
        candidate_spacing_m=5.0,
        max_passes=2,
        min_improvement=1.0,
    )


@pytest.fixture
def pole_config():
    return PolePlacementConfig(
        target_span_m=50.0,
        min_span_m=10.0,
        max_span_m=100.0,
    )


def test_generate_candidates(base_config):
    # Route length 100. Search radius 15, spacing 5.
    # Should get candidates at: 5, 10, 15, 20, 25, 30, 35
    candidates = _generate_candidates(20.0, 100.0, base_config)
    assert candidates == (5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0)


def test_generate_candidates_truncates_at_ends(base_config):
    # Route length 10. Search radius 15, spacing 5.
    # Should get: 0.0, 5.0, 10.0
    candidates = _generate_candidates(5.0, 10.0, base_config)
    assert candidates == (0.0, 5.0, 10.0)


def test_is_feasible_spans(pole_config):
    context = PoleMicroSitingContext(
        route_geometries={},
        route_owner_ids=frozenset(),
        constraint_layers=(),
        land_context=None,
        pole_config=pole_config,
    )

    prev_pole = Pole("P0", "F1", 0, Point(0, 0), "terminal", 0.0)
    next_pole = Pole("P2", "F1", 2, Point(100, 0), "terminal", 100.0)

    # Feasible (span to next is 90 <= max_span=100)
    assert _is_feasible(Point(10, 0), 10.0, prev_pole, next_pole, context, 100.0)

    # Infeasible (span to prev is 110 > max_span=100)
    assert not _is_feasible(Point(110, 0), 110.0, prev_pole, next_pole, context, 100.0)

    # Infeasible (span to next is 110 > max_span=100)
    assert not _is_feasible(Point(-10, 0), -10.0, prev_pole, next_pole, context, 100.0)


def test_is_feasible_rejects_ordering_violations(pole_config):
    context = PoleMicroSitingContext(
        route_geometries={},
        route_owner_ids=frozenset(),
        constraint_layers=(),
        land_context=None,
        pole_config=pole_config,
    )

    prev_pole = Pole("P0", "F1", 0, Point(0, 0), "terminal", 0.0)
    next_pole = Pole("P2", "F1", 2, Point(100, 0), "terminal", 100.0)

    # Rejected: candidate chainage must stay strictly between neighbors
    assert not _is_feasible(Point(120, 0), 120.0, prev_pole, next_pole, context, 100.0)
    assert not _is_feasible(Point(-20, 0), -20.0, prev_pole, next_pole, context, 100.0)


def test_score_candidate(pole_config):
    context = PoleMicroSitingContext(
        route_geometries={},
        route_owner_ids=frozenset(),
        constraint_layers=(),
        land_context=None,
        pole_config=pole_config,
    )

    prev_pole = Pole("P0", "F1", 0, Point(0, 0), "terminal", 0.0)
    next_pole = Pole("P2", "F1", 2, Point(100, 0), "terminal", 100.0)

    # Target span is 50. Placing pole at 50 gives 0 penalty.
    score = _score_candidate(
        Point(50, 0), 50.0, 60.0, prev_pole, next_pole, context, 50.0
    )
    assert score.span_quality_delta == 0.0
    assert score.movement_distance_m == 10.0

    # Target span is 50. Placing pole at 40 gives penalty 10 + 10 = 20.
    score2 = _score_candidate(
        Point(40, 0), 40.0, 60.0, prev_pole, next_pole, context, 50.0
    )
    assert score2.span_quality_delta == 20.0
    assert score2.movement_distance_m == 20.0

    assert score.is_strictly_better_than(score2, 1.0)


def test_optimize_poles(base_config, pole_config):
    context = PoleMicroSitingContext(
        route_geometries={"R1": LineString([(0, 0), (100, 0)])},
        route_owner_ids=frozenset(),
        constraint_layers=(),
        land_context=None,
        pole_config=pole_config,
    )

    p0 = Pole("P0", "F1", 0, Point(0, 0), "terminal", 0.0)
    # Pole placed poorly at 70. Target is 50. Moving to 55 will improve score.
    p1 = Pole("P1", "F1", 1, Point(70, 0), "intermediate", 70.0)
    p2 = Pole("P2", "F1", 2, Point(100, 0), "terminal", 100.0)

    initial_result = CollectorPoleResult(
        routes=(
            PoleRouteResult(
                route_id="R1",
                feeder_id="F1",
                start_node_id="N1",
                end_node_id="N2",
                geometry=LineString([(0, 0), (100, 0)]),
                poles=(p0, p1, p2),
                spans=(),
            ),
        ),
        total_poles=3,
        total_spans=2,
        physical_poles=(),
    )

    # The search radius is 15 from the ORIGINAL position (70), so the best
    # reachable candidate is 55; repeated passes cannot drift beyond it.
    new_result, report = optimize_poles(initial_result, context, base_config)

    assert report.moved_count == 1
    assert len(report.moves) == 1
    assert report.moves[-1].pole_id == "P1"
    assert report.moves[-1].selected_chainage_m == 55.0

    # Verify the pole geometry actually updated
    updated_route = new_result.routes[0]
    updated_p1 = updated_route.poles[1]
    assert updated_p1.distance_along_route_m == 55.0
    assert updated_p1.geometry.x == pytest.approx(55.0)


def test_optimize_poles_reverts_without_global_improvement(base_config, pole_config):
    context = PoleMicroSitingContext(
        route_geometries={"R1": LineString([(0, 0), (100, 0)])},
        route_owner_ids=frozenset(),
        constraint_layers=(),
        land_context=None,
        pole_config=pole_config,
    )

    p0 = Pole("P0", "F1", 0, Point(0, 0), "terminal", 0.0)
    # Already at target span (50): no move improves the network objective.
    p1 = Pole("P1", "F1", 1, Point(50, 0), "intermediate", 50.0)
    p2 = Pole("P2", "F1", 2, Point(100, 0), "terminal", 100.0)

    initial_result = CollectorPoleResult(
        routes=(
            PoleRouteResult(
                route_id="R1",
                feeder_id="F1",
                start_node_id="N1",
                end_node_id="N2",
                geometry=LineString([(0, 0), (100, 0)]),
                poles=(p0, p1, p2),
                spans=(),
            ),
        ),
        total_poles=3,
        total_spans=2,
        physical_poles=(),
    )

    new_result, report = optimize_poles(initial_result, context, base_config)

    assert report.moved_count == 0
    assert report.moves == ()
    assert new_result is initial_result