"""Integration and unit tests for SURGE-PY-014: PNC Network Assembly.

Two public entry points under test
-----------------------------------
build_pnc_network(project_id, project, feeder_capacity_mw, cost_surface)
    Full pipeline.  Tests 1–3 and 7–8 exercise this path.

assemble_pnc_network(project_id, project, topology, refined_routes)
    Assembly from pre-computed results.  Tests 4–6 and all new tests.

Test matrix
-----------
 1  One feeder, linear chain                  — happy path, build_pnc_network
 2  Multiple feeders, correct membership      — happy path, build_pnc_network
 3  Branched feeder — topology survives       — happy path, build_pnc_network
 4  Missing physical route → UNROUTED_TOPOLOGY_EDGE
 5  Orphan WTG → ORPHAN_WTG
 6  Duplicate WTG assignment → DUPLICATE_WTG_ASSIGNMENT
 7  GeoJSON output structure & properties     — build_pnc_network
 8  Determinism — identical input → identical output

New tests added for the two-boundary refactor
 9  build_pnc_network delegates to assemble_pnc_network
10  assemble_pnc_network does not re-run route_collector_topology
11  assemble_pnc_network does not re-run refine_routing_result
12  Both paths produce equivalent PNC networks
13  Extra route rejected → UNKNOWN_FEEDER_SEGMENT
14  Duplicate route rejected → DUPLICATE_SEGMENT_ID
15  Reversed-duplicate route rejected → DUPLICATE_SEGMENT_ID
16  Wrong-feeder route rejected → UNKNOWN_FEEDER_SEGMENT
17  Route endpoint absent from feeder topology → UNKNOWN_FEEDER_SEGMENT
18  Invalid geometry (empty LineString) → UNROUTED_TOPOLOGY_EDGE
19  Zero / non-positive refined_length_m → UNROUTED_TOPOLOGY_EDGE
20  geometry.length inconsistent with refined_length_m → UNROUTED_TOPOLOGY_EDGE
21  Incorrect aggregate total in RefinedRoutingResult → ValueError
22  Deterministic IDs and ordering are identical through both paths
"""

import math
from unittest.mock import patch

import networkx as nx
import numpy as np
import pyproj
import pytest
from affine import Affine
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
    FeederTopology,
    build_feeder_mst,
)
from app.algorithms.wtg_grouping import group_wtgs
from app.gis.cost_surface import CostSurface
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine
from app.pnc.assembly import assemble_pnc_network, build_pnc_network
from app.pnc.errors import PNCAssemblyError, PNCAssemblyErrorCode
from app.pnc.geojson import network_to_feature_collection
from app.pnc.models import ProjectPNCNetwork

# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

_CRS = pyproj.CRS("EPSG:32630")


@pytest.fixture
def cost_surface() -> CostSurface:
    """40 × 40 uniform cost surface covering (0, 0) → (400, 400) m."""
    return CostSurface(
        costs=np.ones((40, 40), dtype=np.float32),
        transform=Affine.translation(0, 400) * Affine.scale(10, -10),
        crs=_CRS,
        width=40,
        height=40,
        resolution_m=10.0,
    )


def _make_project(*turbines: tuple[str, float, float]) -> ProjectSpatialData:
    """Build a ProjectSpatialData from (turbine_id, x, y) triples.

    Substation at (5, 395) — top-left of the cost surface.
    All capacities are 5 MW.
    """
    wtgs = tuple(
        WindTurbine(turbine_id=tid, location=Point(x, y), capacity_mw=5.0)
        for tid, x, y in turbines
    )
    sub = Substation(
        substation_id="SUB1", location=Point(5.0, 395.0), capacity_mw=1000.0
    )
    return ProjectSpatialData(turbines=wtgs, substation=sub, projected_crs=_CRS)


def _run_pipeline_stages(
    project: ProjectSpatialData,
    feeder_capacity_mw: float,
    cost_surface: CostSurface,
) -> tuple[CollectorTopologyResult, RefinedRoutingResult]:
    """Execute grouping → graph → MST → routing → refinement independently."""
    grouping = group_wtgs(project, feeder_capacity_mw)
    graph = build_project_graph(project)
    topology = build_feeder_mst(graph, grouping)
    physical_routes = route_collector_topology(topology, graph, cost_surface)
    refined_routes = refine_routing_result(physical_routes, cost_surface)
    return topology, refined_routes


def _make_single_edge_topology(
    sub_id: str, w_id: str, fid: str = "F1"
) -> CollectorTopologyResult:
    mst = nx.Graph()
    mst.add_edge(sub_id, w_id, distance_m=40.0, weight=40.0)
    ft = FeederTopology(
        feeder_id=fid,
        node_ids=(sub_id, w_id),
        total_capacity_mw=5.0,
        total_length_m=40.0,
        mst_edges=(tuple(sorted((sub_id, w_id))),),
        mst_graph=mst,
    )
    return CollectorTopologyResult(feeders=(ft,))


def _make_simple_route(
    fid: str,
    start: str,
    end: str,
    length: float = 40.0,
    geom: LineString | None = None,
) -> RefinedPhysicalRoute:
    if geom is None:
        geom = LineString([(5.0, 395.0), (5.0 + length, 395.0)])
    return RefinedPhysicalRoute(
        feeder_id=fid,
        start_node_id=start,
        end_node_id=end,
        geometry=geom,
        original_length_m=length,
        refined_length_m=length,
        original_traversal_cost=length,
        refined_traversal_cost=length,
    )


def _make_single_route_result(
    fid: str, sub_id: str, w_id: str, length: float = 40.0
) -> RefinedRoutingResult:
    route = _make_simple_route(fid, sub_id, w_id, length)
    return RefinedRoutingResult(
        routes=(route,),
        total_original_length_m=length,
        total_refined_length_m=length,
    )


# ---------------------------------------------------------------------------
# Test 1 — One feeder, linear chain
# ---------------------------------------------------------------------------


class TestOneFeederLinearChain:
    """SUB → T1 → T2 → T3."""

    @pytest.fixture
    def project(self) -> ProjectSpatialData:
        return _make_project(
            ("T1", 45.0, 395.0),
            ("T2", 95.0, 395.0),
            ("T3", 145.0, 395.0),
        )

    def test_feeder_count(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P001", project, 20.0, cost_surface)
        assert n.feeder_count == 1

    def test_wtg_count(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P001", project, 20.0, cost_surface)
        assert n.wtg_count == 3

    def test_all_wtgs_present(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P001", project, 20.0, cost_surface)
        node_ids = set(n.wtg_coordinates.keys())
        assert turbine_node_id("T1") in node_ids
        assert turbine_node_id("T2") in node_ids
        assert turbine_node_id("T3") in node_ids

    def test_segment_count_equals_edges(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P001", project, 20.0, cost_surface)
        assert n.segment_count == 3  # 4 nodes → 3 edges in a tree

    def test_all_segments_have_routes(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P001", project, 20.0, cost_surface)
        for feeder in n.feeders:
            for seg in feeder.segments:
                assert seg.route_length_m > 0
                assert not seg.route_geometry.is_empty

    def test_feeder_id_format(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P001", project, 20.0, cost_surface)
        assert n.feeders[0].feeder_id == "FDR-001"

    def test_segment_id_format(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P001", project, 20.0, cost_surface)
        for seg in n.feeders[0].segments:
            assert seg.segment_id.startswith("SEG-FDR001-")

    def test_total_length_matches_feeder_sum(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P001", project, 20.0, cost_surface)
        feeder_sum = math.fsum(f.total_length_m for f in n.feeders)
        assert math.isclose(n.total_route_length_m, feeder_sum, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Test 2 — Multiple feeders
# ---------------------------------------------------------------------------


class TestMultipleFeeders:
    @pytest.fixture
    def project(self) -> ProjectSpatialData:
        return _make_project(
            ("T1", 45.0, 395.0),
            ("T2", 95.0, 395.0),
            ("T3", 205.0, 395.0),
            ("T4", 255.0, 395.0),
        )

    def test_feeder_count(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P002", project, 12.0, cost_surface)
        assert n.feeder_count == 2

    def test_each_wtg_belongs_to_exactly_one_feeder(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P002", project, 12.0, cost_surface)
        all_assigned = [wid for feeder in n.feeders for wid in feeder.wtg_ids]
        assert len(all_assigned) == len(set(all_assigned))
        assert len(all_assigned) == 4

    def test_feeder_ids_are_unique(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P002", project, 12.0, cost_surface)
        ids = [f.feeder_id for f in n.feeders]
        assert len(ids) == len(set(ids))

    def test_every_feeder_has_substation(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P002", project, 12.0, cost_surface)
        sub_id = substation_node_id("SUB1")
        for feeder in n.feeders:
            assert feeder.substation_id == sub_id
            assert sub_id in feeder.mst_graph

    def test_metrics_by_feeder_keys(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P002", project, 12.0, cost_surface)
        for feeder in n.feeders:
            assert feeder.feeder_id in n.route_length_by_feeder
            assert feeder.feeder_id in n.wtg_count_by_feeder


# ---------------------------------------------------------------------------
# Test 3 — Branched feeder topology survives assembly
# ---------------------------------------------------------------------------


class TestBranchedFeederTopology:
    @pytest.fixture
    def project(self) -> ProjectSpatialData:
        return _make_project(
            ("T1", 45.0, 395.0),
            ("T2", 95.0, 355.0),
            ("T3", 95.0, 395.0),
        )

    def test_mst_graph_is_tree(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P003", project, 20.0, cost_surface)
        for feeder in n.feeders:
            assert nx.is_tree(feeder.mst_graph)

    def test_all_wtgs_reachable_from_substation(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P003", project, 20.0, cost_surface)
        sub_id = substation_node_id("SUB1")
        for feeder in n.feeders:
            for wtg_id in feeder.wtg_ids:
                assert nx.has_path(feeder.mst_graph, sub_id, wtg_id)

    def test_ordered_node_ids_starts_with_substation(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P003", project, 20.0, cost_surface)
        sub_id = substation_node_id("SUB1")
        for feeder in n.feeders:
            assert feeder.ordered_node_ids[0] == sub_id

    def test_ordered_node_ids_contains_all_nodes(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n = build_pnc_network("P003", project, 20.0, cost_surface)
        for feeder in n.feeders:
            assert set(feeder.mst_graph.nodes) == set(feeder.ordered_node_ids)


# ---------------------------------------------------------------------------
# Test 4 — Missing physical route → must fail
# ---------------------------------------------------------------------------


class TestMissingPhysicalRoute:
    def test_raises_unrouted_topology_edge(self) -> None:
        sub_id = substation_node_id("SUB1")
        w1_id = turbine_node_id("T1")
        w2_id = turbine_node_id("T2")

        project = ProjectSpatialData(
            turbines=(
                WindTurbine("T1", Point(45.0, 395.0), 5.0),
                WindTurbine("T2", Point(95.0, 395.0), 5.0),
            ),
            substation=Substation("SUB1", Point(5.0, 395.0), 1000.0),
            projected_crs=_CRS,
        )

        mst = nx.Graph()
        mst.add_edge(sub_id, w1_id, distance_m=40.0, weight=40.0)
        mst.add_edge(w1_id, w2_id, distance_m=50.0, weight=50.0)
        ft = FeederTopology(
            feeder_id="F1",
            node_ids=(sub_id, w1_id, w2_id),
            total_capacity_mw=10.0,
            total_length_m=90.0,
            mst_edges=(
                tuple(sorted((sub_id, w1_id))),
                tuple(sorted((w1_id, w2_id))),
            ),
            mst_graph=mst,
        )
        topology = CollectorTopologyResult(feeders=(ft,))

        # Only one of the two edges has a route
        partial_routing = _make_single_route_result("F1", sub_id, w1_id, 40.0)

        with pytest.raises(PNCAssemblyError) as exc:
            assemble_pnc_network("P004", project, topology, partial_routing)
        assert exc.value.code == PNCAssemblyErrorCode.UNROUTED_TOPOLOGY_EDGE


# ---------------------------------------------------------------------------
# Test 5 — Orphan WTG → must fail
# ---------------------------------------------------------------------------


class TestOrphanWtg:
    def test_raises_orphan_wtg(self) -> None:
        sub_id = substation_node_id("SUB1")
        w1_id = turbine_node_id("T1")

        # Project has T1 and T2, but topology only covers T1
        project = ProjectSpatialData(
            turbines=(
                WindTurbine("T1", Point(45.0, 395.0), 5.0),
                WindTurbine("T2", Point(95.0, 395.0), 5.0),
            ),
            substation=Substation("SUB1", Point(5.0, 395.0), 1000.0),
            projected_crs=_CRS,
        )

        topology = _make_single_edge_topology(sub_id, w1_id)
        routing = _make_single_route_result("F1", sub_id, w1_id)

        with pytest.raises(PNCAssemblyError) as exc:
            assemble_pnc_network("P005", project, topology, routing)
        assert exc.value.code == PNCAssemblyErrorCode.ORPHAN_WTG


# ---------------------------------------------------------------------------
# Test 6 — Duplicate WTG assignment → must fail
# ---------------------------------------------------------------------------


class TestDuplicateWtgAssignment:
    def test_raises_duplicate_wtg_assignment(self) -> None:
        sub_id = substation_node_id("SUB1")
        w1_id = turbine_node_id("T1")

        project = ProjectSpatialData(
            turbines=(WindTurbine("T1", Point(45.0, 395.0), 5.0),),
            substation=Substation("SUB1", Point(5.0, 395.0), 1000.0),
            projected_crs=_CRS,
        )

        # Both F1 and F2 claim T1
        topology = CollectorTopologyResult(
            feeders=(
                _make_single_edge_topology(sub_id, w1_id, "F1").feeders[0],
                _make_single_edge_topology(sub_id, w1_id, "F2").feeders[0],
            )
        )
        routing = RefinedRoutingResult(
            routes=(
                _make_simple_route("F1", sub_id, w1_id),
                _make_simple_route("F2", sub_id, w1_id),
            ),
            total_original_length_m=80.0,
            total_refined_length_m=80.0,
        )

        with pytest.raises(PNCAssemblyError) as exc:
            assemble_pnc_network("P006", project, topology, routing)
        assert exc.value.code == PNCAssemblyErrorCode.DUPLICATE_WTG_ASSIGNMENT


# ---------------------------------------------------------------------------
# Test 7 — GeoJSON output
# ---------------------------------------------------------------------------


class TestGeoJsonOutput:
    @pytest.fixture
    def network(self, cost_surface: CostSurface) -> ProjectPNCNetwork:
        project = _make_project(("T1", 45.0, 395.0), ("T2", 95.0, 395.0))
        return build_pnc_network("P007", project, 20.0, cost_surface)

    def test_type_is_feature_collection(self, network: ProjectPNCNetwork) -> None:
        assert network_to_feature_collection(network)["type"] == "FeatureCollection"

    def test_contains_substation(self, network: ProjectPNCNetwork) -> None:
        fc = network_to_feature_collection(network)
        subs = [
            f
            for f in fc["features"]
            if f["properties"].get("feature_type") == "pnc_substation"
        ]
        assert len(subs) == 1
        assert subs[0]["geometry"]["type"] == "Point"

    def test_contains_all_wtgs(self, network: ProjectPNCNetwork) -> None:
        fc = network_to_feature_collection(network)
        wtgs = [
            f
            for f in fc["features"]
            if f["properties"].get("feature_type") == "pnc_wtg"
        ]
        assert len(wtgs) == 2
        for f in wtgs:
            assert "wtg_id" in f["properties"]
            assert "feeder_id" in f["properties"]

    def test_contains_all_segments(self, network: ProjectPNCNetwork) -> None:
        fc = network_to_feature_collection(network)
        segs = [
            f
            for f in fc["features"]
            if f["properties"].get("feature_type") == "pnc_segment"
        ]
        assert len(segs) == network.segment_count
        for f in segs:
            props = f["properties"]
            for key in ("segment_id", "feeder_id", "from_node", "to_node", "length_m"):
                assert key in props
            assert f["geometry"]["type"] == "LineString"

    def test_feature_count(self, network: ProjectPNCNetwork) -> None:
        fc = network_to_feature_collection(network)
        assert len(fc["features"]) == 1 + network.wtg_count + network.segment_count

    def test_no_crs_conversion_when_output_crs_none(
        self, network: ProjectPNCNetwork
    ) -> None:
        fc = network_to_feature_collection(network, output_crs=None)
        sub_feat = next(
            f
            for f in fc["features"]
            if f["properties"]["feature_type"] == "pnc_substation"
        )
        coords = sub_feat["geometry"]["coordinates"]
        assert math.isclose(coords[0], 5.0, abs_tol=0.1)
        assert math.isclose(coords[1], 395.0, abs_tol=0.1)


# ---------------------------------------------------------------------------
# Test 8 — Determinism (build_pnc_network path)
# ---------------------------------------------------------------------------


class TestDeterminism:
    @pytest.fixture
    def project(self) -> ProjectSpatialData:
        return _make_project(
            ("T1", 45.0, 395.0),
            ("T2", 95.0, 355.0),
            ("T3", 145.0, 395.0),
            ("T4", 205.0, 355.0),
        )

    def test_feeder_ids_are_stable(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n1 = build_pnc_network("P008", project, 12.0, cost_surface)
        n2 = build_pnc_network("P008", project, 12.0, cost_surface)
        assert [f.feeder_id for f in n1.feeders] == [f.feeder_id for f in n2.feeders]

    def test_segment_ids_are_stable(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n1 = build_pnc_network("P008", project, 12.0, cost_surface)
        n2 = build_pnc_network("P008", project, 12.0, cost_surface)
        segs1 = sorted(s.segment_id for f in n1.feeders for s in f.segments)
        segs2 = sorted(s.segment_id for f in n2.feeders for s in f.segments)
        assert segs1 == segs2

    def test_wtg_assignments_are_stable(
        self, project: ProjectSpatialData, cost_surface: CostSurface
    ) -> None:
        n1 = build_pnc_network("P008", project, 12.0, cost_surface)
        n2 = build_pnc_network("P008", project, 12.0, cost_surface)
        for f1, f2 in zip(
            sorted(n1.feeders, key=lambda f: f.feeder_id),
            sorted(n2.feeders, key=lambda f: f.feeder_id),
            strict=True,
        ):
            assert f1.wtg_ids == f2.wtg_ids


# ---------------------------------------------------------------------------
# Test 9 — build_pnc_network delegates to assemble_pnc_network
# ---------------------------------------------------------------------------


class TestBuilderDelegation:
    """build_pnc_network must call assemble_pnc_network exactly once."""

    def test_builder_calls_assemble(self, cost_surface: CostSurface) -> None:
        project = _make_project(("T1", 45.0, 395.0), ("T2", 95.0, 395.0))

        with patch(
            "app.pnc.assembly.assemble_pnc_network",
            wraps=assemble_pnc_network,
        ) as spy:
            build_pnc_network("P009", project, 20.0, cost_surface)

        spy.assert_called_once()
        _, kwargs = spy.call_args
        assert kwargs["project_id"] == "P009"
        assert kwargs["project"] is project


# ---------------------------------------------------------------------------
# Test 10 & 11 — assemble_pnc_network does not re-run routing/refinement
# ---------------------------------------------------------------------------


class TestPrecomputedPathDoesNotRerunRouting:
    """Calling assemble_pnc_network must not invoke A* or refinement."""

    @pytest.fixture
    def precomputed(
        self, cost_surface: CostSurface
    ) -> tuple[ProjectSpatialData, CollectorTopologyResult, RefinedRoutingResult]:
        project = _make_project(("T1", 45.0, 395.0), ("T2", 95.0, 395.0))
        topology, refined_routes = _run_pipeline_stages(project, 20.0, cost_surface)
        return project, topology, refined_routes

    def test_route_collector_topology_not_called(
        self,
        precomputed: tuple[
            ProjectSpatialData, CollectorTopologyResult, RefinedRoutingResult
        ],
    ) -> None:
        project, topology, refined_routes = precomputed
        with patch("app.pnc.assembly.route_collector_topology") as mock_routing:
            assemble_pnc_network("P010", project, topology, refined_routes)
        mock_routing.assert_not_called()

    def test_refine_routing_result_not_called(
        self,
        precomputed: tuple[
            ProjectSpatialData, CollectorTopologyResult, RefinedRoutingResult
        ],
    ) -> None:
        project, topology, refined_routes = precomputed
        with patch("app.pnc.assembly.refine_routing_result") as mock_refine:
            assemble_pnc_network("P011", project, topology, refined_routes)
        mock_refine.assert_not_called()


# ---------------------------------------------------------------------------
# Test 12 — Both paths produce equivalent PNC networks
# ---------------------------------------------------------------------------


class TestTwoPathEquivalence:
    """build_pnc_network and assemble_pnc_network produce the same result."""

    def test_equivalent_networks(self, cost_surface: CostSurface) -> None:
        project = _make_project(
            ("T1", 45.0, 395.0),
            ("T2", 95.0, 395.0),
            ("T3", 205.0, 395.0),
            ("T4", 255.0, 395.0),
        )
        topology, refined_routes = _run_pipeline_stages(project, 12.0, cost_surface)

        n_full = build_pnc_network("EQUIV", project, 12.0, cost_surface)
        n_pre = assemble_pnc_network("EQUIV", project, topology, refined_routes)

        assert n_full.feeder_count == n_pre.feeder_count
        assert n_full.wtg_count == n_pre.wtg_count
        assert n_full.segment_count == n_pre.segment_count

        fids_full = sorted(f.feeder_id for f in n_full.feeders)
        fids_pre = sorted(f.feeder_id for f in n_pre.feeders)
        assert fids_full == fids_pre

        segs_full = sorted(s.segment_id for f in n_full.feeders for s in f.segments)
        segs_pre = sorted(s.segment_id for f in n_pre.feeders for s in f.segments)
        assert segs_full == segs_pre

    def test_determinism_through_both_paths(self, cost_surface: CostSurface) -> None:
        """Identical inputs produce identical IDs through both paths."""
        project = _make_project(("T1", 45.0, 395.0), ("T2", 145.0, 395.0))
        topology, refined_routes = _run_pipeline_stages(project, 20.0, cost_surface)

        n1 = build_pnc_network("DET", project, 20.0, cost_surface)
        n2 = assemble_pnc_network("DET", project, topology, refined_routes)

        assert [f.feeder_id for f in n1.feeders] == [f.feeder_id for f in n2.feeders]
        assert [f.ordered_node_ids for f in n1.feeders] == [
            f.ordered_node_ids for f in n2.feeders
        ]


# ---------------------------------------------------------------------------
# Tests 13–21 — Pre-computed route validation
# ---------------------------------------------------------------------------


class TestPrecomputedRouteValidation:
    """assemble_pnc_network rejects invalid precomputed routes."""

    # --- fixtures -----------------------------------------------------------

    @pytest.fixture
    def one_wtg_project(self) -> ProjectSpatialData:
        return ProjectSpatialData(
            turbines=(WindTurbine("T1", Point(45.0, 395.0), 5.0),),
            substation=Substation("SUB1", Point(5.0, 395.0), 1000.0),
            projected_crs=_CRS,
        )

    @pytest.fixture
    def one_wtg_setup(
        self, one_wtg_project: ProjectSpatialData
    ) -> tuple[ProjectSpatialData, str, str, CollectorTopologyResult]:
        sub_id = substation_node_id("SUB1")
        w1_id = turbine_node_id("T1")
        topology = _make_single_edge_topology(sub_id, w1_id)
        return one_wtg_project, sub_id, w1_id, topology

    # --- Test 13: extra route -----------------------------------------------

    def test_extra_route_rejected(
        self,
        one_wtg_setup: tuple[ProjectSpatialData, str, str, CollectorTopologyResult],
    ) -> None:
        project, sub_id, w1_id, topology = one_wtg_setup
        # Topology has only SUB→T1; add an extra phantom route
        extra_node = turbine_node_id("T_PHANTOM")
        routing = RefinedRoutingResult(
            routes=(
                _make_simple_route("F1", sub_id, w1_id, 40.0),
                _make_simple_route("F1", w1_id, extra_node, 30.0),
            ),
            total_original_length_m=70.0,
            total_refined_length_m=70.0,
        )
        with pytest.raises(PNCAssemblyError) as exc:
            assemble_pnc_network("EX13", project, topology, routing)
        assert exc.value.code == PNCAssemblyErrorCode.UNKNOWN_FEEDER_SEGMENT

    # --- Test 14: duplicate route (same direction) -------------------------

    def test_duplicate_route_rejected(
        self,
        one_wtg_setup: tuple[ProjectSpatialData, str, str, CollectorTopologyResult],
    ) -> None:
        project, sub_id, w1_id, topology = one_wtg_setup
        routing = RefinedRoutingResult(
            routes=(
                _make_simple_route("F1", sub_id, w1_id, 40.0),
                _make_simple_route("F1", sub_id, w1_id, 40.0),  # duplicate
            ),
            total_original_length_m=80.0,
            total_refined_length_m=80.0,
        )
        with pytest.raises(PNCAssemblyError) as exc:
            assemble_pnc_network("EX14", project, topology, routing)
        assert exc.value.code == PNCAssemblyErrorCode.DUPLICATE_SEGMENT_ID

    # --- Test 15: reversed duplicate route ---------------------------------

    def test_reversed_duplicate_route_rejected(
        self,
        one_wtg_setup: tuple[ProjectSpatialData, str, str, CollectorTopologyResult],
    ) -> None:
        project, sub_id, w1_id, topology = one_wtg_setup
        # Second route has start/end swapped — still same canonical edge
        routing = RefinedRoutingResult(
            routes=(
                _make_simple_route("F1", sub_id, w1_id, 40.0),
                _make_simple_route("F1", w1_id, sub_id, 40.0),  # reversed
            ),
            total_original_length_m=80.0,
            total_refined_length_m=80.0,
        )
        with pytest.raises(PNCAssemblyError) as exc:
            assemble_pnc_network("EX15", project, topology, routing)
        assert exc.value.code == PNCAssemblyErrorCode.DUPLICATE_SEGMENT_ID

    # --- Test 16: wrong-feeder route ----------------------------------------

    def test_wrong_feeder_route_rejected(
        self,
        one_wtg_setup: tuple[ProjectSpatialData, str, str, CollectorTopologyResult],
    ) -> None:
        project, sub_id, w1_id, topology = one_wtg_setup
        # Route claims feeder "F_WRONG" which doesn't exist in topology
        routing = RefinedRoutingResult(
            routes=(_make_simple_route("F_WRONG", sub_id, w1_id, 40.0),),
            total_original_length_m=40.0,
            total_refined_length_m=40.0,
        )
        with pytest.raises(PNCAssemblyError) as exc:
            assemble_pnc_network("EX16", project, topology, routing)
        assert exc.value.code == PNCAssemblyErrorCode.UNKNOWN_FEEDER_SEGMENT

    # --- Test 17: endpoint absent from feeder topology ----------------------

    def test_endpoint_not_in_feeder_topology_rejected(
        self,
        one_wtg_setup: tuple[ProjectSpatialData, str, str, CollectorTopologyResult],
    ) -> None:
        project, sub_id, w1_id, topology = one_wtg_setup
        outsider = turbine_node_id("T_OUTSIDE")
        # Route's end_node is not in the feeder
        routing = RefinedRoutingResult(
            routes=(_make_simple_route("F1", sub_id, outsider, 40.0),),
            total_original_length_m=40.0,
            total_refined_length_m=40.0,
        )
        with pytest.raises(PNCAssemblyError) as exc:
            assemble_pnc_network("EX17", project, topology, routing)
        assert exc.value.code == PNCAssemblyErrorCode.UNKNOWN_FEEDER_SEGMENT

    # --- Test 18: invalid geometry (empty LineString) -----------------------

    def test_invalid_geometry_rejected(
        self,
        one_wtg_setup: tuple[ProjectSpatialData, str, str, CollectorTopologyResult],
    ) -> None:
        project, sub_id, w1_id, topology = one_wtg_setup
        route = RefinedPhysicalRoute(
            feeder_id="F1",
            start_node_id=sub_id,
            end_node_id=w1_id,
            geometry=LineString(),  # empty — invalid
            original_length_m=40.0,
            refined_length_m=40.0,
            original_traversal_cost=40.0,
            refined_traversal_cost=40.0,
        )
        routing = RefinedRoutingResult(
            routes=(route,),
            total_original_length_m=40.0,
            total_refined_length_m=40.0,
        )
        with pytest.raises(PNCAssemblyError) as exc:
            assemble_pnc_network("EX18", project, topology, routing)
        assert exc.value.code == PNCAssemblyErrorCode.UNROUTED_TOPOLOGY_EDGE

    # --- Test 19: zero / non-positive refined_length_m ----------------------

    def test_zero_length_rejected(
        self,
        one_wtg_setup: tuple[ProjectSpatialData, str, str, CollectorTopologyResult],
    ) -> None:
        project, sub_id, w1_id, topology = one_wtg_setup
        route = RefinedPhysicalRoute(
            feeder_id="F1",
            start_node_id=sub_id,
            end_node_id=w1_id,
            geometry=LineString([(5.0, 395.0), (45.0, 395.0)]),
            original_length_m=40.0,
            refined_length_m=0.0,  # invalid: zero length
            original_traversal_cost=40.0,
            refined_traversal_cost=0.0,
        )
        routing = RefinedRoutingResult(
            routes=(route,),
            total_original_length_m=40.0,
            total_refined_length_m=0.0,
        )
        with pytest.raises(PNCAssemblyError) as exc:
            assemble_pnc_network("EX19", project, topology, routing)
        assert exc.value.code == PNCAssemblyErrorCode.UNROUTED_TOPOLOGY_EDGE

    # --- Test 20: geometry.length ≠ refined_length_m -----------------------

    def test_length_geometry_mismatch_rejected(
        self,
        one_wtg_setup: tuple[ProjectSpatialData, str, str, CollectorTopologyResult],
    ) -> None:
        project, sub_id, w1_id, topology = one_wtg_setup
        geom = LineString([(5.0, 395.0), (45.0, 395.0)])  # length ≈ 40 m
        route = RefinedPhysicalRoute(
            feeder_id="F1",
            start_node_id=sub_id,
            end_node_id=w1_id,
            geometry=geom,
            original_length_m=40.0,
            refined_length_m=999.0,  # wildly inconsistent
            original_traversal_cost=40.0,
            refined_traversal_cost=40.0,
        )
        routing = RefinedRoutingResult(
            routes=(route,),
            total_original_length_m=40.0,
            total_refined_length_m=999.0,
        )
        with pytest.raises(PNCAssemblyError) as exc:
            assemble_pnc_network("EX20", project, topology, routing)
        assert exc.value.code == PNCAssemblyErrorCode.UNROUTED_TOPOLOGY_EDGE

    # --- Test 21: incorrect aggregate total --------------------------------

    def test_incorrect_aggregate_total_rejected(
        self,
        one_wtg_setup: tuple[ProjectSpatialData, str, str, CollectorTopologyResult],
    ) -> None:
        project, sub_id, w1_id, topology = one_wtg_setup
        geom = LineString([(5.0, 395.0), (45.0, 395.0)])
        route = RefinedPhysicalRoute(
            feeder_id="F1",
            start_node_id=sub_id,
            end_node_id=w1_id,
            geometry=geom,
            original_length_m=40.0,
            refined_length_m=geom.length,
            original_traversal_cost=40.0,
            refined_traversal_cost=40.0,
        )
        routing = RefinedRoutingResult(
            routes=(route,),
            total_original_length_m=40.0,
            total_refined_length_m=9999.0,  # wrong total
        )
        with pytest.raises(ValueError, match="total_refined_length_m"):
            assemble_pnc_network("EX21", project, topology, routing)
