# Surge MVP Ticket Plan

**Canonical as of:** 2026-08-12  
**MVP freeze:** SURGE-PY-020  
**Current ticket:** SURGE-PY-018 (in progress)

This note is the Obsidian mirror of
[`docs/Surge MVP Ticket Plan.md`](../../docs/Surge%20MVP%20Ticket%20Plan.md) and
is authoritative for Python ticket numbering and MVP scope from SURGE-PY-014
onward. Earlier day-based plans are historical context only.

## Canonical sequence

| Ticket | Final ticket name | Status | MVP responsibility |
| --- | --- | --- | --- |
| SURGE-PY-014 | Automatic PNC Network Assembly | Complete | Produce one validated `ProjectPNCNetwork` with deterministic feeder and segment identities. |
| SURGE-PY-015 | Pandapower Electrical Network + AC Load-Flow Validation | Complete | Evaluate one PNC without repairing or resizing it. |
| SURGE-PY-016 | Map-Ready PNC Result Packaging + GeoJSON Export | Complete | Package one PNC and its electrical result for presentation. |
| SURGE-PY-017 | Candidate PNC Scenario Generation | Complete | Generate 1-5 deterministic, distinct, structurally valid PNC candidates. |
| SURGE-PY-018 | Multi-Objective Scoring + Recommendation | Complete | Score electrically evaluated candidates and return an explainable deterministic recommendation. |
| SURGE-PY-019 | End-to-End Optimisation Orchestrator | In progress | Connect preprocessing, candidate generation, load flow, scoring, recommendation, and presentation behind one internal call. |
| SURGE-PY-020 | MVP Demo API + End-to-End Validation | Planned | Expose the orchestrator compatibly through the existing API and verify one golden demo fixture. |

No feature may be inserted between these tickets unless it blocks the vertical
workflow. If work expands beyond these boundaries, reduce MVP scope rather than
renumbering the sequence.

## Frozen boundaries

### SURGE-PY-017

Input is prepared `ProjectSpatialData`, feeder capacity, a prepared
`CostSurface`, and deterministic scenario configuration. Output contains
candidate records with complete `ProjectPNCNetwork` objects.

PY-017 owns candidate count 1-5 (default 3), deterministic IDs and ordering,
controlled variation through the real PNC pipeline, duplicate suppression,
attempt diagnostics, and structural PNC integrity. It does not own electrical
simulation, scoring, recommendation, API integration, or raw GIS-constraint
ingestion.

### SURGE-PY-018

PY-018 scores candidates after PY-015 evaluates them. It uses routed length,
losses, maximum loading, minimum voltage, and hard validity outcomes.
Non-converged or electrically invalid candidates remain visible but infeasible;
they cannot be recommended. Ranking and tie-breaking are deterministic and the
winner includes plain-language reasons. ML and advanced Pareto search are
post-MVP.

### SURGE-PY-019

```text
validated project data
    -> prepared cost surface
    -> PY-017 candidate PNCs
    -> PY-015 load flow for every candidate
    -> PY-018 scoring and recommendation
    -> PY-016 presentation results
    -> complete optimisation result
```

The internal entry point is conceptually `optimise_project(project_input)` and
owns orchestration rather than duplicating earlier algorithms.

### SURGE-PY-020

`POST /api/v1/optimise` already has a Java consumer. The MVP response is
additive: retain `request_id`, `status`, `scenario`,
`feeder_routes_geojson`, and `metrics`; populate legacy route and metric fields
from the recommended candidate; then add recommendation, comparison,
electrical, and presentation fields.

The golden fixture is deliberately chosen to produce at least three distinct
valid candidates. It verifies HTTP success, candidate generation behaviour,
complete WTG and route coverage, per-candidate load-flow execution,
deterministic recommendation, and valid GeoJSON. General projects may return
fewer candidates when fewer unique valid networks exist.

## Constraint and demo scope

Raw project boundaries, terrain, restrictions, parcels, ROW layers, and their
rasterization are not supported by the current public request and remain
post-MVP. PY-017 still respects blocked or penalized cells already encoded in a
prepared `CostSurface`. The Sunday API demo must use the supported
WTG/substation inputs and must not claim raw constraint-layer ingestion.

## Remaining schedule

| Date | Target |
| --- | --- |
| Wed 12 Aug | PY-017 implemented and focused tests validated |
| Thu 13 Aug | PY-018 deterministic electrical-aware scoring |
| Fri 14 Aug | PY-019 end-to-end orchestrator |
| Sat 15 Aug | PY-020 compatible API and golden fixture |
| Sun 16 Aug | End-to-end stabilization and demonstration only |

PY-017 is implemented. Three tickets remain before the SURGE-PY-020 MVP freeze:
PY-018, PY-019, and PY-020.

## Post-MVP

- Raw GIS constraint transport and rasterization
- Electrical repair, cable sizing, and feeder rebalancing
- Detailed BoQ and additional exports
- Advanced Pareto and parallel scenario search
- ML ranking
- N-1 analysis
- Production hardening and deeper Java integration refinements

## Related

- [[Overview & Layout]]
- [[presentation-boundary|Python Presentation Boundary]]
- [[PNC Network Assembly]]
- [[AC Load Flow Validation]]
