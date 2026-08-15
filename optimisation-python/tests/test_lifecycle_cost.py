import datetime
import subprocess
import sys
from dataclasses import replace
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.algorithms.pole_placement import CollectorPoleResult
from app.costing.failures import CostConfigurationError, CostEvaluationFailureCode
from app.costing.lifecycle import evaluate_candidate_cost
from app.costing.models import (
    ConductorCostItem,
    EngineeringCostCatalogue,
    LandCostPolicy,
    LandPricingBasis,
    LifecycleCostConfig,
    PoleCostItem,
)
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import LoadFlowNetworkResult
from app.optimisation.engineering_metric_models import (
    CandidateEngineeringAssessment,
    CandidateEngineeringMetrics,
    EngineeringMetricFailure,
    EngineeringMetricFailureCode,
    ParcelEngineeringExposure,
)
from app.optimisation.scenario_models import PNCScenario
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork


@pytest.fixture
def dummy_scenario() -> PNCScenario:
    segment = MagicMock(spec=PNCSegment)
    segment.route_length_m = 1000.0
    segment.segment_id = "seg1"

    feeder = MagicMock(spec=PNCFeeder)
    feeder.segments = tuple([segment])

    network = MagicMock(spec=ProjectPNCNetwork)
    network.total_length_m = 1000.0
    network.feeders = tuple([feeder])

    scenario = MagicMock(spec=PNCScenario)
    scenario.scenario_id = "s1"
    scenario.network = network
    return scenario


@pytest.fixture
def dummy_electrical_config() -> LoadFlowConfig:
    return LoadFlowConfig(
        nominal_voltage_kv=33.0,
        slack_voltage_pu=1.0,
        min_voltage_pu=0.95,
        max_voltage_pu=1.05,
        system_base_mva=100.0,
        cable_types=tuple(
            [
                LoadFlowCableType(
                    cable_type_id="cable1",
                    resistance_ohm_per_km=0.1,
                    reactance_ohm_per_km=0.1,
                    capacitance_nf_per_km=0.1,
                    max_current_a=500.0,
                    parallel_count=1,
                    derating_factor=1.0,
                )
            ]
        ),
        default_cable_type_id="cable1",
        segment_cable_type_ids={"seg1": "cable1"},
    )


@pytest.fixture
def dummy_load_flow_result() -> LoadFlowNetworkResult:
    result = MagicMock(spec=LoadFlowNetworkResult)
    result.is_valid = True
    result.converged = True
    result.total_active_loss_mw = 1.5
    result.maximum_loading_percent = 50.0
    result.minimum_voltage_pu = 0.98
    result.maximum_voltage_pu = 1.0
    result.feeders = tuple()
    return result


@pytest.fixture
def dummy_engineering_assessment() -> CandidateEngineeringAssessment:
    metrics = MagicMock(spec=CandidateEngineeringMetrics)
    metrics.total_route_length_m = 1000.0
    metrics.total_traversal_cost = 100.0
    metrics.affected_parcel_count = 1
    metrics.road_crossing_count = 0
    metrics.soft_constraint_overlap_length_m = 0.0
    metrics.environmental_overlap_m2 = 0.0
    metrics.physical_pole_count = 2
    pole_result = MagicMock(spec=CollectorPoleResult)
    pole_result.physical_poles = tuple(
        [
            MagicMock(pole_type="terminal"),
            MagicMock(pole_type="terminal"),
        ]
    )
    exposures = tuple(
        [
            ParcelEngineeringExposure(
                parcel_id="parcel1",
                route_overlap_length_m=500.0,
                row_intersection_area_m2=5000.0,
            )
        ]
    )
    assessment = MagicMock(spec=CandidateEngineeringAssessment)
    assessment.scenario_id = "s1"
    assessment.metrics = metrics
    assessment.eligible = True
    assessment.engineering_metrics_available = True
    assessment.hard_violation_ids = tuple()
    assessment.extraction_failures = tuple()
    assessment.pole_result = pole_result
    assessment.parcel_exposures = exposures
    return assessment


@pytest.fixture
def dummy_catalogue() -> EngineeringCostCatalogue:
    return EngineeringCostCatalogue(
        catalogue_id="cat1",
        version="1.0",
        currency="USD",
        price_basis_date=datetime.date(2025, 1, 1),
        conductor_items=tuple(
            [
                ConductorCostItem(
                    cable_type_id="cable1",
                    installed_cost_per_km_per_parallel_circuit=Decimal("100000.00"),
                )
            ]
        ),
        pole_items=tuple(
            [
                PoleCostItem(
                    pole_type="terminal", installed_cost_each=Decimal("5000.00")
                ),
                PoleCostItem(pole_type="angle", installed_cost_each=Decimal("6000.00")),
                PoleCostItem(
                    pole_type="intermediate", installed_cost_each=Decimal("3000.00")
                ),
                PoleCostItem(
                    pole_type="junction", installed_cost_each=Decimal("7000.00")
                ),
            ]
        ),
        land_policy=LandCostPolicy(
            fixed_cost_per_affected_parcel=Decimal("1000.00"),
            variable_basis=LandPricingBasis.ROW_INTERSECTION_AREA_M2,
            variable_rate=Decimal("10.00"),
        ),
    )


@pytest.fixture
def dummy_lifecycle_config() -> LifecycleCostConfig:
    return LifecycleCostConfig(
        currency="USD",
        energy_price_basis_date=datetime.date(2025, 1, 1),
        analysis_period_years=25,
        discount_rate=Decimal("0.08"),
        annual_operating_hours=8760,
        loss_load_factor=Decimal("0.3"),
        energy_price_per_mwh=Decimal("50.00"),
    )


def test_evaluate_candidate_cost_success(
    dummy_scenario: PNCScenario,
    dummy_load_flow_result: LoadFlowNetworkResult,
    dummy_electrical_config: LoadFlowConfig,
    dummy_engineering_assessment: CandidateEngineeringAssessment,
    dummy_catalogue: EngineeringCostCatalogue,
    dummy_lifecycle_config: LifecycleCostConfig,
) -> None:
    assessment = evaluate_candidate_cost(
        scenario=dummy_scenario,
        load_flow_result=dummy_load_flow_result,
        electrical_config=dummy_electrical_config,
        engineering_assessment=dummy_engineering_assessment,
        catalogue=dummy_catalogue,
        config=dummy_lifecycle_config,
    )

    assert assessment.scenario_id == "s1"
    assert not assessment.failures
    assert assessment.cost is not None
    assert assessment.conductor_capex_amount == Decimal("100000.00")
    assert assessment.pole_capex_amount == Decimal("10000.00")

    # Land: 1 parcel * 1000 + 5000 m2 * 10 = 51000
    assert assessment.land_capex_amount == Decimal("51000.00")

    assert assessment.total_capex_amount == Decimal("161000.00")

    # OPEX: 1.5 MW * 8760 * 0.3 = 3942 MWh/year
    # Cost: 3942 * 50 = 197100 $/year
    # PV factor (25y, 8%) = 10.674776...
    assert assessment.cost.annual_loss_energy_mwh == Decimal("3942.00")
    assert assessment.cost.annual_loss_cost == Decimal("197100.00")
    assert assessment.cost.lifecycle_cost > assessment.cost.total_capex


def test_lifecycle_module_imports_without_orchestrator_preload() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.costing.lifecycle import evaluate_candidate_cost",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_rejects_mixed_catalogue_and_energy_currencies(
    dummy_scenario: PNCScenario,
    dummy_load_flow_result: LoadFlowNetworkResult,
    dummy_electrical_config: LoadFlowConfig,
    dummy_engineering_assessment: CandidateEngineeringAssessment,
    dummy_catalogue: EngineeringCostCatalogue,
    dummy_lifecycle_config: LifecycleCostConfig,
) -> None:
    with pytest.raises(CostConfigurationError, match="currency must match"):
        evaluate_candidate_cost(
            scenario=dummy_scenario,
            load_flow_result=dummy_load_flow_result,
            electrical_config=dummy_electrical_config,
            engineering_assessment=dummy_engineering_assessment,
            catalogue=replace(dummy_catalogue, currency="EUR"),
            config=dummy_lifecycle_config,
        )


def test_spatial_failure_does_not_publish_zero_land_cost(
    dummy_scenario: PNCScenario,
    dummy_load_flow_result: LoadFlowNetworkResult,
    dummy_electrical_config: LoadFlowConfig,
    dummy_engineering_assessment: CandidateEngineeringAssessment,
    dummy_catalogue: EngineeringCostCatalogue,
    dummy_lifecycle_config: LifecycleCostConfig,
) -> None:
    dummy_engineering_assessment.metrics = None
    dummy_engineering_assessment.engineering_metrics_available = False
    dummy_engineering_assessment.parcel_exposures = ()
    dummy_engineering_assessment.extraction_failures = (
        EngineeringMetricFailure(
            code=EngineeringMetricFailureCode.SPATIAL_ANALYSIS_FAILED,
            message="Spatial analysis failed",
        ),
    )

    assessment = evaluate_candidate_cost(
        scenario=dummy_scenario,
        load_flow_result=dummy_load_flow_result,
        electrical_config=dummy_electrical_config,
        engineering_assessment=dummy_engineering_assessment,
        catalogue=dummy_catalogue,
        config=dummy_lifecycle_config,
    )

    assert assessment.land_capex_amount is None
    assert assessment.total_capex_amount is None
    assert not assessment.capex_available
    assert any(
        failure.code == CostEvaluationFailureCode.LAND_EXPOSURE_UNAVAILABLE
        for failure in assessment.failures
    )
