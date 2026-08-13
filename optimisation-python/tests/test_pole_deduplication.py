import pyproj
import pytest
from shapely.geometry import LineString, Point

from app.algorithms.pole_placement import (
    CollectorPoleResult,
    PolePlacementConfig,
    deduplicate_pole_endpoints,
    place_poles_on_network,
    place_poles_on_routes,
)
from app.algorithms.route_refinement import RefinedPhysicalRoute
from app.pnc.models import ProjectPNCNetwork


def _config(*, tolerance_m: float = 0.1) -> PolePlacementConfig:
    return PolePlacementConfig(
        target_span_m=80.0,
        min_span_m=30.0,
        max_span_m=100.0,
        coordinate_tolerance_m=tolerance_m,
    )


def _route(
    route_coordinates: list[tuple[float, float]],
    *,
    feeder_id: str,
    start_node_id: str,
    end_node_id: str,
    route_id: str | None = None,
) -> RefinedPhysicalRoute:
    geometry = LineString(route_coordinates)
    return RefinedPhysicalRoute(
        feeder_id=feeder_id,
        start_node_id=start_node_id,
        end_node_id=end_node_id,
        geometry=geometry,
        original_length_m=geometry.length,
        refined_length_m=geometry.length,
        original_traversal_cost=geometry.length,
        refined_traversal_cost=geometry.length,
        route_id=route_id,
    )


def _deduplicate(
    routes: tuple[RefinedPhysicalRoute, ...],
    *,
    tolerance_m: float = 0.1,
) -> tuple[CollectorPoleResult, CollectorPoleResult]:
    raw = place_poles_on_routes(routes, _config(tolerance_m=tolerance_m))
    deduplicated = deduplicate_pole_endpoints(raw, tolerance_m)
    return raw, deduplicated


def test_two_feeders_share_one_substation_structure() -> None:
    routes = (
        _route(
            [(0.0, 0.0), (200.0, 0.0)],
            feeder_id="F1",
            start_node_id="WTG-1",
            end_node_id="SUB-1",
        ),
        _route(
            [(0.0, 100.0), (200.0, 0.0)],
            feeder_id="F2",
            start_node_id="WTG-2",
            end_node_id="SUB-1",
        ),
    )

    raw, result = _deduplicate(routes)

    junctions = [pole for pole in result.physical_poles if pole.pole_type == "junction"]
    assert result.total_poles == raw.total_poles - 1
    assert len(junctions) == 1
    assert junctions[0].topology_node_id == "SUB-1"
    assert junctions[0].feeder_ids == ("F1", "F2")
    assert junctions[0].route_ids == ("F1_WTG-1_SUB-1", "F2_WTG-2_SUB-1")
    assert len(junctions[0].source_pole_ids) == 2


def test_two_segments_share_one_wtg_structure() -> None:
    routes = (
        _route(
            [(0.0, 0.0), (100.0, 0.0)],
            feeder_id="F1",
            start_node_id="WTG-1",
            end_node_id="WTG-7",
            route_id="SEG-001",
        ),
        _route(
            [(100.05, 0.0), (200.0, 0.0)],
            feeder_id="F1",
            start_node_id="WTG-7",
            end_node_id="WTG-2",
            route_id="SEG-002",
        ),
    )

    raw, result = _deduplicate(routes)

    shared = [
        pole for pole in result.physical_poles if pole.topology_node_id == "WTG-7"
    ]
    assert result.total_poles == raw.total_poles - 1
    assert len(shared) == 1
    assert shared[0].pole_type == "junction"
    assert shared[0].feeder_ids == ("F1",)
    assert shared[0].route_ids == ("SEG-001", "SEG-002")
    assert len(shared[0].source_pole_ids) == 2


def test_distinct_terminals_are_not_merged() -> None:
    routes = (
        _route(
            [(0.0, 0.0), (200.0, 0.0)],
            feeder_id="F1",
            start_node_id="WTG-1",
            end_node_id="SUB-1",
        ),
        _route(
            [(0.0, 100.0), (200.0, 100.0)],
            feeder_id="F2",
            start_node_id="WTG-2",
            end_node_id="SUB-2",
        ),
    )

    raw, result = _deduplicate(routes)

    assert result.total_poles == raw.total_poles
    assert not any(pole.pole_type == "junction" for pole in result.physical_poles)


def test_coincident_unrelated_terminals_are_not_merged() -> None:
    routes = (
        _route(
            [(0.0, 0.0), (200.0, 0.0)],
            feeder_id="F1",
            start_node_id="WTG-1",
            end_node_id="NODE-A",
        ),
        _route(
            [(0.0, 100.0), (200.0, 0.0)],
            feeder_id="F2",
            start_node_id="WTG-2",
            end_node_id="NODE-B",
        ),
    )

    raw, result = _deduplicate(routes)

    coincident = [
        pole
        for pole in result.physical_poles
        if pole.geometry.equals(routes[0].geometry.boundary.geoms[1])
    ]
    assert result.total_poles == raw.total_poles
    assert {pole.topology_node_id for pole in coincident} == {"NODE-A", "NODE-B"}


def test_nearby_mid_route_poles_are_not_merged() -> None:
    routes = (
        _route(
            [(0.0, 0.0), (240.0, 0.0)],
            feeder_id="F1",
            start_node_id="A1",
            end_node_id="B1",
        ),
        _route(
            [(0.0, 0.05), (240.0, 0.05)],
            feeder_id="F2",
            start_node_id="A2",
            end_node_id="B2",
        ),
    )

    raw, result = _deduplicate(routes, tolerance_m=0.1)

    assert result.total_poles == raw.total_poles
    intermediate = [
        pole for pole in result.physical_poles if pole.topology_node_id is None
    ]
    assert len(intermediate) == sum(len(route.poles) - 2 for route in raw.routes)


def test_tolerance_boundary_is_inclusive() -> None:
    at_boundary = (
        _route(
            [(0.0, 0.0), (200.0, 0.0)],
            feeder_id="F1",
            start_node_id="A",
            end_node_id="SHARED",
        ),
        _route(
            [(0.0, 100.0), (200.1, 0.0)],
            feeder_id="F2",
            start_node_id="B",
            end_node_id="SHARED",
        ),
    )
    just_beyond = (
        at_boundary[0],
        _route(
            [(0.0, 100.0), (200.100001, 0.0)],
            feeder_id="F2",
            start_node_id="B",
            end_node_id="SHARED",
        ),
    )

    raw_at, result_at = _deduplicate(at_boundary, tolerance_m=0.1)
    raw_beyond, result_beyond = _deduplicate(just_beyond, tolerance_m=0.1)

    assert result_at.total_poles == raw_at.total_poles - 1
    assert result_beyond.total_poles == raw_beyond.total_poles


def test_three_feeders_share_one_junction() -> None:
    routes = tuple(
        _route(
            [(0.0, float(index * 100)), (200.0, 0.0)],
            feeder_id=f"F{index}",
            start_node_id=f"WTG-{index}",
            end_node_id="SUB-1",
        )
        for index in range(1, 4)
    )

    raw, result = _deduplicate(routes)

    junctions = [pole for pole in result.physical_poles if pole.pole_type == "junction"]
    assert result.total_poles == raw.total_poles - 2
    assert len(junctions) == 1
    assert junctions[0].feeder_ids == ("F1", "F2", "F3")
    assert len(junctions[0].route_ids) == 3


def test_same_feeder_branch_preserves_all_segment_provenance() -> None:
    routes = tuple(
        _route(
            [(float(index * 100), 100.0), (0.0, 0.0)],
            feeder_id="F1",
            start_node_id=f"WTG-{index}",
            end_node_id="BRANCH-1",
            route_id=f"SEG-{index:03d}",
        )
        for index in range(1, 4)
    )

    raw, result = _deduplicate(routes)

    branch = next(
        pole for pole in result.physical_poles if pole.topology_node_id == "BRANCH-1"
    )
    source_ids = {
        route.poles[-1].pole_id
        for route in raw.routes
        if route.end_node_id == "BRANCH-1"
    }
    assert result.total_poles == raw.total_poles - 2
    assert branch.pole_type == "junction"
    assert branch.feeder_ids == ("F1",)
    assert branch.route_ids == ("SEG-001", "SEG-002", "SEG-003")
    assert set(branch.source_pole_ids) == source_ids


def test_deduplication_is_deterministic_and_order_independent() -> None:
    routes = (
        _route(
            [(0.0, 0.0), (200.0, 0.0)],
            feeder_id="F1",
            start_node_id="WTG-1",
            end_node_id="SUB-1",
        ),
        _route(
            [(0.0, 100.0), (200.0, 0.0)],
            feeder_id="F2",
            start_node_id="WTG-2",
            end_node_id="SUB-1",
        ),
    )

    _, first = _deduplicate(routes)
    _, repeated = _deduplicate(routes)
    _, reversed_input = _deduplicate(tuple(reversed(routes)))

    assert repeated == first
    assert reversed_input.total_poles == first.total_poles
    assert reversed_input.total_spans == first.total_spans
    assert reversed_input.physical_poles == first.physical_poles


def test_aggregate_counts_use_physical_poles_and_retain_route_spans() -> None:
    routes = (
        _route(
            [(0.0, 0.0), (200.0, 0.0)],
            feeder_id="F1",
            start_node_id="WTG-1",
            end_node_id="SUB-1",
        ),
        _route(
            [(0.0, 100.0), (200.0, 0.0)],
            feeder_id="F2",
            start_node_id="WTG-2",
            end_node_id="SUB-1",
        ),
    )

    raw, result = _deduplicate(routes)

    assert result.total_poles == len(result.physical_poles)
    assert result.total_poles < sum(len(route.poles) for route in result.routes)
    assert result.total_spans == raw.total_spans
    assert result.total_spans == sum(len(route.spans) for route in result.routes)
    assert result.routes is raw.routes
    assert all(
        deduplicated_route.spans is raw_route.spans
        for deduplicated_route, raw_route in zip(result.routes, raw.routes, strict=True)
    )


def test_strict_pairwise_clustering_prevents_transitive_overreach() -> None:
    routes = tuple(
        _route(
            [(0.0, float(index * 100)), (200.0 + offset, 0.0)],
            feeder_id=f"F{index}",
            start_node_id=f"WTG-{index}",
            end_node_id="SHARED",
        )
        for index, offset in enumerate((0.0, 0.09, 0.18), start=1)
    )

    raw, result = _deduplicate(routes, tolerance_m=0.1)

    junctions = [pole for pole in result.physical_poles if pole.pole_type == "junction"]
    shared_structures = [
        pole for pole in result.physical_poles if pole.topology_node_id == "SHARED"
    ]
    assert result.total_poles == raw.total_poles - 1
    assert len(junctions) == 1
    assert len(junctions[0].source_pole_ids) == 2
    assert len(shared_structures) == 2


def test_project_network_without_routed_segments_is_rejected() -> None:
    network = ProjectPNCNetwork(
        project_id="EMPTY",
        substation_id="SUB-1",
        substation_geometry=Point(0.0, 0.0),
        feeders=(),
        wtg_coordinates={},
        total_route_length_m=0.0,
        feeder_count=0,
        wtg_count=0,
        segment_count=0,
        crs=pyproj.CRS("EPSG:32643"),
        route_length_by_feeder={},
        wtg_count_by_feeder={},
    )

    with pytest.raises(ValueError, match="no routed segments"):
        place_poles_on_network(network, _config())
