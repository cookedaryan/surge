"""WP0B-7: geometry fingerprint canonicaliser, version 1."""

import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import networkx as nx
import pytest
from pyproj import CRS
from shapely.geometry import LineString, Point

from app.evidence.fingerprints.geometry import (
    GEOMETRY_FINGERPRINT_VERSION,
    GeometryFingerprinter,
    GeometryFingerprintError,
    canonical_geometry_payload,
)
from app.optimisation.scenario_models import PNCScenario
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork

UTM_44N = CRS.from_epsg(32644)

# Golden vector for ``build_network()``. It changes only with a new
# GEOMETRY_FINGERPRINT_VERSION; a failure at the same version is a regression.
GOLDEN_V1 = (
    "geometry:1:26ba074fd03fc7b6e6dfb1318b88185dfe7c957dbf06c36ba61d9be9d4dfdda6"
)

Line = list[tuple[float, float]]

DEFAULT_FEEDERS: dict[str, list[tuple[str, str, Line]]] = {
    "FDR-001": [
        ("substation:SS", "wtg:T1", [(500000.0, 800000.0), (500400.25, 800150.5)]),
        (
            "wtg:T1",
            "wtg:T2",
            [(500400.25, 800150.5), (500650.0, 800300.0), (500900.125, 800310.0)],
        ),
    ],
    "FDR-002": [
        ("substation:SS", "wtg:T3", [(500000.0, 800000.0), (499600.0, 799700.75)]),
    ],
}
DEFAULT_TURBINES = {
    "wtg:T1": (500400.25, 800150.5),
    "wtg:T2": (500900.125, 800310.0),
    "wtg:T3": (499600.0, 799700.75),
}


def build_network(
    feeders: dict[str, list[tuple[str, str, Line]]] | None = None,
    *,
    turbines: dict[str, tuple[float, float]] | None = None,
    crs: CRS = UTM_44N,
    substation: tuple[float, float] = (500000.0, 800000.0),
) -> ProjectPNCNetwork:
    feeders = DEFAULT_FEEDERS if feeders is None else feeders
    turbines = DEFAULT_TURBINES if turbines is None else turbines
    built = []
    for feeder_id, specs in feeders.items():
        segments = tuple(
            PNCSegment(
                segment_id=f"SEG-{feeder_id}-{index:04d}",
                feeder_id=feeder_id,
                from_node_id=start,
                to_node_id=end,
                route_geometry=LineString(coords),
                route_length_m=LineString(coords).length,
                traversal_cost=LineString(coords).length,
                segment_type=(
                    "substation_to_wtg"
                    if start.startswith("substation")
                    else "wtg_to_wtg"
                ),
            )
            for index, (start, end, coords) in enumerate(specs, start=1)
        )
        graph = nx.Graph()
        graph.add_edges_from((s.from_node_id, s.to_node_id) for s in segments)
        wtgs = tuple(sorted(n for n in graph.nodes if n.startswith("wtg")))
        built.append(
            PNCFeeder(
                feeder_id=feeder_id,
                substation_id="substation:SS",
                wtg_ids=wtgs,
                ordered_node_ids=("substation:SS", *wtgs),
                segments=segments,
                total_length_m=sum(s.route_length_m for s in segments),
                mst_graph=graph,
            )
        )
    all_segments = [s for f in built for s in f.segments]
    return ProjectPNCNetwork(
        project_id="PROJECT",
        substation_id="substation:SS",
        substation_geometry=Point(substation),
        feeders=tuple(built),
        wtg_coordinates={k: Point(v) for k, v in turbines.items()},
        total_route_length_m=sum(s.route_length_m for s in all_segments),
        feeder_count=len(built),
        wtg_count=len(turbines),
        segment_count=len(all_segments),
        crs=crs,
        route_length_by_feeder={f.feeder_id: f.total_length_m for f in built},
        wtg_count_by_feeder={f.feeder_id: len(f.wtg_ids) for f in built},
    )


fingerprint = GeometryFingerprinter()


# --- format and golden vector ---------------------------------------------------------


def test_fingerprinter_satisfies_the_c4_format() -> None:
    value = fingerprint(build_network())
    kind, version, digest = value.split(":")
    assert (kind, version) == ("geometry", GEOMETRY_FINGERPRINT_VERSION)
    assert len(digest) == 64 and digest == digest.lower()
    int(digest, 16)
    assert fingerprint.kind == "geometry"
    assert fingerprint.version == "1"


def test_golden_vector_v1() -> None:
    assert fingerprint(build_network()) == GOLDEN_V1


def test_canonical_payload_spells_out_the_declared_rules() -> None:
    assert canonical_geometry_payload(build_network()) == {
        "canonicaliser": "geometry",
        "version": "1",
        "crs": "EPSG:32644",
        "axis_order": "easting,northing",
        "unit": "mm",
        "substation": [500000000, 800000000],
        "turbines": [
            [499600000, 799700750],
            [500400250, 800150500],
            [500900125, 800310000],
        ],
        # Sorted; the substation-to-T3 line is written reversed because its
        # reversed form is lexicographically smaller.
        "lines": [
            [[499600000, 799700750], [500000000, 800000000]],
            [[500000000, 800000000], [500400250, 800150500]],
            [[500400250, 800150500], [500650000, 800300000], [500900125, 800310000]],
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
        "from app.evidence.fingerprints.geometry import GeometryFingerprinter;"
        "print(GeometryFingerprinter()(build_network()))"
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


# --- invariance: labels, order, orientation, noise ------------------------------------


def _reversed_lines(
    feeders: dict[str, list[tuple[str, str, Line]]],
) -> dict[str, list[tuple[str, str, Line]]]:
    return {
        fid: [(end, start, list(reversed(coords))) for start, end, coords in specs]
        for fid, specs in feeders.items()
    }


def test_line_direction_does_not_matter() -> None:
    assert fingerprint(build_network(_reversed_lines(DEFAULT_FEEDERS))) == (
        fingerprint(build_network())
    )


def test_feeder_labels_and_feature_order_do_not_matter() -> None:
    relabelled = {
        "FDR-900": list(reversed(DEFAULT_FEEDERS["FDR-001"])),
        "FDR-100": DEFAULT_FEEDERS["FDR-002"],
    }
    turbines = dict(reversed(list(DEFAULT_TURBINES.items())))
    assert fingerprint(build_network(relabelled, turbines=turbines)) == (
        fingerprint(build_network())
    )


def test_sub_millimetre_noise_and_repeated_vertices_do_not_matter() -> None:
    noisy = {
        fid: [
            (
                start,
                end,
                [(x + 1e-7, y - 2e-7) for x, y in coords[:1]]
                + [(x, y) for x, y in coords[:1]]
                + [(x - 3e-7, y + 1e-7) for x, y in coords[1:]],
            )
            for start, end, coords in specs
        ]
        for fid, specs in DEFAULT_FEEDERS.items()
    }
    assert fingerprint(build_network(noisy)) == fingerprint(build_network())


def test_scenario_is_fingerprinted_by_its_network() -> None:
    network = build_network()
    # Only ``network`` is read, so the other scenario fields are left unset.
    scenario = object.__new__(PNCScenario)
    object.__setattr__(scenario, "network", network)
    assert fingerprint(scenario) == fingerprint(network)


def test_other_design_types_are_refused() -> None:
    with pytest.raises(TypeError):
        fingerprint({"type": "FeatureCollection", "features": []})


# --- sensitivity ----------------------------------------------------------------------


def test_moving_one_vertex_by_one_millimetre_changes_the_fingerprint() -> None:
    moved = {
        **DEFAULT_FEEDERS,
        "FDR-001": [
            DEFAULT_FEEDERS["FDR-001"][0],
            (
                "wtg:T1",
                "wtg:T2",
                [(500400.25, 800150.5), (500650.001, 800300.0), (500900.125, 800310.0)],
            ),
        ],
    }
    assert fingerprint(build_network(moved)) != fingerprint(build_network())


def test_crs_turbines_and_substation_are_part_of_the_identity() -> None:
    base = fingerprint(build_network())
    assert fingerprint(build_network(crs=CRS.from_epsg(32643))) != base
    turbines = {**DEFAULT_TURBINES, "wtg:T4": (501000.0, 801000.0)}
    assert fingerprint(build_network(turbines=turbines)) != base
    assert fingerprint(build_network(substation=(500000.0, 800000.001))) != base


def test_duplicate_lines_are_kept() -> None:
    doubled = {
        **DEFAULT_FEEDERS,
        "FDR-003": [DEFAULT_FEEDERS["FDR-002"][0]],
    }
    assert fingerprint(build_network(doubled)) != fingerprint(build_network())


# --- declared rejections --------------------------------------------------------------


@pytest.mark.parametrize(
    "crs",
    [
        CRS.from_epsg(4326),  # geographic
        CRS.from_epsg(2227),  # US survey feet
        CRS.from_proj4(
            "+proj=tmerc +lat_0=0 +lon_0=77.3 +k=0.9996 +x_0=500000 +y_0=0 "
            "+ellps=WGS84 +units=m +no_defs"
        ),  # no EPSG code
    ],
)
def test_crs_outside_the_declared_rule_is_rejected(crs: CRS) -> None:
    with pytest.raises(GeometryFingerprintError):
        fingerprint(build_network(crs=crs))


def _with_first_line(coords: Line | LineString) -> ProjectPNCNetwork:
    network = build_network()
    feeder = network.feeders[0]
    geometry = coords if isinstance(coords, LineString) else LineString(coords)
    segment = replace(feeder.segments[0], route_geometry=geometry)
    feeders = (replace(feeder, segments=(segment, *feeder.segments[1:])),)
    return replace(network, feeders=feeders + network.feeders[1:])


@pytest.mark.parametrize(
    "line",
    [
        LineString(),
        [(500000.0, 800000.0), (float("nan"), 800001.0)],
        [(500000.0, 800000.0), (500000.0002, 800000.0003)],
        LineString([(500000.0, 800000.0, 1.0), (500001.0, 800000.0, 1.0)]),
    ],
    ids=["empty", "non-finite", "collapses", "3d"],
)
@pytest.mark.filterwarnings("ignore:invalid value encountered:RuntimeWarning")
def test_degenerate_lines_are_rejected(line: Line | LineString) -> None:
    with pytest.raises(GeometryFingerprintError):
        fingerprint(_with_first_line(line))


def test_network_without_segments_is_rejected() -> None:
    with pytest.raises(GeometryFingerprintError):
        fingerprint(build_network({"FDR-001": []}))


def test_empty_substation_point_is_rejected() -> None:
    network = replace(build_network(), substation_geometry=Point())
    with pytest.raises(GeometryFingerprintError):
        fingerprint(network)
