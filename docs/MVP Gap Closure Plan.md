# MVP Gap Closure Plan

**Status date:** 2026-08-15
**Author context:** written after a full functional pass through the running
stack (Docker Compose, real Uravakonda KMZ import, live optimisation runs)
and direct source verification of every claim below — not derived from
re-reading the older planning docs alone.
**Relationship to other docs:** `whats-next.md`, `Surge MVP Ticket Plan.md`,
and `MVP - Minimum Viable Product.md` define what SURGE's MVP *is*. This
document does not redefine that scope. It replaces their now-stale "current
state" sections with a verified baseline (§1) and gives a dependency-ordered,
implementation-level plan for what is left (§2–§6). Where this document's
findings contradict an older doc's status claims, this document is correct as
of 2026-08-15 — the older docs were written mid-sprint (2026-08-12/13) and
several items they list as outstanding have since shipped, while at least two
items they implicitly assumed were real turned out to be inert.

---

## 1. Verified baseline — what is actually done

Confirmed by direct code reading and/or a live end-to-end run this session,
not by trusting prior status notes.

### 1.1 Fully working, verified live
- KMZ/KML upload → preview → classify → confirm → persist (`AssetService`,
  `AssetClassifier`, `KmzGeoJsonConverter`), verified against the real
  Uravakonda survey file (95 WTGs across 6 statuses, 9 substations, 2
  restricted areas).
- Optimisation dispatch: Java queries persisted WTGs/substations, builds a
  proximity-based primary-substation selection, and calls the Python engine.
- Constraint transport: `OptimizationJobService.buildAvoidanceGeoJson()`
  ([OptimizationJobService.java:290](../backend-java/src/main/java/com/power/surge/service/OptimizationJobService.java)) sends reference lines, parcels, and
  restricted areas as a real GeoJSON `FeatureCollection` with
  `constraint_type`/`routing_mode`/`buffer_m`/`cost_weight` to Python on every
  job.
- Pole placement is wired end-to-end: Python places and network-deduplicates
  poles on the recommended candidate, Java persists them
  (`GeneratedPole`, `PoleService`), and the frontend renders four pole classes
  (terminal/angle/tangent/junction) as independent map layers.
- Max pole span, system voltage (kV), and feeder capacity from the UI reach
  Python (`pole_config`, `electrical_params.nominal_voltage_kv`) instead of
  being silently hardcoded.
- Per-segment and per-job pole counts are real (`segment_id` ↔
  `connected_route_ids` linkage, V9 migration) instead of a `length / 150m`
  guess.
- The "Why this route?" decision panel surfaces real candidate comparison,
  disqualification reasons, electrical summary, and spatial-constraint summary
  from `resultSummaryJson`.
- Failed/no-route jobs are unmistakable in the UI (red failure card with
  reasons) — no silent fallback to a stale or demo route.
- Scenario comparison (`ReportService.getScenarioComparison`) reads real
  completed jobs per scenario label and omits scenarios that were never run,
  instead of four hardcoded numbers.
- The frontend proactively blocks "Run Optimisation" with a specific reason
  (no optimisable WTGs / no substation / multiple unresolved substations)
  instead of letting the call fail server-side.
- CI (`.github/workflows/ci.yml`) already builds/tests Java (`mvnw verify`),
  Python (`ruff`, `mypy`, `pytest`), the frontend (`npm run build`), and all
  Docker images on every push/PR. Phase 0 of the Obsidian MVP plan
  ("make the stack testable") is materially done on the backend/infra side.
- Map/BOM/elevation-drawer stacking bug (BOM strip and elevation profile
  rendering behind the Leaflet map) fixed 2026-08-15.

### 1.2 Two findings that reorder everything below

**Finding A — the four optimisation scenarios do nothing.**
The scenario dropdown (`Balanced` / `Minimum Cost` / `Minimum Land Impact` /
`Minimum Environmental Impact`,
[OptimizationPane.tsx:12-14](../web-map-next/src/features/optimization/OptimizationPane.tsx)) only sets a display-label string.
`OptimizationJobService` always defaults `capexWeight`/`lossesWeight` to
`0.5`/`0.5` ([OptimizationJobService.java:123-124](../backend-java/src/main/java/com/power/surge/service/OptimizationJobService.java)) regardless of which
label was picked, and — critically — `PythonOptimisationRequest` has no field
for either weight at all, so they are never sent to Python in the first
place. Python's V1 endpoint (the one Java actually calls) defaults
`scoring_weights` to a fixed `ScoringWeightsRequest()`
(`route_length_weight=0.4, electrical_loss_weight=0.25,
cable_loading_weight=0.20, voltage_margin_weight=0.15`,
[v2/optimise.py:86-89](../optimisation-python/app/schemas/v2/optimise.py)) on every call. Running the same
project under all four scenario labels today produces byte-identical
candidate scores, byte-identical routes, and byte-identical pole layouts.
This is the literal MVP release gate from the Obsidian plan ("run each of the
four deterministic scenarios ... their displayed differences come from real
inputs/results") and from `Surge MVP Ticket Plan.md` §14 ("show different
winners across scenarios") — currently false.

**Finding B — every project/job endpoint is unauthenticated.**
`SecurityConfig.java:44-51` has
`.requestMatchers(..., "/api/v1/projects/**").permitAll()`. JWT auth exists
and is enforced on other paths, but every project, asset, optimisation job,
route, pole, and report endpoint bypasses it entirely — there is no
ownership check anywhere in the request path. Any caller can read or mutate
any project. `MVP Execution Plan - Frontend & Java.md` flags this explicitly:
*"`permitAll` on all project paths is not safe for an external MVP."*

### 1.3 Confirmed-but-not-yet-fixed bugs (identified earlier this session)
- BOM electrical losses use a `length_m × 0.005 kW/m` heuristic
  (`RouteService.extractBigDecimal` fallback) instead of Python's real
  Pandapower `active_loss_mw`, because the property name/unit Python emits
  (`active_loss_mw`, MW) never matches what Java looks for
  (`electricalLossesKw`/`electrical_losses_kw`, kW). The "Why this route?"
  panel shows the correct number (259.9 kW); the BOM strip/report shows the
  wrong one (516.46 kW) for the same job.
- Parcel ROW/compensation area in the engineering BOM report uses each
  parcel's full polygon area rather than the real route-corridor overlap.
  Python already has a working, tested overlap engine for this
  (`app/gis/row_analysis.py`, SURGE-PY-011) that computes real
  buffer∩parcel intersection area — it is referenced from
  `result_builder.py`/`engineering_metrics.py` for the *decision-summary*
  path, but `ReportService`'s BOM/PDF parcel-impact table does not consume
  it and instead falls back to the naive full-area figure.

---

## 2. Tier 1 — Make the four scenarios real

**Why first:** this is the single largest gap between "looks like a demo"
and "is the MVP," it's explicitly called out as a must-have in three
different planning docs, and — per the investigation below — it is smaller
than it looks: the scoring-weight wiring already exists in Python and only
needs to be *connected*, not built.

### 2.1 Design: what actually drives each scenario

Python's candidate scorer (`CandidateScoringConfig`,
[scoring_models.py:20-24](../optimisation-python/app/optimisation/scoring_models.py)) ranks already-generated candidates on
exactly four metrics: `route_length`, `electrical_loss`, `cable_loading`,
`voltage_margin`. There is no "land impact" or "environmental impact" metric
in that scorer, and adding one is explicitly deferred to P1 in
`whats-next.md` §5 ("include a spatial-impact metric in cohort ranking ...
only after the end-to-end path is green"). Do not build a fifth scoring
metric for this pass — use the two mechanisms that already exist:

| Scenario | Mechanism | What changes |
| --- | --- | --- |
| **Balanced** | Scoring weights only | Send the Python defaults explicitly: `0.4 / 0.25 / 0.20 / 0.15` (route length / electrical loss / cable loading / voltage margin). |
| **Minimum Cost** | Scoring weights only | Shift weight toward `route_length_weight` (route length is the current proxy for CAPEX until a real cost model exists — say goes to `0.70`, spreading the remaining `0.30` across the other three proportionally). |
| **Minimum Land Impact** | Routing-cost bias | Raise `cost_weight` on `parcel` constraint features in `buildAvoidanceGeoJson()` so A* prefers routes crossing less/cheaper land *before* candidates are even scored. Leave scoring weights at Balanced defaults. |
| **Minimum Environmental Impact** | Routing-cost bias | Raise `cost_weight`/`buffer_m` on `restricted_area` and any forest/environmental reference-line constraints the same way. |

This keeps land/environmental differentiation inside Java's existing
constraint-transport ownership boundary (already real, already tested) and
keeps cost/electrical differentiation inside Python's existing scoring
config (already real, already validated, just unused by V1 callers).

### 2.2 Implementation steps

1. **Python — none required for the scoring axis.** `ScoringWeightsRequest`
   and `CandidateScoringConfig` already validate weights sum to `1.0` and
   already flow through `legacy_mapping.py:40`
   (`scoring_weights=payload.scoring_weights`) on the V1 endpoint. Confirm
   this with one manual call before touching Java: POST `/api/v1/optimise`
   twice with the same project, once omitting `scoring_weights` and once
   with a skewed vector, and diff the `recommendation`/ranked candidates.
2. **Java DTO — add the missing field.**
   `dto/client/python/PythonOptimisationRequest.java` needs a
   `scoringWeights` (→ `scoring_weights`) field: a small record/map with the
   four weight doubles. Follow the existing pattern used for `poleConfig`.
3. **Java — define the scenario → weight table.** In
   `OptimizationJobService`, add a small deterministic lookup (a private
   `Map<String, ScoringWeights>` or switch on `scenario`) for the four known
   labels, defaulting unknown/null scenario strings to Balanced. Do not
   invent a fifth "custom weights" UI control in this pass — keep the four
   fixed presets from `Surge MVP Ticket Plan.md`/`Scope.md`.
4. **Java — bias `buildAvoidanceGeoJson()` by scenario.** Thread the
   `scenario` string into `buildAvoidanceGeoJson(UUID projectId, String
   scenario)`. For `Minimum Land Impact`, multiply the parcel loop's
   `cost_weight` by a fixed factor (e.g. `3.0`×) when one isn't already set
   from a real land rate; for `Minimum Environmental Impact`, do the same for
   `restricted_area` features' effective cost (or `buffer_m`, whichever the
   Python constraint layer weights more strongly for soft features — verify
   against `app/gis/constraints.py` before picking). Leave `Balanced` and
   `Minimum Cost` at the existing unscaled values.
5. **Frontend — no new UI**, the scenario dropdown already exists and
   already reaches Java (`OptimizationPane.tsx:55`). No changes needed here
   beyond confirming the selected label round-trips unchanged (it does).
6. **Regression test — the actual acceptance bar.** Add one Java service
   test and one Python integration test that run the *same* fixture project
   under two different scenario labels and assert the results differ
   (different `recommendation.recommended_scenario_id`, different
   `total_route_length_m`, or different ranked order — any one is sufficient
   proof of differentiation). This test is the concrete, checkable
   replacement for "scenarios are real."

### 2.3 Acceptance criteria
- Running the golden Uravakonda project under all four scenario labels
  produces at least two distinct outcomes (route length and/or recommended
  candidate differ) between at least one pair of scenarios.
- `ScenarioComparisonResponse` shows genuinely different numbers per
  scenario row, not just different labels on identical numbers.
- A new automated test fails if scenario weighting regresses to a no-op.

**Estimated effort:** 0.5–1 day (mostly Java DTO/service wiring; Python side
is already built).

---

## 3. Tier 2 — Close the authorization gap

**Why second:** every other feature sits behind this. Shipping Tier 1
before this is fine (still local/demo-safe), but nothing here should be
exposed beyond a trusted network until it's done.

### 3.1 Implementation steps
1. **Confirm the data model.** Check whether `Project` already has an
   owner/user relation (`created_by`, a join table, etc.). If not, add a
   migration: `owner_id` (FK to the users table) on `projects`, backfilled to
   a system/admin user for existing rows.
2. **Remove the blanket bypass.** In `SecurityConfig.java:44-51`, drop
   `"/api/v1/projects/**"` from the `permitAll()` matcher list. Everything
   under it should require authentication by default (it will, since
   `.anyRequest().authenticated()` already covers the rest).
3. **Add ownership enforcement**, not just authentication. Authentication
   alone (any logged-in user can see any project) does not satisfy the doc's
   requirement ("project ownership/role authorization"). Add either:
   - a `@PreAuthorize` check backed by a small ownership-lookup service, or
   - repository-level scoping (`findByIdAndOwnerId`) used consistently in
     every controller that takes a `projectId` path variable.

   Cover: `ProjectController`, `ProjectAssetController`,
   `OptimizationJobController` (and its route/pole sub-resources),
   `ReportController`.
4. **Decide on a demo/admin bypass explicitly** (many small teams want an
   "admin sees everything" role) — implement it as a real role check, not as
   a second `permitAll()`.
5. **Tests.** Add a Java integration test: user A creates a project, user B
   authenticates and attempts to read/mutate it → expect `403`/`404` (pick
   one convention and use it everywhere — `404` avoids leaking existence).

### 3.2 Acceptance criteria
- No path under `/api/v1/projects/**` is reachable without a valid JWT.
- A second authenticated user cannot read, run jobs on, or export reports
  from a project they do not own.
- Existing single-user demo flows (login → import → run → view) still work
  unchanged for the owning user.

**Estimated effort:** 0.5–1 day, depending on whether project ownership
already exists on the `Project` entity (check first — this may already be
half-done).

---

## 4. Tier 3 — Fix the two known data-correctness bugs

Both were diagnosed to the exact line earlier this session; this section is
the fix, not further investigation.

### 4.1 BOM electrical losses use the wrong number
- **Root cause:** `optimisation-python/app/schemas/legacy_mapping.py`'s
  `_legacy_route_collection` passes through Python's raw property
  `active_loss_mw` (megawatts) unchanged. Java's
  `RouteService.extractBigDecimal` looks for `electricalLossesKw` /
  `electrical_losses_kw` — a different name *and* a different unit — never
  matches, and silently falls back to the `length_m × 0.005` heuristic.
- **Fix:** either (a) have Python additionally emit a correctly-named,
  correctly-unit'd property (`electrical_losses_kw = active_loss_mw *
  1000`) alongside the existing one for backward compatibility, or (b) update
  `RouteService.extractBigDecimal`'s lookup keys to match Python's actual
  property name and convert MW→kW in Java. Prefer (a): it's additive on the
  Python side and doesn't risk breaking any other consumer of
  `active_loss_mw`.
- **Verify:** re-run the Uravakonda job; BOM losses should read ~259.9 kW,
  matching the "Why this route?" panel exactly (both must come from the same
  Pandapower result now).

### 4.2 Parcel ROW/compensation uses full parcel area, not real overlap
- **Root cause:** `ReportService`'s BOM/PDF parcel-impact table computes
  `affectedAreaM2` from each `CadastralParcel`'s whole stored polygon area,
  not the actual route-corridor intersection. `app/gis/row_analysis.py`
  already computes the real per-parcel overlap area
  (`Area(Buffer(route, ROW_width/2) ∩ parcel)`) and is wired into the
  decision-summary path (`spatialConstraintSummary.affected_parcel_count` /
  `affected_parcel_overlap_length_m` in `resultSummaryJson`) — but that
  summary carries only counts/lengths, not per-parcel area, and
  `ReportService` never consumes it at all.
- **Fix:** extend the Python presentation result to include per-parcel
  overlap area (`row_analysis.py` already computes this internally — expose
  it in the same result object `result_builder.py` already builds from), and
  have Java's `ReportService.generateBomReport`/`generateBomCsv` read that
  real per-parcel figure instead of calling
  `CadastralParcel.getGeometry().getArea()` directly.
- **Verify:** on a project where the recommended route actually clips a
  parcel, the BOM parcel-impact table's affected area should be a small
  fraction of that parcel's full area, not the whole polygon.

**Estimated effort:** 0.5 day each (roughly 1 day total) — both are
localized name/wiring fixes against already-correct underlying data, not new
algorithms.

---

## 5. Tier 4 — Release-readiness gaps

These don't block a working demo but block calling it done per the
project's own "Definition of Sunday/MVP done" checklists.

### 5.1 Frontend has no test runner at all
- **Current state:** confirmed — no `*.test.*`/`*.spec.*` files exist under
  `web-map-next/src`, and `package.json` has no test script.
- **Steps:** add Vitest + React Testing Library (matches the Vite toolchain
  already in place). Add a `test` script to `package.json` and a CI step in
  `.github/workflows/ci.yml`'s `frontend` job. Write a small smoke suite
  covering: login gate, project selector populates from the API, the "Run
  Optimisation" button's blocker logic (the run-blocking work done earlier
  this session is exactly the kind of logic worth a unit test), and layer
  toggle state.

### 5.2 No browser end-to-end test
- **Steps:** add Playwright (or reuse the same in-app Browser tooling used
  manually this session, scripted). One test: login → select/create project
  → upload the golden KMZ → preview/confirm → run optimisation → assert the
  map renders routes and poles → download a report. This directly
  operationalizes `whats-next.md` §9's "Full product" test list and
  `Surge MVP Ticket Plan.md`'s Saturday demonstration gate.

### 5.3 No golden-fixture contract test tying constraint transport + pole persistence together
- **Steps:** add one Java `@SpringBootTest` (or slice test) that creates a
  project with a known parcel/restricted-area fixture, runs a job against a
  stubbed/recorded Python response, and asserts (a) the constraint
  `FeatureCollection` Java sent contains the expected `constraint_type`s, and
  (b) the poles/routes returned are persisted and retrievable by job ID.
  `whats-next.md` §6 item 9 asks for exactly this ("Add service/controller
  tests proving imported constraints are sent to Python and returned
  pole/route output remains associated with the same job").

**Estimated effort:** 1–1.5 days total across all three.

---

## 6. Explicitly out of scope for this pass

Carried forward unchanged from `whats-next.md` §5/§11 and
`Surge MVP Ticket Plan.md`'s "Explicit post-MVP work" — do not pull these
forward while Tiers 1–4 are open:

- A fifth "spatial impact" scoring metric (land/environmental scenarios use
  the routing-cost-bias mechanism instead, per §2.1).
- ML/Pareto ranking, N-1 analysis, automatic electrical repair.
- Terrain/DEM slope costs, conductor sag/structural pole design.
- Detailed BoQ, additional export formats beyond the existing CSV/PDF.
- Production security hardening beyond the ownership check in Tier 2 (rate
  limiting, secrets rotation, etc.).
- Live third-party road/parcel data acquisition.

---

## 7. Suggested execution order

1. **Tier 1** (scenarios real) — highest product-credibility impact, and the
   Python half is already built, so it's also the cheapest of the big items.
2. **Tier 3** (BOM losses + ROW area fixes) — small, independent, already
   fully diagnosed; can be done in parallel with Tier 1 by a second
   contributor if available.
3. **Tier 2** (authorization) — must land before any external/non-local
   demo, but doesn't block continued local development of Tiers 1/3/4.
4. **Tier 4** (tests) — do incrementally alongside 1–3 rather than as one
   final push; each new behavior in Tiers 1–3 should ship with the test that
   proves it, per this repo's own CI gates.

## 8. Definition of done for this plan

- All four scenario labels produce measurably different results on the
  golden Uravakonda project, backed by an automated regression test.
- No `/api/v1/projects/**` endpoint is reachable without authentication and
  ownership checks.
- BOM losses and parcel-impact figures match the real Pandapower/ROW-overlap
  values shown elsewhere in the same job's results.
- `npm run test` (frontend), `./mvnw verify` (Java), and `pytest` (Python)
  all stay green in CI throughout, plus one new browser E2E test passes.
- Every number above was verified against a live run, not asserted from a
  planning document — the same standard this document was held to.
