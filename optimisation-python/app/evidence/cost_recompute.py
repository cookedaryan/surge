"""WP3-8: an independent recomputation of the lifecycle cost the engine reports.

Minimum Cost ranks designs by ``lifecycle_cost``. That number is the product of a
long chain — conductor rates times lengths, pole counts times unit costs, land
policy, losses valued over an analysis period — and every link is computed by the
same module that publishes the answer. A mistake anywhere in it produces a number
that is wrong and entirely plausible, and the ranking it drives would look exactly
as it does now.

So this recomputes the total from the evidence the engine publishes alongside it,
by a different route, and reports where the two disagree. The bill of materials is
the input: each line carries its own quantity, unit and rate, so the totals can be
rebuilt from the parts rather than taken on trust. Nothing here calls the costing
engine.

**Two things about the model are easy to get wrong, and both are checked.**

First, ``lifecycle_cost`` is not ``total_capex + present_value_opex``. It is that
plus ``land_recurring_cost_pv``, because ``total_capex`` carries only the *upfront*
land cost while recurring land payments are discounted separately. A reimplementation
that stops at the obvious two terms is short by the whole recurring land bill and
still balances against itself.

Second, the ``opex`` line item is the one line whose ``amount`` is **not**
``quantity * unit_rate``. Its quantity is annual loss energy and its rate is the
energy price, but its amount is their product discounted over the analysis period.
A bill-of-materials checker that applies the obvious identity to every line fails on
that one and reports a defect that is not there.

Tolerance exists because the engine publishes every total rounded to the minor unit.
An identity over three published totals can differ from the engine's own unrounded
arithmetic by a few minor units for that reason alone, which is rounding rather than
a defect. Anything that would change a ranking is larger than this by orders of
magnitude: a mispriced line item is worth thousands, not hundredths.

The golden-project run belongs to S2-1, where L2 is the evidence operator. This
module is what that step calls; the fixtures it is proven against here are synthetic.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.costing.models import (
    CandidateLifecycleCost,
    CostLineItem,
    EngineeringCostCatalogue,
)

#: Published totals are rounded to two decimals, so an identity over several of them
#: carries a few minor units of rounding. Wide enough to ignore that, far too tight
#: to ignore a mispriced line.
MONEY_TOLERANCE = Decimal("0.05")

#: The annuity factor is dimensionless and unrounded, so it is compared far more
#: tightly; the only difference expected is the last digit of Decimal's own working
#: precision.
FACTOR_TOLERANCE = Decimal("1e-12")

#: The single line item whose amount is discounted rather than quantity * rate.
DISCOUNTED_CATEGORY = "opex"

_CONDUCTOR = "conductor"
_POLE = "pole"
_LAND_PROFILED = "land_profiled"
_LAND_FALLBACK_FIXED = "land_fallback_fixed"
_LAND_FALLBACK_VARIABLE = "land_fallback_variable"

_UPFRONT_ITEM = "upfront_cost"
_RECURRING_ITEM = "recurring_cost_pv"

_ZERO = Decimal(0)


@dataclass(frozen=True)
class CostDiscrepancy:
    """One identity that did not hold, with both sides of it."""

    component: str
    reported: Decimal
    recomputed: Decimal
    tolerance: Decimal

    @property
    def difference(self) -> Decimal:
        return self.recomputed - self.reported

    def __str__(self) -> str:
        return (
            f"{self.component}: engine reported {self.reported}, "
            f"recomputed {self.recomputed} (difference {self.difference})"
        )


@dataclass(frozen=True)
class UnpublishedRate:
    """A line priced at a rate the catalogue does not publish.

    Not a discrepancy between two numbers: there is no second number to compare
    against, only a rate that came from somewhere other than the agreed catalogue.
    """

    component: str
    unit_rate: Decimal

    def __str__(self) -> str:
        return (
            f"{self.component}: rate {self.unit_rate} is not published by the catalogue"
        )


@dataclass(frozen=True)
class CostRecomputation:
    """What an independent pass over the published evidence makes of a candidate."""

    scenario_id: str
    currency: str
    #: The lifecycle cost this module arrives at from the bill of materials alone.
    lifecycle_cost: Decimal
    discrepancies: tuple[CostDiscrepancy, ...]
    #: Empty unless a catalogue was supplied to check the rates against.
    unpublished_rates: tuple[UnpublishedRate, ...] = ()

    @property
    def reconciles(self) -> bool:
        return not self.discrepancies and not self.unpublished_rates

    def describe(self) -> str:
        if self.reconciles:
            return (
                f"{self.scenario_id}: reconciles at "
                f"{self.lifecycle_cost} {self.currency}"
            )
        findings: list[str] = [str(item) for item in self.discrepancies]
        findings.extend(str(item) for item in self.unpublished_rates)
        lines = [f"{self.scenario_id}: {len(findings)} finding(s)"]
        lines.extend(f"  {finding}" for finding in findings)
        return "\n".join(lines)


def annuity_factor(rate: Decimal, years: int) -> Decimal:
    """Present value of one unit paid at the end of each year, summed term by term.

    The engine uses the closed form ``(1 - (1 + r) ** -n) / r``. This sums the
    discount factors instead, which is the same quantity computed a different way —
    the point being that a transcription error in either expression does not appear
    in both.
    """
    if years < 0:
        raise ValueError("analysis period must not be negative")
    if rate < 0:
        raise ValueError("discount rate must not be negative")
    if rate == 0:
        return Decimal(years)

    one = Decimal(1)
    discount = one + rate
    total = _ZERO
    for period in range(1, years + 1):
        total += one / (discount**period)
    return total


def _sum_amounts(line_items: Iterable[CostLineItem]) -> Decimal:
    return sum((item.amount for item in line_items), start=_ZERO)


def _in_category(
    cost: CandidateLifecycleCost, category: str, item_id: str | None = None
) -> tuple[CostLineItem, ...]:
    return tuple(
        item
        for item in cost.line_items
        if item.category == category and (item_id is None or item.item_id == item_id)
    )


def _expected_amount(item: CostLineItem, present_value_factor: Decimal) -> Decimal:
    """What a line's amount should be, given how its category is priced."""
    product = item.quantity * item.unit_rate
    if item.category == DISCOUNTED_CATEGORY:
        return product * present_value_factor
    return product


def _catalogue_rates(
    catalogue: EngineeringCostCatalogue, category: str
) -> set[Decimal]:
    if category == _CONDUCTOR:
        return {
            item.installed_cost_per_km_per_parallel_circuit
            for item in catalogue.conductor_items
        }
    if category == _POLE:
        return {item.installed_cost_each for item in catalogue.pole_items}
    if category == _LAND_FALLBACK_FIXED:
        return {catalogue.land_policy.fixed_cost_per_affected_parcel}
    if category == _LAND_FALLBACK_VARIABLE:
        return {catalogue.land_policy.variable_rate}
    return set()


class _Checker:
    """Collects the identities that did not hold, rather than failing on the first."""

    def __init__(self, money_tolerance: Decimal, factor_tolerance: Decimal) -> None:
        self._money_tolerance = money_tolerance
        self._factor_tolerance = factor_tolerance
        self.discrepancies: list[CostDiscrepancy] = []

    def money(self, component: str, reported: Decimal, recomputed: Decimal) -> None:
        self._check(component, reported, recomputed, self._money_tolerance)

    def factor(self, component: str, reported: Decimal, recomputed: Decimal) -> None:
        self._check(component, reported, recomputed, self._factor_tolerance)

    def _check(
        self,
        component: str,
        reported: Decimal,
        recomputed: Decimal,
        tolerance: Decimal,
    ) -> None:
        if abs(recomputed - reported) > tolerance:
            self.discrepancies.append(
                CostDiscrepancy(
                    component=component,
                    reported=reported,
                    recomputed=recomputed,
                    tolerance=tolerance,
                )
            )


def recompute_candidate_cost(
    cost: CandidateLifecycleCost,
    *,
    catalogue: EngineeringCostCatalogue | None = None,
    money_tolerance: Decimal = MONEY_TOLERANCE,
    factor_tolerance: Decimal = FACTOR_TOLERANCE,
) -> CostRecomputation:
    """Rebuild a candidate's lifecycle cost from its bill of materials.

    Each identity is checked against the totals the engine reported for its own
    inputs, so a single wrong aggregate is reported once rather than cascading into
    every total downstream of it.

    The two exceptions are deliberate. The present value of losses is derived from
    the *recomputed* annual loss cost rather than the published one, because the
    published figure is rounded to the minor unit and multiplying it by an annuity
    factor of twenty-odd would turn half a paisa of rounding into a real difference.
    Lifecycle cost is derived the same way, for the same reason.

    Passing ``catalogue`` additionally checks that every line was priced at a rate
    the catalogue actually publishes — the difference between "these numbers are
    consistent" and "these numbers came from the agreed rates".
    """
    checker = _Checker(money_tolerance, factor_tolerance)
    unpublished: list[UnpublishedRate] = []

    # --- Each line is its own quantity times its own rate ---------------------------
    for item in cost.line_items:
        checker.money(
            f"line_item[{item.category}/{item.item_id}]",
            item.amount,
            _expected_amount(item, cost.present_value_factor),
        )
        if catalogue is not None:
            published = _catalogue_rates(catalogue, item.category)
            if published and item.unit_rate not in published:
                unpublished.append(
                    UnpublishedRate(
                        component=f"{item.category}/{item.item_id}",
                        unit_rate=item.unit_rate,
                    )
                )

    # --- Capex, rebuilt from the lines ----------------------------------------------
    conductor_capex = _sum_amounts(_in_category(cost, _CONDUCTOR))
    checker.money("conductor_capex", cost.conductor_capex, conductor_capex)

    pole_capex = _sum_amounts(_in_category(cost, _POLE))
    checker.money("pole_capex", cost.pole_capex, pole_capex)

    land_purchase_capex = (
        _sum_amounts(_in_category(cost, _LAND_PROFILED, _UPFRONT_ITEM))
        + _sum_amounts(_in_category(cost, _LAND_FALLBACK_FIXED))
        + _sum_amounts(_in_category(cost, _LAND_FALLBACK_VARIABLE))
    )
    checker.money("land_purchase_capex", cost.land_purchase_capex, land_purchase_capex)

    land_recurring_cost_pv = _sum_amounts(
        _in_category(cost, _LAND_PROFILED, _RECURRING_ITEM)
    )
    checker.money(
        "land_recurring_cost_pv", cost.land_recurring_cost_pv, land_recurring_cost_pv
    )

    checker.money(
        "land_access_present_value",
        cost.land_access_present_value,
        cost.land_purchase_capex + cost.land_recurring_cost_pv,
    )

    checker.money(
        "total_capex",
        cost.total_capex,
        cost.conductor_capex + cost.pole_capex + cost.land_purchase_capex,
    )

    # --- Losses, valued over the analysis period -------------------------------------
    annual_loss_cost = cost.annual_loss_energy_mwh * cost.energy_price_per_mwh
    checker.money("annual_loss_cost", cost.annual_loss_cost, annual_loss_cost)

    present_value_factor = annuity_factor(
        cost.discount_rate, cost.analysis_period_years
    )
    checker.factor(
        "present_value_factor", cost.present_value_factor, present_value_factor
    )

    present_value_opex = annual_loss_cost * present_value_factor
    checker.money("present_value_opex", cost.present_value_opex, present_value_opex)

    # --- The number Minimum Cost ranks on --------------------------------------------
    lifecycle_cost = cost.total_capex + present_value_opex + cost.land_recurring_cost_pv
    checker.money("lifecycle_cost", cost.lifecycle_cost, lifecycle_cost)

    return CostRecomputation(
        scenario_id=cost.scenario_id,
        currency=cost.currency,
        lifecycle_cost=lifecycle_cost,
        discrepancies=tuple(checker.discrepancies),
        unpublished_rates=tuple(unpublished),
    )


def recompute_all(
    costs: Iterable[CandidateLifecycleCost],
    *,
    catalogue: EngineeringCostCatalogue | None = None,
    money_tolerance: Decimal = MONEY_TOLERANCE,
    factor_tolerance: Decimal = FACTOR_TOLERANCE,
) -> tuple[CostRecomputation, ...]:
    """Recompute a cohort, in the order given. S2-1 runs this over a golden project."""
    return tuple(
        recompute_candidate_cost(
            cost,
            catalogue=catalogue,
            money_tolerance=money_tolerance,
            factor_tolerance=factor_tolerance,
        )
        for cost in costs
    )


__all__ = [
    "DISCOUNTED_CATEGORY",
    "FACTOR_TOLERANCE",
    "MONEY_TOLERANCE",
    "CostDiscrepancy",
    "CostRecomputation",
    "UnpublishedRate",
    "annuity_factor",
    "recompute_all",
    "recompute_candidate_cost",
]
