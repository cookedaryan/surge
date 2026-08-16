"""Candidate-level extraction of canonical raw engineering quantities."""

import math

from shapely.ops import unary_union

from app.algorithms.pole_placement import PolePlacementConfig, place_poles_on_network
from app.algorithms.route_refinement import RefinedPhysicalRoute
from app.electrical.load_flow.config import LoadFlowConfig
from app.electrical.load_flow.models import LoadFlowNetworkResult
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
from app.optimisation.engineering_metric_models import (
    CandidateEngineeringAssessment,
    CandidateEngineeringMetrics,
    EngineeringMetricFailure,
    EngineeringMetricFailureCode,
    ParcelEngineeringExposure,
)
from app.optimisation.scenario_models import PNCScenario
from app.pnc.models import ProjectPNCNetwork


def calculate_voltage_margin(
    minimum_voltage_pu: float,
    maximum_voltage_pu: float,
    configured_minimum_voltage_pu: float,
    configured_maximum_voltage_pu: float,
) -> float:
    """Return the smaller distance from observed voltages to configured limits."""
    return min(
        minimum_voltage_pu - configured_minimum_voltage_pu,
        configured_maximum_voltage_pu - maximum_voltage_pu,
    )


def build_candidate_engineering_metrics(
    scenario: PNCScenario,
    load_flow_result: LoadFlowNetworkResult,
    load_flow_config: LoadFlowConfig,
    constraint_layers: tuple[ConstraintLayer, ...] = (),
    *,
    owner_interaction_count: int = 0,
    pole_config: PolePlacementConfig | None = None,
    row_corridor_width_m: float = 18.0,
) -> CandidateEngineeringAssessment:
    """Extract engineering metrics without changing recommendation eligibility."""
    failures: list[EngineeringMetricFailure] = []
    network = scenario.network

    total_route_length_m = network.total_route_length_m
    total_traversal_cost = math.fsum(
        segment.traversal_cost
        for feeder in network.feeders
        for segment in feeder.segments
    )
    if (
        not math.isfinite(total_route_length_m)
        or total_route_length_m < 0.0
        or not math.isfinite(total_traversal_cost)
        or total_traversal_cost < 0.0
    ):
        failures.append(
            EngineeringMetricFailure(
                EngineeringMetricFailureCode.PHYSICAL_METRICS_INVALID,
                "Route length and traversal cost must be finite and non-negative",
            )
        )

    affected_parcel_count = 0
    road_crossing_count = 0
    soft_overlap_length_m = 0.0
    environmental_overlap_m2 = 0.0
    hard_violation_ids: tuple[str, ...] = ()
    parcel_exposures: tuple[ParcelEngineeringExposure, ...] = ()
    try:
        (
            affected_parcel_count,
            road_crossing_count,
            soft_overlap_length_m,
            environmental_overlap_m2,
            hard_violation_ids,
            parcel_exposures,
        ) = _extract_spatial_metrics(
            network,
            constraint_layers,
            row_corridor_width_m=row_corridor_width_m,
        )
    except Exception as exc:
        failures.append(
            EngineeringMetricFailure(
                EngineeringMetricFailureCode.SPATIAL_ANALYSIS_FAILED,
                f"Spatial metric extraction failed: {exc}",
            )
        )

    pole_result = None
    if pole_config is None:
        failures.append(
            EngineeringMetricFailure(
                EngineeringMetricFailureCode.POLE_CONFIG_MISSING,
                "Pole configuration is required to calculate physical pole count",
            )
        )
    else:
        try:
            pole_result = place_poles_on_network(network, pole_config)
        except Exception as exc:
            failures.append(
                EngineeringMetricFailure(
                    EngineeringMetricFailureCode.POLE_PLACEMENT_FAILED,
                    f"Pole placement failed: {exc}",
                )
            )

    electrical_values: tuple[float, float, float] | None = None
    if not load_flow_result.converged:
        failures.append(
            EngineeringMetricFailure(
                EngineeringMetricFailureCode.LOAD_FLOW_NOT_CONVERGED,
                "Load flow did not converge",
            )
        )
    else:
        loss = load_flow_result.total_active_loss_mw
        loading = load_flow_result.maximum_loading_percent
        minimum_voltage = load_flow_result.minimum_voltage_pu
        maximum_voltage = load_flow_result.maximum_voltage_pu
        raw_electrical_values = (loss, loading, minimum_voltage, maximum_voltage)
        if any(value is None for value in raw_electrical_values):
            failures.append(
                EngineeringMetricFailure(
                    EngineeringMetricFailureCode.ELECTRICAL_METRICS_MISSING,
                    "Required load-flow metrics are missing",
                )
            )
        else:
            assert loss is not None
            assert loading is not None
            assert minimum_voltage is not None
            assert maximum_voltage is not None
            if any(
                not math.isfinite(value)
                for value in (loss, loading, minimum_voltage, maximum_voltage)
            ):
                failures.append(
                    EngineeringMetricFailure(
                        EngineeringMetricFailureCode.ELECTRICAL_METRICS_NOT_FINITE,
                        "Required load-flow metrics are not finite",
                    )
                )
            elif loss < 0.0 or loading < 0.0:
                failures.append(
                    EngineeringMetricFailure(
                        EngineeringMetricFailureCode.ELECTRICAL_METRICS_INVALID,
                        "Electrical loss and loading metrics must be non-negative",
                    )
                )
            elif minimum_voltage > maximum_voltage:
                failures.append(
                    EngineeringMetricFailure(
                        EngineeringMetricFailureCode.ELECTRICAL_METRICS_INVALID,
                        "Minimum observed voltage cannot exceed maximum voltage",
                    )
                )
            else:
                voltage_margin = calculate_voltage_margin(
                    minimum_voltage,
                    maximum_voltage,
                    load_flow_config.min_voltage_pu,
                    load_flow_config.max_voltage_pu,
                )
                electrical_values = (loss, loading, voltage_margin)

    metrics = None
    if not failures and pole_result is not None and electrical_values is not None:
        loss, loading, voltage_margin = electrical_values
        try:
            metrics = CandidateEngineeringMetrics(
                total_route_length_m=total_route_length_m,
                total_traversal_cost=total_traversal_cost,
                affected_parcel_count=affected_parcel_count,
                owner_interaction_count=owner_interaction_count,
                road_crossing_count=road_crossing_count,
                soft_constraint_overlap_length_m=soft_overlap_length_m,
                environmental_overlap_m2=environmental_overlap_m2,
                physical_pole_count=pole_result.total_poles,
                total_active_loss_mw=loss,
                maximum_loading_percent=loading,
                voltage_margin_pu=voltage_margin,
            )
        except ValueError as exc:
            failures.append(
                EngineeringMetricFailure(
                    EngineeringMetricFailureCode.PHYSICAL_METRICS_INVALID,
                    f"Canonical engineering metrics are invalid: {exc}",
                )
            )

    return CandidateEngineeringAssessment(
        scenario_id=scenario.scenario_id,
        metrics=metrics,
        engineering_metrics_available=metrics is not None,
        hard_violation_ids=hard_violation_ids,
        extraction_failures=tuple(failures),
        pole_result=pole_result,
        parcel_exposures=parcel_exposures,
    )


def _extract_spatial_metrics(
    network: ProjectPNCNetwork,
    constraint_layers: tuple[ConstraintLayer, ...],
    *,
    row_corridor_width_m: float,
) -> tuple[
    int,
    int,
    float,
    float,
    tuple[str, ...],
    tuple[ParcelEngineeringExposure, ...],
]:
    pnc_network = network
    routes = _network_routes(pnc_network)
    if any(not layer.crs.equals(pnc_network.crs) for layer in constraint_layers):
        raise ValueError("Constraint layer CRS must match the candidate network CRS")
    constraints = ProjectConstraintLayers(
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
        crs=pnc_network.crs,
    )
    analysis = analyse_row_corridors(
        routes,
        pnc_network.crs,
        constraints,
        RowConfig(corridor_width_m=row_corridor_width_m),
    )
    soft_intersections = tuple(
        intersection
        for intersection in analysis.intersections
        if intersection.severity == "soft" and not intersection.touches_only
    )
    affected_parcel_ids = {
        intersection.feature_id
        for intersection in soft_intersections
        if intersection.layer_type == "parcel"
        and (
            intersection.route_overlap_length_m > 0.0
            or intersection.intersection_area_m2 > 0.0
        )
    }
    environmental_geometries = [
        intersection.geometry
        for intersection in soft_intersections
        if intersection.layer_type in {"environmental", "forest"}
        and intersection.intersection_area_m2 > 0.0
    ]
    hard_ids = {
        layer.layer_id
        for layer in constraint_layers
        if layer.mode == ConstraintMode.HARD_EXCLUSION
        and any(
            route.geometry.intersects(effective_constraint_geometry(layer))
            for route in routes
        )
    }
    parcel_exposures_list: list[ParcelEngineeringExposure] = []
    from collections import defaultdict

    parcel_intersections = defaultdict(list)
    for intersection in soft_intersections:
        if intersection.layer_type == "parcel":
            parcel_intersections[intersection.feature_id].append(intersection)

    for parcel_id in sorted(parcel_intersections.keys()):
        intersections = parcel_intersections[parcel_id]
        merged_row = unary_union([item.geometry for item in intersections])
        merged_route = unary_union(
            [item.route_intersection_geometry for item in intersections]
        )
        exposure = ParcelEngineeringExposure(
            parcel_id=parcel_id,
            route_overlap_length_m=float(merged_route.length),
            row_intersection_area_m2=float(merged_row.area),
        )
        parcel_exposures_list.append(exposure)

    return (
        len(affected_parcel_ids),
        analysis.road_crossing_count,
        math.fsum(
            intersection.route_overlap_length_m
            for intersection in soft_intersections
            if intersection.route_overlap_length_m > 0.0
        ),
        (
            float(unary_union(environmental_geometries).area)
            if environmental_geometries
            else 0.0
        ),
        tuple(sorted(hard_ids)),
        tuple(parcel_exposures_list),
    )


def _network_routes(
    network: ProjectPNCNetwork,
) -> tuple[RefinedPhysicalRoute, ...]:
    return tuple(
        RefinedPhysicalRoute(
            feeder_id=segment.feeder_id,
            start_node_id=segment.from_node_id,
            end_node_id=segment.to_node_id,
            geometry=segment.route_geometry,
            original_length_m=segment.route_length_m,
            refined_length_m=segment.route_length_m,
            original_traversal_cost=segment.traversal_cost,
            refined_traversal_cost=segment.traversal_cost,
            route_id=segment.segment_id,
        )
        for feeder in network.feeders
        for segment in feeder.segments
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
