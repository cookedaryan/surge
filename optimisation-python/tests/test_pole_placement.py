"""
tests/test_pole_placement.py

Unit tests for SURGE-PY-010 — Pole Placement Along Refined Feeder Routes.

Tests are self-contained: they construct RefinedPhysicalRoute objects directly
from Shapely LineStrings and do not require a CostSurface.
"""

import math

import pytest
from shapely.geometry import LineString

from app.algorithms.pole_placement import (
    PolePlacementConfig,
    calculate_span_count,
    place_poles_on_route,
    place_poles_on_routes,
)
from app.algorithms.route_refinement import RefinedPhysicalRoute

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_route(
    coords: list[tuple[float, float]],
    *,
    feeder_id: str = "F1",
    start_node_id: str = "WTG-1",
    end_node_id: str = "SUB-1",
) -> RefinedPhysicalRoute:
    geometry = LineString(coords)
    length = geometry.length
    return RefinedPhysicalRoute(
        feeder_id=feeder_id,
        start_node_id=start_node_id,
        end_node_id=end_node_id,
        geometry=geometry,
        original_length_m=length,
        refined_length_m=length,
        original_traversal_cost=length,
        refined_traversal_cost=length,
    )


def default_config(**overrides: float) -> PolePlacementConfig:
    base = dict(
        target_span_m=80.0,
        min_span_m=40.0,
        max_span_m=100.0,
        angle_pole_threshold_deg=10.0,
        coordinate_tolerance_m=0.1,
    )
    base.update(overrides)
    return PolePlacementConfig(**base)


# ---------------------------------------------------------------------------
# 1. test_route_endpoints_always_get_poles
# ---------------------------------------------------------------------------


def test_route_endpoints_always_get_poles() -> None:
    route = make_route([(0.0, 0.0), (245.0, 0.0)])
    config = default_config()
    result = place_poles_on_route(route, config)

    first = result.poles[0]
    last = result.poles[-1]

    assert math.isclose(first.distance_along_route_m, 0.0, abs_tol=1e-9)
    assert math.isclose(
        last.distance_along_route_m, route.geometry.length, abs_tol=1e-9
    )
    assert first.pole_type == "terminal"
    assert last.pole_type == "terminal"


# ---------------------------------------------------------------------------
# 2. test_straight_route_places_even_spans
# ---------------------------------------------------------------------------


def test_straight_route_places_even_spans() -> None:
    """
    245 m / 80 m target → round(245/80) = round(3.0625) = 3 spans of
    ~81.7 m each.  All spans must be approximately equal.
    """
    route = make_route([(0.0, 0.0), (245.0, 0.0)])
    config = default_config()
    result = place_poles_on_route(route, config)

    span_lengths = [s.span_length_m for s in result.spans]
    mean_span = sum(span_lengths) / len(span_lengths)
    for span in span_lengths:
        assert math.isclose(span, mean_span, rel_tol=1e-6), (
            f"Uneven spans: {span_lengths}"
        )


# ---------------------------------------------------------------------------
# 3. test_max_span_never_exceeded
# ---------------------------------------------------------------------------


def test_max_span_never_exceeded() -> None:
    route = make_route([(0.0, 0.0), (500.0, 0.0)])
    config = default_config(target_span_m=80.0, max_span_m=100.0)
    result = place_poles_on_route(route, config)

    for span in result.spans:
        assert span.span_length_m <= config.max_span_m + 1e-9, (
            f"Span {span.span_length_m:.3f} m exceeds max {config.max_span_m}"
        )


# ---------------------------------------------------------------------------
# 4. test_short_route_gets_two_terminal_poles
# ---------------------------------------------------------------------------


def test_short_route_gets_two_terminal_poles() -> None:
    """Route shorter than min_span_m must still produce exactly two poles."""
    route = make_route([(0.0, 0.0), (25.0, 0.0)])
    config = default_config(min_span_m=40.0)
    result = place_poles_on_route(route, config)

    assert len(result.poles) == 2
    assert result.poles[0].pole_type == "terminal"
    assert result.poles[1].pole_type == "terminal"


# ---------------------------------------------------------------------------
# 5. test_exact_target_span_route
# ---------------------------------------------------------------------------


def test_exact_target_span_route() -> None:
    """Route length equal to target_span_m → exactly 2 poles, 1 span."""
    route = make_route([(0.0, 0.0), (80.0, 0.0)])
    config = default_config(target_span_m=80.0)
    result = place_poles_on_route(route, config)

    assert len(result.poles) == 2
    assert len(result.spans) == 1
    assert math.isclose(result.spans[0].span_length_m, 80.0, abs_tol=1e-9)


# ---------------------------------------------------------------------------
# 6. test_final_span_not_tiny
# ---------------------------------------------------------------------------


def test_final_span_not_tiny() -> None:
    """
    Naive ceiling placement of 245 m / 80 m would give spans [80, 80, 80, 5].
    The round-to-nearest policy gives 3 spans of ~81.7 m — all well above 5 m.
    """
    route = make_route([(0.0, 0.0), (245.0, 0.0)])
    config = default_config()
    result = place_poles_on_route(route, config)

    for span in result.spans:
        assert span.span_length_m > 5.0, (
            f"Suspiciously small span: {span.span_length_m:.3f} m"
        )


# ---------------------------------------------------------------------------
# 7. test_poles_follow_linestring_not_chord
# ---------------------------------------------------------------------------


def test_poles_follow_linestring_not_chord() -> None:
    """
    Poles must be interpolated along the actual LineString geometry, not
    placed on the straight chord from start to end.

    For an L-shaped route:
    - Every pole must lie on the route geometry.
    - The chord from the first to the last pole is shorter than the route arc
      length (proves interpolation followed the bend, not the chord).
    """
    # L-shape: 200 m east then 200 m north → 400 m arc length
    route = make_route([(0.0, 0.0), (200.0, 0.0), (200.0, 200.0)])
    config = default_config(
        target_span_m=80.0,
        # Threshold just below 90° so the bend vertex is NOT a mandatory
        # angle pole — tests that fill poles still follow the LineString.
        angle_pole_threshold_deg=91.0,
    )
    result = place_poles_on_route(route, config)

    # All poles must lie on the route geometry (within numeric tolerance)
    for pole in result.poles:
        d = route.geometry.project(pole.geometry)
        on_route = route.geometry.interpolate(d)
        assert pole.geometry.distance(on_route) < 1e-6, (
            f"Pole at arc-dist {pole.distance_along_route_m:.1f} m "
            f"not on route geometry"
        )

    # Arc-length coverage spans the full route
    assert math.isclose(
        result.poles[-1].distance_along_route_m,
        route.geometry.length,
        abs_tol=1e-9,
    )

    # The chord from first to last pole is strictly shorter than the arc length
    # (proving interpolation followed the bent geometry, not the straight chord)
    chord_start_end = result.poles[0].geometry.distance(result.poles[-1].geometry)
    assert chord_start_end < route.geometry.length


# ---------------------------------------------------------------------------
# 8. test_significant_bend_gets_mandatory_pole
# ---------------------------------------------------------------------------


def test_significant_bend_gets_mandatory_pole() -> None:
    """
    A 90-degree bend must produce a pole at the vertex coordinate
    when angle_pole_threshold_deg ≤ 90.
    """
    # Bend at (100, 0)
    route = make_route([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)])
    config = default_config(
        target_span_m=80.0,
        angle_pole_threshold_deg=10.0,
    )
    result = place_poles_on_route(route, config)

    # The vertex is at arc-length distance 100 m from the start
    bend_distance = 100.0
    distances = [p.distance_along_route_m for p in result.poles]
    assert any(math.isclose(d, bend_distance, abs_tol=1e-6) for d in distances), (
        f"No pole found at bend distance {bend_distance}. Distances: {distances}"
    )


# ---------------------------------------------------------------------------
# 9. test_angle_pole_classification
# ---------------------------------------------------------------------------


def test_angle_pole_classification() -> None:
    """Interior vertex at a 90° bend → pole_type == 'angle'."""
    route = make_route([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)])
    config = default_config(
        target_span_m=80.0,
        angle_pole_threshold_deg=10.0,
    )
    result = place_poles_on_route(route, config)

    bend_distance = 100.0
    angle_poles = [
        p
        for p in result.poles
        if math.isclose(p.distance_along_route_m, bend_distance, abs_tol=1e-6)
    ]
    assert len(angle_poles) == 1
    assert angle_poles[0].pole_type == "angle"


# ---------------------------------------------------------------------------
# 10. test_intermediate_pole_classification
# ---------------------------------------------------------------------------


def test_intermediate_pole_classification() -> None:
    """Fill poles between mandatory structures must be classified as
    'intermediate'."""
    route = make_route([(0.0, 0.0), (400.0, 0.0)])
    config = default_config(target_span_m=80.0)
    result = place_poles_on_route(route, config)

    interior_poles = result.poles[1:-1]
    for pole in interior_poles:
        assert pole.pole_type == "intermediate", (
            f"Expected 'intermediate', got '{pole.pole_type}' for pole "
            f"at distance {pole.distance_along_route_m:.3f}"
        )


# ---------------------------------------------------------------------------
# 11. test_pole_sequence_is_ordered
# ---------------------------------------------------------------------------


def test_pole_sequence_is_ordered() -> None:
    route = make_route([(0.0, 0.0), (245.0, 0.0)])
    config = default_config()
    result = place_poles_on_route(route, config)

    for i, pole in enumerate(result.poles):
        assert pole.sequence == i + 1


# ---------------------------------------------------------------------------
# 12. test_distance_along_route_monotonic
# ---------------------------------------------------------------------------


def test_distance_along_route_monotonic() -> None:
    route = make_route([(0.0, 0.0), (100.0, 0.0), (100.0, 200.0)])
    config = default_config(target_span_m=80.0)
    result = place_poles_on_route(route, config)

    distances = [p.distance_along_route_m for p in result.poles]
    for i in range(1, len(distances)):
        assert distances[i] > distances[i - 1], (
            f"Distances not strictly increasing at index {i}: {distances}"
        )


# ---------------------------------------------------------------------------
# 13. test_span_lengths_match_pole_distances
# ---------------------------------------------------------------------------


def test_span_lengths_match_pole_distances() -> None:
    """PoleSpan.span_length_m must equal the Euclidean chord between poles."""
    route = make_route([(0.0, 0.0), (245.0, 0.0)])
    config = default_config()
    result = place_poles_on_route(route, config)

    for i, span in enumerate(result.spans):
        expected_chord = result.poles[i].geometry.distance(result.poles[i + 1].geometry)
        assert math.isclose(span.span_length_m, expected_chord, rel_tol=1e-9), (
            f"Span {i}: length {span.span_length_m} != chord {expected_chord}"
        )


# ---------------------------------------------------------------------------
# 14. test_multiple_route_sections
# ---------------------------------------------------------------------------


def test_multiple_route_sections() -> None:
    """
    Route with a 90° bend at 100 m divides into two sections:
    [0, 100] and [100, 200].  Each section is filled independently.
    Bend vertex at 100 m must appear as a pole.
    """
    route = make_route([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)])
    config = default_config(target_span_m=60.0, angle_pole_threshold_deg=10.0)
    result = place_poles_on_route(route, config)

    distances = [p.distance_along_route_m for p in result.poles]
    assert math.isclose(distances[0], 0.0, abs_tol=1e-9)
    assert math.isclose(distances[-1], 200.0, abs_tol=1e-9)
    assert any(math.isclose(d, 100.0, abs_tol=1e-6) for d in distances), (
        f"Bend at 100 m missing from {distances}"
    )


# ---------------------------------------------------------------------------
# 15. shared topology metadata retained (route-local scope)
# ---------------------------------------------------------------------------


def test_shared_topology_metadata_retained_for_network_deduplication() -> None:
    """
    Two routes sharing a topology node ID each produce their own terminal
    pole. Route-local results remain separate so their spans stay traceable;
    start_node_id / end_node_id identify them for the network-level pass.
    """
    route_a = make_route(
        [(0.0, 0.0), (240.0, 0.0)],
        feeder_id="F1",
        start_node_id="WTG-2",
        end_node_id="SUB-1",
    )
    route_b = make_route(
        [(0.0, 0.0), (160.0, 0.0)],
        feeder_id="F2",
        start_node_id="WTG-3",
        end_node_id="WTG-2",
    )
    config = default_config()
    result = place_poles_on_routes((route_a, route_b), config)

    assert result.routes[0].poles[0].pole_type == "terminal"
    assert result.routes[1].poles[-1].pole_type == "terminal"
    # Topology node info is preserved for network-level deduplication.
    assert result.routes[0].start_node_id == "WTG-2"
    assert result.routes[1].end_node_id == "WTG-2"


# ---------------------------------------------------------------------------
# 16. test_multiple_feeders_processed
# ---------------------------------------------------------------------------


def test_multiple_feeders_processed() -> None:
    """place_poles_on_routes handles routes from different feeders."""
    routes = (
        make_route([(0.0, 0.0), (240.0, 0.0)], feeder_id="F1"),
        make_route([(0.0, 0.0), (160.0, 0.0)], feeder_id="F2"),
        make_route([(0.0, 0.0), (80.0, 0.0)], feeder_id="F3"),
    )
    config = default_config()
    result = place_poles_on_routes(routes, config)

    assert len(result.routes) == 3
    feeder_ids = [r.feeder_id for r in result.routes]
    assert feeder_ids == ["F1", "F2", "F3"]


# ---------------------------------------------------------------------------
# 17. test_pole_ids_are_deterministic
# ---------------------------------------------------------------------------


def test_pole_ids_are_deterministic() -> None:
    route = make_route([(0.0, 0.0), (245.0, 0.0)], feeder_id="F1")
    config = default_config()

    result_a = place_poles_on_route(route, config)
    result_b = place_poles_on_route(route, config)

    ids_a = [p.pole_id for p in result_a.poles]
    ids_b = [p.pole_id for p in result_b.poles]
    assert ids_a == ids_b
    for pole_id in ids_a:
        assert pole_id.startswith("F1-P"), f"Unexpected pole_id format: {pole_id}"


# ---------------------------------------------------------------------------
# 18. test_total_pole_count
# ---------------------------------------------------------------------------


def test_total_pole_count() -> None:
    routes = (
        make_route([(0.0, 0.0), (240.0, 0.0)], feeder_id="F1"),
        make_route([(0.0, 0.0), (160.0, 0.0)], feeder_id="F2"),
    )
    config = default_config()
    result = place_poles_on_routes(routes, config)

    expected = sum(len(r.poles) for r in result.routes)
    assert result.total_poles == expected


# ---------------------------------------------------------------------------
# 19. test_total_span_count
# ---------------------------------------------------------------------------


def test_total_span_count() -> None:
    routes = (
        make_route([(0.0, 0.0), (240.0, 0.0)], feeder_id="F1"),
        make_route([(0.0, 0.0), (160.0, 0.0)], feeder_id="F2"),
    )
    config = default_config()
    result = place_poles_on_routes(routes, config)

    expected = sum(len(r.spans) for r in result.routes)
    assert result.total_spans == expected


# ---------------------------------------------------------------------------
# 20. test_invalid_span_configuration_rejected
# ---------------------------------------------------------------------------


def test_invalid_span_configuration_rejected() -> None:
    """PolePlacementConfig must reject nonsensical span parameters."""
    with pytest.raises(ValueError, match="target_span_m"):
        PolePlacementConfig(
            target_span_m=-10.0,
            min_span_m=40.0,
            max_span_m=100.0,
        )

    with pytest.raises(ValueError, match="min_span_m"):
        PolePlacementConfig(
            target_span_m=80.0,
            min_span_m=0.0,
            max_span_m=100.0,
        )

    with pytest.raises(ValueError, match="min_span_m"):
        PolePlacementConfig(
            target_span_m=80.0,
            min_span_m=120.0,  # > max_span_m
            max_span_m=100.0,
        )

    with pytest.raises(ValueError, match="target_span_m"):
        PolePlacementConfig(
            target_span_m=110.0,  # > max_span_m
            min_span_m=40.0,
            max_span_m=100.0,
        )

    with pytest.raises(ValueError, match="angle_pole_threshold_deg"):
        PolePlacementConfig(
            target_span_m=80.0,
            min_span_m=40.0,
            max_span_m=100.0,
            angle_pole_threshold_deg=200.0,
        )

    with pytest.raises(ValueError, match="coordinate_tolerance_m"):
        PolePlacementConfig(
            target_span_m=80.0,
            min_span_m=40.0,
            max_span_m=100.0,
            coordinate_tolerance_m=-1.0,
        )


# ---------------------------------------------------------------------------
# Deflection angle tests (P1 regression)
# ---------------------------------------------------------------------------


def test_straight_route_has_no_angle_poles() -> None:
    """
    A three-point collinear route has a 0° deflection at the middle vertex.
    With any positive threshold the middle vertex must NOT become an angle pole.
    This is a regression test for the deflection-angle sign bug where the
    supplementary formula produced 180° for a straight continuation.
    """
    route = make_route([(0.0, 0.0), (100.0, 0.0), (200.0, 0.0)])
    config = default_config(
        target_span_m=80.0,
        angle_pole_threshold_deg=10.0,
    )
    result = place_poles_on_route(route, config)

    angle_poles = [p for p in result.poles if p.pole_type == "angle"]
    assert angle_poles == [], (
        f"Expected no angle poles on straight route, "
        f"got: {[(p.pole_id, p.distance_along_route_m) for p in angle_poles]}"
    )


def test_right_angle_bend_is_classified_angle() -> None:
    """A 90° deflection must be ≥ any threshold ≤ 90°."""
    route = make_route([(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)])
    config = default_config(angle_pole_threshold_deg=89.0)
    result = place_poles_on_route(route, config)

    angle_poles = [p for p in result.poles if p.pole_type == "angle"]
    assert len(angle_poles) == 1, (
        f"Expected 1 angle pole for 90° bend, got {len(angle_poles)}"
    )


def test_shallow_bend_not_angle_pole() -> None:
    """A ~5.7° deflection must not become an angle pole with threshold=10°."""
    # tan(5.7°) ≈ 0.1, so a 10-unit offset over 100-unit run gives ~5.7°
    route = make_route([(0.0, 0.0), (100.0, 0.0), (200.0, 10.0)])
    config = default_config(angle_pole_threshold_deg=10.0)
    result = place_poles_on_route(route, config)

    angle_poles = [p for p in result.poles if p.pole_type == "angle"]
    assert angle_poles == [], (
        f"Shallow bend incorrectly classified as angle: "
        f"{[(p.pole_id, p.distance_along_route_m) for p in angle_poles]}"
    )


# ---------------------------------------------------------------------------
# Pole ID uniqueness across same-feeder routes (P1 regression)
# ---------------------------------------------------------------------------


def test_same_feeder_pole_ids_unique_across_routes() -> None:
    """
    Multiple routes on the same feeder must produce globally unique pole IDs
    when placed via place_poles_on_routes().
    """
    route_a = make_route(
        [(0.0, 0.0), (240.0, 0.0)],
        feeder_id="F1",
        start_node_id="WTG-1",
        end_node_id="WTG-2",
    )
    route_b = make_route(
        [(0.0, 0.0), (160.0, 0.0)],
        feeder_id="F1",
        start_node_id="WTG-2",
        end_node_id="SUB-1",
    )
    config = default_config()
    result = place_poles_on_routes((route_a, route_b), config)

    all_ids = [p.pole_id for r in result.routes for p in r.poles]
    assert len(all_ids) == len(set(all_ids)), (
        f"Duplicate pole IDs found: "
        f"{[pid for pid in all_ids if all_ids.count(pid) > 1]}"
    )


def test_same_feeder_sequences_are_continuous() -> None:
    """Per-feeder pole sequences must be gapless and non-repeating."""
    route_a = make_route(
        [(0.0, 0.0), (240.0, 0.0)],
        feeder_id="F1",
        start_node_id="WTG-1",
        end_node_id="WTG-2",
    )
    route_b = make_route(
        [(0.0, 0.0), (80.0, 0.0)],
        feeder_id="F1",
        start_node_id="WTG-2",
        end_node_id="SUB-1",
    )
    config = default_config()
    result = place_poles_on_routes((route_a, route_b), config)

    all_seqs = sorted(p.sequence for r in result.routes for p in r.poles)
    assert all_seqs == list(range(1, len(all_seqs) + 1)), (
        f"Sequences are not continuous: {all_seqs}"
    )


# ---------------------------------------------------------------------------
# Preferred-span policy (P2 regression)
# ---------------------------------------------------------------------------


def test_single_span_preferred_when_length_near_target() -> None:
    """
    Route length 101 m with target 100, min 90, max 120 should produce
    ONE span of 101 m (closest to target), not two spans of 50.5 m.
    """
    route = make_route([(0.0, 0.0), (101.0, 0.0)])
    config = PolePlacementConfig(
        target_span_m=100.0,
        min_span_m=90.0,
        max_span_m=120.0,
    )
    result = place_poles_on_route(route, config)

    assert len(result.spans) == 1, (
        f"Expected 1 span of 101 m, got {len(result.spans)} spans: "
        f"{[s.span_length_m for s in result.spans]}"
    )


# ---------------------------------------------------------------------------
# Non-finite configuration rejected (P2)
# ---------------------------------------------------------------------------


def test_nan_config_values_rejected() -> None:
    """NaN values must be rejected — comparisons with NaN are always False."""
    with pytest.raises(ValueError, match="target_span_m"):
        PolePlacementConfig(
            target_span_m=float("nan"),
            min_span_m=40.0,
            max_span_m=100.0,
        )

    with pytest.raises(ValueError, match="min_span_m"):
        PolePlacementConfig(
            target_span_m=80.0,
            min_span_m=float("nan"),
            max_span_m=100.0,
        )

    with pytest.raises(ValueError, match="max_span_m"):
        PolePlacementConfig(
            target_span_m=80.0,
            min_span_m=40.0,
            max_span_m=float("nan"),
        )

    with pytest.raises(ValueError, match="angle_pole_threshold_deg"):
        PolePlacementConfig(
            target_span_m=80.0,
            min_span_m=40.0,
            max_span_m=100.0,
            angle_pole_threshold_deg=float("nan"),
        )

    with pytest.raises(ValueError, match="coordinate_tolerance_m"):
        PolePlacementConfig(
            target_span_m=80.0,
            min_span_m=40.0,
            max_span_m=100.0,
            coordinate_tolerance_m=float("nan"),
        )


def test_infinite_config_values_rejected() -> None:
    with pytest.raises(ValueError, match="target_span_m"):
        PolePlacementConfig(
            target_span_m=float("inf"),
            min_span_m=40.0,
            max_span_m=100.0,
        )

    with pytest.raises(ValueError, match="max_span_m"):
        PolePlacementConfig(
            target_span_m=80.0,
            min_span_m=40.0,
            max_span_m=float("inf"),
        )


# ---------------------------------------------------------------------------
# Input validation raises ValueError (P2)
# ---------------------------------------------------------------------------


def test_zero_length_route_raises_value_error() -> None:
    """A zero-length route must raise ValueError, not AssertionError."""
    geometry = LineString([(0.0, 0.0), (0.0, 0.0)])
    # Shapely may or may not mark a zero-length LineString as invalid;
    # either way the explicit length check must fire first.
    route = RefinedPhysicalRoute(
        feeder_id="F1",
        start_node_id="A",
        end_node_id="B",
        geometry=geometry,
        original_length_m=0.0,
        refined_length_m=0.0,
        original_traversal_cost=0.0,
        refined_traversal_cost=0.0,
    )
    config = default_config()
    with pytest.raises(ValueError):
        place_poles_on_route(route, config)


# ---------------------------------------------------------------------------
# Span length is chord distance (P2)
# ---------------------------------------------------------------------------


def test_span_length_is_chord_not_arc() -> None:
    """
    For an L-shaped route with fill poles that span the bend, the reported
    span_length_m must equal the Euclidean chord between the pole Points.

    Route: 140 m east → 140 m north = 280 m arc.
    With target=80 and threshold=91° (bend NOT a mandatory pole):
      round(280/80) = round(3.5) = 4 spans of 70 m each.
      Poles at arc-distances: 0, 70, 140, 210, 280.
      The span from 140→210 crosses the 90° bend at (140, 0).
        arc delta = 70 m
        chord from (140, 0) to (140, 70) = 70 m  ← same because this span
        is entirely on the vertical leg (pole at 140 is exactly the bend).
      The span from 70→140 goes from (70, 0) to (140, 0) — entirely on the
      horizontal leg, chord = arc = 70 m.
    To force a span that genuinely crosses the bend use a target that puts a
    fill pole on each side of the vertex without landing on it.
    Use 90 m target on a 140+140 route:
      round(280/90) = round(3.11) = 3 spans of 93.3 m each.
      Poles at: 0, 93.3, 186.7, 280.
      Span 1: arc 0→93.3 m → along horizontal and round the bend.
        pole at 93.3: (93.3, 0)
        pole at 186.7: arc=186.7-140=46.7 m up the vertical → (140, 46.7)
        chord = sqrt((140-93.3)² + (46.7-0)²) = sqrt(46.7²+46.7²) ≈ 66 m
        arc delta = 93.3 m  →  chord < arc ✓
    """
    route = make_route([(0.0, 0.0), (140.0, 0.0), (140.0, 140.0)])
    config = default_config(
        target_span_m=90.0,
        angle_pole_threshold_deg=91.0,  # no mandatory angle pole at bend
    )
    result = place_poles_on_route(route, config)

    found_chord_lt_arc = False
    for i, span in enumerate(result.spans):
        arc_delta = (
            result.poles[i + 1].distance_along_route_m
            - result.poles[i].distance_along_route_m
        )
        chord = result.poles[i].geometry.distance(result.poles[i + 1].geometry)
        # Every span_length_m must equal the chord
        assert math.isclose(span.span_length_m, chord, rel_tol=1e-9), (
            f"Span {i} length {span.span_length_m} != chord {chord}"
        )
        if chord < arc_delta - 1e-6:
            found_chord_lt_arc = True

    # At least one span must have chord < arc (proves the span crosses the bend)
    span_info = [
        (
            s.span_length_m,
            result.poles[i + 1].distance_along_route_m
            - result.poles[i].distance_along_route_m,
        )
        for i, s in enumerate(result.spans)
    ]
    assert found_chord_lt_arc, (
        "Expected at least one span where chord < arc-length delta "
        f"(span crossing the route bend). Spans: {span_info}"
    )


# ---------------------------------------------------------------------------
# calculate_span_count unit tests
# ---------------------------------------------------------------------------


def test_calculate_span_count_nearest_to_target() -> None:
    """round(245/80) = 3, not ceil(245/80) = 4."""
    config = default_config(target_span_m=80.0, max_span_m=100.0)
    assert calculate_span_count(245.0, config) == 3


def test_calculate_span_count_single_span_when_near_target() -> None:
    """101 m with target 100, max 120 → 1 span (round(1.01) = 1)."""
    config = PolePlacementConfig(
        target_span_m=100.0,
        min_span_m=90.0,
        max_span_m=120.0,
    )
    assert calculate_span_count(101.0, config) == 1


def test_calculate_span_count_enforces_max_span() -> None:
    config = default_config(target_span_m=80.0, max_span_m=90.0)
    n = calculate_span_count(500.0, config)
    actual_span = 500.0 / n
    assert actual_span <= 90.0 + 1e-9


def test_calculate_span_count_exact_multiple() -> None:
    config = default_config(target_span_m=80.0, max_span_m=100.0)
    assert calculate_span_count(240.0, config) == 3


def test_calculate_span_count_rejects_non_positive_length() -> None:
    config = default_config()
    with pytest.raises(ValueError, match="route_length_m"):
        calculate_span_count(0.0, config)
    with pytest.raises(ValueError, match="route_length_m"):
        calculate_span_count(-10.0, config)
