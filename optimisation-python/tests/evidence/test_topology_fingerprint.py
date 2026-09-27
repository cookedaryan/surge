"""WP0B-5: topology fingerprint canonicaliser, version 1."""

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import networkx as nx
import numpy as np
import pyproj
import pytest
from affine import Affine
from shapely.geometry import Point

from app.contracts.response import DesignTruth
from app.evidence.cohort import CohortCandidate, build_cohort
from app.evidence.fingerprints.final_design import (
    FinalDesign,
    FinalDesignFingerprinter,
)
from app.evidence.fingerprints.geometry import GeometryFingerprinter
from app.evidence.fingerprints.topology import (
    TOPOLOGY_FINGERPRINT_VERSION,
    TopologyFingerprinter,
    TopologyFingerprintError,
    canonical_topology_payload,
)
from app.gis.cost_surface import CostSurface
from app.models.spatial import ProjectSpatialData, Substation, WindTurbine
from app.optimisation.scenario_models import PNCScenario
from app.pnc.assembly import build_pnc_network
from app.pnc.models import PNCFeeder, ProjectPNCNetwork
from tests.evidence.test_cohort_runner import evidence
from tests.evidence.test_final_design_fingerprint import truth_for
from tests.evidence.test_geometry_fingerprint import (
    DEFAULT_FEEDERS,
    DEFAULT_TURBINES,
    Line,
    build_network,
)

# Golden vector for ``build_network()``. It changes only with a new
# TOPOLOGY_FINGERPRINT_VERSION; a failure at the same version is a regression.
GOLDEN_V1 = (
    "topology:1:80921dcbbcfe0f44dbc6543487b7a05fa6ea535a68b1bb54d9d1a0ff65cebdc3"
)

fingerprint = TopologyFingerprinter()

Feeders = dict[str, list[tuple[str, str, Line]]]


def _feeder(network: ProjectPNCNetwork, feeder_id: str) -> PNCFeeder:
    return next(f for f in network.feeders if f.feeder_id == feeder_id)


def _with_feeder(
    network: ProjectPNCNetwork, feeder_id: str, **changes: object
) -> ProjectPNCNetwork:
    feeders = tuple(
        replace(f, **changes) if f.feeder_id == feeder_id else f  # type: ignore[arg-type]
        for f in network.feeders
    )
    return replace(network, feeders=feeders)


# --- format, golden vector, payload ---------------------------------------------------


def test_fingerprinter_satisfies_the_c4_format() -> None:
    kind, version, digest = fingerprint(build_network()).split(":")
    assert (kind, version) == ("topology", TOPOLOGY_FINGERPRINT_VERSION)
    assert len(digest) == 64 and digest == digest.lower()
    int(digest, 16)
    assert (fingerprint.kind, fingerprint.version) == ("topology", "1")


def test_golden_vector_v1() -> None:
    assert fingerprint(build_network()) == GOLDEN_V1


def test_canonical_payload_spells_out_the_declared_rules() -> None:
    assert canonical_topology_payload(build_network()) == {
        "canonicaliser": "topology",
        "version": "1",
        "substation": "substation:SS",
        "nodes": ["substation:SS", "wtg:T1", "wtg:T2", "wtg:T3"],
        # Each edge is written low-high; feeders are sorted by their WTGs, and
        # carry no feeder ID.
        "feeders": [
            {
                "wtgs": ["wtg:T1", "wtg:T2"],
                "edges": [["substation:SS", "wtg:T1"], ["wtg:T1", "wtg:T2"]],
            },
            {"wtgs": ["wtg:T3"], "edges": [["substation:SS", "wtg:T3"]]},
        ],
    }


# --- determinism ----------------------------------------------------------------------


def test_repeat_calls_and_rebuilt_inputs_agree() -> None:
    first = fingerprint(build_network())
    assert all(fingerprint(build_network()) == first for _ in range(20))


def test_fingerprint_does_not_depend_on_the_hash_seed() -> None:
    root = Path(__file__).resolve().parents[2]
    script = (
        "from tests.evidence.test_geometry_fingerprint import build_network;"
        "from app.evidence.fingerprints.topology import TopologyFingerprinter;"
        "print(TopologyFingerprinter()(build_network()))"
    )
    outputs = set()
    for seed in ("1", "4242"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        outputs.add(result.stdout.strip())
    assert outputs == {fingerprint(build_network())}


# --- invariance: transient IDs, order, direction, geometry ----------------------------


def test_feeder_ids_are_labels() -> None:
    renamed = {
        f"FDR-{9 - i:03d}": specs for i, specs in enumerate(DEFAULT_FEEDERS.values())
    }
    assert fingerprint(build_network(renamed)) == fingerprint(build_network())


def test_feeder_order_does_not_matter() -> None:
    reordered = dict(reversed(list(DEFAULT_FEEDERS.items())))
    assert fingerprint(build_network(reordered)) == fingerprint(build_network())


def test_segment_ids_are_labels() -> None:
    network = build_network()
    feeder = _feeder(network, "FDR-001")
    relabelled = tuple(
        replace(s, segment_id=f"SEG-X-{i}") for i, s in enumerate(feeder.segments)
    )
    changed = _with_feeder(network, "FDR-001", segments=relabelled)
    assert fingerprint(changed) == fingerprint(network)


def test_segment_order_and_edge_direction_do_not_matter() -> None:
    network = build_network()
    feeder = _feeder(network, "FDR-001")
    flipped = tuple(
        replace(s, from_node_id=s.to_node_id, to_node_id=s.from_node_id)
        for s in reversed(feeder.segments)
    )
    graph = nx.Graph()
    graph.add_edges_from((v, u) for u, v in reversed(list(feeder.mst_graph.edges())))
    changed = _with_feeder(network, "FDR-001", segments=flipped, mst_graph=graph)
    assert fingerprint(changed) == fingerprint(network)


def test_a_different_route_for_the_same_edges_is_the_same_topology() -> None:
    rerouted: Feeders = {
        **DEFAULT_FEEDERS,
        "FDR-002": [
            (
                "substation:SS",
                "wtg:T3",
                [(500000.0, 800000.0), (499900.0, 799600.0), (499600.0, 799700.75)],
            )
        ],
    }
    network = build_network(rerouted)
    assert fingerprint(network) == fingerprint(build_network())
    # The geometry fingerprint is the one that tells them apart.
    assert GeometryFingerprinter()(network) != GeometryFingerprinter()(build_network())


def test_moving_the_whole_site_is_the_same_topology() -> None:
    shifted: Feeders = {
        fid: [(a, b, [(x + 1000.0, y) for x, y in coords]) for a, b, coords in specs]
        for fid, specs in DEFAULT_FEEDERS.items()
    }
    turbines = {k: (x + 1000.0, y) for k, (x, y) in DEFAULT_TURBINES.items()}
    network = build_network(shifted, turbines=turbines, substation=(501000.0, 800000.0))
    assert fingerprint(network) == fingerprint(build_network())


# --- sensitivity: every logical change is a new topology ------------------------------


def test_moving_a_turbine_to_another_feeder_changes_the_topology() -> None:
    moved: Feeders = {
        "FDR-001": [DEFAULT_FEEDERS["FDR-001"][0]],
        "FDR-002": [
            DEFAULT_FEEDERS["FDR-002"][0],
            ("wtg:T3", "wtg:T2", [(499600.0, 799700.75), (500900.125, 800310.0)]),
        ],
    }
    assert fingerprint(build_network(moved)) != fingerprint(build_network())


def test_the_same_membership_wired_differently_changes_the_topology() -> None:
    # T1 and T2 stay on one feeder, but both hang off the substation.
    star: Feeders = {
        **DEFAULT_FEEDERS,
        "FDR-001": [
            DEFAULT_FEEDERS["FDR-001"][0],
            ("substation:SS", "wtg:T2", [(500000.0, 800000.0), (500900.125, 800310.0)]),
        ],
    }
    assert fingerprint(build_network(star)) != fingerprint(build_network())


def test_merging_two_feeders_changes_the_topology() -> None:
    merged: Feeders = {
        "FDR-001": DEFAULT_FEEDERS["FDR-001"] + DEFAULT_FEEDERS["FDR-002"],
    }
    assert fingerprint(build_network(merged)) != fingerprint(build_network())


def test_an_unconnected_turbine_changes_the_topology() -> None:
    turbines = {**DEFAULT_TURBINES, "wtg:T4": (501500.0, 800500.0)}
    network = build_network(turbines=turbines)
    assert fingerprint(network) != fingerprint(build_network())
    assert "wtg:T4" in canonical_topology_payload(network)["nodes"]


def test_a_renamed_turbine_is_another_node() -> None:
    renamed: Feeders = {
        **DEFAULT_FEEDERS,
        "FDR-002": [("substation:SS", "wtg:T9", DEFAULT_FEEDERS["FDR-002"][0][2])],
    }
    turbines = {**DEFAULT_TURBINES}
    turbines["wtg:T9"] = turbines.pop("wtg:T3")
    assert fingerprint(build_network(renamed, turbines=turbines)) != fingerprint(
        build_network()
    )


# --- accepted inputs ------------------------------------------------------------------


def test_a_scenario_and_a_final_design_fingerprint_as_their_network() -> None:
    network = build_network()
    scenario = object.__new__(PNCScenario)
    object.__setattr__(scenario, "network", network)
    final = FinalDesign(network=network, design_truth=truth_for(network))
    assert fingerprint(scenario) == fingerprint(final) == fingerprint(network)


def test_conductors_are_not_topology() -> None:
    network = build_network()
    large = {s.segment_id: "LARGE" for f in network.feeders for s in f.segments}
    a = FinalDesign(network=network, design_truth=truth_for(network))
    b = FinalDesign(network=network, design_truth=truth_for(network, large))
    assert fingerprint(a) == fingerprint(b)
    assert FinalDesignFingerprinter()(a) != FinalDesignFingerprinter()(b)


def test_other_objects_are_refused() -> None:
    with pytest.raises(TypeError, match="Topology fingerprints need"):
        fingerprint({"feeders": []})


# --- rejected designs -----------------------------------------------------------------


def _graph(*edges: tuple[str, str]) -> nx.Graph:
    graph = nx.Graph()
    graph.add_edges_from(edges)
    return graph


def test_a_network_without_feeders_is_rejected() -> None:
    with pytest.raises(TopologyFingerprintError, match="no feeders"):
        fingerprint(replace(build_network(), feeders=()))


def test_a_feeder_without_edges_is_rejected() -> None:
    network = _with_feeder(
        build_network(), "FDR-002", mst_graph=nx.Graph(), segments=()
    )
    with pytest.raises(TopologyFingerprintError, match="FDR-002 has no edges"):
        fingerprint(network)


def test_a_self_loop_is_rejected() -> None:
    graph = _graph(("substation:SS", "wtg:T3"), ("wtg:T3", "wtg:T3"))
    network = _with_feeder(build_network(), "FDR-002", mst_graph=graph)
    with pytest.raises(TopologyFingerprintError, match="self-loop at wtg:T3"):
        fingerprint(network)


def test_an_unknown_node_is_rejected() -> None:
    graph = _graph(("substation:SS", "wtg:T3"), ("wtg:T3", "wtg:GHOST"))
    network = _with_feeder(build_network(), "FDR-002", mst_graph=graph)
    with pytest.raises(TopologyFingerprintError, match="unknown nodes"):
        fingerprint(network)


def test_a_feeder_that_misses_the_substation_is_rejected() -> None:
    graph = _graph(("wtg:T1", "wtg:T2"))
    network = _with_feeder(build_network(), "FDR-001", mst_graph=graph)
    with pytest.raises(TopologyFingerprintError, match="does not reach substation"):
        fingerprint(network)


def test_a_disconnected_feeder_is_rejected() -> None:
    graph = _graph(("substation:SS", "wtg:T1"), ("wtg:T2", "wtg:T3"))
    network = _with_feeder(build_network(), "FDR-001", mst_graph=graph)
    with pytest.raises(TopologyFingerprintError, match="not connected"):
        fingerprint(network)


def test_a_turbine_on_two_feeders_is_rejected() -> None:
    twice: Feeders = {
        **DEFAULT_FEEDERS,
        "FDR-002": [
            DEFAULT_FEEDERS["FDR-002"][0],
            ("wtg:T3", "wtg:T2", [(499600.0, 799700.75), (500900.125, 800310.0)]),
        ],
    }
    with pytest.raises(TopologyFingerprintError, match="wtg:T2 is on feeders"):
        fingerprint(build_network(twice))


def test_a_feeder_naming_another_substation_is_rejected() -> None:
    network = _with_feeder(build_network(), "FDR-002", substation_id="substation:X")
    with pytest.raises(TopologyFingerprintError, match="names substation"):
        fingerprint(network)


def test_a_substation_listed_as_a_turbine_is_rejected() -> None:
    network = build_network()
    wtgs = {**network.wtg_coordinates, "substation:SS": Point(0, 0)}
    with pytest.raises(TopologyFingerprintError, match="also listed as a WTG"):
        fingerprint(replace(network, wtg_coordinates=wtgs))


def test_segments_that_contradict_the_graph_are_rejected() -> None:
    network = build_network()
    feeder = _feeder(network, "FDR-001")
    graph = _graph(("substation:SS", "wtg:T1"), ("substation:SS", "wtg:T2"))
    with pytest.raises(TopologyFingerprintError, match="do not match its graph"):
        fingerprint(_with_feeder(network, "FDR-001", mst_graph=graph))
    doubled = (*feeder.segments, feeder.segments[0])
    with pytest.raises(TopologyFingerprintError, match="repeated"):
        fingerprint(_with_feeder(network, "FDR-001", segments=doubled))


# --- real pipeline and the cohort runner ----------------------------------------------

_CRS = pyproj.CRS("EPSG:32630")


def _surface(cost: float = 1.0) -> CostSurface:
    costs = np.full((40, 40), cost, dtype=np.float32)
    return CostSurface(
        costs=costs,
        transform=Affine.translation(0, 400) * Affine.scale(10, -10),
        crs=_CRS,
        width=40,
        height=40,
        resolution_m=10.0,
    )


def _project() -> ProjectSpatialData:
    turbines = tuple(
        WindTurbine(turbine_id=tid, location=Point(x, y), capacity_mw=5.0)
        for tid, x, y in (
            ("T1", 105.0, 305.0),
            ("T2", 205.0, 205.0),
            ("T3", 305.0, 305.0),
            ("T4", 105.0, 105.0),
        )
    )
    substation = Substation(
        substation_id="SUB1", location=Point(5.0, 395.0), capacity_mw=1000.0
    )
    return ProjectSpatialData(
        turbines=turbines, substation=substation, projected_crs=_CRS
    )


def test_engine_output_fingerprints_the_same_on_every_run() -> None:
    first = build_pnc_network("P", _project(), 10.0, _surface())
    second = build_pnc_network("P", _project(), 10.0, _surface())
    assert fingerprint(first) == fingerprint(second)
    payload = canonical_topology_payload(first)
    assert payload["nodes"] == sorted(
        ["substation:SUB1", *(f"wtg:{t}" for t in ("T1", "T2", "T3", "T4"))]
    )
    assert sum(len(f["wtgs"]) for f in payload["feeders"]) == 4


def test_the_cohort_counts_topologies_with_the_real_canonicalisers() -> None:
    network = build_network()
    large = {s.segment_id: "LARGE" for f in network.feeders for s in f.segments}
    moved = build_network(
        {
            "FDR-001": [DEFAULT_FEEDERS["FDR-001"][0]],
            "FDR-002": [
                DEFAULT_FEEDERS["FDR-002"][0],
                ("wtg:T3", "wtg:T2", [(499600.0, 799700.75), (500900.125, 800310.0)]),
            ],
        }
    )
    moved_truth = truth_for(
        moved, {s.segment_id: "SMALL" for f in moved.feeders for s in f.segments}
    )
    designs: list[tuple[str, DesignTruth, ProjectPNCNetwork]] = [
        ("SCN-001", truth_for(network), network),
        ("SCN-002", truth_for(network, large), network),
        ("SCN-003", moved_truth, moved),
    ]
    result = build_cohort(
        [
            CohortCandidate(evidence(cid), FinalDesign(network=net, design_truth=truth))
            for cid, truth, net in designs
        ],
        required_metrics=frozenset({"cost"}),
        maximum_exclusion_rate=1.0,
        topology_fingerprinter=TopologyFingerprinter(),
        final_design_fingerprinter=FinalDesignFingerprinter(),
    )
    assert len(result.members) == 3
    assert result.distinct_eligible_topologies == 2
    assert {
        m.fingerprints.canonicaliser_versions["topology"] for m in result.members
    } == {"1"}
