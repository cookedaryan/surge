"""Builder for the final presentation result boundary."""

import math
from typing import Literal

import pyproj

from app.algorithms.pole_placement import (
    CollectorPoleResult,
    PolePlacementConfig,
    place_poles_on_network,
)
from app.algorithms.route_refinement import RefinedPhysicalRoute
from app.electrical.load_flow.models import (
    LoadFlowNetworkResult,
    LoadFlowViolationCode,
)
from app.gis.constraints import (
    ConstraintLayer,
    ConstraintMode,
    ConstraintType,
    effective_constraint_geometry,
)
from app.gis.row_analysis import (
    ConstraintFeature,
    ConstraintLayerType,
    ProjectConstraintLayers,
    RowConfig,
    analyse_row_corridors,
)
from app.pnc.models import ProjectPNCNetwork
from app.presentation.exceptions import PresentationDataMismatchError
from app.presentation.geojson import build_enriched_geojson
from app.presentation.models import (
    ElectricalSummary,
    FeederResult,
    NetworkSummary,
    PoleSummary,
    ProjectOptimizationResult,
    SpatialConstraintSummary,
    ViolationPresentation,
)


def build_project_result(
    pnc_network: ProjectPNCNetwork,
    load_flow_result: LoadFlowNetworkResult,
    pole_config: PolePlacementConfig | None = None,
    pole_network: CollectorPoleResult | None = None,
    constraint_layers: tuple[ConstraintLayer, ...] = (),
) -> ProjectOptimizationResult:
    """Merge PNC physical network and AC load flow results into a
    single presentation model.
    """

    # Validation step
    _validate_cross_references(pnc_network, load_flow_result)

    # 1. Network Summary
    network_summary = NetworkSummary(
        wtg_count=pnc_network.wtg_count,
        feeder_count=pnc_network.feeder_count,
        segment_count=pnc_network.segment_count,
        total_route_length_m=round(pnc_network.total_route_length_m, 3),
    )

    # 2. Electrical Summary
    electrical_summary = ElectricalSummary(
        converged=load_flow_result.converged,
        valid=load_flow_result.is_valid,
        solver_algorithm=load_flow_result.solver_algorithm,
        total_active_loss_mw=(
            round(load_flow_result.total_active_loss_mw, 6)
            if load_flow_result.total_active_loss_mw is not None
            else None
        ),
        total_reactive_loss_mvar=(
            round(load_flow_result.total_reactive_loss_mvar, 6)
            if load_flow_result.total_reactive_loss_mvar is not None
            else None
        ),
        minimum_voltage_pu=(
            round(load_flow_result.minimum_voltage_pu, 4)
            if load_flow_result.minimum_voltage_pu is not None
            else None
        ),
        maximum_voltage_pu=(
            round(load_flow_result.maximum_voltage_pu, 4)
            if load_flow_result.maximum_voltage_pu is not None
            else None
        ),
        maximum_loading_percent=(
            round(load_flow_result.maximum_loading_percent, 2)
            if load_flow_result.maximum_loading_percent is not None
            else None
        ),
        violation_count=len(load_flow_result.violations),
    )

    # 3. Violations
    violations: list[ViolationPresentation] = []
    for v in load_flow_result.violations:
        scope: Literal["network", "feeder", "node", "segment"] = "network"
        if v.segment_id:
            scope = "segment"
        elif v.node_id:
            scope = "node"
        elif v.feeder_id:
            scope = "feeder"

        violations.append(
            ViolationPresentation(
                code=str(v.code),
                message=v.message,
                scope=scope,
                node_id=v.node_id,
                segment_id=v.segment_id,
                feeder_id=v.feeder_id,
                measured_value=(
                    round(v.measured_value, 6) if v.measured_value is not None else None
                ),
                limit_value=(
                    round(v.limit_value, 6) if v.limit_value is not None else None
                ),
            )
        )
    # Sort deterministically
    violations.sort(
        key=lambda x: (x.code, x.feeder_id or "", x.segment_id or "", x.node_id or "")
    )

    # 4. Feeders
    electrical_feeder_map = {f.feeder_id: f for f in load_flow_result.feeders}
    segment_to_feeder = {
        segment.segment_id: feeder.feeder_id
        for feeder in pnc_network.feeders
        for segment in feeder.segments
    }
    wtg_to_feeder = {
        wtg_id: feeder.feeder_id
        for feeder in pnc_network.feeders
        for wtg_id in feeder.wtg_ids
    }

    # Associate resource-scoped violations with their owning feeder even when
    # the electrical result omits the redundant feeder_id field.
    feeder_violations_map: dict[str, list[ViolationPresentation]] = {}
    for vp in violations:
        owner_feeder = vp.feeder_id
        if owner_feeder is None and vp.segment_id is not None:
            owner_feeder = segment_to_feeder[vp.segment_id]
        if owner_feeder is None and vp.node_id is not None:
            owner_feeder = wtg_to_feeder.get(vp.node_id)
        if owner_feeder is not None:
            feeder_violations_map.setdefault(owner_feeder, []).append(vp)

    feeder_results: list[FeederResult] = []
    for pnc_feeder in sorted(pnc_network.feeders, key=lambda feeder: feeder.feeder_id):
        f_id = pnc_feeder.feeder_id
        ef = electrical_feeder_map.get(f_id)

        # Default values for non-converged or missing electrical details
        active_loss = round(ef.active_loss_mw, 6) if ef else None
        reactive_loss = round(ef.reactive_loss_mvar, 6) if ef else None
        min_v = round(ef.minimum_voltage_pu, 4) if ef else None
        max_v = round(ef.maximum_voltage_pu, 4) if ef else None
        max_loading = round(ef.maximum_loading_percent, 2) if ef else None
        is_valid = ef.valid if ef else False

        feeder_results.append(
            FeederResult(
                feeder_id=f_id,
                wtg_ids=sorted(list(pnc_feeder.wtg_ids)),
                segment_ids=sorted([s.segment_id for s in pnc_feeder.segments]),
                wtg_count=len(pnc_feeder.wtg_ids),
                segment_count=len(pnc_feeder.segments),
                route_length_m=round(pnc_feeder.total_length_m, 3),
                active_loss_mw=active_loss,
                reactive_loss_mvar=reactive_loss,
                minimum_voltage_pu=min_v,
                maximum_voltage_pu=max_v,
                maximum_loading_percent=max_loading,
                valid=is_valid,
                violations=feeder_violations_map.get(f_id, []),
            )
        )

    refined_routes = _network_routes(pnc_network)
    pole_summary = None
    pole_result = pole_network
    if pole_result is None and pole_config is not None:
        pole_result = place_poles_on_network(pnc_network, pole_config)

    if pole_result is not None:
        type_counts = {
            "terminal": 0,
            "angle": 0,
            "intermediate": 0,
            "junction": 0,
        }
        for pole in pole_result.physical_poles:
            type_counts[pole.pole_type] += 1

        pole_summary = PoleSummary(
            total_poles=pole_result.total_poles,
            terminal_poles=type_counts["terminal"],
            angle_poles=type_counts["angle"],
            intermediate_poles=type_counts["intermediate"],
            junction_poles=type_counts["junction"],
        )

    # 5. GeoJSON
    feature_collection = build_enriched_geojson(
        pnc_network,
        load_flow_result,
        pole_result,
    )

    spatial_constraint_summary = _build_spatial_constraint_summary(
        refined_routes,
        pnc_network.crs,
        constraint_layers,
    )

    return ProjectOptimizationResult(
        project_id=pnc_network.project_id,
        network_summary=network_summary,
        pole_summary=pole_summary,
        spatial_constraint_summary=spatial_constraint_summary,
        electrical_summary=electrical_summary,
        feeders=feeder_results,
        violations=violations,
        feature_collection=feature_collection,
        source_crs=pnc_network.crs.to_string(),
    )


def _network_routes(
    pnc_network: ProjectPNCNetwork,
) -> tuple[RefinedPhysicalRoute, ...]:
    return tuple(
        RefinedPhysicalRoute(
            feeder_id=segment.feeder_id,
            start_node_id=segment.from_node_id,
            end_node_id=segment.to_node_id,
            geometry=segment.route_geometry,
            original_length_m=segment.route_length_m,
            refined_length_m=segment.route_length_m,
            original_traversal_cost=segment.route_length_m,
            refined_traversal_cost=segment.route_length_m,
            route_id=segment.segment_id,
        )
        for feeder in pnc_network.feeders
        for segment in feeder.segments
    )


def _build_spatial_constraint_summary(
    routes: tuple[RefinedPhysicalRoute, ...],
    route_crs: pyproj.CRS,
    constraint_layers: tuple[ConstraintLayer, ...],
) -> SpatialConstraintSummary | None:
    if not constraint_layers:
        return None

    row_constraints = ProjectConstraintLayers(
        features=tuple(
            ConstraintFeature(
                feature_id=layer.layer_id,
                layer_type=_row_layer_type(layer.layer_type),
                geometry=effective_constraint_geometry(layer),
                severity=(
                    "hard" if layer.mode == ConstraintMode.HARD_EXCLUSION else "soft"
                ),
            )
            for layer in constraint_layers
        ),
        crs=route_crs,
    )
    analysis = analyse_row_corridors(
        routes,
        route_crs,
        row_constraints,
        RowConfig(corridor_width_m=0.01),
    )
    hard_ids = {
        layer.layer_id
        for layer in constraint_layers
        if layer.mode == ConstraintMode.HARD_EXCLUSION
        and any(
            route.geometry.intersects(effective_constraint_geometry(layer))
            for route in routes
        )
    }
    if hard_ids:
        raise PresentationDataMismatchError(
            "Recommended route intersects hard exclusion(s): "
            + ", ".join(sorted(hard_ids))
        )

    soft_intersections = tuple(
        intersection
        for intersection in analysis.intersections
        if intersection.severity == "soft"
        and not intersection.touches_only
        and intersection.route_overlap_length_m > 0
    )
    affected_parcels = {
        intersection.feature_id
        for intersection in soft_intersections
        if intersection.layer_type == "parcel"
    }
    return SpatialConstraintSummary(
        hard_exclusion_violation_count=0,
        soft_constraint_intersection_count=len(soft_intersections),
        soft_constraint_overlap_length_m=math.fsum(
            intersection.route_overlap_length_m for intersection in soft_intersections
        ),
        road_crossing_count=analysis.road_crossing_count,
        affected_parcel_count=len(affected_parcels),
        affected_parcel_overlap_length_m=math.fsum(
            intersection.route_overlap_length_m
            for intersection in soft_intersections
            if intersection.layer_type == "parcel"
        ),
    )


def _row_layer_type(layer_type: ConstraintType) -> ConstraintLayerType:
    mapping: dict[ConstraintType, ConstraintLayerType] = {
        ConstraintType.ROAD: "road",
        ConstraintType.HT_LINE: "environmental",
        ConstraintType.WATERCOURSE: "water",
        ConstraintType.PARCEL: "parcel",
        ConstraintType.RESTRICTED_AREA: "restricted",
    }
    return mapping[layer_type]


def _validate_cross_references(
    pnc: ProjectPNCNetwork, lf: LoadFlowNetworkResult
) -> None:
    _validate_load_flow_state(lf)

    # 1. Validation for ALL results (converged or not)
    # Check that violation references actually exist in PNC.
    pnc_nodes = set(pnc.wtg_coordinates.keys())
    pnc_nodes.add(pnc.substation_id)
    pnc_segment_rows = [
        segment for feeder in pnc.feeders for segment in feeder.segments
    ]
    pnc_segments = {segment.segment_id: segment for segment in pnc_segment_rows}
    pnc_feeders = {f.feeder_id for f in pnc.feeders}
    wtg_to_feeder = {
        wtg_id: feeder.feeder_id for feeder in pnc.feeders for wtg_id in feeder.wtg_ids
    }

    if len(pnc_feeders) != len(pnc.feeders):
        raise PresentationDataMismatchError("Duplicate feeder IDs in PNC network")
    if len(wtg_to_feeder) != sum(len(feeder.wtg_ids) for feeder in pnc.feeders):
        raise PresentationDataMismatchError("A WTG belongs to more than one PNC feeder")
    assigned_wtgs = set(wtg_to_feeder)
    coordinate_wtgs = set(pnc.wtg_coordinates)
    if assigned_wtgs != coordinate_wtgs:
        raise PresentationDataMismatchError(
            "PNC WTG membership mismatch. "
            f"Missing assignments: {sorted(coordinate_wtgs - assigned_wtgs)}. "
            f"Unknown assignments: {sorted(assigned_wtgs - coordinate_wtgs)}."
        )
    if len(pnc_segments) != len(pnc_segment_rows):
        raise PresentationDataMismatchError("Duplicate segment IDs in PNC network")
    for feeder in pnc.feeders:
        if feeder.substation_id != pnc.substation_id:
            raise PresentationDataMismatchError(
                f"PNC feeder {feeder.feeder_id} references a different substation"
            )
        for segment in feeder.segments:
            if segment.feeder_id != feeder.feeder_id:
                raise PresentationDataMismatchError(
                    f"PNC segment {segment.segment_id} has the wrong feeder ID"
                )
            if (
                segment.from_node_id not in pnc_nodes
                or segment.to_node_id not in pnc_nodes
            ):
                raise PresentationDataMismatchError(
                    f"PNC segment {segment.segment_id} references an unknown endpoint"
                )

    for v in lf.violations:
        if v.node_id and v.node_id not in pnc_nodes:
            raise PresentationDataMismatchError(
                f"Violation references unknown node: {v.node_id}"
            )
        if v.segment_id and v.segment_id not in pnc_segments:
            raise PresentationDataMismatchError(
                f"Violation references unknown segment: {v.segment_id}"
            )
        if v.feeder_id and v.feeder_id not in pnc_feeders:
            raise PresentationDataMismatchError(
                f"Violation references unknown feeder: {v.feeder_id}"
            )
        if v.segment_id and v.feeder_id:
            segment_feeder = pnc_segments[v.segment_id].feeder_id
            if v.feeder_id != segment_feeder:
                raise PresentationDataMismatchError(
                    f"Violation feeder mismatch for segment {v.segment_id}: "
                    f"{v.feeder_id} != {segment_feeder}"
                )
        if v.node_id and v.feeder_id and v.node_id != pnc.substation_id:
            node_feeder = wtg_to_feeder[v.node_id]
            if v.feeder_id != node_feeder:
                raise PresentationDataMismatchError(
                    f"Violation feeder mismatch for node {v.node_id}: "
                    f"{v.feeder_id} != {node_feeder}"
                )

    if not lf.converged:
        return

    # 2. Validation strictly for CONVERGED results
    # Check for duplicates in load flow results
    lf_bus_ids = [b.node_id for b in lf.buses]
    if len(set(lf_bus_ids)) != len(lf_bus_ids):
        raise PresentationDataMismatchError(
            "Duplicate bus IDs in LoadFlowNetworkResult."
        )

    lf_seg_ids = [s.segment_id for s in lf.segments]
    if len(set(lf_seg_ids)) != len(lf_seg_ids):
        raise PresentationDataMismatchError(
            "Duplicate segment IDs in LoadFlowNetworkResult."
        )

    lf_feeder_ids = [f.feeder_id for f in lf.feeders]
    if len(set(lf_feeder_ids)) != len(lf_feeder_ids):
        raise PresentationDataMismatchError(
            "Duplicate feeder IDs in LoadFlowNetworkResult."
        )

    # Check exact coverage of nodes, segments, feeders
    lf_nodes = set(lf_bus_ids)
    if lf_nodes != pnc_nodes:
        missing = pnc_nodes - lf_nodes
        extra = lf_nodes - pnc_nodes
        raise PresentationDataMismatchError(
            f"Bus coverage mismatch. Missing from LF: {missing}. Extra in LF: {extra}."
        )

    lf_segments_set = set(lf_seg_ids)
    pnc_segments_set = set(pnc_segments.keys())
    if lf_segments_set != pnc_segments_set:
        missing = pnc_segments_set - lf_segments_set
        extra = lf_segments_set - pnc_segments_set
        raise PresentationDataMismatchError(
            f"Segment coverage mismatch. Missing from LF: {missing}. "
            f"Extra in LF: {extra}."
        )

    lf_feeders_set = set(lf_feeder_ids)
    if lf_feeders_set != pnc_feeders:
        missing = pnc_feeders - lf_feeders_set
        extra = lf_feeders_set - pnc_feeders
        raise PresentationDataMismatchError(
            f"Feeder coverage mismatch. Missing from LF: {missing}. "
            f"Extra in LF: {extra}."
        )

    # Check node types
    for b in lf.buses:
        expected_type = "substation" if b.node_id == pnc.substation_id else "wtg"
        if b.node_type != expected_type:
            raise PresentationDataMismatchError(
                f"Node type mismatch for {b.node_id}: LF says {b.node_type}, "
                f"PNC says {expected_type}."
            )

    # Check segment to feeder association
    for s in lf.segments:
        pnc_seg = pnc_segments[s.segment_id]
        if s.feeder_id != pnc_seg.feeder_id:
            raise PresentationDataMismatchError(
                f"Segment to feeder association mismatch for {s.segment_id}: "
                f"LF says {s.feeder_id}, PNC says {pnc_seg.feeder_id}."
            )

    pnc_feeder_map = {feeder.feeder_id: feeder for feeder in pnc.feeders}
    for feeder_result in lf.feeders:
        expected_count = len(pnc_feeder_map[feeder_result.feeder_id].wtg_ids)
        if feeder_result.wtg_count != expected_count:
            raise PresentationDataMismatchError(
                f"WTG count mismatch for feeder {feeder_result.feeder_id}: "
                f"LF says {feeder_result.wtg_count}, PNC says {expected_count}."
            )


def _validate_load_flow_state(result: LoadFlowNetworkResult) -> None:
    """Reject internally inconsistent or non-JSON-safe electrical results."""

    if not result.converged:
        if result.is_valid:
            raise PresentationDataMismatchError(
                "A non-converged load-flow result cannot be valid"
            )
        if result.buses or result.segments or result.feeders:
            raise PresentationDataMismatchError(
                "A non-converged load-flow result must not contain detail rows"
            )
        if not any(
            violation.code == LoadFlowViolationCode.LOAD_FLOW_NOT_CONVERGED
            for violation in result.violations
        ):
            raise PresentationDataMismatchError(
                "A non-converged result requires LOAD_FLOW_NOT_CONVERGED"
            )
    elif result.is_valid != (len(result.violations) == 0):
        raise PresentationDataMismatchError(
            "Converged result validity does not match its violation collection"
        )

    network_values = (
        result.total_generation_mw,
        result.slack_power_mw,
        result.total_active_loss_mw,
        result.total_reactive_loss_mvar,
        result.minimum_voltage_pu,
        result.maximum_voltage_pu,
        result.maximum_loading_percent,
    )
    if not result.converged and any(value is not None for value in network_values):
        raise PresentationDataMismatchError(
            "A non-converged result must not contain network electrical metrics"
        )
    if result.converged and any(value is None for value in network_values):
        raise PresentationDataMismatchError(
            "A converged result must contain all network electrical metrics"
        )
    _require_finite_optional(network_values, "network electrical metrics")

    for bus in result.buses:
        _require_finite_optional(
            (
                bus.voltage_pu,
                bus.voltage_kv,
                bus.voltage_angle_degree,
                bus.net_active_power_demand_mw,
                bus.net_reactive_power_demand_mvar,
            ),
            f"bus {bus.node_id}",
        )
    for segment in result.segments:
        _require_finite_optional(
            (
                segment.p_from_mw,
                segment.q_from_mvar,
                segment.p_to_mw,
                segment.q_to_mvar,
                segment.active_loss_mw,
                segment.reactive_loss_mvar,
                segment.current_from_a,
                segment.current_to_a,
                segment.maximum_current_a,
                segment.loading_percent,
            ),
            f"segment {segment.segment_id}",
        )
    for feeder in result.feeders:
        _require_finite_optional(
            (
                feeder.active_loss_mw,
                feeder.reactive_loss_mvar,
                feeder.minimum_voltage_pu,
                feeder.maximum_voltage_pu,
                feeder.maximum_loading_percent,
            ),
            f"feeder {feeder.feeder_id}",
        )
    for violation in result.violations:
        _require_finite_optional(
            (violation.measured_value, violation.limit_value),
            f"violation {violation.code}",
        )


def _require_finite_optional(
    values: tuple[float | None, ...],
    subject: str,
) -> None:
    if any(value is not None and not math.isfinite(value) for value in values):
        raise PresentationDataMismatchError(f"Non-finite value in {subject}")
