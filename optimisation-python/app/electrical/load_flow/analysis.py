"""Pandapower electrical AC load flow solver and analysis."""

import math
from collections.abc import Iterable

import pandapower as pp
from pandapower.powerflow import LoadflowNotConverged

from app.electrical.errors import CandidateElectricalEvaluationError
from app.electrical.load_flow.builder import build_pandapower_network
from app.electrical.load_flow.config import LoadFlowConfig
from app.electrical.load_flow.models import (
    LoadFlowBusResult,
    LoadFlowFeederResult,
    LoadFlowNetworkResult,
    LoadFlowSegmentResult,
    LoadFlowViolation,
    LoadFlowViolationCode,
    WTGOperatingPoint,
)
from app.pnc.models import ProjectPNCNetwork


def run_load_flow(
    pnc_network: ProjectPNCNetwork,
    operating_points: Iterable[WTGOperatingPoint],
    config: LoadFlowConfig,
) -> LoadFlowNetworkResult:
    """Execute AC load flow and map results back to domain models."""
    phase = "build"
    try:
        ops_tuple = tuple(operating_points)
        build_result = build_pandapower_network(pnc_network, ops_tuple, config)
        net = build_result.net

        phase = "solve"
        try:
            pp.runpp(
                net,
                algorithm="nr",
                numba=False,
                calculate_voltage_angles=True,
                check_connectivity=True,
            )
        except LoadflowNotConverged:
            return LoadFlowNetworkResult(
                converged=False,
                is_valid=False,
                solver_algorithm="nr",
                total_generation_mw=None,
                slack_power_mw=None,
                total_active_loss_mw=None,
                total_reactive_loss_mvar=None,
                minimum_voltage_pu=None,
                maximum_voltage_pu=None,
                maximum_loading_percent=None,
                buses=(),
                segments=(),
                feeders=(),
                violations=(
                    LoadFlowViolation(
                        code=LoadFlowViolationCode.LOAD_FLOW_NOT_CONVERGED,
                        message="Pandapower load flow did not converge.",
                    ),
                ),
            )

        phase = "extract"
        # 1. Extract buses
        bus_results = []
        violations = []

        # We track non-finite results. If any occur, we mark as non-finite.
        has_non_finite = False

        min_v_pu = float("inf")
        max_v_pu = -float("inf")
        worst_voltage_dev = 0.0

        for bus_idx, node_id in build_result.bus_to_node.items():
            v_pu = net.res_bus.at[bus_idx, "vm_pu"]
            v_angle = net.res_bus.at[bus_idx, "va_degree"]
            p_mw = net.res_bus.at[bus_idx, "p_mw"]
            q_mvar = net.res_bus.at[bus_idx, "q_mvar"]

            if any(not math.isfinite(x) for x in (v_pu, v_angle, p_mw, q_mvar)):
                has_non_finite = True
                continue

            bus_results.append(
                LoadFlowBusResult(
                    node_id=node_id,
                    node_type="substation"
                    if node_id == pnc_network.substation_id
                    else "wtg",
                    voltage_pu=float(v_pu),
                    voltage_kv=float(v_pu * config.nominal_voltage_kv),
                    voltage_angle_degree=float(v_angle),
                    net_active_power_demand_mw=float(p_mw),
                    net_reactive_power_demand_mvar=float(q_mvar),
                )
            )

            # Violation checks
            if v_pu < config.min_voltage_pu:
                violations.append(
                    LoadFlowViolation(
                        code=LoadFlowViolationCode.BUS_UNDERVOLTAGE,
                        message=f"Bus {node_id!r} voltage {v_pu:.4f} "
                        f"is below minimum {config.min_voltage_pu}",
                        node_id=node_id,
                        measured_value=float(v_pu),
                        limit_value=config.min_voltage_pu,
                    )
                )
            elif v_pu > config.max_voltage_pu:
                violations.append(
                    LoadFlowViolation(
                        code=LoadFlowViolationCode.BUS_OVERVOLTAGE,
                        message=f"Bus {node_id!r} voltage {v_pu:.4f} "
                        f"is above maximum {config.max_voltage_pu}",
                        node_id=node_id,
                        measured_value=float(v_pu),
                        limit_value=config.max_voltage_pu,
                    )
                )

            # Track global voltage metrics
            min_v_pu = min(min_v_pu, v_pu)
            max_v_pu = max(max_v_pu, v_pu)
            dev = abs(v_pu - 1.0)
            if dev > worst_voltage_dev:
                worst_voltage_dev = dev

        # 2. Extract segments
        segment_results = []
        max_loading = -float("inf")
        most_loaded_segment_id = None
        total_active_loss = 0.0
        total_reactive_loss = 0.0

        # Build mapping to assign segment results to feeders
        seg_id_to_feeder = {}
        for f in pnc_network.feeders:
            for s in f.segments:
                seg_id_to_feeder[s.segment_id] = f.feeder_id

        for line_idx, seg_id in build_result.line_to_segment.items():
            feeder_id = seg_id_to_feeder[seg_id]

            p_from = net.res_line.at[line_idx, "p_from_mw"]
            q_from = net.res_line.at[line_idx, "q_from_mvar"]
            p_to = net.res_line.at[line_idx, "p_to_mw"]
            q_to = net.res_line.at[line_idx, "q_to_mvar"]
            p_loss = net.res_line.at[line_idx, "pl_mw"]
            q_loss = net.res_line.at[line_idx, "ql_mvar"]
            i_from_ka = net.res_line.at[line_idx, "i_from_ka"]
            i_to_ka = net.res_line.at[line_idx, "i_to_ka"]
            loading = net.res_line.at[line_idx, "loading_percent"]

            if any(
                not math.isfinite(x)
                for x in (
                    p_from,
                    q_from,
                    p_to,
                    q_to,
                    p_loss,
                    q_loss,
                    i_from_ka,
                    i_to_ka,
                    loading,
                )
            ):
                has_non_finite = True
                continue

            max_i_ka = net.line.at[line_idx, "max_i_ka"]

            segment_results.append(
                LoadFlowSegmentResult(
                    segment_id=seg_id,
                    feeder_id=feeder_id,
                    p_from_mw=float(p_from),
                    q_from_mvar=float(q_from),
                    p_to_mw=float(p_to),
                    q_to_mvar=float(q_to),
                    active_loss_mw=float(p_loss),
                    reactive_loss_mvar=float(q_loss),
                    current_from_a=float(i_from_ka * 1000.0),
                    current_to_a=float(i_to_ka * 1000.0),
                    maximum_current_a=float(max_i_ka * 1000.0),
                    loading_percent=float(loading),
                )
            )

            total_active_loss += p_loss
            total_reactive_loss += q_loss

            if loading > 100.0:
                violations.append(
                    LoadFlowViolation(
                        code=LoadFlowViolationCode.CABLE_OVERLOAD,
                        message=f"Segment {seg_id!r} is overloaded at {loading:.1f}%",
                        segment_id=seg_id,
                        feeder_id=feeder_id,
                        measured_value=float(loading),
                        limit_value=100.0,
                    )
                )

            if loading > max_loading:
                max_loading = loading
                most_loaded_segment_id = seg_id  # noqa: F841

        total_gen = sum(op.active_power_mw for op in ops_tuple)
        slack_idx = net.ext_grid.index[0]
        slack_p = float(net.res_ext_grid.at[slack_idx, "p_mw"])

        if not math.isfinite(slack_p) or not math.isfinite(total_gen):
            has_non_finite = True

        if has_non_finite:
            violations.append(
                LoadFlowViolation(
                    code=LoadFlowViolationCode.RESULT_NOT_FINITE,
                    message="Pandapower returned non-finite results (NaN or Inf).",
                )
            )

        # 3. Feeder results
        feeder_results = []
        bus_results_map = {br.node_id: br for br in bus_results}

        for feeder in pnc_network.feeders:
            f_segs = [sr for sr in segment_results if sr.feeder_id == feeder.feeder_id]
            f_wtg_count = len(feeder.wtg_ids)
            f_active_loss = sum(sr.active_loss_mw for sr in f_segs)
            f_reactive_loss = sum(sr.reactive_loss_mvar for sr in f_segs)

            f_min_v = float("inf")
            f_max_v = -float("inf")
            f_max_loading = -float("inf")
            f_worst_node = None
            f_most_loaded_seg = None
            f_worst_dev = 0.0

            # Include all WTGs and the Substation in the feeder's voltage calculations
            nodes_in_feeder = list(feeder.wtg_ids) + [feeder.substation_id]
            for node_id in nodes_in_feeder:
                br = bus_results_map.get(node_id)
                if br:
                    f_min_v = min(f_min_v, br.voltage_pu)
                    f_max_v = max(f_max_v, br.voltage_pu)
                    dev = abs(br.voltage_pu - 1.0)
                    if dev > f_worst_dev:
                        f_worst_dev = dev
                        f_worst_node = node_id

            for sr in f_segs:
                if sr.loading_percent > f_max_loading:
                    f_max_loading = sr.loading_percent
                    f_most_loaded_seg = sr.segment_id

            f_violations = [
                v
                for v in violations
                if v.feeder_id == feeder.feeder_id
                or v.node_id in feeder.wtg_ids
                or v.node_id == feeder.substation_id
            ]

            feeder_results.append(
                LoadFlowFeederResult(
                    feeder_id=feeder.feeder_id,
                    wtg_count=f_wtg_count,
                    active_loss_mw=float(f_active_loss),
                    reactive_loss_mvar=float(f_reactive_loss),
                    minimum_voltage_pu=float(f_min_v) if f_segs else 1.0,
                    maximum_voltage_pu=float(f_max_v) if f_segs else 1.0,
                    maximum_loading_percent=float(f_max_loading) if f_segs else 0.0,
                    worst_voltage_node_id=f_worst_node,
                    most_loaded_segment_id=f_most_loaded_seg,
                    valid=not f_violations and not has_non_finite,
                )
            )

        is_valid = not violations and not has_non_finite

        return LoadFlowNetworkResult(
            converged=True,
            is_valid=is_valid,
            solver_algorithm="nr",
            total_generation_mw=float(total_gen),
            slack_power_mw=float(slack_p) if math.isfinite(slack_p) else None,
            total_active_loss_mw=float(total_active_loss),
            total_reactive_loss_mvar=float(total_reactive_loss),
            minimum_voltage_pu=float(min_v_pu) if math.isfinite(min_v_pu) else None,
            maximum_voltage_pu=float(max_v_pu) if math.isfinite(max_v_pu) else None,
            maximum_loading_percent=float(max_loading)
            if math.isfinite(max_loading)
            else None,
            buses=tuple(bus_results),
            segments=tuple(segment_results),
            feeders=tuple(feeder_results),
            violations=tuple(violations),
        )
    except Exception as exc:
        if phase in {"build", "solve"}:
            raise CandidateElectricalEvaluationError(str(exc)) from exc
        raise
