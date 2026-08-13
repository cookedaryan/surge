# Surge MVP Ticket Plan

**Canonical as of:** 2026-08-13
**MVP freeze:** SURGE-PY-020
**Current focus:** Two-day demo productisation sprint

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
| SURGE-PY-019 | End-to-End Optimisation Orchestrator | Complete | Connect preprocessing, candidate generation, load flow, scoring, recommendation, and presentation behind one internal call. |
| SURGE-PY-020 | MVP Demo API + End-to-End Validation | Complete | Expose the orchestrator compatibly through the existing API and verify one golden demo fixture. |
| SURGE-PY-021 | V1 Constraint Regression Coverage | Complete | Enforce the existing V1 constraint behavior with deterministic positive, rejection, and compatibility API tests. |
| SURGE-PY-022 | Constraint Fixture Provenance Labeling | Complete | Label the hand-authored constraint payload as a Python-contract fixture and document the evidence needed for verified KMZ provenance. |

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

The workflow validates project, raster, electrical, and operating-point inputs
before generation. Candidate-local electrical or presentation failures remain
traceable without erasing completed upstream results. Every evaluated
candidate contains its score and either map-ready presentation output or an
explicit packaging failure; frozen result models enforce valid status and
artifact combinations.

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

The implemented V1 endpoint preserves the Java request and legacy response
fields, runs `optimise_project`, and adds workflow status, generation,
candidate, recommendation, presentation, and failure data. A caller that omits
cable properties receives the documented 33 kV MVP compatibility profile,
whose ampacity is derived from legacy `feeder_capacity_mw`; explicit cable
configuration overrides that profile.

`POST /api/v2/optimise` exposes an explicit engineering request requiring
cable properties. Its golden fixture produces three unique valid candidates
and verifies deterministic repeated output, coverage, ranking,
recommendation, and WGS-84 GeoJSON.

### SURGE-PY-021

PY-021 adds test coverage above the frozen PY-020 MVP boundary without changing
the public contract. `optimisation-python/tests/api/test_optimise_v1.py` reuses
the deterministic constraint fixture to verify hard/soft handling,
geometry-level hard-exclusion avoidance, identical repeat responses, named
hard-buffer endpoint rejection, and unchanged uniform-cost routing when
`avoidance_geojson` is omitted.

### SURGE-PY-022

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

This sprint turns the completed engine into credible product proof. It does
not expand the engineering scope, and it does not display synthetic,
placeholder, or unsupported results as calculated output.

### Day 1 - Thursday, 13 August: make the real product path reliable

**Goal:** prove one honest path from project data to a persisted, visible
optimisation result.

| Time box | Work | Evidence |
| --- | --- | --- |
| First 2 hours | Freeze one named demo dataset and its electrical assumptions. | Versioned fixture, input checklist, and expected high-level result. |
| Next 3 hours | Verify Web GIS -> Java job API -> Python V1 -> PostGIS -> route API -> Web GIS; fix only path blockers. | A fresh run completes without manually inserting result data. |
| Next 2 hours | Remove or hide false-success behaviour and synthetic engineering outputs from the demo path. | Failures are visible and every shown value has a real source. |
| Final 1-2 hours | Write the smoke procedure and run focused checks from the correct project directories. | Another engineer can repeat the startup and smoke test. |

**Exit gate:** Python remains green (`460 passed` on Python 3.11.9); the UI
starts a real job, persists and redraws the recommended WGS-84 route after
refresh; a disconnected optimiser produces a failed state; and two identical
runs select the same candidate. Docker, missing web dependencies, and the
managed Maven cache path are known environment blockers to resolve early.

### Day 2 - Friday, 14 August: make the proof feel investable

**Goal:** communicate an engineering decision, not merely draw a line.

| Time box | Work | Evidence |
| --- | --- | --- |
| First 3 hours | Carry the rich optimiser result into the product: winner, reason, score, length, loss, loading, voltage, feasibility, and rejection reasons. | A reviewer can answer "why this route?" without reading logs. |
| Next 2 hours | Tighten running/failed/completed states, units, preliminary labels, empty states, and recommended-route map focus. | The primary workflow works without developer narration. |
| Next 2 hours | Export the real recommended-route GeoJSON and compact candidate/electrical summary; hide untrustworthy exports. | Downloads match the on-screen job and candidate. |
| Final 1-2 hours | Run available checks, perform two cold-start rehearsals, and capture the evidence pack. | Logs, screenshots, runtime, demo script, and limitations are ready. |

**Exit gate:** the golden fixture evaluates at least three distinct candidates;
the winner and rejected candidates are explained; all values have units and
come from the current run; the map, summary, and download share one job and
candidate identity; and two complete rehearsals pass.

### Saturday demonstration gate

1. Introduce the WTGs, substation, and engineering assumptions.
2. Run one job with honest progress and completion states.
3. Show candidate comparison and the recommended radial network.
4. Explain the winner using length, loss, loading, voltage, and feasibility.
5. Export the result and state the current limitations.

Ready means a fresh run needs no manual data repair, repeats its recommendation
for identical input, and displays only traceable values. Do not claim raw
terrain, parcel, ROW, ML, or production-readiness support.

### Deliberate two-day cuts

- KMZ-to-constraint provenance, Java transport, and terrain-derived costs
- ML, N-1 analysis, and automatic electrical repair
- New algorithms or a broad UI redesign
- Cloud deployment and production security hardening
- Detailed BoQ/PDF work not backed by the current run

## Post-MVP

- Project-boundary clipping, terrain-derived costs, and verified KMZ-to-Python
  constraint provenance/transport
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
