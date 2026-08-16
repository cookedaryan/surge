"""Deterministic per-segment cable sizing."""

import math
from collections.abc import Mapping
from dataclasses import dataclass

import networkx as nx

from app.electrical.feeder_validation import EdgeKey
from app.electrical.load_flow.config import LoadFlowCableType
from app.pnc.models import ProjectPNCNetwork


class NoFeasibleCableError(Exception):
    """Raised when no catalogue cable can carry the required current."""


def _edge_key(first: str, second: str) -> EdgeKey:
    return (first, second) if first < second else (second, first)


@dataclass(frozen=True)
class SegmentCableSizing:
    segment_id: str
    downstream_active_power_mw: float
    downstream_reactive_power_mvar: float
    sizing_basis: str
    assumed_power_factor: float | None
    nominal_voltage_kv: float
    required_current_a: float
    selected_cable_type_id: str
    base_ampacity_a: float
    derating_factor: float
    parallel_count: int
    effective_ampacity_a: float
    utilization_fraction: float


@dataclass(frozen=True)
class CableSizingResult:
    assignments: tuple[SegmentCableSizing, ...]
    segment_cable_type_ids: Mapping[str, str]


def _aggregate_downstream_power(
    tree: nx.DiGraph,
    active_power: Mapping[str, float],
    reactive_power: Mapping[str, float],
) -> dict[EdgeKey, tuple[float, float]]:
    """Aggregate downstream P and Q for each edge in a rooted tree."""
    if tree.number_of_nodes() == 0 or not nx.is_arborescence(tree):
        raise ValueError("tree must be a non-empty rooted arborescence")

    node_power: dict[str, tuple[float, float]] = {}
    edge_pq: dict[EdgeKey, tuple[float, float]] = {}

    for node in reversed(tuple(nx.lexicographical_topological_sort(tree, key=str))):
        node_id = str(node)
        p = active_power.get(node_id, 0.0)
        q = reactive_power.get(node_id, 0.0)
        for child in tree.successors(node):
            child_p, child_q = node_power[str(child)]
            p += child_p
            q += child_q
        node_power[node_id] = p, q

        parent = next(iter(tree.predecessors(node)), None)
        if parent is not None:
            edge_key = _edge_key(str(parent), node_id)
            edge_pq[edge_key] = (p, q)

    return edge_pq


def size_cables_for_network(
    network: ProjectPNCNetwork,
    wtg_active_power_mw: Mapping[str, float],
    wtg_reactive_power_mvar: Mapping[str, float],
    nominal_voltage_kv: float,
    cable_types: tuple[LoadFlowCableType, ...],
    sizing_power_factor: float = 1.0,
) -> CableSizingResult:
    """Assign minimum electrically suitable cable to each radial segment."""
    def effective_ampacity(c: LoadFlowCableType) -> float:
        return c.max_current_a * c.derating_factor * c.parallel_count

    sorted_cables = sorted(
        cable_types,
        key=lambda c: (
            effective_ampacity(c),
            c.parallel_count,
            c.cable_type_id,
        ),
    )

    assignments: list[SegmentCableSizing] = []
    segment_ids: dict[str, str] = {}

    for feeder in network.feeders:
        rooted = nx.DiGraph(
            nx.bfs_tree(
                feeder.mst_graph,
                source=network.substation_id,
                sort_neighbors=lambda nodes: sorted(nodes, key=str),
            )
        )
        edge_pq = _aggregate_downstream_power(
            rooted, wtg_active_power_mw, wtg_reactive_power_mvar
        )
        segment_by_edge = {
            _edge_key(segment.from_node_id, segment.to_node_id): segment
            for segment in feeder.segments
        }

        for parent, child in rooted.edges:
            parent_id, child_id = str(parent), str(child)
            edge_key = _edge_key(parent_id, child_id)
            p_mw, q_mvar = edge_pq[edge_key]
            segment = segment_by_edge.get(edge_key)
            if segment is None:
                continue

            if q_mvar != 0.0:
                s_mva = math.hypot(p_mw, q_mvar)
                basis = "APPARENT_POWER"
                assumed_pf = None
            else:
                s_mva = (
                    abs(p_mw) / sizing_power_factor
                    if sizing_power_factor > 0
                    else 0.0
                )
                basis = "ACTIVE_POWER_ONLY"
                assumed_pf = sizing_power_factor

            required_current_a = (s_mva * 1000.0) / (math.sqrt(3) * nominal_voltage_kv)

            selected_cable = next(
                (
                    cable
                    for cable in sorted_cables
                    if effective_ampacity(cable) >= required_current_a - 1e-6
                ),
                None,
            )
            if selected_cable is None:
                raise NoFeasibleCableError(
                    f"No feasible cable for segment {segment.segment_id}. "
                    f"Required: {required_current_a:.1f} A"
                )

            eff_amp = effective_ampacity(selected_cable)
            sizing = SegmentCableSizing(
                segment_id=segment.segment_id,
                downstream_active_power_mw=p_mw,
                downstream_reactive_power_mvar=q_mvar,
                sizing_basis=basis,
                assumed_power_factor=assumed_pf,
                nominal_voltage_kv=nominal_voltage_kv,
                required_current_a=required_current_a,
                selected_cable_type_id=selected_cable.cable_type_id,
                base_ampacity_a=selected_cable.max_current_a,
                derating_factor=selected_cable.derating_factor,
                parallel_count=selected_cable.parallel_count,
                effective_ampacity_a=eff_amp,
                utilization_fraction=required_current_a / eff_amp,
            )
            assignments.append(sizing)
            segment_ids[segment.segment_id] = selected_cable.cable_type_id

    return CableSizingResult(
        assignments=tuple(assignments),
        segment_cable_type_ids=segment_ids,
    )
