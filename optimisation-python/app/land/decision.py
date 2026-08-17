"""Deterministic commercial decisions for candidate parcel exposures."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from app.costing.models import LifecycleCostConfig
from app.land.models import (
    CandidateLandAssessment,
    LandAvailabilityStatus,
    LandCommercialContext,
    LandCostBasis,
    LandOptionAssessment,
    LandPriceStatus,
    LandTransactionTerms,
    OwnerInteractionBasis,
    ParcelCommercialProfile,
    ParcelLandDecision,
)

if TYPE_CHECKING:
    from app.optimisation.engineering_metric_models import ParcelEngineeringExposure

_ZERO = Decimal(0)


def present_value_factor(rate: Decimal, years: int) -> Decimal:
    """Return the ordinary-annuity present-value factor."""
    if rate == 0:
        return Decimal(years)
    one = Decimal(1)
    return (one - (one + rate) ** -years) / rate


def assess_transaction_option(
    terms: LandTransactionTerms,
    lifecycle_config: LifecycleCostConfig | None,
) -> LandOptionAssessment:
    """Value one transaction option using the available project horizon."""
    if lifecycle_config is None:
        years = terms.term_years
    else:
        years = min(
            terms.term_years or lifecycle_config.analysis_period_years,
            lifecycle_config.analysis_period_years,
        )

    recurring_pv = _ZERO
    recurring_cost_is_known = terms.annual_cost == 0 or years is not None
    if terms.annual_cost and years is not None:
        rate = lifecycle_config.discount_rate if lifecycle_config else _ZERO
        recurring_pv = terms.annual_cost * present_value_factor(rate, years)

    feasible = terms.price_status != LandPriceStatus.UNKNOWN and recurring_cost_is_known
    return LandOptionAssessment(
        mode=terms.mode,
        price_status=terms.price_status,
        upfront_cost=terms.upfront_cost,
        annual_cost=terms.annual_cost,
        term_years=terms.term_years,
        price_date=terms.price_date,
        present_value=terms.upfront_cost + recurring_pv,
        feasible=feasible,
    )


def assess_candidate_land(
    *,
    scenario_id: str,
    parcel_exposures: tuple[ParcelEngineeringExposure, ...],
    land_context: LandCommercialContext | None,
    lifecycle_config: LifecycleCostConfig | None,
) -> CandidateLandAssessment:
    """Select the lowest-PV feasible option for every affected parcel."""
    if (
        land_context
        and lifecycle_config
        and (land_context.currency.casefold() != lifecycle_config.currency.casefold())
    ):
        raise ValueError(
            "Land commercial context currency must match lifecycle currency"
        )

    profiles = (
        {profile.parcel_id: profile for profile in land_context.parcel_profiles}
        if land_context
        else {}
    )
    unique_exposures = {exposure.parcel_id: exposure for exposure in parcel_exposures}
    decisions = tuple(
        _assess_parcel(parcel_id, profiles.get(parcel_id), lifecycle_config)
        for parcel_id in sorted(unique_exposures)
    )
    selected_options = tuple(
        option
        for decision in decisions
        if (option := _selected_option(decision)) is not None
    )

    purchase_capex = sum(
        (option.upfront_cost for option in selected_options),
        start=_ZERO,
    )
    recurring_cost_pv = sum(
        (option.present_value - option.upfront_cost for option in selected_options),
        start=_ZERO,
    )
    unavailable_ids = tuple(
        decision.parcel_id
        for decision in decisions
        if decision.availability_status == LandAvailabilityStatus.UNAVAILABLE
    )
    unknown_owner_count = sum(decision.owner_id is None for decision in decisions)
    known_owner_ids = {
        decision.owner_id for decision in decisions if decision.owner_id is not None
    }
    all_owners_confirmed = bool(decisions) and unknown_owner_count == 0
    owner_basis = (
        OwnerInteractionBasis.CONFIRMED_OWNER_IDS
        if all_owners_confirmed
        else OwnerInteractionBasis.PARCEL_PROXY
    )
    owner_count = (
        len(known_owner_ids)
        if all_owners_confirmed
        else len(known_owner_ids) + unknown_owner_count
    )

    return CandidateLandAssessment(
        scenario_id=scenario_id,
        parcel_decisions=decisions,
        parcel_count=len(decisions),
        owner_interaction_count=owner_count,
        owner_interaction_basis=owner_basis,
        unknown_owner_count=unknown_owner_count,
        unavailable_parcel_ids=unavailable_ids,
        land_purchase_capex=purchase_capex,
        land_recurring_cost_pv=recurring_cost_pv,
        land_access_present_value=purchase_capex + recurring_cost_pv,
        land_cost_basis=_aggregate_cost_basis(selected_options),
        is_feasible=not unavailable_ids,
    )


def _assess_parcel(
    parcel_id: str,
    profile: ParcelCommercialProfile | None,
    lifecycle_config: LifecycleCostConfig | None,
) -> ParcelLandDecision:
    if profile is None:
        return ParcelLandDecision(
            parcel_id=parcel_id,
            owner_id=None,
            availability_status=LandAvailabilityStatus.UNKNOWN,
            feasible_options=(),
            selected_mode=None,
            selected_present_value=None,
            cost_basis=LandPriceStatus.UNKNOWN,
            price_date=None,
        )

    options = tuple(
        assess_transaction_option(terms, lifecycle_config)
        for terms in profile.transaction_options
    )
    selectable = (
        ()
        if profile.availability_status == LandAvailabilityStatus.UNAVAILABLE
        else tuple(option for option in options if option.feasible)
    )
    selected = min(
        selectable,
        key=lambda option: (option.present_value, option.mode.value),
        default=None,
    )
    return ParcelLandDecision(
        parcel_id=parcel_id,
        owner_id=profile.owner_id,
        availability_status=profile.availability_status,
        feasible_options=options,
        selected_mode=selected.mode if selected else None,
        selected_present_value=selected.present_value if selected else None,
        cost_basis=selected.price_status if selected else LandPriceStatus.UNKNOWN,
        price_date=selected.price_date if selected else None,
    )


def _aggregate_cost_basis(
    selected_options: tuple[LandOptionAssessment, ...],
) -> LandCostBasis:
    statuses = {option.price_status for option in selected_options}
    if statuses == {LandPriceStatus.QUOTED}:
        return LandCostBasis.QUOTED
    if statuses == {LandPriceStatus.ESTIMATED}:
        return LandCostBasis.ESTIMATED
    if statuses:
        return LandCostBasis.MIXED
    return LandCostBasis.UNKNOWN


def _selected_option(
    decision: ParcelLandDecision,
) -> LandOptionAssessment | None:
    return next(
        (
            option
            for option in decision.feasible_options
            if option.mode == decision.selected_mode
            and option.present_value == decision.selected_present_value
        ),
        None,
    )
