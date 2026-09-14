# Lifecycle Cost Objective Model

`app/costing/lifecycle.py` evaluates candidate lifecycle cost with `Decimal`
arithmetic:

`Lifecycle Cost = conductor CAPEX + pole CAPEX + land CAPEX + PV(loss OPEX)`

## Components

- Conductor CAPEX uses routed circuit-kilometres, parallel circuit count, and the selected cable catalogue rate.
- Pole CAPEX uses the deduplicated physical-pole count by pole type.
- Land CAPEX uses unique affected parcels and either route-overlap length or actual ROW-intersection area.
- Loss OPEX uses active loss, annual operating hours, loss-load factor, energy price, analysis period, and discount rate.

## Correctness and Availability

- Catalogue and lifecycle configuration currencies must match.
- Area-based land pricing uses the configured total ROW width, which defaults to 18 m in V2 and is mapped from the V1 `row_width_m` input.
- A known empty parcel exposure is a valid zero land cost. Failed spatial analysis emits `LAND_EXPOSURE_UNAVAILABLE`; it does not fabricate zero land CAPEX.
- Successfully evaluated components and catalogue provenance remain visible when another component fails. A combined lifecycle cost is returned only when all CAPEX and OPEX components are available.

## Catalogue Contract

V2 accepts an inline, versioned engineering catalogue. The catalogue ID and
version are returned as provenance. ID-only lookup is intentionally not part of
the request schema until the application has a configured catalogue store.
