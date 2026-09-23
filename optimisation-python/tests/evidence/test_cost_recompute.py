"""WP3-8: the independent Minimum Cost recomputation, checked against real output.

Exit evidence: BOM x catalogue plus valued losses match the reported lifecycle cost
within tolerance on synthetic fixtures.

The fixtures here drive the real costing engine rather than hand-building a
``CandidateLifecycleCost``, because a checker validated only against numbers written
by the same person who wrote the checker proves that the two agree and nothing else.
What has to be true is that it reconciles what the engine actually produces, and that
it notices when that stops being right - so most of this file corrupts genuine engine
output one field at a time and asserts the corruption is reported.
"""

from __future__ import annotations

import datetime
from dataclasses import replace
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.algorithms.pole_placement import CollectorPoleResult
from app.costing.lifecycle import evaluate_candidate_cost
from app.costing.models import (
    CandidateLifecycleCost,
    ConductorCostItem,
    CostLineItem,
    EngineeringCostCatalogue,
    LandCostPolicy,
    LandPricingBasis,
    LifecycleCostConfig,
    PoleCostItem,
)
from app.electrical.load_flow.config import LoadFlowCableType, LoadFlowConfig
from app.electrical.load_flow.models import LoadFlowNetworkResult
from app.evidence.cost_recompute import (
    DISCOUNTED_CATEGORY,
    annuity_factor,
    recompute_all,
    recompute_candidate_cost,
)
from app.land.decision import present_value_factor
from app.land.models import (
    CandidateLandAssessment,
    LandAvailabilityStatus,
    LandCostBasis,
    LandPriceStatus,
    OwnerInteractionBasis,
    ParcelLandDecision,
)
from app.optimisation.engineering_metric_models import (
    CandidateEngineeringAssessment,
    CandidateEngineeringMetrics,
    ParcelEngineeringExposure,
)
from app.optimisation.scenario_models import PNCScenario
from app.pnc.models import PNCFeeder, PNCSegment, ProjectPNCNetwork

# --- A project the engine will cost end to end --------------------------------------


@pytest.fixture
def scenario() -> PNCScenario:
    segment = MagicMock(spec=PNCSegment)
    segment.route_length_m = 1000.0
    segment.segment_id = "seg1"

    feeder = MagicMock(spec=PNCFeeder)
    feeder.segments = (segment,)

    network = MagicMock(spec=ProjectPNCNetwork)
    network.total_length_m = 1000.0
    network.feeders = (feeder,)

    built = MagicMock(spec=PNCScenario)
    built.scenario_id = "SCN-COST-1"
    built.network = network
    return built


@pytest.fixture
def electrical_config() -> LoadFlowConfig:
    return LoadFlowConfig(
        nominal_voltage_kv=33.0,
        slack_voltage_pu=1.0,
        min_voltage_pu=0.95,
        max_voltage_pu=1.05,
        system_base_mva=100.0,
        cable_types=(
            LoadFlowCableType(
                cable_type_id="cable1",
                resistance_ohm_per_km=0.1,
                reactance_ohm_per_km=0.1,
                capacitance_nf_per_km=0.1,
                max_current_a=500.0,
                parallel_count=1,
                derating_factor=1.0,
            ),
        ),
        default_cable_type_id="cable1",
        segment_cable_type_ids={"seg1": "cable1"},
    )


@pytest.fixture
def load_flow_result() -> LoadFlowNetworkResult:
    result = MagicMock(spec=LoadFlowNetworkResult)
    result.is_valid = True
    result.converged = True
    result.total_active_loss_mw = 1.5
    result.maximum_loading_percent = 50.0
    result.minimum_voltage_pu = 0.98
    result.maximum_voltage_pu = 1.0
    result.feeders = ()
    return result


@pytest.fixture
def engineering_assessment() -> CandidateEngineeringAssessment:
    metrics = MagicMock(spec=CandidateEngineeringMetrics)
    metrics.total_route_length_m = 1000.0
    metrics.total_traversal_cost = 100.0
    metrics.affected_parcel_count = 1
    metrics.road_crossing_count = 0
    metrics.soft_constraint_overlap_length_m = 0.0
    metrics.environmental_overlap_m2 = 0.0
    metrics.physical_pole_count = 3

    pole_result = MagicMock(spec=CollectorPoleResult)
    pole_result.physical_poles = (
        MagicMock(pole_type="terminal"),
        MagicMock(pole_type="terminal"),
        MagicMock(pole_type="angle"),
    )

    assessment = MagicMock(spec=CandidateEngineeringAssessment)
    assessment.scenario_id = "SCN-COST-1"
    assessment.metrics = metrics
    assessment.eligible = True
    assessment.engineering_metrics_available = True
    assessment.hard_violation_ids = ()
    assessment.extraction_failures = ()
    assessment.pole_result = pole_result
    assessment.parcel_exposures = (
        ParcelEngineeringExposure(
            parcel_id="parcel1",
            route_overlap_length_m=500.0,
            row_intersection_area_m2=5000.0,
        ),
    )
    return assessment


@pytest.fixture
def catalogue() -> EngineeringCostCatalogue:
    return EngineeringCostCatalogue(
        catalogue_id="cat1",
        version="1.0",
        currency="USD",
        price_basis_date=datetime.date(2025, 1, 1),
        conductor_items=(
            ConductorCostItem(
                cable_type_id="cable1",
                installed_cost_per_km_per_parallel_circuit=Decimal("100000.00"),
            ),
        ),
        pole_items=(
            PoleCostItem(pole_type="terminal", installed_cost_each=Decimal("5000.00")),
            PoleCostItem(pole_type="angle", installed_cost_each=Decimal("6000.00")),
            PoleCostItem(
                pole_type="intermediate", installed_cost_each=Decimal("3000.00")
            ),
            PoleCostItem(pole_type="junction", installed_cost_each=Decimal("7000.00")),
        ),
        land_policy=LandCostPolicy(
            fixed_cost_per_affected_parcel=Decimal("1000.00"),
            variable_basis=LandPricingBasis.ROW_INTERSECTION_AREA_M2,
            variable_rate=Decimal("10.00"),
        ),
    )


@pytest.fixture
def lifecycle_config() -> LifecycleCostConfig:
    return LifecycleCostConfig(
        currency="USD",
        energy_price_basis_date=datetime.date(2025, 1, 1),
        analysis_period_years=25,
        discount_rate=Decimal("0.08"),
        annual_operating_hours=8760,
        loss_load_factor=Decimal("0.3"),
        energy_price_per_mwh=Decimal("50.00"),
    )


def _land_assessment(
    *, purchase: str = "0.00", recurring: str = "0.00"
) -> CandidateLandAssessment:
    purchase_decimal = Decimal(purchase)
    recurring_decimal = Decimal(recurring)
    return CandidateLandAssessment(
        scenario_id="SCN-COST-1",
        parcel_decisions=(
            ParcelLandDecision(
                parcel_id="parcel1",
                owner_id=None,
                availability_status=LandAvailabilityStatus.UNKNOWN,
                feasible_options=(),
                selected_mode=None,
                selected_present_value=None,
                cost_basis=LandPriceStatus.UNKNOWN,
                price_date=None,
            ),
        ),
        parcel_count=1,
        owner_interaction_count=1,
        owner_interaction_basis=OwnerInteractionBasis.PARCEL_PROXY,
        unknown_owner_count=1,
        unavailable_parcel_ids=(),
        land_purchase_capex=purchase_decimal,
        land_recurring_cost_pv=recurring_decimal,
        land_access_present_value=purchase_decimal + recurring_decimal,
        land_cost_basis=LandCostBasis.UNKNOWN,
        is_feasible=True,
    )


@pytest.fixture
def engine_cost(
    scenario: PNCScenario,
    load_flow_result: LoadFlowNetworkResult,
    electrical_config: LoadFlowConfig,
    engineering_assessment: CandidateEngineeringAssessment,
    catalogue: EngineeringCostCatalogue,
    lifecycle_config: LifecycleCostConfig,
) -> CandidateLifecycleCost:
    """What the costing engine actually produces for the project above."""
    assessment = evaluate_candidate_cost(
        scenario=scenario,
        load_flow_result=load_flow_result,
        electrical_config=electrical_config,
        engineering_assessment=engineering_assessment,
        catalogue=catalogue,
        config=lifecycle_config,
        land_assessment=_land_assessment(),
    )
    assert assessment.cost is not None
    return assessment.cost


# --- The engine's own output reconciles ---------------------------------------------


def test_the_engines_lifecycle_cost_reconciles_from_its_own_bill_of_materials(
    engine_cost: CandidateLifecycleCost,
) -> None:
    result = recompute_candidate_cost(engine_cost)

    assert result.reconciles, result.describe()
    assert result.scenario_id == "SCN-COST-1"
    assert result.currency == "USD"
    assert abs(result.lifecycle_cost - engine_cost.lifecycle_cost) <= Decimal("0.05")


def test_it_reconciles_when_land_carries_both_an_upfront_and_a_recurring_cost(
    scenario: PNCScenario,
    load_flow_result: LoadFlowNetworkResult,
    electrical_config: LoadFlowConfig,
    engineering_assessment: CandidateEngineeringAssessment,
    catalogue: EngineeringCostCatalogue,
    lifecycle_config: LifecycleCostConfig,
) -> None:
    # The case the totals are easiest to get wrong in: recurring land cost sits
    # outside total_capex and has to be added back at the end.
    assessment = evaluate_candidate_cost(
        scenario=scenario,
        load_flow_result=load_flow_result,
        electrical_config=electrical_config,
        engineering_assessment=engineering_assessment,
        catalogue=catalogue,
        config=lifecycle_config,
        land_assessment=_land_assessment(purchase="40000.00", recurring="12000.00"),
    )
    assert assessment.cost is not None

    assert assessment.cost.land_recurring_cost_pv == Decimal("12000.00")
    assert recompute_candidate_cost(assessment.cost).reconciles


def test_the_catalogue_cross_check_accepts_the_rates_that_priced_the_run(
    engine_cost: CandidateLifecycleCost, catalogue: EngineeringCostCatalogue
) -> None:
    result = recompute_candidate_cost(engine_cost, catalogue=catalogue)

    assert result.unpublished_rates == ()
    assert result.reconciles, result.describe()


def test_a_cohort_is_recomputed_in_the_order_given(
    engine_cost: CandidateLifecycleCost,
) -> None:
    other = replace(engine_cost, scenario_id="SCN-COST-2")

    results = recompute_all([engine_cost, other])

    assert [result.scenario_id for result in results] == [
        "SCN-COST-1",
        "SCN-COST-2",
    ]
    assert all(result.reconciles for result in results)


# --- The two traps the module exists to document ------------------------------------


def test_the_loss_line_is_the_one_whose_amount_is_not_quantity_times_rate(
    engine_cost: CandidateLifecycleCost,
) -> None:
    (loss_line,) = [
        item for item in engine_cost.line_items if item.category == DISCOUNTED_CATEGORY
    ]

    # Its amount is discounted over the analysis period, so the obvious bill-of-
    # materials identity does not hold for it - and a checker that applied that
    # identity everywhere would report a defect that is not there.
    assert loss_line.amount != loss_line.quantity * loss_line.unit_rate
    assert loss_line.amount == (
        loss_line.quantity * loss_line.unit_rate * engine_cost.present_value_factor
    )
    assert recompute_candidate_cost(engine_cost).reconciles


def test_dropping_the_recurring_land_term_from_the_total_is_caught(
    scenario: PNCScenario,
    load_flow_result: LoadFlowNetworkResult,
    electrical_config: LoadFlowConfig,
    engineering_assessment: CandidateEngineeringAssessment,
    catalogue: EngineeringCostCatalogue,
    lifecycle_config: LifecycleCostConfig,
) -> None:
    # The mistake this module is most likely to be written with: lifecycle cost is
    # NOT total_capex + present_value_opex. A reimplementation that stops there is
    # short by the whole recurring land bill and balances perfectly against itself.
    assessment = evaluate_candidate_cost(
        scenario=scenario,
        load_flow_result=load_flow_result,
        electrical_config=electrical_config,
        engineering_assessment=engineering_assessment,
        catalogue=catalogue,
        config=lifecycle_config,
        land_assessment=_land_assessment(purchase="40000.00", recurring="12000.00"),
    )
    assert assessment.cost is not None

    understated = replace(
        assessment.cost,
        lifecycle_cost=assessment.cost.total_capex + assessment.cost.present_value_opex,
    )

    result = recompute_candidate_cost(understated)

    assert not result.reconciles
    (discrepancy,) = result.discrepancies
    assert discrepancy.component == "lifecycle_cost"
    # Short by the recurring land bill, to within the rounding the engine publishes:
    # the recomputed present value of losses is unrounded, its published figure is not.
    assert abs(discrepancy.difference - Decimal("12000.00")) <= Decimal("0.05")


# --- Each identity bites -------------------------------------------------------------


@pytest.mark.parametrize(
    ("field", "component"),
    [
        ("conductor_capex", "conductor_capex"),
        ("pole_capex", "pole_capex"),
        ("land_purchase_capex", "land_purchase_capex"),
        ("total_capex", "total_capex"),
        ("annual_loss_cost", "annual_loss_cost"),
        ("present_value_opex", "present_value_opex"),
        ("lifecycle_cost", "lifecycle_cost"),
    ],
)
def test_an_inflated_total_is_reported_against_its_own_name(
    engine_cost: CandidateLifecycleCost, field: str, component: str
) -> None:
    inflated = replace(
        engine_cost, **{field: getattr(engine_cost, field) + Decimal("1000.00")}
    )

    result = recompute_candidate_cost(inflated)

    assert not result.reconciles
    assert component in {item.component for item in result.discrepancies}


def test_a_corrupted_line_item_is_reported_by_category_and_id(
    engine_cost: CandidateLifecycleCost,
) -> None:
    lines = list(engine_cost.line_items)
    conductor_index = next(
        index for index, item in enumerate(lines) if item.category == "conductor"
    )
    original = lines[conductor_index]
    lines[conductor_index] = replace(original, amount=original.amount * 2)

    result = recompute_candidate_cost(replace(engine_cost, line_items=tuple(lines)))

    assert not result.reconciles
    assert f"line_item[conductor/{original.item_id}]" in {
        item.component for item in result.discrepancies
    }


def test_a_wrong_annuity_factor_is_caught_even_though_it_is_not_money(
    engine_cost: CandidateLifecycleCost,
) -> None:
    # Reported against a 20-year horizon while the config says 25: the kind of
    # mismatch that leaves every money figure self-consistent and the answer wrong.
    result = recompute_candidate_cost(
        replace(
            engine_cost,
            present_value_factor=present_value_factor(Decimal("0.08"), 20),
        )
    )

    assert "present_value_factor" in {item.component for item in result.discrepancies}


def test_a_rate_the_catalogue_does_not_publish_is_reported(
    engine_cost: CandidateLifecycleCost, catalogue: EngineeringCostCatalogue
) -> None:
    lines = list(engine_cost.line_items)
    pole_index = next(
        index for index, item in enumerate(lines) if item.category == "pole"
    )
    original = lines[pole_index]
    # Same arithmetic, a rate nobody agreed: quantity x rate still equals amount, so
    # only the catalogue check can see it.
    lines[pole_index] = CostLineItem(
        category=original.category,
        item_id=original.item_id,
        quantity=original.quantity,
        unit=original.unit,
        unit_rate=Decimal("5500.00"),
        amount=original.quantity * Decimal("5500.00"),
    )

    result = recompute_candidate_cost(
        replace(engine_cost, line_items=tuple(lines)), catalogue=catalogue
    )

    assert not result.reconciles
    (unpublished,) = result.unpublished_rates
    assert unpublished.unit_rate == Decimal("5500.00")
    assert unpublished.component.startswith("pole/")


def test_without_a_catalogue_an_unagreed_rate_passes_unnoticed(
    engine_cost: CandidateLifecycleCost,
) -> None:
    # Stated so the limit of the arithmetic-only check is on the record: it proves
    # the numbers are consistent, not that they came from the agreed rates.
    lines = list(engine_cost.line_items)
    pole_index = next(
        index for index, item in enumerate(lines) if item.category == "pole"
    )
    original = lines[pole_index]
    lines[pole_index] = CostLineItem(
        category=original.category,
        item_id=original.item_id,
        quantity=original.quantity,
        unit=original.unit,
        unit_rate=Decimal("5500.00"),
        amount=original.quantity * Decimal("5500.00"),
    )
    corrupted = replace(engine_cost, line_items=tuple(lines))

    assert recompute_candidate_cost(corrupted).unpublished_rates == ()
    # The totals no longer add up, which is what does catch it here.
    assert not recompute_candidate_cost(corrupted).reconciles


# --- Tolerance -----------------------------------------------------------------------


def test_a_difference_within_tolerance_is_not_a_discrepancy(
    engine_cost: CandidateLifecycleCost,
) -> None:
    nudged = replace(engine_cost, total_capex=engine_cost.total_capex + Decimal("0.02"))

    assert recompute_candidate_cost(nudged).reconciles


def test_the_tolerance_can_be_tightened_by_the_caller(
    engine_cost: CandidateLifecycleCost,
) -> None:
    nudged = replace(engine_cost, total_capex=engine_cost.total_capex + Decimal("0.02"))

    result = recompute_candidate_cost(nudged, money_tolerance=Decimal("0.001"))

    assert not result.reconciles


# --- The annuity factor, computed the other way --------------------------------------


@pytest.mark.parametrize("rate", ["0.05", "0.08", "0.12"])
@pytest.mark.parametrize("years", [1, 5, 25, 40])
def test_the_summed_annuity_factor_agrees_with_the_closed_form(
    rate: str, years: int
) -> None:
    summed = annuity_factor(Decimal(rate), years)
    closed = present_value_factor(Decimal(rate), years)

    assert abs(summed - closed) < Decimal("1e-12")


def test_a_zero_discount_rate_values_each_year_at_par() -> None:
    assert annuity_factor(Decimal(0), 25) == Decimal(25)


@pytest.mark.parametrize(
    ("rate", "years"), [(Decimal("0.08"), -1), (Decimal("-0.01"), 25)]
)
def test_an_impossible_horizon_or_rate_is_refused(rate: Decimal, years: int) -> None:
    with pytest.raises(ValueError):
        annuity_factor(rate, years)


# --- What a reader is told ------------------------------------------------------------


def test_a_reconciled_candidate_describes_itself_with_its_total(
    engine_cost: CandidateLifecycleCost,
) -> None:
    description = recompute_candidate_cost(engine_cost).describe()

    assert "reconciles" in description
    assert "USD" in description


def test_a_failing_candidate_names_the_component_and_both_numbers(
    engine_cost: CandidateLifecycleCost,
) -> None:
    inflated = replace(
        engine_cost, pole_capex=engine_cost.pole_capex + Decimal("1234.00")
    )

    description = recompute_candidate_cost(inflated).describe()

    assert "pole_capex" in description
    assert str(engine_cost.pole_capex + Decimal("1234.00")) in description
