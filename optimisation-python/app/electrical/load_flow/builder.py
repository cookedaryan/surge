"""Pandapower electrical network builder for AC load flow."""

import math
from collections.abc import Iterable

import pandapower as pp
from shapely.geometry import Point

from app.electrical.load_flow.config import LoadFlowConfig
from app.electrical.load_flow.models import PandapowerBuildResult, WTGOperatingPoint
from app.pnc.models import PNCSegment, ProjectPNCNetwork


def build_pandapower_network(
    pnc_network: ProjectPNCNetwork,
    operating_points: Iterable[WTGOperatingPoint],
    config: LoadFlowConfig,
) -> PandapowerBuildResult:
    """Build a pandapower electrical network from a PNC network.

    Validates inputs strictly before construction. The resulting PandapowerBuildResult
    contains the network and deterministic ID mappings.
    """
    ops = tuple(operating_points)
    _validate_inputs(pnc_network, ops, config)

    net = pp.create_empty_network(sn_mva=config.system_base_mva)

    node_to_bus: dict[str, int] = {}
    bus_to_node: dict[int, str] = {}
    segment_to_line: dict[str, int] = {}
    line_to_segment: dict[int, str] = {}
    wtg_to_sgen: dict[str, int] = {}

    op_map = {op.node_id: op for op in ops}
    cable_types = {ct.cable_type_id: ct for ct in config.cable_types}

    # 1. Substation Bus & Ext Grid
    sub_id = pnc_network.substation_id
    sub_bus = pp.create_bus(
        net,
        name=sub_id,
        vn_kv=config.nominal_voltage_kv,
        type="n",
        in_service=True,
    )
    node_to_bus[sub_id] = sub_bus
    bus_to_node[sub_bus] = sub_id

    pp.create_ext_grid(
        net,
        bus=sub_bus,
        vm_pu=config.slack_voltage_pu,
        va_degree=0.0,
        name="Grid",
    )

    # 2. WTG Buses & Generators
    # Sort WTG IDs deterministically
    wtg_ids = sorted(pnc_network.wtg_coordinates.keys())
    for wtg_id in wtg_ids:
        bus_idx = pp.create_bus(
            net,
            name=wtg_id,
            vn_kv=config.nominal_voltage_kv,
            type="n",
            in_service=True,
        )
        node_to_bus[wtg_id] = bus_idx
        bus_to_node[bus_idx] = wtg_id

        op = op_map[wtg_id]
        sgen_idx = pp.create_sgen(
            net,
            bus=bus_idx,
            p_mw=op.active_power_mw,
            q_mvar=op.reactive_power_mvar,
            name=wtg_id,
            in_service=True,
        )
        wtg_to_sgen[wtg_id] = sgen_idx

    # 3. Segments (Lines)
    # Sort segments deterministically
    all_segments: list[PNCSegment] = []
    for feeder in pnc_network.feeders:
        all_segments.extend(feeder.segments)
    all_segments.sort(key=lambda s: s.segment_id)

    for seg in all_segments:
        cable_id = config.segment_cable_type_ids.get(
            seg.segment_id, config.default_cable_type_id
        )
        cable = cable_types[cable_id]

        from_bus = node_to_bus[seg.from_node_id]
        to_bus = node_to_bus[seg.to_node_id]
        length_km = seg.route_length_m / 1000.0

        # Max current in kA
        max_i_ka = cable.max_current_a / 1000.0

        line_idx = pp.create_line_from_parameters(
            net,
            from_bus=from_bus,
            to_bus=to_bus,
            length_km=length_km,
            r_ohm_per_km=cable.resistance_ohm_per_km,
            x_ohm_per_km=cable.reactance_ohm_per_km,
            c_nf_per_km=cable.capacitance_nf_per_km,
            max_i_ka=max_i_ka,
            name=seg.segment_id,
            df=cable.derating_factor,
            parallel=cable.parallel_count,
            in_service=True,
        )
        segment_to_line[seg.segment_id] = line_idx
        line_to_segment[line_idx] = seg.segment_id

    import types

    return PandapowerBuildResult(
        net=net,
        node_to_bus=types.MappingProxyType(node_to_bus),
        bus_to_node=types.MappingProxyType(bus_to_node),
        segment_to_line=types.MappingProxyType(segment_to_line),
        line_to_segment=types.MappingProxyType(line_to_segment),
        wtg_to_sgen=types.MappingProxyType(wtg_to_sgen),
    )


def _validate_inputs(
    pnc_network: ProjectPNCNetwork,
    operating_points: Iterable[WTGOperatingPoint],
    config: LoadFlowConfig,
) -> None:
    """Strict input validation prior to network construction.

    Raises ValueError on any malformed input to distinguish it from
    electrical load-flow failure.
    """
    if not pnc_network.project_id or not pnc_network.substation_id:
        raise ValueError("Project and substation IDs must be non-empty.")

    if pnc_network.feeder_count == 0 or pnc_network.wtg_count == 0:
        raise ValueError("Network must have at least one feeder and one WTG.")

    if pnc_network.crs.is_geographic:
        raise ValueError("Project CRS must be projected (metric), not geographic.")

    axis_unit = pnc_network.crs.axis_info[0].unit_name
    if axis_unit not in ("metre", "meter"):
        raise ValueError(f"Project CRS must be metre-based, got {axis_unit}.")

    # Check cable configuration
    cable_ids = {c.cable_type_id for c in config.cable_types}
    if config.default_cable_type_id not in cable_ids:
        raise ValueError(
            f"Default cable type {config.default_cable_type_id!r} "
            "not in configured cable types."
        )

    for seg_id, cid in config.segment_cable_type_ids.items():
        if cid not in cable_ids:
            raise ValueError(
                f"Segment {seg_id!r} references unknown cable type {cid!r}."
            )

    # Validate exact WTG coverage with operating points
    ops = tuple(operating_points)
    op_ids = {op.node_id for op in ops}
    wtg_ids = set(pnc_network.wtg_coordinates.keys())

    if len(op_ids) != len(ops):
        raise ValueError("Duplicate operating points found.")

    missing = wtg_ids - op_ids
    if missing:
        raise ValueError(f"Missing operating points for WTGs: {sorted(missing)}")

    extra = op_ids - wtg_ids
    if extra:
        raise ValueError(f"Operating points for unknown WTGs: {sorted(extra)}")

    # Validate PNC invariants
    feeder_ids = set()
    segment_ids = set()
    assigned_wtgs = set()
    total_segments = 0
    total_length = 0.0

    sub_id = pnc_network.substation_id

    for feeder in pnc_network.feeders:
        if feeder.feeder_id in feeder_ids:
            raise ValueError(f"Duplicate feeder ID: {feeder.feeder_id!r}")
        feeder_ids.add(feeder.feeder_id)

        # Check connectivity
        expected_nodes = set(feeder.wtg_ids) | {sub_id}
        if set(feeder.mst_graph.nodes) != expected_nodes:
            raise ValueError(
                f"Feeder {feeder.feeder_id!r} MST nodes do not match expected nodes."
            )

        # Check WTGs
        for wtg_id in feeder.wtg_ids:
            if wtg_id in assigned_wtgs:
                raise ValueError(f"WTG {wtg_id!r} is assigned to multiple feeders.")
            assigned_wtgs.add(wtg_id)

        mst_edges = {tuple(sorted((u, v))) for u, v in feeder.mst_graph.edges}
        feeder_segments_edges = set()

        # Check segments
        for seg in feeder.segments:
            if seg.segment_id in segment_ids:
                raise ValueError(f"Duplicate segment ID: {seg.segment_id!r}")
            segment_ids.add(seg.segment_id)
            total_segments += 1
            total_length += seg.route_length_m

            if seg.feeder_id != feeder.feeder_id:
                raise ValueError(
                    f"Segment {seg.segment_id!r} has wrong feeder_id {seg.feeder_id!r}"
                )

            if seg.from_node_id == seg.to_node_id:
                raise ValueError(f"Self-loop on segment {seg.segment_id!r}")

            edge_key = tuple(sorted((seg.from_node_id, seg.to_node_id)))
            if edge_key not in mst_edges:
                raise ValueError(
                    f"Segment {seg.segment_id!r} does not match any MST edge."
                )
            feeder_segments_edges.add(edge_key)

            if seg.route_length_m <= 0:
                raise ValueError(
                    f"Segment {seg.segment_id!r} has invalid length "
                    f"{seg.route_length_m}"
                )

            # Geometry validation
            geom = seg.route_geometry
            from shapely.geometry import LineString

            if not isinstance(geom, LineString):
                raise ValueError(
                    f"Segment {seg.segment_id!r} geometry is not a LineString."
                )
            if not geom.is_valid:
                raise ValueError(f"Segment {seg.segment_id!r} geometry is invalid.")

            coords = list(geom.coords)
            if any(not (math.isfinite(c[0]) and math.isfinite(c[1])) for c in coords):
                raise ValueError(
                    f"Segment {seg.segment_id!r} geometry has non-finite coordinates."
                )

            if abs(geom.length - seg.route_length_m) > 1e-3:
                raise ValueError(
                    f"Segment {seg.segment_id!r} route_length_m mismatches "
                    "geometry length."
                )

            # Connectivity
            u_coord = (
                pnc_network.substation_geometry
                if seg.from_node_id == sub_id
                else pnc_network.wtg_coordinates[seg.from_node_id]
            )
            v_coord = (
                pnc_network.substation_geometry
                if seg.to_node_id == sub_id
                else pnc_network.wtg_coordinates[seg.to_node_id]
            )
            start_coord = coords[0]
            end_coord = coords[-1]

            def dist(p1: tuple[float, float], p2: Point) -> float:
                return math.hypot(p1[0] - p2.x, p1[1] - p2.y)

            if not (
                (
                    dist(start_coord, u_coord) <= 1e-3
                    and dist(end_coord, v_coord) <= 1e-3
                )
                or (
                    dist(start_coord, v_coord) <= 1e-3
                    and dist(end_coord, u_coord) <= 1e-3
                )
            ):
                raise ValueError(
                    f"Segment {seg.segment_id!r} endpoints "
                    "do not match node coordinates."
                )

        if feeder_segments_edges != mst_edges:
            raise ValueError(
                f"Feeder {feeder.feeder_id!r} segments do not cover all MST edges."
            )

    # Aggregate checks
    if set(pnc_network.wtg_coordinates.keys()) != assigned_wtgs:
        raise ValueError("Network WTG coordinates do not match assigned WTGs.")
    if pnc_network.segment_count != total_segments:
        raise ValueError("Network segment_count mismatches actual segment count.")
    if abs(pnc_network.total_route_length_m - total_length) > 1e-3:
        raise ValueError("Network total_route_length_m mismatches actual sum.")
