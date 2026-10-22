# Surge — Project Review

**Review date:** 2026-10-22
**Reviewed:** branch `test` at `e672571` (identical to local `main`). Working tree clean apart from one untracked file, `docs/V1→V2 Gap Closure — Ticket Plan.md`.
**Method:** read-only. Nothing was edited, deleted, moved or committed before this file was written. Test runs wrote only to gitignored directories (`target/`, `node_modules/`, `dist/`, caches); `git status` was identical before and after.

> **Read this first — the checkout is stale.** `origin/main` (`a0ecfc8`) is **29 commits ahead** of this branch and has **0** commits this branch lacks. Against `HEAD` it changes 206 files (+82k lines): an ML pre-ranker (`app/optimisation/ml/`, `artifacts/ml/`), V0 golden fixtures, a `contracts/` pack with a Python contract-test suite, `scripts/ci/check_ownership.py`, 3 Java test files, 3 frontend files, and a **reorganisation of `docs/` into subfolders** (`docs/product/`, `docs/routing/`, …). Everything below describes `HEAD` unless it says "origin/main". Spot checks against `origin/main` (via `git grep`, not a checkout) are named where they change a conclusion. **Merge or rebase before editing any doc** or the doc moves will conflict with the cleanup.

---

## 1. Verdict

**Surge is a working, well-tested vertical slice, not a finished product.** A KMZ goes in; a costed, electrically screened 33 kV network with classified poles, a BOM and a "why this route" explanation comes out, across three services. The baseline is green on all three: 279 Java tests, 601 Python tests (ruff and strict mypy clean), 130 frontend tests plus a clean typecheck and build. Of the 21 tickets in the Consumption Gap plan, 18 are real in code; P-2 (cable data) is not done, and L-1/L-2 (land) are plumbing that has no commercial data to carry. The V1→V2 gap list is right on five of six points; the two corrections are in §2.1. What stands between this and a deployable system is not features but **trust**: an unescaped-HTML path that turns an imported KMZ into account takeover, a login throttle that can be bypassed with one header, resource-exhaustion holes around the Python call and the KMZ parser, and several places where missing data becomes a plausible number. The README and CONTEXT security sections are wrong in both directions (they list fixed things as open and omit things that are open).

**Top 5 risks**

1. **Stored XSS → token theft (Critical, F-01).** Imported KMZ names are interpolated unescaped into Leaflet popup HTML; the JWT lives in `localStorage`. Any user who can import a file can run script as every other user who opens a popup, including an admin.
2. **The login throttle is bypassable (High, F-02).** It keys on the leftmost `X-Forwarded-For` entry, which nginx *appends to* rather than overwrites, and port 8080 is published directly. One rotating header defeats the control that CONTEXT/README call the fix for "no brute-force protection".
3. **Hangs and memory exhaustion (High, F-03, F-04).** `zis.readAllBytes()` has no decompressed-size limit (zip bomb inside the 25 MB upload cap), and the Java→Python `RestClient` has **no timeout**, so one stuck solve pins a worker and a DB transaction, and the stale-job sweeper only runs at startup.
4. **Silent plausible-number fallbacks (High/Medium, F-05, F-09, F-11, F-12).** With no `cable_config`, Python invents a "MVP-COMPATIBILITY-CABLE" and returns losses on it as `success`; `PARTIAL_SUCCESS` is reported as "completed successfully"; spatial-analysis failures are logged and the candidate is scored without them; parallel-count/derating silently default to 1×/1.0 when a catalogue row changes; parcel rates are labelled `$` against an INR catalogue.
5. **The safety net under the data and the contract is thin (High/Medium, F-06, F-13).** Flyway V1–V20 are never executed in any test (`flyway.enabled: false`, H2 `create-drop`), and the Java↔Python "contract" test mocks the client with a hand-written response — nothing validates Java's request against Python's `extra="forbid"` models.

### 1.1 Baseline (Phase 1)

| Service | Command (from the service directory) | Result |
| --- | --- | --- |
| Java | `./mvnw verify --batch-mode`, **JDK 21.0.12** via `JAVA_HOME` override (default `java` here is 25.0.2) | `BUILD SUCCESS` — **279 tests**, 0 failures / errors / skipped |
| Python | `ruff check app tests`; `mypy app`; `pytest -q` in the existing `.venv` = **Python 3.14.0** | ruff: all checks passed · mypy: no issues in **111** source files · pytest: **601 passed**, 1 warning (Starlette `httpx` deprecation), 87.8 s |
| Frontend | Node v24.19.0: `npm ci`; `tsc --noEmit`; `vitest run`; `vite build` | `npm ci` ok (279 pkgs) · tsc 0 errors · **16 files / 130 tests passed** · build ok (one 603 kB chunk > 500 kB warning) |

Could not run, or deviated from CI: see §6. Headline deviations: Python ran on **3.14** (CI and `AGENTS.md` say 3.11/3.13; neither is installed), Node was 24 (CI uses 20), and `gh` is not installed so CI history is unread.

Counts the docs quote are all stale: README/CONTEXT say 209 / ~489 / 26 tests; actual 279 / 601 / 130. Files at review time: 130 Java main `.java`, 38 Java test files, 111 Python app `.py` (104 after the cleanup), 48 Python test files, 81 non-test frontend `.ts`/`.tsx` (CONTEXT says 112 / 79 / 65).

---

## 2. Completion check

### 2.1 The V1→V2 gap list — confirmed or corrected

| # | Your claim | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | `land_context` is on Python's request schema; Java's `PythonOptimisationRequest` has no `landContext`, so land decisions are always empty | **Confirmed, with a precision.** | Python v1 `app/schemas/optimise.py:69`, v2 `app/schemas/v2/optimise.py:294`. Java record has 11 fields, none land (`PythonOptimisationRequest.java`); zero hits for `landContext`/`land_context` in `backend-java/` on HEAD *and* origin/main. **"Empty" means unpriced, not absent:** `assess_candidate_land` runs with `land_context=None` (`app/land/decision.py:85-89`, `profiles = {}`), so a decision exists per affected parcel but with no priced option and owners counted per parcel (`OwnerInteractionBasis.PARCEL_PROXY`, set in the same function). Also note `decision.py:76-83` raises `ValueError` if the land currency ≠ lifecycle currency, so whoever wires INT-002 must send **INR**. |
| 2 | Cable sizing is persisted and shown in the BOM | **Partly correct.** | Persisted (V14): `cable_type_id`, required current, effective ampacity, utilisation. **Not persisted:** `parallel_count` and `derating_factor` — `ReportService.java:317-318` looks them up from the *live* catalogue at report time and falls back to `1` / `1.0` when the row is gone. The BOM label "Twin … (2×)" (`BomBoqTable.tsx:19-23`) therefore depends on today's catalogue, not the run. Also: sizing is only live when the catalogue is non-empty — `CableCatalogueService.java:55` returns `null` otherwise and Python substitutes the fabricated compatibility cable (F-05). |
| 3 | `PoleMicroSitingConfig.enabled` defaults `False`; no request schema exposes it | **Confirmed.** | `pole_placement.py:89` (`enabled: bool = False`); `PoleConfig.micro_siting` defaults `None` (`:167`); the only consumer is `candidate_evaluation.py:321`; `git grep -i micro` over `app/schemas` and `app/api` is empty on HEAD and origin/main. Unreachable through any API. |
| 4 | `app/reporting/` has no HTTP endpoint and no caller outside its own tests | **Confirmed.** | 14 files, **1,336 lines**. Only `tests/test_decision_report.py` and `tests/test_engineering_report.py` import `builder`/`report`/`renderers.text`. **On origin/main** `app/presentation/models.py:12` also imports `app.reporting.schema_version` (a 10-line constants module) — the builder itself still has no runtime caller. |
| 5 | Span-vs-buy does not exist | **Confirmed.** | No hit for `span_vs_buy`, `overhead_easement`, `span_limit` in `app/`, `backend-java/`, `web-map-next/`. `max_span_m` is one number per request (`pole_placement.py:164`). |
| 6 | Java calls `/api/v1/optimise` only; `/api/v2` is mounted and tested, but nothing consumes it | **Confirmed.** | `PythonOptimizationClient.java:23`; v2 mounted `app/main.py:26-29`; the only non-test mention of `api/v2` outside Python is `core/config.py:11`. |

**Two corrections to the untracked plan itself.** (a) Its "What's already done" table lists **P-2 as done**. It is not: V15/V16/V17 seed every conductor as `INDICATIVE`, with no `VERIFIED` row anywhere; the Consumption plan correctly calls P-2 a quality gate that "blocks nothing". (b) It says `PARTIAL_SUCCESS` "isn't read anywhere to distinguish". True — and it is *pinned as intended* by `OptimisationContractTest.java:289` (`aPartiallySuccessfulRunStillPersistsWhatItProduced`), which asserts `COMPLETED`. What is missing is any signal to the operator, not the persistence (F-09).

### 2.2 Area-by-area

| Area | Claimed state | Actual state | Evidence | Remaining work |
| --- | --- | --- | --- | --- |
| Python core pipeline PY-014 → PY-025 | Complete (MVP Ticket Plan table) | **Real** | 601 tests pass; ruff + strict mypy clean; modules present (`app/pnc`, `app/electrical/load_flow`, `app/optimisation`) | Plan header line 4 still says "Current ticket: PY-024 (in progress)" while its own table says Complete |
| Java → Python transport of constraints, poles, cable and cost config | `whats-next.md` §3.3 says it does not exist | **Real now** | `OptimizationJobService.java:234` (constraints), `:246-249` (cable/cost config), `:288-290` (poles persisted); `OptimisationContractTest` (15 tests) | `whats-next.md` is stale — archive |
| Scenarios genuinely differ (Gap Plan Tier 1) | Done | **Real** | `ScenarioProfile` (17 tests), weights sent at `OptimizationJobService.java:245` | none |
| Auth, admin panel, audit (Tier 2) | Done | **Real, narrower than described** | `JwtAuthenticationFilter.java:64-83` re-checks the account every request; `UserAdminController` + service guard last-admin/self-lockout | Role enforcement exists **only** for ADMIN (`@PreAuthorize` appears only in `UserAdminController` and `/auth/register`); `ROLE_VIEWER` can write (F-08); audit log open to all users (F-15) |
| Credential defaults + brute-force (§5.7 items 1–2) | Gap Plan: DONE 2026-08-16. README/CONTEXT: still open | **Real in code; throttle bypassable** | `AuthService.java:60-98` refuses blank or `admin` password; `LoginThrottleService` (5 failures / 15 min, 15 min lockout) + 429 handler | F-02; the docs contradict the code (§4) |
| Async jobs, SSE, post-commit completion (§5.5–5.6) | Done | **Real** | `OptimizationJobRunner`, `completeAfterCommit` (`OptimizationJobService.java:329`), `StaleJobSweeper` (3 tests) | No timeouts (F-04); sweeper is startup-only |
| Cost catalogue P-1, C-1, F-1, C-2–C-4 | Done | **Real** | V18, V19, `CostCatalogueService`, `CostOutcome`, "Not costed" (`ReportService.java:574`, `PdfReportService.java:448`), `CostBreakdown.tsx`, `BomBoqTable.tsx` | Rates are all `INDICATIVE` (a business input); **F-1's claim to close the INR/`$` mismatch is only partly true** — parcel compensation is still `$` (F-12) |
| P-2 verify cable catalogue | Plan lists "Done"; Consumption plan lists open | **Not done** | V15–V17: no `VERIFIED` row | Datasheet values (data edit, no code) |
| Repair diagnostics E-1b / E-4 / E-6 | Done | **Real** | `repair.py`: 8 `REPAIR_EXHAUSTED` returns, 8 `exhaustion_reason=`; `OptimizationPane.diagnostics.test.tsx` (9 tests) | `repair.py:192` swallows an exception without logging it (F-11) |
| E-2, F-2 popups | Done | **Real, with residue** | `popupValues.ts`; `SurgeMapEngine.ts:218-234` | `props.bufferMeters` still falls back to 0 (`SurgeMapEngine.ts:336`); `asRatePerM2` hardcodes `$` (`popupValues.ts:51`) |
| E-3, E-5, R-1, R-2, R-3, M-1, M-2 | Done | **Real** | `OptimizationJobService.java:605-606` forwards `feeders`/`violations`; `DecisionExplainer.tsx` (10 tests), `decisionInsight.ts` (13), feeders panel (12) | Cosmetic: popup builds `` `Twin ${cableTypeId} (2×)` `` (`SurgeMapEngine.ts:233`) while the ids already contain `TWIN` — likely reads "Twin ACSR-TWIN-PANTHER (2×)" (code reading; UI not run) |
| L-1 / L-2 land table | Done | **Done as plumbing** | `LandOutcome.java`, `ParcelImpactTable.tsx` (+ test) | Displays unpriced results because `land_context` is never sent (§2.1 #1) |
| L-3 converge ROW | Done | **Real** | `c4814ba` deleted 45 lines from `CadastralParcelRepository`; `ReportService.java:138` takes `affectedAreaM2` from Python | Parcel rate/compensation labelled `$` (F-12) |
| Land commercial data (INT-001 → 006) | Planned | **Not started** | plan is untracked; no `landContext`, no PATCH endpoint on `CadastralParcelController` | whole chain |
| Engineering report (PY-036/037) | Built | **Built, tested, unwired** | 1,336 lines, test-only callers | Decision D2 (INT-007) |
| Pole micro-siting (PY-035) | Built | **Built, off, unreachable** | §2.1 #3 | INT-009/010 |
| v1 → v2 client migration | Planned | **Not started** | `PythonOptimizationClient.java:23` | Golden contract test first (INT-011) |
| Span-vs-buy | Planned | **Does not exist** | §2.1 #5 | last, per both source docs |
| ML pre-ranker | "post-MVP" | HEAD: corpus generator only (`scripts/generate_search_corpus.py`, `app/optimisation/corpus/`). **origin/main:** trained artefact + `app/optimisation/ml/` | `git diff --stat HEAD origin/main` | Decide whether to merge |
| CI | "Four jobs" | **Four jobs, with gaps** | `.github/workflows/ci.yml` | No frontend lint (none exists), Playwright E2E not run, no DB-backed test, `docker compose build` only (never `up`) |

---

## 3. Flaws

Severity is for a deployment that is reachable by more than the author. Evidence is code reading unless it says "run". **No exploit was executed.** One-line fixes only.

| ID | Sev | Finding | Evidence | Fix |
| --- | --- | --- | --- | --- |
| F-01 | **Critical** | **Stored XSS via imported KMZ text.** Every map popup builds HTML by template string from backend values (`externalId`, `ownerName`, `name`, `lineSection`, `parcelId`, `status`, `feederName`, …) and passes it to `bindPopup`, which sets `innerHTML`. `shown()` returns `String(value)` raw. No escape helper exists in `src/`; the Java side has no sanitisation (grep). The JWT is in `localStorage`, so one crafted placemark name steals any viewer's session, and the model is "everyone sees everything". | `SurgeMapEngine.ts:87-90, 115, 142, 177, 220, 286, 308-312, 331-336, 378, 392`; `popupValues.ts:34`; `client.ts:5`; `git grep escapeHtml` → none | Escape every interpolated value (in `shown()` and the templates) or build popup DOM with `textContent`; add a test with a `<img onerror>` name |
| F-02 | High | **Login throttle bypass.** `ClientAddress` takes the *leftmost* `X-Forwarded-For` entry as the client; nginx sets `$proxy_add_x_forwarded_for`, which *appends* to whatever the caller sent, so the leftmost value is attacker-controlled even through the proxy. The comment's "leftmost entry is the original client" is false for a client-supplied header. Port 8080 is also published, so nginx can be skipped entirely. Lockout is per-IP only (no per-username). | `ClientAddress.java:29`; `nginx.conf:12-13` (it already sets `X-Real-IP $remote_addr`, which is trustworthy but is only the fallback); `docker-compose.yml:29` | Key on `X-Real-IP`/rightmost XFF; add a per-username counter; stop publishing 8080 |
| F-03 | High | **KMZ zip bomb.** The 25 MB limit is on the compressed upload; the `.kml` entry is inflated with `readAllBytes()` and then DOM-parsed, with no size or feature cap. A ~25 MB archive can inflate by orders of magnitude and exhaust the heap. (XXE is correctly closed, `disallow-doctype-decl` at `:329`; zip-slip is not possible, entry names are only tested with `endsWith`.) | `KmzGeoJsonConverter.java:310-316`; `application.yml:12-13` | Bounded read (`readNBytes(limit+1)`, reject above e.g. 50 MB) and a feature-count cap |
| F-04 | High | **No timeout on the Python call; no mid-run watchdog.** `RestClient.builder().baseUrl(..).build()` sets no connect or read timeout. A hung solve holds the worker thread and the `@Transactional` DB connection forever (pool 2–4 workers, queue 20, then 503); the only stuck-job recovery is `StaleJobSweeper`, which runs once at startup. | `PythonOptimizationClient.java:16`; `AsyncConfig.java`; `StaleJobSweeper.java` | Set read/connect timeouts on the request factory; add a periodic sweep of `RUNNING` jobs older than N minutes |
| F-05 | High | **Fabricated cable when `cable_config` is absent.** Python substitutes `MVP-COMPATIBILITY-CABLE` (R 0.03 Ω/km, X 0.10, C 200 nF/km, ampacity derived from `feeder_capacity_mw`) and returns loss/voltage/loading as `status: "success"`. Nothing in the response says the cable was invented. Java triggers it whenever the catalogue yields nothing. | `legacy_mapping.py:28, 111-137`; `CableCatalogueService.java:55`; V15 header comment | 422 on a v1 request with no `cable_config`, or surface `compatibility_cable_used` and have Java fail/warn |
| F-06 | High | **Migrations are never run by any test.** Test profile disables Flyway and builds the schema from entities on H2; CI has no database job. A broken or drifting V1–V20 reaches deploy undetected (three of them — V5, V7, V13 — rewrite data). | `application-test.yml:11-12`; `OptimisationContractTest.java:60-63` (admits the gap); `ci.yml` | Testcontainers PostGIS test that runs V1–V20 and boots with `ddl-auto: validate` |
| F-07 | High | **Unused write endpoints let any authenticated user overwrite a job's results.** `POST /jobs/{jobId}/routes` and `/routes/geojson` persist caller-supplied geometry against any `jobId` (the `projectId` path variable is not checked on write). The frontend only ever GETs routes/poles. | `GeneratedRouteController.java:31, 41`; frontend URL inventory (`lib/api/*`) | Delete both POSTs (and the matching service overloads if tests allow) |
| F-08 | Medium | **Only ADMIN is a role.** No `@PreAuthorize` outside `UserAdminController` and `/auth/register`; `ROLE_VIEWER` can create/modify projects, import assets and start compute-heavy jobs. No ownership checks (documented as deliberate in CONTEXT §2). Unbounded concurrent jobs per project. | `grep PreAuthorize` over `controller/`; `ProjectController.java` | `hasAnyRole('ADMIN','ENGINEER')` on mutating routes; limit one active job per project |
| F-09 | Medium | **`PARTIAL_SUCCESS` is invisible.** v1 maps it to `status: "success"`; Java stores `workflowStatus` but only ever writes it, the TS type declares it but nothing reads it. The operator sees "completed successfully!" when candidates failed. | `legacy_mapping.py:81`; `OptimizationJobService.java:259, 295, 590`; `types.ts:206` | Read `workflowStatus` and show a "partial" badge with the failed-candidate reasons |
| F-10 | Medium | **Error responses leak internals.** The catch-all returns `"An error occurred: " + exception.getMessage()`; constraint errors return the raw DB message ("Key (…)=(…)…"). Job `errorMessage` stores `e.getMessage()` from the Python client, including response bodies. | `ApiExceptionHandler.java:91, 71`; `OptimizationJobService.java:306` | Log server-side, return a fixed message + correlation id |
| F-11 | Medium | **Python turns failures into missing data.** Spatial-analysis failure is logged and the candidate is scored without spatial metrics; pole-placement failure sets `pole_result = None`; the repair cable-sizing catch returns `CABLE_SIZING_FAILED` without logging the exception; dead `most_loaded_segment_id` silenced by a blanket `noqa`. | `candidate_evaluation.py:307-311, 333-340`; `repair.py:192`; `analysis.py:214` | Record the failure on the candidate and lower its eligibility/flag it; `logger.exception`; delete the variable |
| F-12 | Medium | **Currency: INR catalogue, `$` on parcels.** Parcel rate and compensation are labelled `$` in the map popup, CSV and PDF, while every other figure carries the catalogue currency. The Consumption plan records this mismatch as closed. | `popupValues.ts:51`; `ReportService.java:500`; `PdfReportService.java:334` | Carry a currency on parcel rates, or label "per m² (currency not recorded)" |
| F-13 | Medium | **The "contract" test is a mock.** `OptimisationContractTest` mocks `PythonOptimizationClient` and hand-writes the response; eight request fields are untyped `Map<String,Object>`; Python's nested models are `extra="forbid"`, so a Java key typo is a runtime 422 no CI step sees. The v1 top-level model ignores unknown fields, which already silently dropped `costing_config` once (its own comment says so). No shared golden JSON on HEAD. origin/main adds a Python-side `contracts/` pack; no Java consumer was found there (unverified). | `OptimisationContractTest.java:60-185`; `PythonOptimisationRequest.java`; `schemas/optimise.py:38`, `schemas/v2/optimise.py:15` | Commit one golden request/response pair, validate it in both Pydantic and a Java test; set `extra="forbid"` on the v1 model |
| F-14 | Medium | **Frontend swallows fetch errors into plausible empties.** Assets, parcels and restricted-area fetchers, the audit log and the project BOM catch everything and return an empty collection or a *zeroed report* (`totalPoles: 0`, `totalNetworkLengthMeters: 0`) — the exact failure mode `jobs.ts` documents and fixed for routes/poles. | `assets.ts:44-70`; `audit.ts:8`; `reports.ts:18` | Throw; let the query's error state render |
| F-15 | Medium | **Audit log readable by every authenticated user, returned as the JPA entity.** | `AuditLogController.java:21-23` | `@PreAuthorize("hasRole('ADMIN')")` + a DTO |
| F-16 | Medium | **Public actuator detail and verbose SQL logging.** `show-details: always` with `/actuator/health/**` permitted exposes DB/disk status to anonymous callers; `org.hibernate.SQL: DEBUG` and `BasicBinder: TRACE` log bound values (password hashes on user insert, emails, imported text) in the default profile. | `application.yml:67, 73-74`; `SecurityConfig.java:59-60` | `when-authorized`; move SQL logging to a dev profile |
| F-17 | Medium | **Cable parallel-count/derating not persisted** (see §2.1 #2): historic BOMs change if the catalogue is edited, and fall back to "1×". | `ReportService.java:317-318`; V14 | Add the two columns (new migration) and write them at job time |
| F-18 | Medium | **Ports published beyond the browser path.** Postgres (`${DB_PORT:-5432}`), backend (8080) and the **unauthenticated** optimiser (8000) are all bound on the host, contradicting README's "never exposed". | `docker-compose.yml:13, 29, 63` | Drop `ports:` for `db`/`optimizer`; bind others to `127.0.0.1` |
| F-19 | Medium | **Whole run in one transaction, and a swallow-and-commit path.** `executeJob` holds a pooled connection for the whole solve; a non-DB exception after routes are saved is caught, the job is marked failed, and the transaction **commits** the routes (the failure test covers only a Python-reported failure). Also an unbounded in-memory import staging map (no per-user or size cap). *Not reproduced.* | `OptimizationJobService.java:165, 304-313`; `OptimisationContractTest.java:485`; `AssetImportStagingService.java:26` | Persist results in a separate short transaction after the solve; cap staged imports |
| F-20 | Low | Sessions: 24 h tokens, `/auth/me` mints a fresh token each call (sliding forever), wrong-username returns before BCrypt (timing), `register` returns the new user's token to the admin. | `AuthService.java:122-151` | Don't re-issue on `/me`; hash a dummy on unknown user |
| F-21 | Low | CORS `allowedOriginPatterns("*")` (header tokens, no cookies, so low impact; not wired into the Security chain — behaviour of preflights unverified). | `WebConfig.java:13` | Restrict or remove (same-origin via nginx) |
| F-22 | Low | Containers: backend and nginx run as root; images unpinned (`nginx:alpine`, `node:20-alpine`, `eclipse-temurin:21-*-alpine`); the Python runtime image installs mypy/pytest/ruff from the shared lock. Python image *does* drop to a non-root user. | `backend-java/Dockerfile`, `web-map-next/Dockerfile`, `optimisation-python/Dockerfile:30` | `USER` lines, digest pins, split dev/runtime requirements |
| F-23 | Low | Dead or inert: `capexWeight`/`lossesWeight` are accepted and stored but never sent or read (frontend never sends them); `createAndRunJob` and `getRoleFromToken` are test-only; `percent = success ? 100 : 100`. | `OptimizationJobService.java:140-141, 154`; `JwtTokenProvider.java:78`; `SseProgressService.java` | Remove or wire |
| F-24 | Low | 14 `npm audit` advisories (2 critical, 7 high) — **all dev-only** (vitest, vite, tailwind chain); `npm audit --omit=dev` reports 0. | `npm audit` run | Plan a vitest/vite major bump |
| F-25 | Low | SSE emitter times out at 5 minutes while runs can be longer (polling covers it, `useJob` every 3 s); no `Retry` semantic. | `SseProgressService.java:19` | Fine; document |

**Checked and found sound** (so you know what *not* to spend time on): XXE disabled and DOCTYPE banned; no zip-slip; JWT secret has no default and the service refuses to boot without one; the filter re-reads the account per request; `ddl-auto: validate`; WTG cap (`MAX_WTGS = 500`) and raster cap (`MAX_RASTER_CELLS = 15_000_000`) enforced at the Python boundary (`domain_mapping.py:64-65, 155, 178`); A\* uses a monotonic tie-break counter and the engine has no `random`/`uuid`/`time` use (KMeans seeded, `random_state=42`); Python container non-root; no secrets matched in tracked files; `.env` untracked and never in history; load-flow non-convergence returns a structured result rather than raising.

**Secrets in history.** The old JWT constant and the `engineer`/`engineer123` demo credentials are in public history (`git log -S` hits: `0e59566`, `f7b7239`, `5d66566`, `12d5be5`, `3336276`, `d74d9cf`). CONTEXT §3.1 already records them as burned. Nothing further to do except confirm they were rotated everywhere they were reused.

---

## 4. Documentation changes

Proposed only — nothing rewritten. IDs are for picking in the apply phase.

| ID | File : line | What is wrong | Proposal |
| --- | --- | --- | --- |
| D-01 | `README.md:86-90`, `:159-160` | Says a fresh DB seeds `admin`/`admin` and `SURGE_BOOTSTRAP_ADMIN_PASSWORD` "defaults to `admin`". `AuthService.java:60-98` refuses to seed without a real password. The comment at `AuthService.java:56` ("defaults exist only to keep a fresh checkout usable") is stale in the same way. | Update README + that Javadoc |
| D-02 | `README.md:161-162` | "No brute-force protection… no rate limit, lockout or delay." `LoginThrottleService` exists (5 / 15 min, 429). It is bypassable (F-02), which is the accurate thing to say. | Rewrite the Security section |
| D-03 | `README.md:157` | Points at §5.7 as open. `MVP Gap Closure Plan.md:838` and `:844` strike items 1 and 2 as DONE 2026-08-16; only TLS remains. | Update |
| D-04 | `README.md:109, 117`, `CONTEXT.md:164-165` | Vite dev port 5174. `vite.config.ts:12` and `.claude/launch.json` say **5173**. | Fix both |
| D-05 | `README.md:141-143`, `CONTEXT.md:20-22` | Counts 209 / ~489 / 26; Flyway "V1–V13"; 112 / 79 / 65 files. Actual 279 / 601 / 130 at review time; V1–V20; 130 / 111 / 81 files. | Update, or drop the numbers |
| D-06 | `README.md:18-19` | "The optimiser is never exposed to the browser" — port 8000 is published on the host (`docker-compose.yml:63`). | Fix with F-18 |
| D-07 | `README.md:185` | Mentions `web-map/`. | Remove with X-01 |
| D-08 | `CONTEXT.md:5, 25-28, 181` | "Last updated 2026-08-15"; deployment blockers list is out of date (two of three done). | Refresh |
| D-09 | `AGENTS.md:1, 28, 33, 34, 38` | Title and 4 body references say `AGENT.md`; the file is `AGENTS.md`. `:82-83` lists `requirements.txt` as the dependency file. The on-disk `.venv` is Python 3.14.0, which `AGENTS.md` §9 says not to rely on. | Rename references; recreate the venv on 3.11/3.13 (local, not a repo change) |
| D-10 | `optimisation-python/README.md:1-14, 16-73, 70` | Describes the service as of PY-017 ("standalone modules"), shows a tree of 2 tests and stub modules, lists a non-existent `AGENTS.md`. | Replace with a short pointer to the root README and `docs/Python Engine - Architecture.md`, or delete |
| D-11 | `docs/Python Engine Integration Plan.md:23, 102` | "`land_context` is v2-only"; whole §1 table predates cable sizing emission/persistence. | Mark superseded by the V1→V2 plan, or correct |
| D-12 | `docs/Land Acquisition and Route Decision Engine.md:94, 100` | "defined on the **v2** request schema only" — also on v1 (`optimise.py:69`); "cable sizing… v2-only and unreachable" no longer true. | Correct |
| D-13 | `docs/Surge MVP Ticket Plan.md:4` | "Current ticket: PY-024 (in progress)" contradicts its own table (PY-024 and PY-025 Complete). | Fix |
| D-14 | `docs/whats-next.md:1-5, 133, 140-143, 156-181` | A Thursday 13 Aug plan for a Sunday demo; its "missing link" section is now implemented. | Archive |
| D-15 | `docs/Consumption Gap Ticket Plan.md` (F-1 section) and `docs/V1→V2 Gap Closure — Ticket Plan.md` ("What's already done") | F-1 "closes the INR/`$` mismatch" (F-12 says it did not fully); the V1→V2 table marks P-2 done (§2.1). | Correct both; the V1→V2 file is untracked — decide whether to commit it |
| D-16 | `docs/MVP Gap Closure Plan.md:3` | Status date 2026-08-15 but records items done 2026-08-16. | Date bump |
| D-17 | `obsidian-vault/12-testing/Testing Status.md:38, 54, 195` | `:38` claims **SpotBugs, Checkstyle and ESLint**; `:54` claims Surefire *and Failsafe*. None exist: `pom.xml` configures only Surefire and no static-analysis plugin; `web-map-next` has no ESLint config or script. `:195` runs `pip install -r requirements.txt`. | Correct |
| D-18 | `obsidian-vault/` — 14 notes repeat the stale counts (`Dashboard.md:74-75`, `Scope.md:105,118-119`, `Roadmap.md:79`, `Backend.md:4`, `Deployment.md:134`, `Overview & Layout.md:6,121`, `Sunday KMZ to 33kV Network Plan.md:11-12,47`, …) | Same as D-05 | Replace numbers with a link, or update |
| D-19 | `docs/superpowers/plans/2026-08-12-web-map-frontend-redesign.md` (4,290 lines) and the two `specs/` | Implementation plan/spec for a redesign that has shipped (`9877206`, `baff5a6`, `198f5c0`). | Archive |

**Duplication between `docs/` and `obsidian-vault/`.** 11 notes exist in both and **none is byte-identical** (114–454 changed lines each): AC Load Flow Validation, ADR-007, Candidate PNC Scenario Generation, Canonical Candidate Engineering Metrics, Constraint-aware Routing, Cost Model, Multi-Objective Candidate Scoring, PNC Network Assembly, Route Scoring Architecture, Surge MVP Ticket Plan, presentation-boundary. Cross-links are sparse: `README.md` and one `docs/` file link to the vault; three vault files link back (`Sunday KMZ…`, two journals). The vault uses 611 wikilinks internally.
**Proposal — single source of truth:** `docs/`. It is what the README links to, the code comments cite, and where origin/main has already restructured into topic folders. Keep in the vault only what has no `docs/` twin (vision, requirements, journal, research papers, templates, canvas); replace the 11 duplicates with a one-line pointer after a last diff, so nothing unique is lost. **Do this after merging origin/main.**

**Per-service setup/run/test/env docs.** Root README covers Docker, Java, Python, Node accurately *except* D-04/D-05; `.env.example` lists `PORT` (never read — `server.port` is fixed at `application.yml:2`) and omits `app.jwt.expiration-ms`; `optimisation-python/.env.example` omits `API_V2_PREFIX`; the Python service README is stale (D-10); `web-map-next` has no top-level README (only `src/test/e2e/README.md`; setup lives in the root one).

---

## 5. Unnecessary-file candidates

Evidence is zero references across the three services, tests, scripts, Dockerfiles, `docker-compose.yml`, CI and docs (dynamic imports and Spring/FastAPI auto-registration counted as use). "T" = tracked in git.

### SAFE TO DELETE

| ID | Path | T | Evidence |
| --- | --- | --- | --- |
| X-01 | `web-map/` (17 files; local `dist/`, `node_modules/`, `public/` are ignored) | T | Not in `docker-compose.yml` (frontend context is `./web-map-next`) or `ci.yml`; only `README.md:185` mentions it. Remove README line with it. |
| X-02 | `optimisation-python/mypy_output.txt` | T | UTF-16, 92 lines of old test-file mypy errors; `mypy app` is clean now; zero references (`git grep mypy_output`). |
| X-03 | `optimisation-python/app/utils/` (`coordinate_transform.py` is a docstring-only stub, plus `__init__.py`) | T | AST import scan: no importer in `app/`, `tests/`, `scripts/`; named only in `optimisation-python/README.md`'s tree. |
| X-04 | `optimisation-python/app/algorithms/cost_function.py`, `electrical_analysis.py` | T | Docstring-only stubs, 75 B / 62 B, never imported. |
| X-05 | `optimisation-python/app/services/` (`optimisation_service.py`, 3.7 kB, `OptimisationService`) | T | Never imported by app, tests or scripts. It re-implements the pre-orchestrator pipeline. Docstring mentions in `app/pnc/__init__.py:13` and `app/pnc/assembly.py:13, 154` should be reworded. |
| X-06 | `optimisation-python/app/costing/catalogue.py` (`CostCatalogueProvider` Protocol + `JSONCatalogueProvider`) | T | Zero importers; the real catalogue is passed inline as `config.costing.catalogue`. One-implementation Protocol. |
| X-07 | `optimisation-python/requirements.txt` | T | UTF-16 file whose content is identical to `requirements.lock.txt`; `Dockerfile:12`, `ci.yml:39-41` and the README install the lock. Two doc references to fix (`optimisation-python/README.md:70`, `Testing Status.md:195`). |
| X-08 | `database/` (`init.sql` is 0 bytes; `migrations/.gitkeep`) | T | Not mounted by compose, not read by Flyway (`backend-java/.../db/migration`); mentioned only in the MVP doc's tree. |
| X-09 | 9 redundant `.gitkeep`: `backend-java/src/main/java/com/power/surge/{client,config,controller,domain,repository,service}/`, `backend-java/src/main/resources/`, `backend-java/src/test/java/com/power/surge/`, `optimisation-python/tests/` | T | Every one of those directories now holds real files. |
| X-10 | `obsidian-vault/Untitled.canvas` | T | 2 bytes, `{}`. |
| X-11 | `optimisation-python;C/` (empty directory) | — | Untracked artefact of a mangled `;` path (Aug 17). Local `rmdir` only. |

### DECIDE FIRST

| ID | Path | T | Why it needs your answer |
| --- | --- | --- | --- |
| X-20 | `optimisation-python/app/reporting/` (14 files, 1,336 lines) | T | The D2 decision (INT-007). Test-only callers on HEAD; origin/main adds one constants import. **Do not touch without your answer.** |
| X-21 | `optimisation-python/app/algorithms/route_scoring.py` (339 lines) | T | Imported only by `tests/test_route_scoring.py`; the preliminary PY-012 scorer, superseded in practice by `app/optimisation/scoring.py`, but two docs describe it. |
| X-22 | `GeneratedRouteController` POST routes + the matching `RouteService` overloads | T | Security-relevant (F-07) and unused by the frontend, but `GeneratedRouteControllerTest.java:85` and `RouteServiceTest.java:88` exercise them. |
| X-23 | `capexWeight` / `lossesWeight` (request DTO, entity, columns) | T | Dead plumbing (F-23); the columns exist in applied migrations, so removal is code-only unless you want a new migration. |
| X-24 | `OptimizationJobService.createAndRunJob`, `JwtTokenProvider.getRoleFromToken` | T | Test-only; deleting means rewriting ~8 tests. |
| X-25 | `docs/whats-next.md`, `docs/superpowers/` (plan 4,290 lines + 2 specs) | T | Historical; archive vs delete. |
| X-26 | The 11 duplicated `obsidian-vault/` notes | T | Which side wins (§4). |
| X-27 | `optimisation-python/notebooks/.gitkeep` | T | Placeholder for notebooks you may still want. |
| X-28 | `docs/V1→V2 Gap Closure — Ticket Plan.md` | untracked | Commit it (after D-15), or keep local. |

### KEEP

| Path | Reason |
| --- | --- |
| `contracts/` (incl. `schemas/.gitkeep`) | origin/main fills it (35 files); touching it on this branch only creates conflicts. |
| `backend-java/.../db/migration/V1–V20` | Applied migrations; editing breaks Flyway checksums. **V5 and V7 overlap** (both reclassify towers/substations out of `wtg_locations` with near-identical regex) — document, don't dedupe. |
| `app/optimisation/corpus/`, `scripts/generate_search_corpus.py` | Test/script-only on HEAD, but the ML pre-ranker on origin/main builds on them. |
| `.github/workflows/ci.yml`, `.env.example`, `.gitignore`, `AGENTS.md` (content), `obsidian-vault/Templates/`, `obsidian-vault/journal/` | In use / personal. |

### Gitignored but present (local clutter, not in git)

`.idea/` (7 files, includes a 26 kB `dbnavigator.xml`), `.claude/` (`launch.json`, `settings.local.json` — contains only a plugin toggle, no secret), `web-map-next/test-results/` (empty), `web-map-next/dist`, `backend-java/target`, `optimisation-python/{.venv,.mypy_cache,.ruff_cache,.pytest_cache,**/__pycache__}`, `web-map/{dist,node_modules,public}`. No repo change needed. `.venv` is Python 3.14.0 — recreate on 3.11/3.13 once one is installed.

**Not found:** no unreferenced Java class or DTO (the only zero-referrer classes are Spring-stereotyped); no unused npm dependency or orphan `src/` file in the frontend; no unused Python dependency that is a *direct* choice (`scikit-learn`/`scipy` are used by `wtg_grouping.py`). The Java per-method dead-code scan returned nothing and is **inconclusive**, not clean.

---

## 6. Not verified

| What | Why |
| --- | --- |
| GitHub Actions status / history | `gh` is not installed; no CI run was read. |
| Python on 3.11 or 3.13 | Only 3.14.0 is installed (`py -0p`); the 601-pass result is on 3.14, which `AGENTS.md` says not to rely on. |
| Frontend on Node 20 | Ran on Node 24.19.0 (`engines` allows ≥ 20.18). |
| Java on the default JDK | Default `java` is 25.0.2; verified under the 21.0.12 JDK found in `~/.jdks`. |
| `docker compose build` / `up`, Dockerfile behaviour, healthchecks | Not run (deployment-adjacent; no instruction to). `COPY .mvn/` etc. unproven at build time. |
| Flyway V1–V20 against Postgres/PostGIS | No database available; no test runs them (F-06). |
| Playwright E2E | Not in CI; needs a running stack; `test-results/` is empty. |
| Any exploit or hang (F-01, F-02, F-03, F-04, F-19) | Established from code and config only. Nothing was attacked or reproduced. |
| Runtime UI behaviour (popup text, `Twin …` label, error banners) | Code reading only; app not launched. |
| `AssetService` (1,094 lines), `ReportService`, `RouteService`, `PoleService`, `ParcelService` | Read by grep and targeted lines; transaction boundaries and N+1 patterns beyond the places cited are **not** assessed. |
| Python modules beyond those cited | ~111 files; determinism judged from grep, existing `test_search_determinism.py` and the passing suite, not from a repeated-run diff. |
| Documentation body text | 22 `docs/` and 67 vault files were keyword- and number-checked and sampled, not read line by line; the vault's 611 wikilinks were not resolved. |
| Git-history secret scan | Limited to named files and strings (`.env*`, keys, the old JWT constant, `engineer123`) plus pattern greps on tracked files; no gitleaks/trufflehog. |
| `origin/main` | Compared by `git diff --stat` / `git grep` only; not checked out, built or tested. |
| Accessibility | Counted attributes only (16 `aria-label`, 14 `role=`, no `<img>`, no clickable `div`/`span`); no keyboard or screen-reader pass. |
| Frontend lint | There is no lint script or ESLint config to run. |

---

## 7. What to apply

Reply with IDs. Suggested order, and what each group touches:

1. **Merge first (yours to do):** bring `origin/main` in, or tell me to rebase. Doc edits and deletions below are safer afterwards.
2. **Docs only** (separate change set): D-01 → D-19. D-09's rename and D-01/D-02/D-03/D-04/D-05 are mechanical and low-risk.
3. **Deletions** (`git rm`, then run that service's tests/build): X-01 → X-10 are safe; X-11 is a local `rmdir`. Nothing in X-20 → X-28 will be touched without a direct answer from you.
4. **Code fixes** (not part of the cleanup you described; each is a separate small change with a test): F-01 first, then F-02, F-03, F-04, F-07, F-15, F-16.

---

## 8. Applied on `chore/project-review-cleanup`

Everything above describes `e672571` as reviewed. This section records what was then done, on a branch cut from that commit, one commit per item so any of them can be reverted alone. Nothing was pushed or merged.

| Items | Commit | Notes |
| --- | --- | --- |
| X-01 `web-map/` | `4523d29` | |
| X-02 → X-07 dead Python modules, `mypy_output.txt`, UTF-16 `requirements.txt` | `3c95582` | ruff clean, mypy clean (104 files), pytest 601 passed |
| X-08 → X-10 empty placeholders; X-11 stray `optimisation-python;C/` | `28976cb` | X-11 was an untracked empty directory, removed locally |
| F-01 popup XSS | `f875bef` | 10 hostile-input cases, failed 10/10 first. Frontend: tsc clean, 144 tests, build ok |
| F-02 login-throttle key, plus loopback port binding (the part of F-18 that makes F-02 sound) | `326c095` | `ClientAddressTest` failed 3/5 first. `docker compose config` shows `127.0.0.1` for 8080, 8000 and 5432 |
| F-03 zip-bomb bound (64 MB unpacked) | `c3bc4fd` | failed first (the 65 MB payload was fully inflated and parsed) |
| F-04 Python-call timeouts (5 s connect, 600 s read, configurable) | `3f78fa5` | mutation-checked: removing the read timeout fails the test |
| F-16 actuator detail and SQL/bind-value logging | `64f1deb` | failed 2/2 first. SQL logging moved to `application-dev.yml` |
| F-10 error bodies no longer echo internal text | `ce8ab9b` | failed 2/2 first |
| D-01 → D-10 | `3829947` | README, CONTEXT, AGENTS.md, Python README, both `.env.example` |
| D-11 → D-13, D-15 → D-18 | `865b61a` (+ count bump) | corrections are marked as corrections, not silently edited |

**Final state of the branch:** Java `./mvnw verify` on JDK 21 → **290 tests, 0 failures**. Python (3.14.0 venv) → ruff clean, mypy clean, **601 passed**. Frontend (Node 24) → tsc clean, **144 passed**, build ok.

### Not applied, and why

| Item | Why it was left |
| --- | --- |
| **F-15** audit log admin-only | **Needs a product decision.** The Audit tab is shown to every role in the UI (`RailNav.tsx`: only `Users` is `adminOnly`), so restricting the endpoint would blank it for engineers and viewers. Say which you want and it is a one-line change plus the tab flag. |
| **F-07 / X-22** unused route-write endpoints | On the DECIDE FIRST list; two Java tests exercise them. |
| **X-20** `app/reporting/`, **X-21** `route_scoring.py`, **X-23** `capexWeight`/`lossesWeight`, **X-24** test-only methods, **X-26** vault duplicates, **X-27** notebooks placeholder, **X-28** the untracked V1→V2 plan | DECIDE FIRST — untouched. |
| **D-14, D-19** archive `whats-next.md` and `docs/superpowers/` | These are X-25 (DECIDE FIRST). |
| **D-15, second half** — the P-2 "done" claim in `docs/V1→V2 Gap Closure — Ticket Plan.md` | The file is untracked, so an edit would not be recoverable. Change that row to "not done" when you commit it. |
| **F-05** compatibility cable, **F-09** `PARTIAL_SUCCESS`, **F-12** `$` on parcels, **F-17** derating/parallel columns | Each changes behaviour or needs a schema or label decision (reject vs warn; what to print when the currency was never recorded). |
| **F-06** Flyway under Testcontainers, **F-13** shared golden contract | New test infrastructure and a dependency; larger than a cleanup. |
| **F-08** viewer role enforcement, **F-14** swallowed fetch errors, **F-11**, **F-19** → **F-25** | Access-model and UX changes that should be tested in a browser; I did not run the app. |
| **F-18** rest (drop published ports entirely) | Loopback binding was done; removing the ports would break the Vite dev proxy and the documented health URLs. |
| **F-02** rest | A per-username counter and edge rate limiting. |

### What was *not* verified after the changes

`docker compose build`/`up` was not run (only `docker compose config`), so the image builds with the removed Python modules are unproven, though `Dockerfile` copies only `app/` and nothing deleted was imported. The popup fix and the compose port change were not exercised in a browser or on a running stack. CI has not run on this branch. Local `web-map/{dist,node_modules,public}` (ignored) remain on disk.

---

## 9. Merge with `origin/main` (2026-10-22)

`test` was brought up to date with `origin/main` (`237ccc3`, 85 commits ahead of the review baseline) by a merge, not a rebase, so the cleanup commits keep their identity.

- **Textual conflicts:** three documents only (`README.md`, `CONTEXT.md`, `optimisation-python/README.md`), because `main` moved `docs/` into topic folders. Resolved by keeping the corrected wording and `main`'s new paths. Two relative links to this file in moved documents were repointed (`../Project Review.md`), and `docs/README.md` links it.
- **One semantic conflict, found only by compiling:** `main` added a `profile` component to `PythonOptimisationRequest`, which broke the constructor call in `PythonOptimizationClientTest`. The test now builds the request from JSON, so it no longer depends on the record's arity.
- **Frozen path restored:** `contracts/frozen.txt` lists `optimisation-python/requirements.txt`. The review's X-07 deleted it; the merge restores it (byte-identical to `requirements.lock.txt`). Deleting it is a contract change request, not a cleanup.
- **Counts updated** to the merged numbers: Java 376 tests, Python 1,750, web 144; Flyway V1–V23 (V21–V22 are reserved by `contracts/persistence.md`).

Verification on the merged tree: Java `./mvnw verify` on JDK 21 → **376 tests, 0 failures**. Frontend → tsc clean, **144 passed**, build ok. Python (3.14.0 venv) → ruff clean, mypy clean (148 files), **1,748 passed, 2 failed**. The two failures (`test_search_off_golden` and `test_v1_response_golden`, case `SYN-3-CLUSTERED-20`, a `topology_fingerprint` mismatch) fail identically on a pristine checkout of `origin/main`, so they are not caused by this branch. They are probably the Python 3.14 mismatch (CI and `AGENTS.md` use 3.11/3.13), which could not be confirmed because neither is installed here.
