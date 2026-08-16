"""Land decision intelligence module.

Assesses the commercial impact of a candidate's routed corridor and its
optimized pole network: which parcels are crossed, which owners require
interaction, which parcels are unavailable, and the implied land costs.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import TYPE_CHECKING

from shapely.geometry import Point

from app.algorithms.pole_placement import CollectorPoleResult
from app.costing.models import LifecycleCostConfig
from app.gis.constraints import (
    ConstraintLayer,
    ConstraintType,
    effective_constraint_geometry,
)
from app.land.models import (
    CandidateLandAssessment,
    LandAvailabilityStatus,
    LandCommercialContext,
    LandCostBasis,
    LandOptionAssessment,
    LandPriceStatus,
    LandTransactionMode,
    LandTransactionTerms,
    OwnerInteractionBasis,
    ParcelLandDecision,
)

if TYPE_CHECKING:
    from app.optimisation.engineering_metrics import SpatialExtractionResult


def _parcel_layers_for_point(
    point: Point,
    constraint_layers: tuple[ConstraintLayer, ...],
) -> tuple[str, ...]:
    """Return every distinct PARCEL layer containing ``point``."""
    parcel_ids: set[str] = set()
    for layer in constraint_layers:
        if layer.layer_type != ConstraintType.PARCEL:
            continue
        try:
            geometry = effective_constraint_geometry(layer)
        except ValueError:
            continue
        if geometry.covers(point):
            parcel_ids.add(layer.layer_id)
    return tuple(sorted(parcel_ids))


def _annuity_factor(years: int, rate: Decimal) -> Decimal:
    """Present-value annuity factor for ``years`` periods at ``rate``."""
    if rate == 0:
        return Decimal(years)
    return (Decimal(1) - (Decimal(1) + rate) ** -years) / rate


def _option_present_value(
    terms: LandTransactionTerms,
    lifecycle_config: LifecycleCostConfig | None,
) -> Decimal:
    """Present value of one land transaction option."""
    if lifecycle_config is not None:
        rate = lifecycle_config.discount_rate
        default_years = lifecycle_config.analysis_period_years
    else:
        rate = Decimal(0)
        default_years = 0
    years = terms.term_years if terms.term_years is not None else default_years
    annual_pv = Decimal(0)
    if years > 0:
        annual_pv = terms.annual_cost * _annuity_factor(years, rate)
    return terms.upfront_cost + annual_pv


def derive_owner_interactions(
    parcel_ids: Iterable[str],
    land_context: LandCommercialContext | None,
) -> frozenset[str]:
    """Owner ids (if any) for the given parcels from the commercial context."""
    if land_context is None:
        return frozenset()
    profiles = {p.parcel_id: p for p in land_context.parcel_profiles}
    owners: set[str] = set()
    for parcel_id in parcel_ids:
        profile = profiles.get(parcel_id)
        if profile is not None and profile.owner_id is not None:
            owners.add(profile.owner_id)
    return frozenset(owners)


def assess_candidate_land(
    scenario_id: str,
    poles: CollectorPoleResult | None = None,
    route_context: SpatialExtractionResult | None = None,
    land_context: LandCommercialContext | None = None,
    lifecycle_config: LifecycleCostConfig | None = None,
    constraint_layers: tuple[ConstraintLayer, ...] = (),
) -> CandidateLandAssessment:
    """Assess land commercial feasibility and costs for a candidate.

    Route owner interactions come from the parcels crossed by the routed
    corridor (``route_context.parcel_exposures``); pole owner interactions
    come from the parcels occupied by physical poles. Both are combined into
    the total owner interaction set so a pole moved out of a parcel already
    crossed by the route is not reported as a newly-negotiated owner.
    """
    profiles = (
        {p.parcel_id: p for p in land_context.parcel_profiles}
        if land_context is not None
        else {}
    )

    route_parcel_ids = {
        exposure.parcel_id
        for exposure in (
            route_context.parcel_exposures if route_context is not None else ()
        )
    }

    pole_parcel_ids: set[str] = set()
    if poles is not None:
        for physical in poles.physical_poles:
            pole_parcel_ids.update(
                _parcel_layers_for_point(physical.geometry, constraint_layers)
            )

    affected_parcel_ids = sorted(route_parcel_ids | pole_parcel_ids)

    parcel_decisions: list[ParcelLandDecision] = []
    owner_ids: set[str] = set()
    unknown_owner_count = 0
    unavailable_ids: list[str] = []
    purchase_capex = Decimal(0)
    recurring_pv = Decimal(0)
    selected_statuses: list[LandPriceStatus] = []

    for parcel_id in affected_parcel_ids:
        profile = profiles.get(parcel_id)
        if profile is None:
            unknown_owner_count += 1
            parcel_decisions.append(
                ParcelLandDecision(
                    parcel_id=parcel_id,
                    owner_id=None,
                    availability_status=LandAvailabilityStatus.UNKNOWN,
                    feasible_options=(),
                    selected_mode=None,
                    selected_present_value=None,
                    cost_basis=LandPriceStatus.UNKNOWN,
                    price_date=None,
                )
            )
            continue

        if profile.owner_id is None:
            unknown_owner_count += 1
        else:
            owner_ids.add(profile.owner_id)

        if profile.availability_status == LandAvailabilityStatus.UNAVAILABLE:
            unavailable_ids.append(parcel_id)

        options = tuple(
            LandOptionAssessment(
                mode=terms.mode,
                price_status=terms.price_status,
                upfront_cost=terms.upfront_cost,
                annual_cost=terms.annual_cost,
                term_years=terms.term_years,
                price_date=terms.price_date,
                present_value=_option_present_value(terms, lifecycle_config),
                feasible=True,
            )
            for terms in profile.transaction_options
        )
        selected = (
            min(options, key=lambda option: option.present_value) if options else None
        )
        if selected is not None:
            selected_statuses.append(selected.price_status)
            if selected.mode == LandTransactionMode.PURCHASE:
                purchase_capex += selected.present_value
            else:
                recurring_pv += selected.present_value

        parcel_decisions.append(
            ParcelLandDecision(
                parcel_id=parcel_id,
                owner_id=profile.owner_id,
                availability_status=profile.availability_status,
                feasible_options=options,
                selected_mode=selected.mode if selected is not None else None,
                selected_present_value=(
                    selected.present_value if selected is not None else None
                ),
                cost_basis=(
                    selected.price_status
                    if selected is not None
                    else LandPriceStatus.UNKNOWN
                ),
                price_date=selected.price_date if selected is not None else None,
            )
        )

    land_access_present_value = purchase_capex + recurring_pv

    if selected_statuses and all(
        status == LandPriceStatus.QUOTED for status in selected_statuses
    ):
        land_cost_basis = LandCostBasis.QUOTED
    elif selected_statuses and all(
        status == LandPriceStatus.ESTIMATED for status in selected_statuses
    ):
        land_cost_basis = LandCostBasis.ESTIMATED
    elif selected_statuses:
        land_cost_basis = LandCostBasis.MIXED
    else:
        land_cost_basis = LandCostBasis.UNKNOWN

    owner_interaction_basis = (
        OwnerInteractionBasis.CONFIRMED_OWNER_IDS
        if affected_parcel_ids and unknown_owner_count == 0
        else OwnerInteractionBasis.PARCEL_PROXY
    )

    return CandidateLandAssessment(
        scenario_id=scenario_id,
        parcel_decisions=tuple(parcel_decisions),
        parcel_count=len(affected_parcel_ids),
        owner_interaction_count=len(owner_ids) + unknown_owner_count,
        owner_interaction_basis=owner_interaction_basis,
        unknown_owner_count=unknown_owner_count,
        unavailable_parcel_ids=tuple(sorted(unavailable_ids)),
        land_purchase_capex=purchase_capex,
        land_recurring_cost_pv=recurring_pv,
        land_access_present_value=land_access_present_value,
        land_cost_basis=land_cost_basis,
        is_feasible=not unavailable_ids,
    )
