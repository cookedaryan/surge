# Lifecycle Cost Objective Model

> [!warning] Implementation status: Planned
> `cost_function.py` contains only a module description. Stored route cost values can be aggregated by Java, but Python does not calculate them.

## Purpose

Shortest distance is not necessarily the least expensive build. SURGE's target objective combines construction, land, and operating effects over the asset lifetime:

$$
\text{Lifecycle Cost} = \text{CAPEX}_{poles} + \text{CAPEX}_{conductor} + \text{CAPEX}_{ROW} + \text{PV}(\text{OPEX}_{losses})
$$

**CAPEX** is up-front capital expenditure. **OPEX** is recurring operating expenditure. **Present value (PV)** discounts future costs so values from different years can be compared at the decision date.

## Intended Components

- Pole and foundation cost based on type, count, terrain, and access
- Conductor cost based on installed route length and conductor selection
- ROW compensation based on actual corridor-parcel intersection area and parcel rate
- Lifetime energy-loss cost based on electrical losses, operating profile, energy price, analysis period, and discount rate

## Why Keep Raw Metrics?

Each candidate should retain raw length, pole count, affected area, losses, and cost components as well as a combined score. Raw values make explanations possible and prevent normalized scenario scores from being mistaken for currency.

## Required Decisions

- currency and price date
- discount rate and analysis lifetime
- energy-price escalation and WTG operating profile
- whether environmental impacts are money values, separate constraints, or normalized penalties
- treatment of shared corridors and common infrastructure
- source and version of every cost catalogue

## Related Notes

- [[Routing]]
- [[Pole Placement]]
- [[Explainability]]
- [[ADR-004 Lifecycle Cost Objective]]
