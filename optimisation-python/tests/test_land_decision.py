"""Tests for parcel-level land transaction decisions and fingerprints."""

import datetime
from dataclasses import replace
from decimal import Decimal

from app.costing.models import LifecycleCostConfig
from app.land.decision import assess_candidate_land, present_value_factor
from app.land.fingerprint import (
    compute_land_economic_context_id,
    compute_land_routing_context_id,
)
from app.land.models import (
    LandAvailabilityStatus,
    LandCommercialContext,
    LandCostBasis,
    LandPriceStatus,
    LandTransactionMode,
    LandTransactionTerms,
    OwnerInteractionBasis,
    ParcelCommercialProfile,
)
from app.optimisation.engineering_metric_models import ParcelEngineeringExposure


def _terms(
    mode: LandTransactionMode,
    *,
    upfront: str = "0",
    annual: str = "0",
    years: int | None = None,
    status: LandPriceStatus = LandPriceStatus.QUOTED,
) -> LandTransactionTerms:
    return LandTransactionTerms(
        mode=mode,
        price_status=status,
        upfront_cost=Decimal(upfront),
        annual_cost=Decimal(annual),
        term_years=years,
        price_date=datetime.date(2026, 1, 1),
    )


def _lifecycle() -> LifecycleCostConfig:
    return LifecycleCostConfig(
        currency="USD",
        energy_price_basis_date=datetime.date(2026, 1, 1),
        analysis_period_years=10,
        discount_rate=Decimal("0.10"),
        annual_operating_hours=8760,
        loss_load_factor=Decimal("0.3"),
        energy_price_per_mwh=Decimal("50"),
    )


def _exposure(parcel_id: str) -> ParcelEngineeringExposure:
    return ParcelEngineeringExposure(
        parcel_id=parcel_id,
        route_overlap_length_m=10.0,
        row_intersection_area_m2=100.0,
    )


def test_assessment_selects_lowest_present_value_and_counts_unique_owners() -> None:
    context = LandCommercialContext(
        currency="USD",
        as_of_date=datetime.date(2026, 1, 1),
        parcel_profiles=(
            ParcelCommercialProfile(
                parcel_id="P1",
                owner_id="OWNER-1",
                availability_status=LandAvailabilityStatus.NEGOTIABLE,
                transaction_options=(
                    _terms(LandTransactionMode.PURCHASE, upfront="10000"),
                    _terms(LandTransactionMode.LEASE, annual="1000", years=5),
                ),
            ),
            ParcelCommercialProfile(
                parcel_id="P2",
                owner_id="OWNER-1",
                availability_status=LandAvailabilityStatus.AVAILABLE,
                transaction_options=(
                    _terms(
                        LandTransactionMode.PURCHASE,
                        upfront="2000",
                        status=LandPriceStatus.ESTIMATED,
                    ),
                ),
            ),
        ),
    )

    assessment = assess_candidate_land(
        scenario_id="scenario-1",
        parcel_exposures=(_exposure("P2"), _exposure("P1")),
        land_context=context,
        lifecycle_config=_lifecycle(),
    )

    lease_pv = Decimal("1000") * present_value_factor(Decimal("0.10"), 5)
    assert assessment.scenario_id == "scenario-1"
    assert tuple(d.parcel_id for d in assessment.parcel_decisions) == ("P1", "P2")
    assert assessment.parcel_decisions[0].selected_mode == LandTransactionMode.LEASE
    assert assessment.owner_interaction_count == 1
    assert (
        assessment.owner_interaction_basis
        == OwnerInteractionBasis.CONFIRMED_OWNER_IDS
    )
    assert assessment.land_purchase_capex == Decimal("2000")
    assert assessment.land_recurring_cost_pv == lease_pv
    assert assessment.land_access_present_value == Decimal("2000") + lease_pv
    assert assessment.land_cost_basis == LandCostBasis.MIXED
    assert assessment.is_feasible


def test_unavailable_and_unprofiled_parcels_are_reported_conservatively() -> None:
    context = LandCommercialContext(
        currency="USD",
        as_of_date=datetime.date(2026, 1, 1),
        parcel_profiles=(
            ParcelCommercialProfile(
                parcel_id="P1",
                owner_id=None,
                availability_status=LandAvailabilityStatus.UNAVAILABLE,
                transaction_options=(),
            ),
        ),
    )

    assessment = assess_candidate_land(
        scenario_id="scenario-2",
        parcel_exposures=(_exposure("P1"), _exposure("P2")),
        land_context=context,
        lifecycle_config=_lifecycle(),
    )

    assert assessment.unavailable_parcel_ids == ("P1",)
    assert not assessment.is_feasible
    assert assessment.unknown_owner_count == 2
    assert assessment.owner_interaction_count == 2
    assert assessment.owner_interaction_basis == OwnerInteractionBasis.PARCEL_PROXY


def test_fingerprints_are_order_independent_and_scope_routing_state() -> None:
    profile = ParcelCommercialProfile(
        parcel_id="P1",
        owner_id="OWNER-1",
        availability_status=LandAvailabilityStatus.AVAILABLE,
        transaction_options=(
            _terms(LandTransactionMode.PURCHASE, upfront="5000"),
            _terms(LandTransactionMode.LEASE, annual="500", years=10),
        ),
    )
    context = LandCommercialContext(
        currency="USD",
        as_of_date=datetime.date(2026, 1, 1),
        parcel_profiles=(profile,),
    )
    reordered = replace(
        context,
        parcel_profiles=(
            replace(
                profile,
                transaction_options=tuple(reversed(profile.transaction_options)),
            ),
        ),
    )

    assert compute_land_economic_context_id(context) == (
        compute_land_economic_context_id(reordered)
    )
    assert compute_land_economic_context_id(context) != (
        compute_land_economic_context_id(
            replace(context, as_of_date=datetime.date(2026, 2, 1))
        )
    )
    assert compute_land_routing_context_id(context) != (
        compute_land_routing_context_id(
            replace(
                context,
                parcel_profiles=(
                    replace(
                        profile,
                        availability_status=LandAvailabilityStatus.UNAVAILABLE,
                    ),
                ),
            )
        )
    )
