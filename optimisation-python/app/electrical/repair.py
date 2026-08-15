"""Deterministic iterative electrical repair for radial collector networks."""

import itertools
import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from enum import StrEnum

import networkx as nx

from app.electrical.cable_sizing import CableSizingResult, size_cables_for_network
from app.electrical.load_flow.analysis import run_load_flow
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import (
    LoadFlowNetworkResult,
    LoadFlowViolation,
    LoadFlowViolationCode,
    WTGOperatingPoint,
)
from app.pnc.models import ProjectPNCNetwork


class RepairStatus(StrEnum):
    VALID = "VALID"
    REPAIR_EXHAUSTED = "REPAIR_EXHAUSTED"
    MAX_ITERATIONS_REACHED = "MAX_ITERATIONS_REACHED"
    LOAD_FLOW_FAILED = "LOAD_FLOW_FAILED"


class RepairReason(StrEnum):
    OVERLOAD_CAPACITY_UPGRADE = "OVERLOAD_CAPACITY_UPGRADE"
    UNDERVOLTAGE_IMPEDANCE_REDUCTION = "UNDERVOLTAGE_IMPEDANCE_REDUCTION"
    OVERVOLTAGE_IMPEDANCE_REDUCTION = "OVERVOLTAGE_IMPEDANCE_REDUCTION"
    UNSUPPORTED_VIOLATION = "UNSUPPORTED_VIOLATION"


@dataclass(frozen=True)
class RepairAction:
    segment_id: str
    original_cable_type_id: str
    upgraded_cable_type_id: str
    trigger_violation_type: str
    trigger_bus_id: str | None
    pre_repair_loading_pct: float | None
    post_repair_loading_pct: float | None
    pre_repair_voltage_pu: float | None
    post_repair_voltage_pu: float | None
    repair_iteration: int
    reason_code: RepairReason


@dataclass(frozen=True)
class ClosedLoopRepairResult:
    status: RepairStatus
    final_electrical_config: LoadFlowConfig
    load_flow_result: LoadFlowNetworkResult | None
    repair_log: tuple[RepairAction, ...]
    initial_cable_sizing: CableSizingResult | None


def _effective_ampacity(c: LoadFlowCableType) -> float:
    return c.max_current_a * c.derating_factor * c.parallel_count


def _ordered_cable_types(config: LoadFlowConfig) -> list[LoadFlowCableType]:
    return sorted(
        config.cable_types,
        key=lambda c: (
            _effective_ampacity(c),
            c.parallel_count,
            c.cable_type_id,
        ),
    )


def _find_next_capacity_upgrade(
    current_cable_id: str,
    required_current_a: float,
    ordered_cables: list[LoadFlowCableType],
) -> LoadFlowCableType | None:
    current_idx = next(
        (
            i
            for i, c in enumerate(ordered_cables)
            if c.cable_type_id == current_cable_id
        ),
        None,
    )
    if current_idx is None:
        return None

    for candidate in ordered_cables[current_idx + 1 :]:
        if candidate.cable_type_id == current_cable_id:
            continue
        if _effective_ampacity(candidate) >= required_current_a:
            return candidate
    return None


def _find_next_voltage_upgrade(
    current_cable_id: str,
    ordered_cables: list[LoadFlowCableType],
    is_undervoltage: bool,
) -> LoadFlowCableType | None:
    current_idx = next(
        (
            i
            for i, c in enumerate(ordered_cables)
            if c.cable_type_id == current_cable_id
        ),
        None,
    )
    if current_idx is None:
        return None

    current = ordered_cables[current_idx]
    current_amp = _effective_ampacity(current)
    current_z = (
        math.hypot(current.resistance_ohm_per_km, current.reactance_ohm_per_km)
        / current.parallel_count
    )
    current_c = current.capacitance_nf_per_km * current.parallel_count

    for candidate in ordered_cables[current_idx + 1 :]:
        if candidate.cable_type_id == current_cable_id:
            continue
        if _effective_ampacity(candidate) >= current_amp:
            cand_z = (
                math.hypot(
                    candidate.resistance_ohm_per_km, candidate.reactance_ohm_per_km
                )
                / candidate.parallel_count
            )
            cand_c = candidate.capacitance_nf_per_km * candidate.parallel_count

            if is_undervoltage:
                if cand_z < current_z - 1e-9:
                    return candidate
            else:
                # Overvoltage Pareto heuristic
                if cand_z <= current_z + 1e-9 and cand_c <= current_c + 1e-9:
                    if cand_z < current_z - 1e-9 or cand_c < current_c - 1e-9:
                        return candidate
    return None


def repair_electrical_design(
    network: ProjectPNCNetwork,
    operating_points: Iterable[WTGOperatingPoint],
    config: LoadFlowConfig,
    wtg_active_power_mw: Mapping[str, float],
    wtg_reactive_power_mvar: Mapping[str, float],
    max_iterations: int = 20,
) -> ClosedLoopRepairResult:
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")

    operating_points = tuple(operating_points)

    try:
        sizing = size_cables_for_network(
            network=network,
            wtg_active_power_mw=wtg_active_power_mw,
            wtg_reactive_power_mvar=wtg_reactive_power_mvar,
            nominal_voltage_kv=config.nominal_voltage_kv,
            cable_types=config.cable_types,
            sizing_power_factor=1.0,
        )
    except Exception:
        # Fallback for any sizing failures
        return ClosedLoopRepairResult(
            status=RepairStatus.REPAIR_EXHAUSTED,
            final_electrical_config=config,
            load_flow_result=None,
            repair_log=(),
            initial_cable_sizing=None,
        )

    current_config = replace(
        config, segment_cable_type_ids=dict(sizing.segment_cable_type_ids)
    )
    repair_actions: list[RepairAction] = []
    pending_actions: list[RepairAction] = []
    ordered_cables = _ordered_cable_types(config)

    for iteration in range(1, max_iterations + 1):
        lf_result = run_load_flow(network, operating_points, current_config)

        if pending_actions:
            segment_loadings = {
                s.segment_id: s.loading_percent for s in lf_result.segments
            }
            bus_voltages = {b.node_id: b.voltage_pu for b in lf_result.buses}
            for pa in pending_actions:
                repair_actions.append(
                    replace(
                        pa,
                        post_repair_loading_pct=segment_loadings.get(pa.segment_id),
                        post_repair_voltage_pu=bus_voltages.get(pa.trigger_bus_id)
                        if pa.trigger_bus_id
                        else None,
                    )
                )
            pending_actions.clear()

        if not lf_result.converged or any(
            v.code == LoadFlowViolationCode.RESULT_NOT_FINITE
            for v in lf_result.violations
        ):
            return ClosedLoopRepairResult(
                status=RepairStatus.LOAD_FLOW_FAILED,
                final_electrical_config=current_config,
                load_flow_result=lf_result,
                repair_log=tuple(repair_actions),
                initial_cable_sizing=sizing,
            )

        if lf_result.is_valid:
            return ClosedLoopRepairResult(
                status=RepairStatus.VALID,
                final_electrical_config=current_config,
                load_flow_result=lf_result,
                repair_log=tuple(repair_actions),
                initial_cable_sizing=sizing,
            )

        if iteration == max_iterations:
            return ClosedLoopRepairResult(
                status=RepairStatus.MAX_ITERATIONS_REACHED,
                final_electrical_config=current_config,
                load_flow_result=lf_result,
                repair_log=tuple(repair_actions),
                initial_cable_sizing=sizing,
            )

        overloads = [
            v
            for v in lf_result.violations
            if v.code == LoadFlowViolationCode.CABLE_OVERLOAD
        ]
        voltage_violations = [
            v
            for v in lf_result.violations
            if v.code
            in (
                LoadFlowViolationCode.BUS_UNDERVOLTAGE,
                LoadFlowViolationCode.BUS_OVERVOLTAGE,
            )
        ]

        new_assignments = dict(current_config.segment_cable_type_ids)
        made_upgrade = False
        segment_results_by_id = {s.segment_id: s for s in lf_result.segments}

        if overloads:
            overloads.sort(key=lambda v: str(v.segment_id))

            for overload in overloads:
                seg_id = overload.segment_id
                if not seg_id:
                    continue

                current_cable_id = new_assignments[seg_id]
                seg_result = segment_results_by_id.get(seg_id)
                if not seg_result:
                    continue

                required_current_a = max(
                    seg_result.current_from_a, seg_result.current_to_a
                )
                next_cable = _find_next_capacity_upgrade(
                    current_cable_id, required_current_a, ordered_cables
                )

                if next_cable:
                    new_assignments[seg_id] = next_cable.cable_type_id
                    made_upgrade = True
                    pending_actions.append(
                        RepairAction(
                            segment_id=seg_id,
                            original_cable_type_id=current_cable_id,
                            upgraded_cable_type_id=next_cable.cable_type_id,
                            trigger_violation_type=str(overload.code),
                            trigger_bus_id=None,
                            pre_repair_loading_pct=seg_result.loading_percent,
                            pre_repair_voltage_pu=None,
                            post_repair_loading_pct=None,
                            post_repair_voltage_pu=None,
                            repair_iteration=iteration,
                            reason_code=RepairReason.OVERLOAD_CAPACITY_UPGRADE,
                        )
                    )

            if not made_upgrade:
                return ClosedLoopRepairResult(
                    status=RepairStatus.REPAIR_EXHAUSTED,
                    final_electrical_config=current_config,
                    load_flow_result=lf_result,
                    repair_log=tuple(repair_actions),
                    initial_cable_sizing=sizing,
                )

        elif voltage_violations:

            def severity(v: LoadFlowViolation) -> float:
                if v.measured_value is None or v.limit_value is None:
                    return 0.0
                return abs(v.measured_value - v.limit_value)

            voltage_violations.sort(key=lambda v: (-severity(v), str(v.node_id)))
            target_violation = voltage_violations[0]
            target_node_id = target_violation.node_id

            if not target_node_id:
                return ClosedLoopRepairResult(
                    status=RepairStatus.REPAIR_EXHAUSTED,
                    final_electrical_config=current_config,
                    load_flow_result=lf_result,
                    repair_log=tuple(repair_actions),
                    initial_cable_sizing=sizing,
                )

            target_feeder = next(
                (f for f in network.feeders if target_node_id in f.wtg_ids), None
            )
            if not target_feeder:
                return ClosedLoopRepairResult(
                    status=RepairStatus.REPAIR_EXHAUSTED,
                    final_electrical_config=current_config,
                    load_flow_result=lf_result,
                    repair_log=tuple(repair_actions),
                    initial_cable_sizing=sizing,
                )

            try:
                path = nx.shortest_path(
                    target_feeder.mst_graph, target_feeder.substation_id, target_node_id
                )
            except nx.NetworkXNoPath:
                return ClosedLoopRepairResult(
                    status=RepairStatus.REPAIR_EXHAUSTED,
                    final_electrical_config=current_config,
                    load_flow_result=lf_result,
                    repair_log=tuple(repair_actions),
                    initial_cable_sizing=sizing,
                )
            except nx.NodeNotFound:
                return ClosedLoopRepairResult(
                    status=RepairStatus.REPAIR_EXHAUSTED,
                    final_electrical_config=current_config,
                    load_flow_result=lf_result,
                    repair_log=tuple(repair_actions),
                    initial_cable_sizing=sizing,
                )

            is_undervoltage = (
                target_violation.code == LoadFlowViolationCode.BUS_UNDERVOLTAGE
            )
            node_voltages = {b.node_id: b.voltage_pu for b in lf_result.buses}

            edge_to_segment = {}
            for seg in target_feeder.segments:
                u, v = seg.from_node_id, seg.to_node_id
                edge_to_segment[(u, v)] = seg.segment_id
                edge_to_segment[(v, u)] = seg.segment_id

            path_segments = []
            for u, v in itertools.pairwise(path):
                v_u = node_voltages.get(u, 1.0)
                v_v = node_voltages.get(v, 1.0)

                delta_v = v_u - v_v if is_undervoltage else v_v - v_u
                seg_id = edge_to_segment.get((u, v))
                if seg_id:
                    path_segments.append((delta_v, seg_id))

            path_segments.sort(key=lambda x: (-x[0], x[1]))

            for _, seg_id in path_segments:
                current_cable_id = new_assignments[seg_id]
                next_cable = _find_next_voltage_upgrade(
                    current_cable_id, ordered_cables, is_undervoltage
                )
                if next_cable:
                    new_assignments[seg_id] = next_cable.cable_type_id
                    made_upgrade = True

                    seg_result = segment_results_by_id.get(seg_id)
                    loading = seg_result.loading_percent if seg_result else None

                    pending_actions.append(
                        RepairAction(
                            segment_id=seg_id,
                            original_cable_type_id=current_cable_id,
                            upgraded_cable_type_id=next_cable.cable_type_id,
                            trigger_violation_type=str(target_violation.code),
                            trigger_bus_id=target_node_id,
                            pre_repair_loading_pct=loading,
                            pre_repair_voltage_pu=node_voltages.get(target_node_id),
                            post_repair_loading_pct=None,
                            post_repair_voltage_pu=None,
                            repair_iteration=iteration,
                            reason_code=RepairReason.UNDERVOLTAGE_IMPEDANCE_REDUCTION
                            if is_undervoltage
                            else RepairReason.OVERVOLTAGE_IMPEDANCE_REDUCTION,
                        )
                    )
                    break

            if not made_upgrade:
                return ClosedLoopRepairResult(
                    status=RepairStatus.REPAIR_EXHAUSTED,
                    final_electrical_config=current_config,
                    load_flow_result=lf_result,
                    repair_log=tuple(repair_actions),
                    initial_cable_sizing=sizing,
                )
        else:
            # We have violations, but no overloads and no voltage violations
            # Unsupported violation fallback
            return ClosedLoopRepairResult(
                status=RepairStatus.REPAIR_EXHAUSTED,
                final_electrical_config=current_config,
                load_flow_result=lf_result,
                repair_log=tuple(repair_actions),
                initial_cable_sizing=sizing,
            )

        current_config = replace(current_config, segment_cable_type_ids=new_assignments)

    # Unreachable in normal operation: the final iteration returns inside the loop.
    return ClosedLoopRepairResult(
        status=RepairStatus.MAX_ITERATIONS_REACHED,
        final_electrical_config=current_config,
        load_flow_result=lf_result,
        repair_log=tuple(repair_actions),
        initial_cable_sizing=sizing,
    )
