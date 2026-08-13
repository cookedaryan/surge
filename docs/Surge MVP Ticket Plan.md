# Surge MVP Ticket Plan

**Canonical as of:** 2026-08-13
**MVP freeze:** SURGE-PY-020
**Current focus:** Two-day demo productisation sprint

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
| SURGE-PY-021 | V1 Constraint Regression Coverage | Complete | Enforce the existing V1 constraint behavior with deterministic positive, rejection, and compatibility API tests. |
| SURGE-PY-022 | Constraint Fixture Provenance Labeling | Complete | Label the hand-authored constraint payload as a Python-contract fixture and document the evidence needed for verified KMZ provenance. |

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

### SURGE-PY-021 - V1 Constraint Regression Coverage [COMPLETE]

PY-021 is additive test coverage above the frozen PY-020 MVP boundary; it does
not change the request or response contract.
`optimisation-python/tests/api/test_optimise_v1.py` reuses the deterministic
constraint fixture to verify successful hard/soft constraint handling,
route-level hard-polygon avoidance, byte-identical repeat responses, endpoint
rejection inside a named hard buffer, and unchanged uniform-cost routing when
`avoidance_geojson` is omitted.

### SURGE-PY-022 - Constraint Fixture Provenance Labeling [COMPLETE]

PY-022 documents `constraint_demo_project_v2.json` as a hand-authored,
deterministic Python-contract fixture. It verifies Python behavior after a
well-formed payload reaches the service; it does not verify Java's KMZ-to-JSON
transformation. The fixture README records the cross-team capture and comparison
steps required before the payload may be described as a verified KMZ round-trip
artifact. No request data, test behavior, schema, or production code changed.

## Constraint and demo scope

The public V1 and V2 requests accept optional `avoidance_geojson` features and
the production pipeline maps them to hard exclusions or soft penalties before
routing. PY-021 closes the V1 API coverage gap for that implemented path.
Project-boundary clipping, terrain-derived costs, fixture provenance from a KMZ
round trip, and pole endpoint deduplication remain separate follow-up work.

## Two-day demo productisation sprint

**Outcome by Saturday, 15 August:** a repeatable vertical-slice demonstration
that accepts a controlled wind-project dataset, runs the real optimisation
workflow, shows the selected route on the map, and explains the recommendation
with traceable electrical and routing evidence.

This sprint is about turning the completed engine into credible product proof.
It does not expand the engineering scope. The demonstration must be narrower
before it is allowed to display synthetic, placeholder, or unsupported results.

### Day 1 - Thursday, 13 August: make the real product path reliable

**Goal:** prove one honest path from project data to a persisted, visible
optimisation result.

| Time box | Work | Evidence at the end of the block |
| --- | --- | --- |
| First 2 hours | Freeze one named demo dataset and its electrical assumptions. Record the supported inputs and expected candidate count. | Versioned fixture, input checklist, and expected high-level result. |
| Next 3 hours | Bring up and verify the actual path: Web GIS -> Java job API -> Python V1 compatibility endpoint -> PostGIS -> route API -> Web GIS. Fix only blockers in this path. | A fresh run completes without manually inserting result data. |
| Next 2 hours | Remove or hide false-success behaviour from the demo path. An optimiser, persistence, or refresh failure must be visible to the user. Synthetic scenario-comparison and parcel-impact values must not be presented as calculated results. | Failed runs fail clearly; every visible engineering value has a real source. |
| Final 1-2 hours | Add a repeatable smoke procedure and run the focused quality checks from the correct project directories. Capture runtime and known warnings. | One short startup/smoke checklist that another engineer can follow. |

**Day 1 exit gate**

- The Python suite remains green; the current baseline is `460 passed` on
  Python 3.11.9.
- A job created from the UI reaches the real Python optimiser, persists the
  recommended WGS-84 route, and renders it after a page refresh.
- A broken optimiser connection produces a visible failed state rather than a
  simulated completion.
- The same fixed input produces the same recommendation on two consecutive
  runs.
- Environment blockers are explicit. At planning time Docker is unavailable
  on the workstation, web dependencies are not installed, and the Maven
  wrapper cannot create its default user-level `.m2` directory in the managed
  environment.

### Day 2 - Friday, 14 August: make the proof feel investable

**Goal:** make the working vertical slice communicate an engineering decision,
not merely draw a line.

| Time box | Work | Evidence at the end of the block |
| --- | --- | --- |
| First 3 hours | Carry the existing rich optimiser result across the product boundary. Show the recommended candidate, score/reason, route length, active losses, maximum loading, minimum voltage, feasibility, and rejected-candidate reasons. | A reviewer can answer "why this route?" from the product without reading raw logs. |
| Next 2 hours | Tighten the result experience: clear running/failed/completed states, units, preliminary-engineering labels, useful empty states, and map focus on the recommended network. | The primary workflow is understandable without developer narration. |
| Next 2 hours | Provide trustworthy outputs using existing real data: recommended-route GeoJSON plus a compact candidate/electrical summary. Hide exports whose figures are still synthetic or disconnected from the optimiser. | Downloaded evidence matches the on-screen recommendation. |
| Final 1-2 hours | Run the full available checks, perform two cold-start demo rehearsals, fix only release blockers, and capture a short evidence pack. | Test/build logs, screenshots, measured runtime, demo script, and limitations are ready. |

**Day 2 exit gate**

- At least three distinct candidates are evaluated for the golden fixture and
  the recommended candidate is clearly identified.
- All displayed metrics are generated by the current run and use explicit
  units; no hard-coded scenario numbers appear in the demo.
- Invalid or electrically infeasible candidates remain visible with rejection
  reasons and cannot be recommended.
- The map, summary, and exported result refer to the same candidate and job.
- The product survives two consecutive rehearsals from startup to export.

### Saturday demonstration gate

Use a 6-8 minute story:

1. Introduce the project, WTGs, substation, and engineering assumptions.
2. Start one optimisation job and show honest progress and completion states.
3. Show the candidate comparison and the selected radial network on the map.
4. Explain the winner using length, loss, loading, voltage, and feasibility.
5. Export the recommended route and summary, then state the current limits.

The build is ready only if a fresh run completes without manual data repair,
the recommendation repeats for the same input, every demonstrated number is
traceable to stored or returned data, and no unsupported terrain, parcel, ROW,
ML, or production-readiness claim is made.

### Deliberate two-day cuts

- KMZ-to-constraint provenance, Java transport, and terrain-derived costs
- ML ranking, N-1 analysis, and automatic electrical repair
- New algorithms or a broad UI redesign
- Cloud deployment and production security hardening
- Detailed BoQ/PDF work not backed by the current optimisation result

These cuts protect the Saturday outcome: one real, deterministic,
electrically screened decision workflow that looks like the foundation of an
industry product.

## Explicit post-MVP work

- project-boundary clipping, terrain-derived costs, and verified KMZ-to-Python
  constraint provenance/transport;
- automatic electrical repair, cable resizing, and feeder rebalancing;
- detailed BoQ and additional export formats;
- advanced Pareto and large-scale parallel candidate search;
- ML ranking;
- N-1 analysis; and
- production hardening and Java integration refinements beyond additive MVP
  compatibility.
