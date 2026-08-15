"""Lifecycle costing domain models."""

import datetime
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from app.costing.failures import CostConfigurationError, CostEvaluationFailure


class LandPricingBasis(StrEnum):
    NONE = "NONE"
    ROUTE_OVERLAP_LENGTH_M = "ROUTE_OVERLAP_LENGTH_M"
    ROW_INTERSECTION_AREA_M2 = "ROW_INTERSECTION_AREA_M2"


@dataclass(frozen=True)
class ConductorCostItem:
    cable_type_id: str
    installed_cost_per_km_per_parallel_circuit: Decimal

    def __post_init__(self) -> None:
        if not self.cable_type_id.strip():
            raise CostConfigurationError("cable_type_id must not be empty")
        installed_cost = self.installed_cost_per_km_per_parallel_circuit
        if not installed_cost.is_finite() or installed_cost < 0:
            raise CostConfigurationError(
                "Conductor cost must be finite and non-negative"
            )


@dataclass(frozen=True)
class PoleCostItem:
    pole_type: Literal["terminal", "angle", "intermediate", "junction"]
    installed_cost_each: Decimal

    def __post_init__(self) -> None:
        if self.pole_type not in {"terminal", "angle", "intermediate", "junction"}:
            raise CostConfigurationError(f"Invalid pole_type: {self.pole_type}")
        if not self.installed_cost_each.is_finite() or self.installed_cost_each < 0:
            raise CostConfigurationError("Pole cost must be finite and non-negative")


@dataclass(frozen=True)
class LandCostPolicy:
    fixed_cost_per_affected_parcel: Decimal
    variable_basis: LandPricingBasis
    variable_rate: Decimal

    def __post_init__(self) -> None:
        fixed_cost = self.fixed_cost_per_affected_parcel
        if not fixed_cost.is_finite() or fixed_cost < 0:
            raise CostConfigurationError(
                "Fixed land cost must be finite and non-negative"
            )
        if not self.variable_rate.is_finite() or self.variable_rate < 0:
            raise CostConfigurationError(
                "Variable land rate must be finite and non-negative"
            )


@dataclass(frozen=True)
class EngineeringCostCatalogue:
    catalogue_id: str
    version: str
    currency: str
    price_basis_date: datetime.date
    conductor_items: tuple[ConductorCostItem, ...]
    pole_items: tuple[PoleCostItem, ...]
    land_policy: LandCostPolicy

    def __post_init__(self) -> None:
        if not self.catalogue_id.strip():
            raise CostConfigurationError("catalogue_id must not be empty")
        if not self.version.strip():
            raise CostConfigurationError("version must not be empty")
        if (
            not self.currency.strip()
            or not self.currency.isalpha()
            or len(self.currency) != 3
        ):
            raise CostConfigurationError("currency must be a valid 3-letter code")

        seen_conductors = set()
        for conductor_item in self.conductor_items:
            if conductor_item.cable_type_id in seen_conductors:
                raise CostConfigurationError(
                    f"Duplicate conductor entry: {conductor_item.cable_type_id}"
                )
            seen_conductors.add(conductor_item.cable_type_id)

        seen_poles = set()
        required_poles = {"terminal", "angle", "intermediate", "junction"}
        for pole_item in self.pole_items:
            if pole_item.pole_type in seen_poles:
                raise CostConfigurationError(
                    f"Duplicate pole entry: {pole_item.pole_type}"
                )
            seen_poles.add(pole_item.pole_type)
        if seen_poles != required_poles:
            missing = required_poles - seen_poles
            raise CostConfigurationError(f"Missing required pole types: {missing}")


@dataclass(frozen=True)
class LifecycleCostConfig:
    currency: str
    energy_price_basis_date: datetime.date
    analysis_period_years: int
    discount_rate: Decimal
    annual_operating_hours: int
    loss_load_factor: Decimal
    energy_price_per_mwh: Decimal

    def __post_init__(self) -> None:
        if (
            not self.currency.strip()
            or not self.currency.isalpha()
            or len(self.currency) != 3
        ):
            raise CostConfigurationError("currency must be a valid 3-letter code")
        if self.analysis_period_years < 1:
            raise CostConfigurationError("analysis_period_years must be >= 1")
        if (
            not self.discount_rate.is_finite()
            or self.discount_rate < 0
            or self.discount_rate >= 1
        ):
            raise CostConfigurationError(
                "discount_rate must be between 0 and 1 (exclusive of 1)"
            )
        if self.annual_operating_hours < 0 or self.annual_operating_hours > 8760:
            raise CostConfigurationError(
                "annual_operating_hours must be between 0 and 8760"
            )
        if (
            not self.loss_load_factor.is_finite()
            or self.loss_load_factor < 0
            or self.loss_load_factor > 1
        ):
            raise CostConfigurationError("loss_load_factor must be between 0 and 1")
        if not self.energy_price_per_mwh.is_finite() or self.energy_price_per_mwh < 0:
            raise CostConfigurationError(
                "energy_price_per_mwh must be finite and non-negative"
            )


@dataclass(frozen=True)
class CostLineItem:
    category: str
    item_id: str
    quantity: Decimal
    unit: str
    unit_rate: Decimal
    amount: Decimal


@dataclass(frozen=True)
class CandidateLifecycleCost:
    scenario_id: str
    conductor_capex: Decimal
    pole_capex: Decimal
    land_capex: Decimal
    total_capex: Decimal
    annual_loss_energy_mwh: Decimal
    annual_loss_cost: Decimal
    present_value_factor: Decimal
    present_value_opex: Decimal
    lifecycle_cost: Decimal
    line_items: tuple[CostLineItem, ...]
    currency: str
    catalogue_id: str
    catalogue_version: str
    catalogue_price_basis_date: datetime.date
    energy_price_basis_date: datetime.date
    cost_model_version: str


@dataclass(frozen=True)
class CandidateCostAssessment:
    scenario_id: str
    cost: CandidateLifecycleCost | None
    failures: tuple[CostEvaluationFailure, ...]

    conductor_capex_amount: Decimal | None = None
    pole_capex_amount: Decimal | None = None
    land_capex_amount: Decimal | None = None
    total_capex_amount: Decimal | None = None
    present_value_opex_amount: Decimal | None = None
    annual_loss_energy_mwh: Decimal | None = None
    annual_loss_cost_amount: Decimal | None = None
    present_value_factor: Decimal | None = None
    line_items: tuple[CostLineItem, ...] = ()
    currency: str | None = None
    catalogue_id: str | None = None
    catalogue_version: str | None = None
    catalogue_price_basis_date: datetime.date | None = None
    energy_price_basis_date: datetime.date | None = None
    cost_model_version: str | None = None

    @property
    def capex_available(self) -> bool:
        return (
            self.conductor_capex_amount is not None
            and self.pole_capex_amount is not None
            and self.land_capex_amount is not None
            and self.total_capex_amount is not None
        )

    @property
    def opex_available(self) -> bool:
        return self.present_value_opex_amount is not None
