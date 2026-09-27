"""Topology fingerprint canonicaliser. Owned by L2 (WP0B-5).

Sorted logical nodes and edges plus feeder membership, independent of transient
IDs and serialisation order. Output format: ``topology:<version>:<sha256>``.

Canonicalisation rules, version 1
---------------------------------
Input is a ``ProjectPNCNetwork``, a ``PNCScenario`` (its ``network`` is used) or
a ``FinalDesign`` (its ``network`` is used), because the cohort runner hands the
same design object to the topology and final-design fingerprinters.

* **Source.** Each feeder's ``mst_graph`` is the topology, as ``app.pnc.models``
  requires; it is never reconstructed from geometry. The routed segments must
  describe the same edges, one segment per edge, or the design is rejected:
  a network whose segments and graph disagree has no single topology to name.
* **Nodes.** The substation node ID and every WTG node ID in
  ``wtg_coordinates``, sorted. These are stable project identities taken from
  the input, not transient labels. A WTG on no feeder stays in the node list,
  so leaving a turbine unconnected is a different topology.
* **Edges.** Each edge is its two node IDs in sorted order, because a cable
  has no direction. Edges within a feeder are sorted.
* **Feeder membership.** A feeder is written as its sorted WTG IDs and its
  sorted edges. Feeders are sorted by that content.
* **Not hashed.** Feeder IDs and segment IDs (assigned by output order, so
  transient), geometry, lengths, costs, conductors, segment types and
  ``ordered_node_ids`` (derived from the graph). Two designs that route the same
  edges along different paths share a topology fingerprint; the geometry
  fingerprint is what tells them apart.
* **Rejected** with ``TopologyFingerprintError``, never hashed: a network with
  no feeders or no edges, a feeder without edges, a self-loop, an edge naming an
  unknown node, a feeder whose graph omits the substation or is not connected,
  a WTG on two feeders, a feeder naming another substation, and segments that
  do not match the graph.

Any change to these rules is a new ``TOPOLOGY_FINGERPRINT_VERSION``.
"""

from collections import Counter
from typing import Any, Literal

import networkx as nx

from app.contracts.canonical_json import canonical_sha256
from app.evidence.fingerprints.final_design import FinalDesign
from app.evidence.fingerprints.geometry import network_of
from app.pnc.models import PNCFeeder, ProjectPNCNetwork

TOPOLOGY_FINGERPRINT_VERSION = "1"

Edge = tuple[str, str]


class TopologyFingerprintError(ValueError):
    """Raised when a design's topology breaks a declared canonicalisation rule."""


def _network(design: object) -> ProjectPNCNetwork:
    if isinstance(design, FinalDesign):
        return network_of(design.network)
    try:
        return network_of(design)
    except TypeError:
        raise TypeError(
            "Topology fingerprints need a ProjectPNCNetwork, PNCScenario or "
            f"FinalDesign, not {type(design).__name__}"
        ) from None


def _edge(u: object, v: object, feeder_id: str) -> Edge:
    if not isinstance(u, str) or not isinstance(v, str):
        raise TopologyFingerprintError(
            f"feeder {feeder_id} has a non-string node ID in edge {(u, v)!r}"
        )
    if u == v:
        raise TopologyFingerprintError(f"feeder {feeder_id} has a self-loop at {u}")
    low, high = sorted((u, v))
    return low, high


def _feeder_edges(
    feeder: PNCFeeder, substation_id: str, nodes: frozenset[str]
) -> list[Edge]:
    fid = feeder.feeder_id
    if feeder.substation_id != substation_id:
        raise TopologyFingerprintError(
            f"feeder {fid} names substation {feeder.substation_id}, "
            f"not the network's {substation_id}"
        )
    graph = feeder.mst_graph
    edges = sorted(_edge(u, v, fid) for u, v in graph.edges())
    if not edges:
        raise TopologyFingerprintError(f"feeder {fid} has no edges")
    unknown = sorted({n for edge in edges for n in edge} - nodes)
    if unknown:
        raise TopologyFingerprintError(f"feeder {fid} has unknown nodes {unknown}")
    if substation_id not in graph:
        raise TopologyFingerprintError(
            f"feeder {fid} does not reach substation {substation_id}"
        )
    if not nx.is_connected(graph):
        raise TopologyFingerprintError(f"feeder {fid} is not connected")

    routed = Counter(_edge(s.from_node_id, s.to_node_id, fid) for s in feeder.segments)
    if routed != Counter(edges):
        missing = sorted(set(edges) - routed.keys())
        extra = sorted(routed.keys() - set(edges))
        repeated = sorted(edge for edge, count in routed.items() if count > 1)
        raise TopologyFingerprintError(
            f"feeder {fid} segments do not match its graph: missing {missing}, "
            f"extra {extra}, repeated {repeated}"
        )
    return edges


def canonical_topology_payload(network: ProjectPNCNetwork) -> dict[str, Any]:
    """Return the canonical JSON value the topology fingerprint hashes."""
    substation_id = network.substation_id
    wtg_ids = set(network.wtg_coordinates)
    if substation_id in wtg_ids:
        raise TopologyFingerprintError(
            f"substation {substation_id} is also listed as a WTG"
        )
    nodes = frozenset(wtg_ids | {substation_id})
    if not network.feeders:
        raise TopologyFingerprintError("network has no feeders")

    feeders: list[dict[str, Any]] = []
    owner: dict[str, str] = {}
    for feeder in network.feeders:
        edges = _feeder_edges(feeder, substation_id, nodes)
        members = sorted({n for edge in edges for n in edge} - {substation_id})
        for wtg in members:
            if wtg in owner:
                raise TopologyFingerprintError(
                    f"WTG {wtg} is on feeders {owner[wtg]} and {feeder.feeder_id}"
                )
            owner[wtg] = feeder.feeder_id
        feeders.append({"wtgs": members, "edges": [list(edge) for edge in edges]})

    feeders.sort(key=lambda f: (f["wtgs"], f["edges"]))
    return {
        "canonicaliser": "topology",
        "version": TOPOLOGY_FINGERPRINT_VERSION,
        "substation": substation_id,
        "nodes": sorted(nodes),
        "feeders": feeders,
    }


class TopologyFingerprinter:
    kind: Literal["topology"] = "topology"
    version = TOPOLOGY_FINGERPRINT_VERSION

    def __call__(self, design: object) -> str:
        payload = canonical_topology_payload(_network(design))
        return f"{self.kind}:{self.version}:{canonical_sha256(payload)}"
