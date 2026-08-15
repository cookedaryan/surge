# Lifecycle Cost Objective Model

> [!success] Implementation status: Implemented
> `app/costing/lifecycle.py` computes lifecycle cost dynamically within the Python Orchestrator using exact `Decimal` arithmetic.

The API currently accepts an inline, versioned engineering catalogue. Catalogue
IDs remain part of result provenance, but ID-only lookup is not exposed until a
configured persistent catalogue store exists.

## Purpose

Shortest distance is not necessarily the least expensive build. SURGE's target objective combines construction, land, and operating effects over the asset lifetime:

$$
\text{Lifecycle Cost} = \text{CAPEX}_{poles} + \text{CAPEX}_{conductor} + \text{CAPEX}_{ROW} + \text{PV}(\text{OPEX}_{losses})
$$

**CAPEX** is up-front capital expenditure. **OPEX** is recurring operating expenditure. **Present value (PV)** discounts future costs so values from different years can be compared at the decision date.

## Intended Components

- **Pole CAPEX**: Pole and foundation cost based on type (terminal, angle, intermediate, junction) and count.
- **Conductor CAPEX**: Conductor cost based on installed route length and conductor selection.
- **Land CAPEX**: ROW compensation based on actual corridor-parcel intersection area and parcel rate.
- **Loss OPEX**: Lifetime energy-loss cost based on electrical losses, operating profile, energy price, analysis period, and discount rate.

## Why Keep Raw Metrics?

Each candidate should retain raw length, pole count, affected area, losses, and cost components as well as a combined score. Raw values make explanations possible and prevent normalized scenario scores from being mistaken for currency.

## Required Decisions

- currency and price date
- discount rate and analysis lifetime
- energy-price escalation and WTG operating profile
- whether environmental impacts are money values, separate constraints, or normalized penalties
- treatment of shared corridors and common infrastructure
- source and version of every cost catalogue

## Evaluation Rules

- Catalogue CAPEX and energy-price OPEX must use the same three-letter currency.
- Area-based land pricing uses the request's configured total ROW width (18 m by default), not a route-centreline approximation.
- A known empty parcel exposure produces zero land CAPEX. Failed spatial analysis produces `LAND_EXPOSURE_UNAVAILABLE` and no land or total CAPEX.
- Candidate responses retain successfully evaluated cost components and provenance when another component fails; lifecycle cost is published only when every component is available.

## Related Notes

- [[Routing]]
- [[Pole Placement]]
- [[Explainability]]
- [[ADR-004 Lifecycle Cost Objective]]
