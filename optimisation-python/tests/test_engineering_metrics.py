"""Tests for SURGE-PY-026 canonical candidate engineering metrics."""

from dataclasses import replace

import networkx as nx
import pyproj
import pytest
from shapely.geometry import LineString, Point, Polygon

from app.algorithms.pole_placement import PolePlacementConfig
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import LoadFlowNetworkResult
from app.gis.constraints import ConstraintLayer, ConstraintMode, ConstraintType
from app.optimisation.engineering_metric_models import EngineeringMetricFailureCode
from app.optimisation.engineering_metrics import (
    build_candidate_engineering_metrics,
    calculate_voltage_margin,
)
from app.optimisation.scenario_models import (  # type: ignore
    GroupingObjective,
    PNCScenario,
    ScenarioParameters,
    ScenarioStrategy,
    TopologyWeightProfile,
)
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork

CRS = pyproj.CRS.from_epsg(32644)


@pytest.fixture
def load_flow_config() -> LoadFlowConfig:
    return LoadFlowConfig(
        nominal_voltage_kv=33.0,
        slack_voltage_pu=1.0,
        min_voltage_pu=0.95,
        max_voltage_pu=1.05,
        system_base_mva=100.0,
        cable_types=(
            LoadFlowCableType(
                cable_type_id="CABLE-1",
                resistance_ohm_per_km=0.1,
                reactance_ohm_per_km=0.1,
                capacitance_nf_per_km=0.2,
                max_current_a=300.0,
            ),
        ),
        default_cable_type_id="CABLE-1",
        segment_cable_type_ids={},
    )


@pytest.fixture
def pole_config() -> PolePlacementConfig:
    return PolePlacementConfig(
        target_span_m=50.0,
        min_span_m=20.0,
        max_span_m=60.0,
        coordinate_tolerance_m=0.1,
    )


def _scenario(
    scenario_id: str = "SCN-001",
    traversal_costs: tuple[float, float] = (150.0, 250.0),
) -> PNCScenario:
    segments = (
        PNCSegment(
            segment_id="SEG-1",
            feeder_id="FDR-1",
            from_node_id="SUB-1",
            to_node_id="WTG-1",
            route_geometry=LineString([(0.0, 0.0), (100.0, 0.0)]),
            route_length_m=100.0,
            traversal_cost=traversal_costs[0],
            segment_type="substation_to_wtg",
        ),
        PNCSegment(
            segment_id="SEG-2",
            feeder_id="FDR-1",
            from_node_id="WTG-1",
            to_node_id="WTG-2",
            route_geometry=LineString([(100.0, 0.0), (200.0, 0.0)]),
            route_length_m=100.0,
            traversal_cost=traversal_costs[1],
            segment_type="wtg_to_wtg",
        ),
    )
    mst = nx.Graph()
    mst.add_edges_from((("SUB-1", "WTG-1"), ("WTG-1", "WTG-2")))
    feeder = PNCFeeder(
        feeder_id="FDR-1",
        substation_id="SUB-1",
        wtg_ids=("WTG-1", "WTG-2"),
        ordered_node_ids=("SUB-1", "WTG-1", "WTG-2"),
        segments=segments,
        total_length_m=200.0,
        mst_graph=mst,
    )
    network = ProjectPNCNetwork(
        project_id="PROJECT-1",
        substation_id="SUB-1",
        substation_geometry=Point(0.0, 0.0),
        feeders=(feeder,),
        wtg_coordinates={
            "WTG-1": Point(100.0, 0.0),
            "WTG-2": Point(200.0, 0.0),
        },
        total_route_length_m=200.0,
        feeder_count=1,
        wtg_count=2,
        segment_count=2,
        crs=CRS,
        route_length_by_feeder={"FDR-1": 200.0},
        wtg_count_by_feeder={"FDR-1": 2},
    )
    strategy = ScenarioStrategy.BASELINE
    return PNCScenario(
        scenario_id=scenario_id,
        strategy=strategy.value,
        parameters=ScenarioParameters(
            parameter_set_id="PS-001",
            strategy=strategy,
            grouping_seed=42,
            grouping_objective=GroupingObjective.MINIMIZE_DISTANCE,
            topology_weight_profile=TopologyWeightProfile.DEFAULT,
            topology_penalty=0.0,
            effective_feeder_capacity_mw=10.0,
        ),
        network=network,
        topology_fingerprint=f"v1:{scenario_id}",
        comparison_group_id="CG-1",
        feeder_count=1,
        wtg_count=2,
        segment_count=2,
        total_route_length_m=200.0,
        route_length_by_feeder={"FDR-1": 200.0},
        wtg_count_by_feeder={"FDR-1": 2},
    )


def _load_flow(*, converged: bool = True) -> LoadFlowNetworkResult:
    return LoadFlowNetworkResult(
        converged=converged,
        is_valid=converged,
        solver_algorithm="nr" if converged else None,
        total_generation_mw=10.0 if converged else None,
        slack_power_mw=10.2 if converged else None,
        total_active_loss_mw=0.2 if converged else None,
        total_reactive_loss_mvar=0.1 if converged else None,
        minimum_voltage_pu=0.98 if converged else None,
        maximum_voltage_pu=1.01 if converged else None,
        maximum_loading_percent=62.0 if converged else None,
        buses=(),
        segments=(),
        feeders=(),
        violations=(),
    )


def _constraint_layers() -> tuple[ConstraintLayer, ...]:
    return (
        ConstraintLayer(
            layer_id="PARCEL-1",
            layer_type=ConstraintType.PARCEL,
            mode=ConstraintMode.SOFT_PENALTY,
            geometry=Polygon([(90, -10), (110, -10), (110, 10), (90, 10)]),
            buffer_m=0.0,
            cost_weight=2.0,
            crs=CRS,
        ),
        ConstraintLayer(
            layer_id="ROAD-1",
            layer_type=ConstraintType.ROAD,
            mode=ConstraintMode.SOFT_PENALTY,
            geometry=LineString([(50, -10), (50, 10)]),
            buffer_m=0.0,
            cost_weight=2.0,
            crs=CRS,
        ),
        ConstraintLayer(
            layer_id="ENV-1",
            layer_type=ConstraintType.HT_LINE,
            mode=ConstraintMode.SOFT_PENALTY,
            geometry=Polygon([(140, -10), (160, -10), (160, 10), (140, 10)]),
            buffer_m=0.0,
            cost_weight=2.0,
            crs=CRS,
        ),
        ConstraintLayer(
            layer_id="HARD-1",
            layer_type=ConstraintType.RESTRICTED_AREA,
            mode=ConstraintMode.HARD_EXCLUSION,
            geometry=Polygon([(170, -10), (180, -10), (180, 10), (170, 10)]),
            buffer_m=0.0,
            cost_weight=None,
            crs=CRS,
        ),
    )


def test_extracts_complete_metrics_with_unique_counts_and_hard_evidence(
    load_flow_config: LoadFlowConfig,
    pole_config: PolePlacementConfig,
) -> None:
    assessment = build_candidate_engineering_metrics(
        _scenario(),
        _load_flow(),
        load_flow_config,
        _constraint_layers(),
        pole_config,
    )

    assert assessment.engineering_metrics_available
    assert assessment.extraction_failures == ()
    assert assessment.hard_violation_ids == ("HARD-1",)
    assert assessment.metrics is not None
    assert assessment.metrics.total_route_length_m == pytest.approx(200.0)
    assert assessment.metrics.total_traversal_cost == pytest.approx(400.0)
    assert assessment.metrics.affected_parcel_count == 1
    assert assessment.metrics.road_crossing_count == 1
    assert assessment.metrics.soft_constraint_overlap_length_m == pytest.approx(40.0)
    assert assessment.metrics.environmental_overlap_m2 == pytest.approx(0.2)
    assert assessment.metrics.physical_pole_count == 5
    assert assessment.metrics.total_active_loss_mw == pytest.approx(0.2)
    assert assessment.metrics.maximum_loading_percent == pytest.approx(62.0)
    assert assessment.metrics.voltage_margin_pu == pytest.approx(0.03)
    assert assessment.pole_result is not None
    assert assessment.pole_result.total_poles == 5


def test_missing_pole_config_makes_complete_metrics_unavailable(
    load_flow_config: LoadFlowConfig,
) -> None:
    assessment = build_candidate_engineering_metrics(
        _scenario(),
        _load_flow(),
        load_flow_config,
    )

    assert not assessment.engineering_metrics_available
    assert assessment.metrics is None
    assert assessment.pole_result is None
    assert tuple(failure.code for failure in assessment.extraction_failures) == (
        EngineeringMetricFailureCode.POLE_CONFIG_MISSING,
    )


def test_non_convergence_is_isolated_from_successful_pole_extraction(
    load_flow_config: LoadFlowConfig,
    pole_config: PolePlacementConfig,
) -> None:
    assessment = build_candidate_engineering_metrics(
        _scenario(),
        _load_flow(converged=False),
        load_flow_config,
        pole_config=pole_config,
    )

    assert assessment.metrics is None
    assert assessment.pole_result is not None
    assert tuple(failure.code for failure in assessment.extraction_failures) == (
        EngineeringMetricFailureCode.LOAD_FLOW_NOT_CONVERGED,
    )


@pytest.mark.parametrize(
    ("load_flow", "expected_code"),
    (
        (
            replace(_load_flow(), total_active_loss_mw=None),
            EngineeringMetricFailureCode.ELECTRICAL_METRICS_MISSING,
        ),
        (
            replace(_load_flow(), maximum_loading_percent=float("nan")),
            EngineeringMetricFailureCode.ELECTRICAL_METRICS_NOT_FINITE,
        ),
    ),
)
def test_incomplete_electrical_results_have_structured_failures(
    load_flow: LoadFlowNetworkResult,
    expected_code: EngineeringMetricFailureCode,
    load_flow_config: LoadFlowConfig,
    pole_config: PolePlacementConfig,
) -> None:
    assessment = build_candidate_engineering_metrics(
        _scenario(),
        load_flow,
        load_flow_config,
        pole_config=pole_config,
    )

    assert assessment.metrics is None
    assert tuple(failure.code for failure in assessment.extraction_failures) == (
        expected_code,
    )


def test_pole_failure_is_structured_and_does_not_escape(
    load_flow_config: LoadFlowConfig,
    pole_config: PolePlacementConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.optimisation import engineering_metrics

    def fail_placement(*args: object, **kwargs: object) -> None:
        raise ValueError("bad route")

    monkeypatch.setattr(engineering_metrics, "place_poles_on_network", fail_placement)
    assessment = build_candidate_engineering_metrics(
        _scenario(),
        _load_flow(),
        load_flow_config,
        pole_config=pole_config,
    )

    assert assessment.metrics is None
    assert tuple(failure.code for failure in assessment.extraction_failures) == (
        EngineeringMetricFailureCode.POLE_PLACEMENT_FAILED,
    )


def test_results_are_deterministic_and_candidate_isolated(
    load_flow_config: LoadFlowConfig,
    pole_config: PolePlacementConfig,
) -> None:
    first = build_candidate_engineering_metrics(
        _scenario("SCN-001", (150.0, 250.0)),
        _load_flow(),
        load_flow_config,
        _constraint_layers(),
        pole_config,
    )
    repeated = build_candidate_engineering_metrics(
        _scenario("SCN-001", (150.0, 250.0)),
        _load_flow(),
        load_flow_config,
        tuple(reversed(_constraint_layers())),
        pole_config,
    )
    second = build_candidate_engineering_metrics(
        _scenario("SCN-002", (100.0, 100.0)),
        replace(_load_flow(), total_active_loss_mw=0.1),
        load_flow_config,
        _constraint_layers(),
        pole_config,
    )

    assert first == repeated
    assert first.metrics is not None
    assert second.metrics is not None
    assert first.metrics.total_traversal_cost == pytest.approx(400.0)
    assert second.metrics.total_traversal_cost == pytest.approx(200.0)
    assert first.metrics.total_active_loss_mw == pytest.approx(0.2)
    assert second.metrics.total_active_loss_mw == pytest.approx(0.1)


def test_voltage_margin_uses_the_tighter_limit() -> None:
    assert calculate_voltage_margin(0.98, 1.01, 0.95, 1.05) == pytest.approx(0.03)
    assert calculate_voltage_margin(0.94, 1.01, 0.95, 1.05) == pytest.approx(-0.01)
