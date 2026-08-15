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

## 2. Tier 1 — Make the four scenarios real ✅ DONE (2026-08-15)

> **Completed.** Implemented on `feat/mvp-tier1-real-scenarios`. See §2.4 for the
> verified result and the one design correction made during implementation.

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

### 2.4 Outcome and the one design correction

**Correction to §2.1.** The table above assigned *Minimum Cost* to scoring
weights alone. Verification showed that would have been a no-op: on the real
Uravakonda data only one of three candidates survives electrical screening
(`"Only one candidate was electrically feasible"`), and a sole eligible
candidate wins under every possible weight vector. Every scenario therefore
also carries a cost-surface bias, so the candidate routes differ before scoring
runs at all. Two further constraints discovered while reading the engine:

- Soft-constraint cost is **additive to the raster**
  (`costs[finite_mask] += layer.cost_weight`, `constraints.py:217`), with a
  documented default of `20.0` when a feature carries no explicit cost.
- Hard exclusions **must not** carry `cost_weight` — Python raises on it
  (`constraints.py:67`) — so the environmental scenario expresses its
  preference as extra `buffer_m` clearance instead, added on top of Python's
  own `avoidance_buffer_m` default of `10.0` m so it can never resolve to
  *less* clearance than the baseline.

**As-built profile table** (`ScenarioProfile.java`):

| Scenario | Weights (len/loss/load/volt) | Constraint bias |
| --- | --- | --- |
| Balanced | 0.40 / 0.25 / 0.20 / 0.15 | none — imported values used as-is |
| Minimum Cost | 0.70 / 0.12 / 0.10 / 0.08 | soft crossings ×0.5 |
| Minimum Land Impact | 0.40 / 0.25 / 0.20 / 0.15 | parcels ×3 |
| Minimum Environmental Impact | 0.40 / 0.25 / 0.20 / 0.15 | watercourses ×3, restricted +25 m clearance |

Balanced at a 1.0 multiplier reproduces the previous behaviour exactly, so the
default scenario is not a regression.

**Verified live** against `Uravakonda PCN Route Test` (95 WTGs / 38 optimisable,
45 reference lines, 1 parcel, 2 restricted areas):

| Scenario | Length (m) | Poles | Losses (kW) |
| --- | ---: | ---: | ---: |
| Balanced | 69,991.4 | 606 | 324.18 |
| Minimum Cost | 68,476.4 | 581 | 317.29 |
| Minimum Land Impact | 69,933.6 | 601 | 324.12 |
| Minimum Environmental Impact | 70,142.2 | 608 | 324.82 |

Four distinct lengths, four distinct pole counts, four distinct loss figures —
and the ordering is physically sensible: Minimum Cost is the shortest and
cheapest because it accepts crossings, Minimum Environmental Impact is the
longest because it detours around the widened clearance.

**Also fixed in passing:** `OptimizationJobResponse` never exposed the job's
`scenario`, so the UI could not show which scenario produced a result. Added
the field and surfaced it in the decision card ("Optimised for …").

**Test coverage added:** `ScenarioProfileTest` (17 tests: weights total 1.0 per
the Python contract, per-weight range, no two scenarios share a configuration,
every scenario biases the surface, direction-of-effect per scenario, fallback
and casing) and `OptimizationJobServiceTest.eachScenarioDispatchesADistinct
OptimisationRequest` (captures all four dispatched payloads and asserts they
differ). Both were mutation-tested: forcing `forScenario()` to always return
Balanced fails 6 of them, so the guard has teeth. Full suite: 153 Java tests
green, frontend typecheck and build clean.

---

## 3. Tier 2 — Close the authorization gap

> **Scope changed after discussion (2026-08-15).** SURGE is used by a handful of trusted
> colleagues who all need full access, so per-project ownership was dropped as
> over-engineering: it would have meant a migration, a backfill, and enforcement
> threaded through 42 endpoints to police a boundary that does not exist in the
> organisation. Individual accounts were kept over a single shared login — they cost
> the same to build and preserve a usable audit trail. Tier 2 is now three phases:
>
> - **Phase 1 — authentication (✅ done, see §3.3)**
> - **Phase 2 — admin panel (✅ done, see §3.4)**
> - **Phase 3 — audit coverage (✅ done, see §3.5)**

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
half-done). *Superseded: ownership was dropped, see the note at the top of §3.*

### 3.3 Phase 1 outcome — authentication (done 2026-08-15)

**What was closed**

1. `/api/v1/projects/**` removed from `permitAll()`. That single entry had been
   exempting 9 controllers and 42 project-scoped endpoints.
2. `POST /api/v1/auth/register` restricted to administrators, in both the filter
   chain and a `@PreAuthorize` on the method. This mattered more than the first
   item: registration was world-open, so anyone could have created an account,
   received a valid token, and walked back in legitimately. Locking the project
   routes without this would have been security theatre.
3. `seedDemoUsers()` replaced with `seedBootstrapAdmin()`. The old version ran on
   every startup and re-encoded the password each time, so **any credential change
   was silently reverted on the next restart** — which would have broken the admin
   panel's password-reset feature on day one, and silently undone manual database
   edits. The replacement creates the account only when missing, never overwrites,
   takes credentials from configuration, and warns when the built-in default is
   still in use.

**Three problems found while verifying, each fixed**

- *Anonymous requests returned 403, not 401.* Added an `HttpStatusEntryPoint` so a
  missing session is distinguishable from a forbidden action — the UI needs that to
  send an expired session to the login screen rather than showing a permission error.
- *Denied requests returned 401 even when authenticated.* `sendError()` makes the
  container re-dispatch to `/error` through the same filter chain; that dispatch
  carries no credentials, so it was itself rejected and the entry point overwrote
  the real 403. Fixed by permitting `DispatcherType.ERROR`. Worth remembering:
  **MockMvc performs no ERROR dispatch, so the test suite showed 403 while the
  running server returned 401** — only live verification caught it.
- *A 401 masqueraded as "no projects".* `listProjects` swallowed errors into an
  empty array, which made `ProjectSelector` auto-create a replacement project, and
  `createProject` fabricated a fake project with a client-generated id when the API
  call failed. Enabling auth made that path reachable on every pre-login render.
  All three were removed: failures now propagate, auto-create requires an
  authenticated caller, and no synthetic project is ever invented. This was the
  "simulated success after an API failure" the Obsidian MVP plan explicitly forbids.

**Client changes**

- Job progress moved from `EventSource` to a fetch-based stream. `EventSource`
  cannot attach an `Authorization` header, and the alternative — a token in the
  query string — would leak the credential into access logs, browser history and
  referrer headers. The progress endpoint is now authenticated like everything else.
- A 401 from any transport clears the token and returns to the sign-in screen.
- Successful sign-in invalidates cached queries, so the workstation loads without a
  manual page reload.

**Verified against the running stack**

| Caller | Endpoint | Result |
| --- | --- | --- |
| anonymous | `/api/v1/projects` | 401 |
| anonymous | `/api/v1/projects/{id}/jobs/{jid}/progress` | 401 |
| anonymous | `/api/v1/audit-logs` | 401 |
| anonymous | `POST /api/v1/auth/register` | 401 |
| engineer | `/api/v1/projects` | 200 |
| engineer | `POST /api/v1/auth/register` | 403 |
| admin | `POST /api/v1/auth/register` | 201 |
| anyone | `/api/v1/health` | 200 |

The admin password survived a container restart, confirming the seed no longer
overwrites. A full UI pass — sign in, project list loads without a reload, run an
optimisation, read the decision card — works end to end, and the fetch stream was
confirmed to receive events with a valid token and to sign the operator out on a
rejected one.

**Tests:** `SecurityBoundaryTest` (11 tests) runs with the security filters *on*,
unlike every other controller test (`addFilters = false`), and mints real tokens
through `JwtTokenProvider`. `AuthServiceBootstrapTest` (3 tests) pins the
never-overwrite contract. Suite: 167 Java tests green, frontend build clean.

**Known gap:** roles are enforced only for registration. `ROLE_VIEWER` still has
write access everywhere else — deliberate for now, and the natural companion to the
Phase 2 admin panel.

### 3.4 Phase 2 outcome — admin panel (done 2026-08-15)

**API** — `/api/v1/admin/users`, with a class-level `@PreAuthorize("hasRole('ADMIN')")`
so a route added later is restricted by default rather than by remembering to
annotate it:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/admin/users` | List accounts |
| `POST` | `/admin/users` | Provision an account |
| `PATCH` | `/admin/users/{id}` | Change role and/or suspension state |
| `POST` | `/admin/users/{id}/password` | Set a new password |

`PATCH` treats `null` fields as "leave unchanged", so role and suspension can be
changed independently. Password reset is a separate route so it is audited as its
own distinct event.

**Suspension rather than deletion.** Migration `V11` adds `users.enabled`. Deleting
an account would leave its audit-log entries naming someone who can no longer be
looked up; suspending keeps the history interpretable while blocking sign-in
immediately. `AuthService.login` rejects a disabled account *after* the password
check, so a suspended account is not distinguishable from a wrong password, and
records a `USER_LOGIN_DENIED` event so a locked-out colleague's attempts are visible.

**Two lockout invariants**, enforced in the service rather than the UI because the
UI is not the only possible caller:

- an administrator cannot suspend or demote *their own* account; and
- the last enabled administrator cannot be suspended or demoted.

Recovering from zero administrators would need direct database access — exactly what
this panel exists to avoid.

**A real bug this surfaced.** Method-level authorization failures were being reported
as **500 Internal Server Error**: `@PreAuthorize` throws inside the dispatcher, and
`ApiExceptionHandler`'s catch-all `@ExceptionHandler(Exception.class)` swallowed it
before Spring Security could translate it. Every `@PreAuthorize` in the codebase was
affected, including the Phase 1 annotation on `register` (masked there only because a
filter-level rule denied it first). Added an explicit `AccessDeniedException` handler
returning 403.

**Session restore.** The auth store inferred "signed in" from a token existing in
storage, but username and role lived only in memory — so after a reload an
administrator came back with no role and silently lost the admin tab. The app now
resolves the account from `/auth/me` on load, which revalidates the token at the same
time and takes the role from the server rather than trusting local storage.

**Verified against the running stack:** create → sign in as the new account → suspend
→ sign-in refused (400) → reset password → reinstate → sign in with the new password
(200) while the old one is refused (400). Self-suspend and self-demote are refused
with readable messages and the account is left untouched; a non-administrator gets 403
from every route. Driving a suspension from the UI updated the database, blocked that
user's next sign-in, and wrote `USER_SUSPENDED` against **the acting administrator**,
which is the "who did what" the panel was for.

**Tests:** `UserAdminServiceTest` (12) covers creation, duplicate rejection, both
lockout invariants, audit-on-change, no-audit-when-unchanged, and that a reset stores
a hash and never logs the password. `SecurityBoundaryTest` grew 3 cases for the new
routes. Suite: 182 Java tests green, frontend build clean.

**Note:** a malformed UUID in any path still returns 500 via the catch-all rather than
400. Pre-existing across every `{id}` route, not introduced here — worth a small
`MethodArgumentTypeMismatchException` handler when convenient.

### 3.5 Phase 3 outcome — audit coverage (done 2026-08-15)

Before this, `recordAudit` was called from exactly two places in the whole codebase, so
the log could say who signed in and nothing about what they did.

**Attribution without plumbing.** `AuditLogService.record(action, resourceType,
resourceId, details)` resolves the acting user from the security context. Threading a
username through every service signature is what leads to a log that covers two call
sites instead of the application. Two properties matter:

- It runs in its own transaction (`REQUIRES_NEW`), so a record survives even when the
  surrounding work rolls back — a failed import or rejected job is exactly what you
  want in the log.
- A storage failure is swallowed and reported to the application log. Audit logging is
  observability, not business logic; it must never take down the operation it records.

**Now instrumented:** project created, project updated (naming the rename explicitly),
assets imported (both the reviewed preview/commit path and the one-step upload), an
optimisation completing or failing, and report exports.

**Deliberately not instrumented:** `generateBomReport`, which also backs the
always-visible BOM panel. Auditing it would bury real actions under a stream of page
renders. Only taking data *out* of the system — the CSV and PDF exports — is recorded.

**Details carry the facts, not just the verb.** "Imported a file" is useless six weeks
later; "95 WTG, 9 substation, 2 restricted" explains why a project's results changed.
Likewise the optimisation entry names the scenario and turbine count, so a change in
output has a visible cause.

**One correction during verification.** The KMZ upload endpoint converts to GeoJSON
before reaching the service, so it was logging "Direct GeoJSON import" — describing the
internal plumbing rather than what the operator did. It now records the actual entry
point and filename.

**A real trail from a real run** (create project → upload the Uravakonda KMZ → run an
optimisation → export a PDF):

```text
admin | USER_LOGIN              | Successful user authentication
admin | PROJECT_CREATED         | Created project 'Audit Trace v2'
admin | ASSETS_IMPORTED         | One-step KMZ/KML upload of 'Uravakonda WTG Substation
                                  Restricted.kmz' into 'Audit Trace v2': 106 features
                                  (95 WTG, 9 substation, 0 tower, 0 line, 0 parcel,
                                  2 restricted)
admin | OPTIMIZATION_COMPLETED  | Scenario 'Minimum Environmental Impact' completed for
                                  project 'Audit Trace v2' (38 optimisable WTG, 33 kV)
admin | REPORT_EXPORTED         | Exported executive PDF report for project
                                  'Audit Trace v2'
```

**Audit pane** now shows the entry count, colours by consequence (failures and
suspensions in red, creations in accent, changes in amber) so a problem stands out when
skimming, and shows a date for entries older than today rather than a bare time.

**Tests:** `AuditLogServiceTest` gains attribution from the security context, the
anonymous fallback, and proof that a storage failure does not propagate. Suite: 185
Java tests green, frontend build clean.

**Known limits:** the endpoint returns the most recent 50 entries with no pagination,
filtering or retention policy — fine at this scale, but worth revisiting before the log
becomes long enough to hide something. There is still no DELETE endpoint anywhere in
the application, so no deletion auditing was needed.

---

## 4. Tier 3 — Fix the two known data-correctness bugs ✅ DONE (2026-08-15)

> **Completed.** Both fixed and verified against the running stack; see §4.3 for the
> outcome and for two things that turned out to be worse than recorded below.

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

### 4.3 Outcome (done 2026-08-15)

**Losses — fixed as planned.** Python now emits `electrical_losses_kw` alongside
`active_loss_mw` in the segment properties. Java already accepted that key, so no
backend change was needed at all. Verified on a fresh run of the reference project:
BOM losses **324.18 kW**, exactly matching Pandapower's `total_active_loss_mw`, where
the old heuristic gave 349.96 kW. The BOM and the "Why This Route" panel now agree —
their disagreement was the original symptom.

**Parcel area — worse than recorded, and the fix is different.** The plan assumed
Python already computed a usable per-parcel overlap. It does compute
`RowIntersection.intersection_area_m2`, but `result_builder.py` invokes the analysis
with `RowConfig(corridor_width_m=0.01)` — a **1 cm** corridor used to *detect*
crossings, not a real right-of-way. Widening it there would have changed the
crossing-detection and hard-violation semantics that the Python suite pins, so the
overlap is computed in PostGIS instead, which is already the storage layer and can
measure on the ellipsoid via `::geography`.

The old Java figure was also worse than "full parcel area". It was:

```java
p.getGeometry().getArea() * 111000.0 * 111000.0 * 0.001
```

— the whole parcel, converted with a fixed metres-per-degree factor that ignores
latitude, then scaled by an unexplained `0.001`. On the reference project:

| Basis | m² |
| --- | ---: |
| Whole parcel | 36,862 |
| **True 18 m ROW overlap** | **18,884** |
| Figure previously reported | 38 |

Roughly 500× too small, feeding `estimatedCompensationCost` — a money field.

`CadastralParcelRepository.findRowCorridorAreaByParcel` now returns the area of
`ST_Intersection(ST_Buffer(route::geography, width/2), parcel)` per parcel. Parcels the
corridor misses return zero rather than being dropped, so they still appear as
unaffected. If the spatial query cannot run, every parcel reports zero and a warning is
logged: showing no impact is honest, inventing an area that feeds a compensation
estimate is not.

**One assumption made explicit.** ROW width is accepted on the job request and sent to
Python but never persisted, so the report uses the documented 18 m default. Rather than
bury that behind a number, the CSV export now states the corridor width and the basis
of the calculation. Persisting `rowWidthM` on the job is the proper follow-up.

**Verified:** 187 Java tests and 487 Python tests green; a live run of the reference
project shows 324.18 kW losses and 11,475 m² of corridor overlap for the job's actual
routes (the figure differs from the 18,884 m² above because that measured a different
job's route set).

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

1. ~~**Tier 1** (scenarios real)~~ — **done 2026-08-15**, see §2.4.
2. ~~**Tier 3** (BOM losses + ROW area fixes)~~ — **done 2026-08-15**, see §4.3.
3. ~~**Tier 2** (authorization)~~ — **done 2026-08-15**, see §3.3–§3.5.
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
