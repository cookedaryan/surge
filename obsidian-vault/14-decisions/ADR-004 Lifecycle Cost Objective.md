# ADR-004: Lifecycle Cost as Primary Objective Function

* Status: **Accepted**
* Date: 2026-08-04

## Context
Traditional routing algorithms optimize solely for geometric distance. However, in wind farm grid evacuation, line length is only one component of cost; terrain slope foundations, land acquisition ROW, and lifetime $I^2R$ electrical losses heavily influence total project financial viability.

## Decision
Adopt **Total Project Lifecycle Cost** (CAPEX + Land ROW + 20-Year Discounted OPEX Losses) as the primary optimization cost metric rather than shortest physical path.

## Consequences
- **Positive**: Directly aligns route optimization with financial ROI and land acquisition reality.
- **Negative**: Requires financial parameters (discount rate, energy cost per kWh, parcel compensation rates) as inputs.
