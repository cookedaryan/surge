# Python Engine Integration Plan

**Status date:** 2026-08-16
**Scope:** what has to be built to make the capabilities merged in PY-030 … PY-037 reach a user.
**Method:** direct source reading of `optimisation-python/app/` and `backend-java/src/main/` at
commit `985a580`.

---

## 1. The reframing

The obvious plan is "Java is behind, move it to v2 and catch up". That is wrong, and following it
would waste the first sprint.

Of the six capability areas merged, **exactly one becomes usable when Java moves to v2.** The rest
are not blocked on Java at all — they are unfinished at the Python edge: computed internally, never
emitted, or not switchable on.

| Capability | Computed? | Reaches the API response? | Switchable? | Usable after a v2 migration alone |
| --- | --- | --- | --- | --- |
| PY-030 cable sizing | yes | **no** — absent from `presentation/models.py` | n/a | **no** |
| PY-031 electrical repair | yes | yes — `recommended_candidate_repair_log` | n/a | **yes** |
| PY-034 land decisions | yes | **count only** — `owner_interaction_count` | request: v2 only | partly |
| PY-035 pole micro-siting | yes | via pole positions | **no** — `enabled=False`, no request field | **no** |
| PY-036/037 decision report | yes | **no endpoint at all** | n/a | **no** |
| Search caching / budgeting | yes | internal | unconfirmed | n/a |

So the work splits into three tracks, and the Python track has to lead.

---

## 2. Dependency map

```
A. Finish the Python edges  ──┐
                              ├──> C. Java consumes + persists ──> D. Surface in UI/reports
B. Java moves v1 -> v2      ──┘
                                   E. Parcel commercial data (model + entry) ──> D
```

**B is a hard prerequisite for everything on the Java side.** A and B are independent and can run in
parallel. E is independent of both and is the long pole for land features, because it needs a
migration, an ingestion path and a UI.

---

## 3. Track A — finish the Python edges

Owned by whoever wrote PY-030 … PY-037. Each item is "the capability exists but nothing outside the
module can see it".

### A1. Emit per-segment cable sizing
`PY-030` computes conductor selection per segment, but `FeederResult`
(`app/presentation/models.py:70`) has no cable field and `presentation/geojson.py` emits none.
Add the selected cable type, rating and utilisation per segment to the presentation layer and the
segment GeoJSON properties.
**Done when:** a v2 response names the conductor chosen for every segment.
**Why it matters first:** it is a bill-of-materials line item. The BOM the Java side now produces
has a natural slot for it and currently cannot fill it.

### A2. Emit the land decision, not just the count
`CandidateLandAssessment` holds per-parcel decisions — chosen instrument, present value, price
provenance, unavailable parcels. Only `owner_interaction_count` reaches the response
(`schemas/v2/optimise.py:328`). Add the per-parcel decision list and the land cost totals.
**Done when:** the response says, for each affected parcel, which instrument was selected, at what
present value, and on what price basis.

### A3. Make micro-siting reachable
`PoleMicroSitingConfig.enabled` defaults to `False` and appears in neither request schema
(`app/algorithms/pole_placement.py:89`). As shipped it can never run.
Expose it in the v2 request with its search radius and spacing, and decide the default.
**Done when:** a request can turn it on, and the response indicates whether it ran and what it
changed.
**Open question for the authors:** was off-by-default intended pending validation, or an oversight?

### A4. Expose the engineering report
`app/reporting/` now holds a substantial subsystem: `builder.py`, `decision_models.py`,
`report.py`, `limitations.py`, a `sections/` package (executive summary, economics, electrical,
land, alternatives, reasoning, recommendation, traceability) and a `renderers/` package with a
`ReportRenderer` abstraction rendering to a string — `TextRenderer` is the only implementation so
far.

**No endpoint returns any of it, on any API version.** Either include it in the v2 response or add
`GET /api/v2/.../engineering-report`, with the renderer selectable.
**Done when:** the report is retrievable over HTTP.
**This is the most under-used thing in the codebase** — an entire reporting framework, with a
pluggable renderer, that nothing outside Python can call.

### A5. Confirm search budgeting is configurable
Caching, budgeting, screening and determinism controls landed in `app/optimisation/search_*.py`.
Confirm whether beam width, budget and screening thresholds are settable per request; if not,
expose them.
**Done when:** an operator-facing "fast versus thorough" setting is possible.

---

## 4. Track B — move Java to v2

One task, and everything on the Java side waits behind it.

### B1. Repoint `PythonOptimizationClient` at `/api/v2/optimise`
`PythonOptimizationClient.java:23` calls v1. v1 is a compatibility shim: `land_context` is v2-only,
and the richer response lives there.

Work: map `CreateOptimizationJobRequest` to the v2 request shape, parse
`OptimiseProjectResponse`, handle the four-value `status`
(`SUCCESS` / `PARTIAL_SUCCESS` / `NO_FEASIBLE_CANDIDATE` / `FAILED`) — note this is richer than
v1's two-value status and the existing failure handling collapses it.

**Done when:** a run through the UI produces the same routes and poles as before, via v2, with
`PARTIAL_SUCCESS` distinguishable from `SUCCESS` in the job record.
**Risk:** this is the change most likely to regress working behaviour. It wants the golden-fixture
contract test extended before the switch, not after.

---

## 5. Track C — Java consumes and persists

Each depends on B1, and on the matching Track A item where noted.

### C1. Persist the electrical repair log *(needs B1 only)*
`recommended_candidate_repair_log` already ships in the response. Store it against the job and show
it in the decision panel — "the optimiser upgraded this cable to clear an overload" is exactly the
kind of statement the panel exists to make.
**This is the only item deliverable from a v2 migration alone.**

### C2. Persist per-segment cable type *(needs A1)*
Add to `generated_routes` (migration), populate in `RouteService`, and add a BOM column. Conductor
is a real cost line and the report currently cannot show it.

### C3. Persist land decisions *(needs A2 + E1)*
Store the per-parcel chosen instrument and present value against the job, so the BOM's parcel table
can report what was actually decided rather than only area and a rate.

### C4. Surface pole micro-siting results *(needs A3)*
If micro-siting moves poles, the decision panel should say so and by how much — otherwise pole
positions change between runs with no explanation.

---

## 6. Track D — surfacing

### D1. Extend the BOM report with conductor and land decisions
The report rebuilt on 2026-08-15 already has run parameters, feeder rollup, per-segment schedule,
pole schedule and parcel impact. Conductor per segment slots into the segment schedule; the chosen
land instrument and PV slot into the parcel table.

### D2. Decide the authoritative report — and do it now
There are now two reporting subsystems, and both are still growing:

- **Java** — `PdfReportService` and `ReportService`, rebuilt 2026-08-15: run parameters, feeder
  rollup, per-segment schedule with coordinates, full pole setting-out schedule, parcel impact.
  Renders PDF and CSV, and is wired to the export buttons.
- **Python** — PY-036/037, still landing as of `993c71a`: recommendation reasoning, alternatives,
  rejected candidates with causes, economics, land, traceability, plus a `ReportRenderer`
  abstraction.

Python is now heading toward owning rendering as well as reasoning, which makes this a decision to
take deliberately rather than discover. Two implementations of one answer is precisely the failure
already on record for right-of-way area, where a PostGIS query and `ParcelEngineeringExposure`
compute the same quantity differently.

**Recommendation:** Python owns the *reasoning* — it has the candidates, the deltas and the reasons
a candidate lost, none of which Java can reconstruct. Java owns the *document* — it has the
project, the assets, the coordinates and the export path. Java should render Python's report rather
than deriving a second one, and the Python `TextRenderer` should be understood as a debugging aid
rather than the delivery format.

Whichever way it goes, it should be decided before either subsystem grows further.

### D3. Show owner interactions in the UI
Owner-contact count is already a scoring objective. It should be visible on the decision panel and
in scenario comparison, or nobody can tell that a scenario chose a longer route to talk to fewer
people.

---

## 7. Track E — parcel commercial data

The long pole. Nothing in the land engine produces a real answer without this.

### E1. Extend the parcel model
Migration adding, in priority order:
1. **`owner_id`** — a stable owner identity. Without it, owner-contact minimisation counts parcels
   and calls them owners, and still returns a number.
2. `availability_status` — `AVAILABLE` / `NEGOTIABLE` / `UNAVAILABLE` / `UNKNOWN`.
3. Transaction options — purchase / lease / easement, each with upfront cost, annual cost, term
   years, price date and a quoted-versus-estimated flag.

### E2. Ingestion
KMZ import carries geometry and sometimes a name. Decide how commercial data arrives — a CSV keyed
on parcel id is probably enough and avoids touching the KMZ path.

### E3. Admin UI
Somewhere to set owner identity, availability and terms per parcel, and to see which parcels are
missing data. An engine that models `UNKNOWN` price status honestly is only useful if someone can
correct it.

### E4. Send `land_context` from Java *(needs B1 + E1)*
Build the context from the extended parcel data and include it in the v2 request.

---

## 8. Suggested order

1. **B1** (v2 migration) and **A1** (emit cable sizing) — in parallel, different people.
2. **C1** (repair log) — lands as soon as B1 does, and proves the migration end to end on something
   small.
3. **A2**, **A4**, **A3** — the remaining Python edges.
4. **E1**, **E2**, **E3** — parcel data; long lead time, start early even though it lands later.
5. **C2**, **C3**, **E4** — Java consumption.
6. **D1**, **D2**, **D3** — surfacing.

Span-versus-buy is deliberately absent: it needs span-dependent structure cost, conductor physics
and terrain data first. See `Land Acquisition and Route Decision Engine.md` §4.

---

## 9. Verification notes

- **CI was off while all of this merged.** `.github/` was deleted and gitignored; twenty-six
  commits landed with no automated verification. Restored at `9a714ee`, but the Python job's first
  run against this work has not been seen yet. Check it before planning on top of these modules.
- The golden-fixture contract test should be extended **before** B1, not after.
- Three of the four CI jobs were run locally against the current tree (227 Java tests, 50 frontend
  tests plus build, all three container images). The Python job could not be reproduced locally —
  no 3.11 environment on the machine used.
