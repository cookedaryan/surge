"""Tests for the presentation boundary layer."""

import json
from dataclasses import replace

import pyproj
import pytest
from shapely.geometry import LineString, Point, Polygon

from app.electrical.load_flow.models import (
    LoadFlowBusResult,
    LoadFlowFeederResult,
    LoadFlowNetworkResult,
    LoadFlowSegmentResult,
    LoadFlowViolation,
    LoadFlowViolationCode,
)
from app.gis.constraints import ConstraintLayer, ConstraintMode, ConstraintType
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork
from app.presentation.exceptions import PresentationDataMismatchError
from app.presentation.result_builder import build_project_result

UTM_CRS = pyproj.CRS("EPSG:32643")


def _valid_inputs() -> tuple[ProjectPNCNetwork, LoadFlowNetworkResult]:
    segment = PNCSegment(
        segment_id="SEG-1",
        feeder_id="FDR-1",
        from_node_id="SUB-1",
        to_node_id="WTG-1",
        route_geometry=LineString([(500000.0, 1000000.0), (500100.0, 1000000.0)]),
        route_length_m=100.0,
        segment_type="substation_to_wtg",
    )
    pnc = ProjectPNCNetwork(
        project_id="PROJ-01",
        substation_id="SUB-1",
        substation_geometry=Point(500000.0, 1000000.0),
        feeders=(
            PNCFeeder(
                feeder_id="FDR-1",
                substation_id="SUB-1",
                wtg_ids=("WTG-1",),
                ordered_node_ids=("SUB-1", "WTG-1"),
                segments=(segment,),
                total_length_m=100.0,
                mst_graph=None,
            ),
        ),
        wtg_coordinates={"WTG-1": Point(500100.0, 1000000.0)},
        total_route_length_m=100.0,
        feeder_count=1,
        wtg_count=1,
        segment_count=1,
        crs=UTM_CRS,
        route_length_by_feeder={"FDR-1": 100.0},
        wtg_count_by_feeder={"FDR-1": 1},
    )
    load_flow = LoadFlowNetworkResult(
        converged=True,
        is_valid=True,
        solver_algorithm="nr",
        total_generation_mw=3.0,
        slack_power_mw=-2.9,
        total_active_loss_mw=0.1,
        total_reactive_loss_mvar=0.05,
        minimum_voltage_pu=0.98,
        maximum_voltage_pu=1.0,
        maximum_loading_percent=55.0,
        buses=(
            LoadFlowBusResult("SUB-1", "substation", 1.0, 33.0, 0.0, 0.0, 0.0),
            LoadFlowBusResult("WTG-1", "wtg", 0.98, 32.34, 1.2, 3.0, 0.0),
        ),
        segments=(
            LoadFlowSegmentResult(
                "SEG-1",
                "FDR-1",
                -3.0,
                0.0,
                2.9,
                0.05,
                0.1,
                0.05,
                55.0,
                54.0,
                100.0,
                55.0,
            ),
        ),
        feeders=(
            LoadFlowFeederResult(
                "FDR-1",
                1,
                0.1,
                0.05,
                0.98,
                1.0,
                55.0,
                "WTG-1",
                "SEG-1",
                True,
            ),
        ),
        violations=(),
    )
    return pnc, load_flow


def test_build_project_result_success() -> None:
    """Test successful generation of presentation output."""
    # Build simple PNC network
    pnc = ProjectPNCNetwork(
        project_id="PROJ-01",
        substation_id="SUB-1",
        substation_geometry=Point(1000.0, 1000.0),
        feeders=(
            PNCFeeder(
                feeder_id="FDR-1",
                substation_id="SUB-1",
                wtg_ids=("WTG-1",),
                ordered_node_ids=("SUB-1", "WTG-1"),
                segments=(
                    PNCSegment(
                        segment_id="SEG-1",
                        feeder_id="FDR-1",
                        from_node_id="SUB-1",
                        to_node_id="WTG-1",
                        route_geometry=LineString([(1000.0, 1000.0), (1050.0, 1050.0)]),
                        route_length_m=70.7,
                        segment_type="substation_to_wtg",
                    ),
                ),
                total_length_m=70.7,
                mst_graph=None,  # Not used in presentation
            ),
        ),
        wtg_coordinates={"WTG-1": Point(1050.0, 1050.0)},
        total_route_length_m=70.7,
        feeder_count=1,
        wtg_count=1,
        segment_count=1,
        crs=UTM_CRS,
        route_length_by_feeder={"FDR-1": 70.7},
        wtg_count_by_feeder={"FDR-1": 1},
    )

    # Build converged load flow result
    lf = LoadFlowNetworkResult(
        converged=True,
        is_valid=True,
        solver_algorithm="nr",
        total_generation_mw=3.0,
        slack_power_mw=-2.9,
        total_active_loss_mw=0.1,
        total_reactive_loss_mvar=0.05,
        minimum_voltage_pu=0.98,
        maximum_voltage_pu=1.0,
        maximum_loading_percent=55.0,
        buses=(
            LoadFlowBusResult("SUB-1", "substation", 1.0, 33.0, 0.0, 0.0, 0.0),
            LoadFlowBusResult("WTG-1", "wtg", 0.98, 32.34, 1.2, 3.0, 0.0),
        ),
        segments=(
            LoadFlowSegmentResult(
                "SEG-1",
                "FDR-1",
                -3.0,
                0.0,
                2.9,
                0.05,
                0.1,
                0.05,
                55.0,
                54.0,
                100.0,
                55.0,
            ),
        ),
        feeders=(
            LoadFlowFeederResult(
                "FDR-1", 1, 0.1, 0.05, 0.98, 1.0, 55.0, "WTG-1", "SEG-1", True
            ),
        ),
        violations=(),
    )

    result = build_project_result(pnc, lf)

    # Assert JSON safety and serialization
    json_str = json.dumps(result.model_dump(mode="json"), allow_nan=False)
    assert json_str

    # Assert basic structure
    assert result.project_id == "PROJ-01"
    assert result.electrical_summary.converged is True
    assert result.electrical_summary.valid is True
    assert result.network_summary.feeder_count == 1

    assert len(result.feeders) == 1
    f1 = result.feeders[0]
    assert f1.feeder_id == "FDR-1"
    assert f1.wtg_ids == ["WTG-1"]

    # Assert GeoJSON structure and enrichment
    fc = result.feature_collection
    assert fc["type"] == "FeatureCollection"
    features = fc["features"]
    assert len(features) == 3  # SUB, WTG, SEG

    # Verify order: SUB, WTG, SEG
    assert features[0]["properties"]["feature_type"] == "pnc_substation"
    assert features[1]["properties"]["feature_type"] == "pnc_wtg"
    assert features[2]["properties"]["feature_type"] == "pnc_segment"

    # Verify enrichment
    wtg_props = features[1]["properties"]
    assert wtg_props["voltage_pu"] == 0.98

    seg_props = features[2]["properties"]
    assert seg_props["loading_percent"] == 55.0
    assert seg_props["from_voltage_pu"] == 1.0
    assert seg_props["to_voltage_pu"] == 0.98


def test_build_project_result_with_poles() -> None:
    """Test successful generation of presentation output including poles."""
    pnc, lf = _valid_inputs()
    # Provide a simple pole config to generate poles
    from app.algorithms.pole_placement import PolePlacementConfig

    pole_config = PolePlacementConfig(
        target_span_m=50.0,
        min_span_m=10.0,
        max_span_m=60.0,
    )

    result = build_project_result(pnc, lf, pole_config=pole_config)

    # Assert pole summary exists
    assert result.pole_summary is not None
    assert result.pole_summary.total_poles > 0
    assert result.pole_summary.terminal_poles >= 2

    # Assert GeoJSON structure and enrichment
    fc = result.feature_collection
    assert fc["type"] == "FeatureCollection"
    features = fc["features"]

    # Verify order: SUB, WTG, SEG, POLES
    assert features[0]["properties"]["feature_type"] == "pnc_substation"
    assert features[1]["properties"]["feature_type"] == "pnc_wtg"
    assert features[2]["properties"]["feature_type"] == "pnc_segment"

    # Rest should be poles
    pole_features = features[3:]
    assert len(pole_features) == result.pole_summary.total_poles
    assert pole_features[0]["properties"]["feature_type"] == "pnc_pole"

    # Bbox should include pole coordinates
    bbox = fc["bbox"]
    assert len(bbox) == 4
    for pole_feature in pole_features:
        lon, lat = pole_feature["geometry"]["coordinates"]
        assert bbox[0] <= lon <= bbox[2]
        assert bbox[1] <= lat <= bbox[3]


def test_place_poles_on_network_deduplicates_junction_poles() -> None:
    """The project-level pole service applies endpoint deduplication."""
    # Build a PNC network with two feeders leaving the same substation
    # Both feeders share the substation node at (1000.0, 1000.0)
    pnc = ProjectPNCNetwork(
        project_id="PROJ-02",
        substation_id="SUB-1",
        substation_geometry=Point(1000.0, 1000.0),
        feeders=(
            PNCFeeder(
                feeder_id="FDR-1",
                substation_id="SUB-1",
                wtg_ids=("WTG-1",),
                ordered_node_ids=("SUB-1", "WTG-1"),
                segments=(
                    PNCSegment(
                        segment_id="SEG-1",
                        feeder_id="FDR-1",
                        from_node_id="SUB-1",
                        to_node_id="WTG-1",
                        route_geometry=LineString([(1000.0, 1000.0), (1050.0, 1000.0)]),
                        route_length_m=50.0,
                        segment_type="substation_to_wtg",
                    ),
                ),
                total_length_m=50.0,
                mst_graph=None,
            ),
            PNCFeeder(
                feeder_id="FDR-2",
                substation_id="SUB-1",
                wtg_ids=("WTG-2",),
                ordered_node_ids=("SUB-1", "WTG-2"),
                segments=(
                    PNCSegment(
                        segment_id="SEG-2",
                        feeder_id="FDR-2",
                        from_node_id="SUB-1",
                        to_node_id="WTG-2",
                        route_geometry=LineString([(1000.0, 1000.0), (1000.0, 1050.0)]),
                        route_length_m=50.0,
                        segment_type="substation_to_wtg",
                    ),
                ),
                total_length_m=50.0,
                mst_graph=None,
            ),
        ),
        wtg_coordinates={
            "WTG-1": Point(1050.0, 1000.0),
            "WTG-2": Point(1000.0, 1050.0),
        },
        total_route_length_m=100.0,
        feeder_count=2,
        wtg_count=2,
        segment_count=2,
        crs=UTM_CRS,
        route_length_by_feeder={"FDR-1": 50.0, "FDR-2": 50.0},
        wtg_count_by_feeder={"FDR-1": 1, "FDR-2": 1},
    )

    _lf = LoadFlowNetworkResult(
        converged=True,
        is_valid=True,
        solver_algorithm="nr",
        total_generation_mw=6.0,
        slack_power_mw=-5.8,
        total_active_loss_mw=0.2,
        total_reactive_loss_mvar=0.1,
        minimum_voltage_pu=0.98,
        maximum_voltage_pu=1.0,
        maximum_loading_percent=55.0,
        buses=(
            LoadFlowBusResult("SUB-1", "substation", 1.0, 33.0, 0.0, 0.0, 0.0),
            LoadFlowBusResult("WTG-1", "wtg", 0.98, 32.34, 1.2, 3.0, 0.0),
            LoadFlowBusResult("WTG-2", "wtg", 0.98, 32.34, 1.2, 3.0, 0.0),
        ),
        segments=(
            LoadFlowSegmentResult(
                "SEG-1",
                "FDR-1",
                -3.0,
                0.0,
                2.9,
                0.05,
                0.1,
                0.05,
                55.0,
                54.0,
                100.0,
                55.0,
            ),
            LoadFlowSegmentResult(
                "SEG-2",
                "FDR-2",
                -3.0,
                0.0,
                2.9,
                0.05,
                0.1,
                0.05,
                55.0,
                54.0,
                100.0,
                55.0,
            ),
        ),
        feeders=(
            LoadFlowFeederResult(
                "FDR-1", 1, 0.1, 0.05, 0.98, 1.0, 55.0, "WTG-1", "SEG-1", True
            ),
            LoadFlowFeederResult(
                "FDR-2", 1, 0.1, 0.05, 0.98, 1.0, 55.0, "WTG-2", "SEG-2", True
            ),
        ),
        violations=(),
    )

    from app.algorithms.pole_placement import (
        PolePlacementConfig,
        place_poles_on_network,
    )

    pole_config = PolePlacementConfig(
        target_span_m=50.0,
        min_span_m=10.0,
        max_span_m=60.0,
        coordinate_tolerance_m=1.0,
    )

    result = place_poles_on_network(pnc, pole_config)

    assert result.total_poles == 3
    junctions = [pole for pole in result.physical_poles if pole.pole_type == "junction"]
    assert len(junctions) == 1
    junction = junctions[0]
    assert junction.feeder_ids == ("FDR-1", "FDR-2")
    assert junction.route_ids == ("SEG-1", "SEG-2")
    assert len(junction.source_pole_ids) == 2
    assert junction.topology_node_id == "SUB-1"


def test_soft_constraint_impacts_are_disclosed() -> None:
    pnc, load_flow = _valid_inputs()
    constraints = (
        ConstraintLayer(
            layer_id="road-1",
            layer_type=ConstraintType.ROAD,
            mode=ConstraintMode.SOFT_PENALTY,
            geometry=LineString([(500050.0, 999990.0), (500050.0, 1000010.0)]),
            buffer_m=5.0,
            cost_weight=20.0,
            crs=UTM_CRS,
        ),
        ConstraintLayer(
            layer_id="parcel-1",
            layer_type=ConstraintType.PARCEL,
            mode=ConstraintMode.SOFT_PENALTY,
            geometry=Polygon(
                [
                    (500070.0, 999990.0),
                    (500090.0, 999990.0),
                    (500090.0, 1000010.0),
                    (500070.0, 1000010.0),
                ]
            ),
            buffer_m=0.0,
            cost_weight=5.0,
            crs=UTM_CRS,
        ),
    )

    result = build_project_result(
        pnc,
        load_flow,
        constraint_layers=constraints,
    )

    summary = result.spatial_constraint_summary
    assert summary is not None
    assert summary.hard_exclusion_violation_count == 0
    assert summary.soft_constraint_intersection_count == 2
    assert summary.soft_constraint_overlap_length_m == pytest.approx(30.0)
    assert summary.road_crossing_count == 1
    assert summary.affected_parcel_count == 1
    assert summary.affected_parcel_overlap_length_m == pytest.approx(20.0)


def test_hard_constraint_intersection_fails_packaging() -> None:
    pnc, load_flow = _valid_inputs()
    hard_constraint = ConstraintLayer(
        layer_id="restricted-1",
        layer_type=ConstraintType.RESTRICTED_AREA,
        mode=ConstraintMode.HARD_EXCLUSION,
        geometry=Polygon(
            [
                (500040.0, 999990.0),
                (500060.0, 999990.0),
                (500060.0, 1000010.0),
                (500040.0, 1000010.0),
            ]
        ),
        buffer_m=0.0,
        cost_weight=None,
        crs=UTM_CRS,
    )

    with pytest.raises(
        PresentationDataMismatchError,
        match="Recommended route intersects hard exclusion",
    ):
        build_project_result(
            pnc,
            load_flow,
            constraint_layers=(hard_constraint,),
        )


def test_missing_bus_mismatch() -> None:
    pnc, load_flow = _valid_inputs()
    lf = replace(load_flow, buses=(load_flow.buses[0],))

    with pytest.raises(PresentationDataMismatchError, match="Bus coverage mismatch"):
        build_project_result(pnc, lf)


def test_rejects_unassigned_pnc_wtg() -> None:
    pnc, load_flow = _valid_inputs()
    pnc = replace(
        pnc,
        wtg_coordinates={
            **pnc.wtg_coordinates,
            "WTG-UNASSIGNED": Point(500200.0, 1000000.0),
        },
        wtg_count=2,
    )

    with pytest.raises(PresentationDataMismatchError, match="WTG membership mismatch"):
        build_project_result(pnc, load_flow)


def test_non_converged_logic() -> None:
    pnc, _ = _valid_inputs()
    # Non-converged LF has empty electrical arrays
    lf = LoadFlowNetworkResult(
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
                message="Not converged",
            ),
        ),
    )

    # Should NOT raise mismatched error despite empty arrays because converged=False
    result = build_project_result(pnc, lf)

    assert result.electrical_summary.converged is False
    assert result.electrical_summary.valid is False
    assert result.electrical_summary.total_active_loss_mw is None

    assert len(result.violations) == 1
    assert result.violations[0].code == "LOAD_FLOW_NOT_CONVERGED"


def test_non_converged_output_keeps_map_contract() -> None:
    pnc, load_flow = _valid_inputs()
    non_converged = LoadFlowNetworkResult(
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
                message="Not converged",
            ),
        ),
    )

    result = build_project_result(pnc, non_converged)
    features = result.feature_collection["features"]

    assert [feature["id"] for feature in features] == [
        "substation-SUB-1",
        "wtg-WTG-1",
        "segment-SEG-1",
    ]
    assert features[1]["properties"]["voltage_pu"] is None
    assert features[2]["properties"]["loading_percent"] is None
    assert features[1]["properties"]["has_voltage_violation"] is False
    assert features[2]["properties"]["has_cable_overload"] is False
    assert len(result.feature_collection["bbox"]) == 4
    assert result.source_crs == "EPSG:32643"
    json.dumps(result.model_dump(mode="json"), allow_nan=False)


def test_rejects_non_finite_electrical_value() -> None:
    pnc, load_flow = _valid_inputs()
    buses = (
        load_flow.buses[0],
        replace(load_flow.buses[1], voltage_pu=float("nan")),
    )

    with pytest.raises(PresentationDataMismatchError, match="Non-finite value"):
        build_project_result(pnc, replace(load_flow, buses=buses))


def test_rejects_non_finite_segment_property() -> None:
    pnc, load_flow = _valid_inputs()
    invalid_segment = replace(pnc.feeders[0].segments[0], route_length_m=float("nan"))
    invalid_feeder = replace(pnc.feeders[0], segments=(invalid_segment,))
    pnc = replace(pnc, feeders=(invalid_feeder,))

    with pytest.raises(PresentationDataMismatchError, match="Non-finite value"):
        build_project_result(pnc, load_flow)


def test_rejects_inconsistent_non_converged_state() -> None:
    pnc, load_flow = _valid_inputs()
    inconsistent = replace(
        load_flow,
        converged=False,
        is_valid=False,
        violations=(
            LoadFlowViolation(
                LoadFlowViolationCode.LOAD_FLOW_NOT_CONVERGED,
                "Not converged",
            ),
        ),
    )

    with pytest.raises(PresentationDataMismatchError, match="detail rows"):
        build_project_result(pnc, inconsistent)


def test_rejects_non_converged_network_metrics() -> None:
    pnc, load_flow = _valid_inputs()
    inconsistent = replace(
        load_flow,
        converged=False,
        is_valid=False,
        total_generation_mw=None,
        slack_power_mw=None,
        total_active_loss_mw=0.0,
        total_reactive_loss_mvar=None,
        minimum_voltage_pu=None,
        maximum_voltage_pu=None,
        maximum_loading_percent=None,
        buses=(),
        segments=(),
        feeders=(),
        violations=(
            LoadFlowViolation(
                LoadFlowViolationCode.LOAD_FLOW_NOT_CONVERGED,
                "Not converged",
            ),
        ),
    )

    with pytest.raises(PresentationDataMismatchError, match="network electrical"):
        build_project_result(pnc, inconsistent)


def test_only_voltage_and_overload_codes_set_feature_flags() -> None:
    pnc, load_flow = _valid_inputs()
    diagnostic = LoadFlowViolation(
        code=LoadFlowViolationCode.RESULT_NOT_FINITE,
        message="Diagnostic",
        node_id="WTG-1",
        segment_id="SEG-1",
        feeder_id="FDR-1",
    )
    invalid_result = replace(load_flow, is_valid=False, violations=(diagnostic,))

    result = build_project_result(pnc, invalid_result)
    features = result.feature_collection["features"]

    assert features[1]["properties"]["has_voltage_violation"] is False
    assert features[2]["properties"]["has_cable_overload"] is False


def test_resource_violation_is_included_in_owning_feeder() -> None:
    pnc, load_flow = _valid_inputs()
    violation = LoadFlowViolation(
        code=LoadFlowViolationCode.BUS_UNDERVOLTAGE,
        message="Low voltage",
        node_id="WTG-1",
        measured_value=0.89,
        limit_value=0.9,
    )
    invalid_feeder = replace(load_flow.feeders[0], valid=False)

    result = build_project_result(
        pnc,
        replace(
            load_flow,
            is_valid=False,
            feeders=(invalid_feeder,),
            violations=(violation,),
        ),
    )

    assert result.feeders[0].violations == [result.violations[0]]
    assert result.feeders[0].violations[0].node_id == "WTG-1"


def test_rejects_violation_with_wrong_segment_feeder() -> None:
    pnc, load_flow = _valid_inputs()
    pnc = replace(
        pnc,
        feeders=(
            pnc.feeders[0],
            PNCFeeder(
                feeder_id="FDR-2",
                substation_id="SUB-1",
                wtg_ids=(),
                ordered_node_ids=("SUB-1",),
                segments=(),
                total_length_m=0.0,
                mst_graph=None,
            ),
        ),
        feeder_count=2,
    )
    diagnostic = LoadFlowViolation(
        code=LoadFlowViolationCode.CABLE_OVERLOAD,
        message="Wrong owner",
        segment_id="SEG-1",
        feeder_id="FDR-2",
    )
    invalid_result = replace(load_flow, is_valid=False, violations=(diagnostic,))

    with pytest.raises(PresentationDataMismatchError, match="feeder mismatch"):
        build_project_result(pnc, invalid_result)
