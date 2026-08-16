"""Lifecycle cost evaluation engine."""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import TYPE_CHECKING

from app.costing.failures import (
    CostConfigurationError,
    CostEvaluationFailure,
    CostEvaluationFailureCode,
)
from app.costing.models import (
    CandidateCostAssessment,
    CandidateLifecycleCost,
    CostLineItem,
    EngineeringCostCatalogue,
    LandPricingBasis,
    LifecycleCostConfig,
    PoleCostItem,
)
from app.electrical.load_flow.config import LoadFlowConfig
from app.electrical.load_flow.models import LoadFlowNetworkResult

if TYPE_CHECKING:
    from app.optimisation.engineering_metric_models import (
        CandidateEngineeringAssessment,
    )
    from app.optimisation.scenario_models import PNCScenario


def _quantize_money(value: Decimal) -> Decimal:
    """Quantize to two decimal places for published monetary totals."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def evaluate_candidate_cost(
    scenario: PNCScenario,
    load_flow_result: LoadFlowNetworkResult,
    electrical_config: LoadFlowConfig,
    engineering_assessment: CandidateEngineeringAssessment,
    catalogue: EngineeringCostCatalogue,
    config: LifecycleCostConfig,
) -> CandidateCostAssessment:
    if catalogue.currency.upper() != config.currency.upper():
        raise CostConfigurationError(
            "Cost catalogue currency must match lifecycle configuration currency"
        )

    failures: list[CostEvaluationFailure] = []
    line_items: list[CostLineItem] = []

    conductor_capex_amount: Decimal | None = None
    pole_capex_amount: Decimal | None = None
    land_capex_amount: Decimal | None = None
    total_capex_amount: Decimal | None = None
    present_value_opex_amount: Decimal | None = None

    # 1. Conductor CAPEX
    conductor_costs = {item.cable_type_id: item for item in catalogue.conductor_items}
    conductor_total = Decimal(0)
    conductor_valid = True

    for feeder in scenario.network.feeders:
        for segment in feeder.segments:
            cable_type_id = electrical_config.segment_cable_type_ids.get(
                segment.segment_id, electrical_config.default_cable_type_id
            )
            conductor_cost_item = conductor_costs.get(cable_type_id)
            if conductor_cost_item is None:
                failures.append(
                    CostEvaluationFailure(
                        code=CostEvaluationFailureCode.CABLE_COST_NOT_FOUND,
                        component="conductor_capex",
                        message=(
                            f"Cable type {cable_type_id} not found in cost catalogue"
                        ),
                        segment_id=segment.segment_id,
                    )
                )
                conductor_valid = False
                continue

            if not conductor_valid:
                continue

            # Find matching LoadFlowCableType
            cable_config = next(
                (
                    ct
                    for ct in electrical_config.cable_types
                    if ct.cable_type_id == cable_type_id
                ),
                None,
            )
            parallel_count = cable_config.parallel_count if cable_config else 1
            length_km = Decimal(str(segment.route_length_m)) / Decimal("1000")
            rate = conductor_cost_item.installed_cost_per_km_per_parallel_circuit
            count_dec = Decimal(parallel_count)
            amount = length_km * count_dec * rate

            line_items.append(
                CostLineItem(
                    category="conductor",
                    item_id=segment.segment_id,
                    quantity=length_km * count_dec,
                    unit="circuit-km",
                    unit_rate=rate,
                    amount=amount,
                )
            )
            conductor_total += amount

    if conductor_valid:
        conductor_capex_amount = conductor_total

    # 2. Pole CAPEX
    if engineering_assessment.pole_result is None:
        failures.append(
            CostEvaluationFailure(
                code=CostEvaluationFailureCode.POLE_RESULT_UNAVAILABLE,
                component="pole_capex",
                message="Deduplicated pole result is not available",
            )
        )
    elif (
        engineering_assessment.metrics is not None
        and engineering_assessment.metrics.physical_pole_count
        != len(engineering_assessment.pole_result.physical_poles)
    ):
        failures.append(
            CostEvaluationFailure(
                code=CostEvaluationFailureCode.POLE_RESULT_UNAVAILABLE,
                component="pole_capex",
                message="Pole count mismatch indicates invalid physical poles",
            )
        )
    else:
        pole_costs: dict[str, PoleCostItem] = {
            item.pole_type: item for item in catalogue.pole_items
        }
        pole_total = Decimal(0)
        pole_counts: dict[str, int] = {}
        for p in engineering_assessment.pole_result.physical_poles:
            pole_counts[p.pole_type] = pole_counts.get(p.pole_type, 0) + 1

        for ptype, count in pole_counts.items():
            pole_cost_item = pole_costs.get(ptype)
            if pole_cost_item is None:
                failures.append(
                    CostEvaluationFailure(
                        code=CostEvaluationFailureCode.POLE_COST_NOT_FOUND,
                        component="pole_capex",
                        message=f"Pole type {ptype} not found in cost catalogue",
                    )
                )
            else:
                count_dec = Decimal(count)
                rate = pole_cost_item.installed_cost_each
                amount = count_dec * rate
                line_items.append(
                    CostLineItem(
                        category="pole",
                        item_id=ptype,
                        quantity=count_dec,
                        unit="each",
                        unit_rate=rate,
                        amount=amount,
                    )
                )
                pole_total += amount

        if not any(f.component == "pole_capex" for f in failures):
            pole_capex_amount = pole_total

    # 3. Land CAPEX
    spatial_analysis_failed = any(
        failure.code == "SPATIAL_ANALYSIS_FAILED"
        for failure in engineering_assessment.extraction_failures
    )
    if spatial_analysis_failed:
        failures.append(
            CostEvaluationFailure(
                code=CostEvaluationFailureCode.LAND_EXPOSURE_UNAVAILABLE,
                component="land_capex",
                message=(
                    "Parcel exposure is unavailable because spatial analysis failed"
                ),
            )
        )
    else:
        land_total = Decimal(0)
        policy = catalogue.land_policy
        unique_parcels = len(engineering_assessment.parcel_exposures)
        fixed_rate = policy.fixed_cost_per_affected_parcel
        fixed_amount = Decimal(unique_parcels) * fixed_rate
        if fixed_amount > 0:
            line_items.append(
                CostLineItem(
                    category="land_fixed",
                    item_id="unique_parcels",
                    quantity=Decimal(unique_parcels),
                    unit="each",
                    unit_rate=fixed_rate,
                    amount=fixed_amount,
                )
            )
        land_total += fixed_amount

        var_rate = policy.variable_rate
        if policy.variable_basis == LandPricingBasis.ROUTE_OVERLAP_LENGTH_M:
            qty = sum(
                (
                    Decimal(str(exposure.route_overlap_length_m))
                    for exposure in engineering_assessment.parcel_exposures
                ),
                start=Decimal(0),
            )
            var_amount = qty * var_rate
            if var_amount > 0:
                line_items.append(
                    CostLineItem(
                        category="land_variable",
                        item_id="route_overlap_length_m",
                        quantity=qty,
                        unit="m",
                        unit_rate=var_rate,
                        amount=var_amount,
                    )
                )
            land_total += var_amount
        elif policy.variable_basis == LandPricingBasis.ROW_INTERSECTION_AREA_M2:
            qty = sum(
                (
                    Decimal(str(exposure.row_intersection_area_m2))
                    for exposure in engineering_assessment.parcel_exposures
                ),
                start=Decimal(0),
            )
            var_amount = qty * var_rate
            if var_amount > 0:
                line_items.append(
                    CostLineItem(
                        category="land_variable",
                        item_id="row_intersection_area_m2",
                        quantity=qty,
                        unit="m2",
                        unit_rate=var_rate,
                        amount=var_amount,
                    )
                )
            land_total += var_amount

        land_capex_amount = land_total

    if (
        conductor_capex_amount is not None
        and pole_capex_amount is not None
        and land_capex_amount is not None
    ):
        total_capex_amount = (
            conductor_capex_amount + pole_capex_amount + land_capex_amount
        )

    # 4. OPEX Losses
    pv_factor = Decimal(0)
    annual_loss_energy_mwh = Decimal(0)
    annual_loss_cost = Decimal(0)

    if not load_flow_result.converged:
        failures.append(
            CostEvaluationFailure(
                code=CostEvaluationFailureCode.LOAD_FLOW_NOT_CONVERGED,
                component="loss_opex",
                message="Load flow did not converge",
            )
        )
    elif load_flow_result.total_active_loss_mw is None:
        failures.append(
            CostEvaluationFailure(
                code=CostEvaluationFailureCode.ACTIVE_LOSS_MISSING,
                component="loss_opex",
                message="Active loss is missing from converged load flow",
            )
        )
    else:
        loss_mw = Decimal(str(load_flow_result.total_active_loss_mw))
        if not loss_mw.is_finite() or loss_mw < 0:
            failures.append(
                CostEvaluationFailure(
                    code=CostEvaluationFailureCode.ACTIVE_LOSS_INVALID,
                    component="loss_opex",
                    message="Active loss is not finite or is negative",
                )
            )
        else:
            hours = Decimal(config.annual_operating_hours)
            factor = config.loss_load_factor
            annual_loss_energy_mwh = loss_mw * hours * factor
            annual_loss_cost = annual_loss_energy_mwh * config.energy_price_per_mwh

            r = config.discount_rate
            n = config.analysis_period_years
            if r > 0:
                # PV factor = (1 - (1 + r)^(-n)) / r
                one = Decimal(1)
                pv_factor = (one - (one + r) ** (-n)) / r
            else:
                pv_factor = Decimal(n)

            present_value_opex_amount = annual_loss_cost * pv_factor

            if present_value_opex_amount > 0:
                line_items.append(
                    CostLineItem(
                        category="opex",
                        item_id="electrical_losses_pv",
                        quantity=annual_loss_energy_mwh,
                        unit="MWh/year",
                        unit_rate=config.energy_price_per_mwh,
                        amount=present_value_opex_amount,
                    )
                )

    cost_obj: CandidateLifecycleCost | None = None
    if (
        conductor_capex_amount is not None
        and pole_capex_amount is not None
        and land_capex_amount is not None
        and total_capex_amount is not None
        and present_value_opex_amount is not None
    ):
        cost_obj = CandidateLifecycleCost(
            scenario_id=scenario.scenario_id,
            conductor_capex=_quantize_money(conductor_capex_amount),
            pole_capex=_quantize_money(pole_capex_amount),
            land_capex=_quantize_money(land_capex_amount),
            total_capex=_quantize_money(total_capex_amount),
            annual_loss_energy_mwh=annual_loss_energy_mwh,
            annual_loss_cost=_quantize_money(annual_loss_cost),
            present_value_factor=pv_factor,
            present_value_opex=_quantize_money(present_value_opex_amount),
            lifecycle_cost=_quantize_money(
                total_capex_amount + present_value_opex_amount
            ),
            line_items=tuple(line_items),
            currency=config.currency,
            catalogue_id=catalogue.catalogue_id,
            catalogue_version=catalogue.version,
            catalogue_price_basis_date=catalogue.price_basis_date,
            energy_price_basis_date=config.energy_price_basis_date,
            cost_model_version="1.0",
            analysis_period_years=config.analysis_period_years,
            discount_rate=config.discount_rate,
            annual_operating_hours=config.annual_operating_hours,
            loss_load_factor=config.loss_load_factor,
            energy_price_per_mwh=config.energy_price_per_mwh,
        )

    return CandidateCostAssessment(
        scenario_id=scenario.scenario_id,
        cost=cost_obj,
        failures=tuple(failures),
        conductor_capex_amount=conductor_capex_amount,
        pole_capex_amount=pole_capex_amount,
        land_capex_amount=land_capex_amount,
        total_capex_amount=total_capex_amount,
        present_value_opex_amount=present_value_opex_amount,
        annual_loss_energy_mwh=(
            annual_loss_energy_mwh if present_value_opex_amount is not None else None
        ),
        annual_loss_cost_amount=(
            annual_loss_cost if present_value_opex_amount is not None else None
        ),
        present_value_factor=(
            pv_factor if present_value_opex_amount is not None else None
        ),
        line_items=tuple(line_items),
        currency=config.currency,
        catalogue_id=catalogue.catalogue_id,
        catalogue_version=catalogue.version,
        catalogue_price_basis_date=catalogue.price_basis_date,
        energy_price_basis_date=config.energy_price_basis_date,
        cost_model_version="1.0",
        analysis_period_years=config.analysis_period_years,
        discount_rate=config.discount_rate,
        annual_operating_hours=config.annual_operating_hours,
        loss_load_factor=config.loss_load_factor,
        energy_price_per_mwh=config.energy_price_per_mwh,
    )
