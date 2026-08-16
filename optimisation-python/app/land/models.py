"""Land commercial profile and intelligence domain models."""

import datetime
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class LandAvailabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    NEGOTIABLE = "NEGOTIABLE"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class LandTransactionMode(StrEnum):
    PURCHASE = "PURCHASE"
    LEASE = "LEASE"
    EASEMENT = "EASEMENT"


class LandPriceStatus(StrEnum):
    QUOTED = "QUOTED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class LandCostBasis(StrEnum):
    QUOTED = "QUOTED"
    ESTIMATED = "ESTIMATED"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


class OwnerInteractionBasis(StrEnum):
    CONFIRMED_OWNER_IDS = "CONFIRMED_OWNER_IDS"
    PARCEL_PROXY = "PARCEL_PROXY"


@dataclass(frozen=True)
class LandTransactionTerms:
    mode: LandTransactionMode
    price_status: LandPriceStatus
    upfront_cost: Decimal
    annual_cost: Decimal
    term_years: int | None
    price_date: datetime.date | None

    def __post_init__(self) -> None:
        if not self.upfront_cost.is_finite() or self.upfront_cost < 0:
            raise ValueError("upfront_cost must be finite and non-negative")
        if not self.annual_cost.is_finite() or self.annual_cost < 0:
            raise ValueError("annual_cost must be finite and non-negative")
        if self.term_years is not None and (
            isinstance(self.term_years, bool)
            or not isinstance(self.term_years, int)
            or self.term_years < 1
        ):
            raise ValueError("term_years must be a positive integer if provided")


@dataclass(frozen=True)
class ParcelCommercialProfile:
    parcel_id: str
    owner_id: str | None
    availability_status: LandAvailabilityStatus
    transaction_options: tuple[LandTransactionTerms, ...]

    def __post_init__(self) -> None:
        if not self.parcel_id.strip():
            raise ValueError("parcel_id must not be empty")
        if self.owner_id is not None and not self.owner_id.strip():
            raise ValueError("owner_id must not be blank if provided")
        modes = [option.mode for option in self.transaction_options]
        if len(modes) != len(set(modes)):
            raise ValueError("transaction option modes must be unique per parcel")


@dataclass(frozen=True)
class LandCommercialContext:
    currency: str
    as_of_date: datetime.date
    parcel_profiles: tuple[ParcelCommercialProfile, ...]

    def __post_init__(self) -> None:
        if (
            not self.currency.strip()
            or not self.currency.isalpha()
            or len(self.currency) != 3
        ):
            raise ValueError("currency must be a valid 3-letter code")

        seen_parcels: set[str] = set()
        for profile in self.parcel_profiles:
            if profile.parcel_id in seen_parcels:
                raise ValueError(
                    f"Duplicate commercial profile for parcel_id: {profile.parcel_id}"
                )
            seen_parcels.add(profile.parcel_id)


@dataclass(frozen=True)
class LandOptionAssessment:
    mode: LandTransactionMode
    price_status: LandPriceStatus
    upfront_cost: Decimal
    annual_cost: Decimal
    term_years: int | None
    price_date: datetime.date | None
    present_value: Decimal
    feasible: bool


@dataclass(frozen=True)
class ParcelLandDecision:
    parcel_id: str
    owner_id: str | None
    availability_status: LandAvailabilityStatus
    feasible_options: tuple[LandOptionAssessment, ...]
    selected_mode: LandTransactionMode | None
    selected_present_value: Decimal | None
    cost_basis: LandPriceStatus
    price_date: datetime.date | None


@dataclass(frozen=True)
class CandidateLandAssessment:
    scenario_id: str
    parcel_decisions: tuple[ParcelLandDecision, ...]
    parcel_count: int
    owner_interaction_count: int
    owner_interaction_basis: OwnerInteractionBasis
    unknown_owner_count: int
    unavailable_parcel_ids: tuple[str, ...]
    land_purchase_capex: Decimal
    land_recurring_cost_pv: Decimal
    land_access_present_value: Decimal
    land_cost_basis: LandCostBasis
    is_feasible: bool

    def __post_init__(self) -> None:
        if not self.scenario_id.strip():
            raise ValueError("scenario_id must not be empty")
        if self.parcel_count < 0:
            raise ValueError("parcel_count must be non-negative")
        if self.owner_interaction_count < 0:
            raise ValueError("owner_interaction_count must be non-negative")
        if self.unknown_owner_count < 0:
            raise ValueError("unknown_owner_count must be non-negative")
        if not self.land_purchase_capex.is_finite() or self.land_purchase_capex < 0:
            raise ValueError("land_purchase_capex must be finite and non-negative")
        if (
            not self.land_recurring_cost_pv.is_finite()
            or self.land_recurring_cost_pv < 0
        ):
            raise ValueError("land_recurring_cost_pv must be finite and non-negative")
        if (
            not self.land_access_present_value.is_finite()
            or self.land_access_present_value < 0
        ):
            raise ValueError(
                "land_access_present_value must be finite and non-negative"
            )
        expected_total = self.land_purchase_capex + self.land_recurring_cost_pv
        if self.land_access_present_value != expected_total:
            raise ValueError(
                "land_access_present_value must equal purchase plus recurring PV"
            )
        if self.unavailable_parcel_ids != tuple(
            sorted(set(self.unavailable_parcel_ids))
        ):
            raise ValueError("unavailable_parcel_ids must be sorted and unique")
        if self.is_feasible == bool(self.unavailable_parcel_ids):
            raise ValueError("is_feasible must reflect unavailable parcels")
