"""Immutable domain models for the Project PNC Network.

Three frozen dataclasses represent the three layers of the assembled network:

  PNCSegment      — one routed cable/pole segment between two nodes
  PNCFeeder       — one complete feeder (substation + ordered WTGs + segments)
  ProjectPNCNetwork — the full project-wide PNC network

Design notes
------------
- All geometry is stored in the *projected* CRS used during optimisation.
  Callers that need WGS-84 should use network_to_feature_collection() which
  performs the CRS conversion.
- The mst_graph on PNCFeeder is the authoritative topology graph retained from
  the optimisation stage.  Topology must never be reconstructed from geometry.
- ordered_node_ids is a deterministic BFS traversal starting from the
  substation node, using lexicographic neighbour ordering.  It is a read-only
  convenience; the mst_graph remains the single source of truth.
"""

from dataclasses import dataclass
from typing import Literal

import networkx as nx
import pyproj
from shapely.geometry import LineString, Point


@dataclass(frozen=True)
class PNCSegment:
    """One routed segment between two network nodes.

    segment_id is deterministic:  SEG-{feeder_suffix}-{n:04d}
    where feeder_suffix is derived from the normalised feeder ID (e.g. FDR001).
    """

    segment_id: str
    feeder_id: str
    from_node_id: str
    to_node_id: str
    route_geometry: LineString  # projected CRS
    route_length_m: float
    segment_type: Literal["substation_to_wtg", "wtg_to_wtg"]


@dataclass(frozen=True)
class PNCFeeder:
    """One complete feeder in the assembled PNC network.

    Attributes
    ----------
    feeder_id:
        Normalised feeder identifier, e.g. ``FDR-001``.
    substation_id:
        Node ID of the substation this feeder connects to.
    wtg_ids:
        Tuple of WTG node IDs belonging to this feeder, sorted for determinism.
    ordered_node_ids:
        Deterministic BFS traversal starting from the substation node using
        lexicographic neighbour ordering.  Useful for consumers that need a
        sequence representation of the feeder topology.
        The underlying mst_graph remains the authoritative topology.
    segments:
        All routed segments for this feeder, sorted by segment_id.
    total_length_m:
        Sum of route_length_m over all segments.
    mst_graph:
        The original undirected MST graph produced by the topology stage.
        Retained verbatim — not reconstructed from geometry.
    """

    feeder_id: str
    substation_id: str
    wtg_ids: tuple[str, ...]
    ordered_node_ids: tuple[str, ...]
    segments: tuple[PNCSegment, ...]
    total_length_m: float
    mst_graph: nx.Graph


@dataclass(frozen=True)
class ProjectPNCNetwork:
    """The complete automatically assembled Project PNC Network.

    Attributes
    ----------
    project_id:
        Caller-supplied project identifier.
    substation_id:
        Node ID of the project substation.
    substation_geometry:
        Substation location in the projected CRS.
    feeders:
        All feeders, sorted by feeder_id for determinism.
    wtg_coordinates:
        Mapping of WTG node ID → projected Point.
        Includes every WTG present in the project.
    total_route_length_m:
        Sum of all segment lengths across all feeders.
    feeder_count:
        Number of feeders in the network.
    wtg_count:
        Total number of WTGs across all feeders.
    segment_count:
        Total number of routed segments.
    crs:
        The projected CRS used for all geometry in this object.
    route_length_by_feeder:
        Per-feeder sum of routed cable length in metres.
    wtg_count_by_feeder:
        Per-feeder WTG count.
    """

    project_id: str
    substation_id: str
    substation_geometry: Point
    feeders: tuple[PNCFeeder, ...]
    wtg_coordinates: dict[str, Point]
    total_route_length_m: float
    feeder_count: int
    wtg_count: int
    segment_count: int
    crs: pyproj.CRS
    route_length_by_feeder: dict[str, float]
    wtg_count_by_feeder: dict[str, int]
