# Surge MVP Ticket Plan

**Canonical as of:** 2026-08-13
**MVP freeze:** SURGE-PY-020
**Current ticket:** SURGE-PY-020 (complete)

This document is authoritative for Python ticket numbering and MVP scope from
SURGE-PY-014 onward. Earlier day-based plans are historical context only.

## Canonical sequence

| Ticket | Final ticket name | Status | MVP responsibility |
| --- | --- | --- | --- |
| SURGE-PY-014 | Automatic PNC Network Assembly | Complete | Produce one validated `ProjectPNCNetwork` with deterministic feeder and segment identities. |
| SURGE-PY-015 | Pandapower Electrical Network + AC Load-Flow Validation | Complete | Evaluate one PNC without repairing or resizing it. |
| SURGE-PY-016 | Map-Ready PNC Result Packaging + GeoJSON Export | Complete | Package one PNC and its electrical result for presentation. |
| SURGE-PY-017 | Candidate PNC Scenario Generation | Complete | Generate 1-5 deterministic, distinct, structurally valid PNC candidates. |
| SURGE-PY-018 | Multi-Objective Scoring + Recommendation | Complete | Score electrically evaluated candidates and return an explainable deterministic recommendation. |
| SURGE-PY-019 | End-to-End Optimisation Orchestrator | Complete | Connect preprocessing, candidate generation, load flow, scoring, recommendation, and presentation behind one internal call. |
| SURGE-PY-020 | MVP Demo API + End-to-End Validation | Complete | Expose the orchestrator compatibly through the existing API and verify one golden demo fixture. |

No feature may be inserted between these tickets unless it blocks the vertical
workflow. If work expands beyond these boundaries, reduce MVP scope rather than
renumbering the sequence.

## Frozen ticket boundaries

### SURGE-PY-017 - Candidate PNC Scenario Generation

Input is prepared `ProjectSpatialData`, feeder capacity, a prepared
`CostSurface`, and deterministic scenario configuration. Output is a scenario
generation result containing candidate records, each with a complete
`ProjectPNCNetwork`.

PY-017 owns:

- configurable candidate count from 1 through 5, defaulting to 3;
- deterministic scenario IDs, parameter schedules, ordering, and diagnostics;
- controlled variation that reaches the existing grouping, topology, routing,
  refinement, and PNC assembly pipeline;
- duplicate-network suppression; and
- structural PNC integrity for every accepted candidate.

PY-017 does not own electrical simulation, candidate scoring, recommendation,
API integration, or raw GIS-constraint ingestion.

### SURGE-PY-018 - Multi-Objective Candidate Scoring + Explainable Recommendation [COMPLETE]

PY-018 consumes candidates after PY-015 has evaluated each network. The MVP
score is deterministic and transparent; ML ranking and an advanced Pareto
search remain post-MVP.

At minimum, scoring uses:

- total routed length;
- total active losses;
- maximum cable loading;
- minimum bus voltage; and
- explicit hard-constraint or electrical-validity outcomes.

Non-converged and electrically invalid candidates are infeasible and cannot be
recommended. They remain in the comparison output with explicit rejection
reasons. Feasible candidates are ranked deterministically, including stable
tie-breaking, and the result explains why the winner was selected.

The existing SURGE-PY-012 route scorer is preliminary spatial/constructability
infrastructure. It may be reused, but it is not by itself completion of PY-018
because it does not consume the PY-015 electrical result.

### SURGE-PY-019 - End-to-End Optimisation Orchestrator

PY-019 owns orchestration only:

```text
validated project data
    -> prepared cost surface
    -> PY-017 candidate PNCs
    -> PY-015 load flow for every candidate
    -> PY-018 scoring and recommendation
    -> PY-016 presentation result for each exposed candidate
    -> complete optimisation result
```

The public internal entry point should be conceptually equivalent to
`optimise_project(project_input)`. It must not duplicate algorithms already
owned by earlier tickets.

The implemented workflow validates shared project, raster, electrical, and
operating-point inputs before candidate generation. Candidate-local solver and
electrical failures remain attached to the affected candidate, while shared or
unexpected stage failures return a structured `FAILED` result. Every
electrically evaluated candidate retains its scoring result. The recommended
candidate additionally receives a presentation result; a recommendation
packaging failure returns a structured `FAILED` result. Frozen workflow models
enforce these state combinations.

### SURGE-PY-020 - MVP Demo API + End-to-End Validation

`POST /api/v1/optimise` already exists and is consumed by the Java backend.
PY-020 therefore extends the existing response additively instead of silently
replacing it. Until Java adopts the richer contract:

- retain `request_id`, `status`, `scenario`, `feeder_routes_geojson`, and
  `metrics`;
- populate the legacy GeoJSON and metrics from the recommended candidate; and
- add recommended-scenario, candidate-comparison, electrical-summary, and
  map-ready result fields without changing the meaning of existing fields.

The golden API fixture must be deliberately chosen to produce at least three
distinct valid candidates. It must prove HTTP success, configured attempt/count
behaviour, complete WTG coverage, routed physical segments, load-flow execution
for every accepted candidate, a deterministic recommendation, and valid
GeoJSON. The general scenario-generation contract may return fewer candidates
when a project has fewer unique valid networks.

The implemented V1 endpoint keeps the Java request and the legacy
`request_id`, lowercase `status`, `scenario`, `feeder_routes_geojson`, and
`metrics` fields. It now runs `optimise_project` and adds `workflow_status`,
generation diagnostics, candidate comparisons, recommendation details, the
typed presentation result, and failures. When the legacy caller does not
supply cable data, the adapter derives ampacity from `feeder_capacity_mw` and
uses the documented 33 kV MVP compatibility cable parameters; explicit cable
configuration overrides that compatibility profile.

`POST /api/v2/optimise` exposes the same orchestrator through an explicit
engineering request that requires cable properties. The golden fixture
requests and receives three unique electrically valid candidates, then checks
repeat-call equality, complete WTG and segment coverage, ranked candidates,
recommendation, and WGS-84 GeoJSON.

## Constraint and demo scope

The current public request does not transport project boundaries or raw
restriction/exclusion layers, and the production pipeline does not rasterize
those layers. To preserve the PY-020 deadline, raw GIS constraint transport and
rasterization are outside this MVP freeze.

The internal scenario generator must continue to respect blocked or penalized
cells already encoded in its prepared `CostSurface`. The public golden fixture
uses the currently supported WTG/substation inputs and uniform prepared cost
surface. Raw boundary, exclusion, terrain, parcel, and ROW inputs must not be
claimed in the Sunday API demonstration until a later ticket integrates them.

## Remaining schedule

| Date | Target |
| --- | --- |
| Wed 12 Aug | PY-017 implemented and focused tests validated |
| Thu 13 Aug | PY-018 deterministic electrical-aware scoring |
| Fri 14 Aug | PY-019 end-to-end orchestrator |
| Sat 15 Aug | PY-020 compatible API and golden fixture |
| Sun 16 Aug | End-to-end stabilization and demonstration only |

The deterministic MVP sequence through PY-020 is complete.

## Explicit post-MVP work

- raw project-boundary, terrain, exclusion, parcel, ROW, and accessibility
  transport/rasterization;
- automatic electrical repair, cable resizing, and feeder rebalancing;
- detailed BoQ and additional export formats;
- advanced Pareto and large-scale parallel candidate search;
- ML ranking;
- N-1 analysis; and
- production hardening and Java integration refinements beyond additive MVP
  compatibility.
