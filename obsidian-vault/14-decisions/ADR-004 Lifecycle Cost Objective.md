# ADR-004: Lifecycle Cost as the Primary Financial Objective

- **Status**: Accepted direction; implementation deferred
- **Date**: 2026-08-04

## Context

Shortest routes can require expensive foundations, affect costly land, or create higher electrical losses. A decision based on distance alone can therefore be worse over the asset lifetime.

## Decision

Use total lifecycle cost—construction, land/ROW, and discounted operating losses—as the primary financial metric. Preserve environmental and safety requirements as explicit constraints or separately visible metrics rather than hiding them inside an unexplained currency value.

## Why This Decision

Lifecycle cost aligns route comparison with project economics while keeping the components inspectable. It also allows scenario views to change weights without losing the underlying engineering measurements.

## Consequences

- **Positive**: Alternatives can be compared on a common financial horizon.
- **Positive**: Cost breakdowns support engineering review and explainability.
- **Negative**: Results depend on price date, currency, discount rate, operating profile, energy price, catalogue versions, and parcel rates.
- **Negative**: Sensitivity analysis is required because long-term assumptions are uncertain.

## Implementation Status

The Python cost module is a placeholder. Java can sum cost values already stored on route records, but it does not calculate lifecycle cost.
