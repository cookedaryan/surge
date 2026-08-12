# MVP Execution Plan — Frontend & Java

> **Purpose:** A dependency-ordered work plan for the Java/backend and web-map/frontend owner to deliver SURGE's documented vertical-slice MVP. This plan reflects the implementation boundary verified on 2026-08-12.

## MVP release gate

For one golden wind-project dataset, an authenticated engineer must be able to import project GIS data, run each of the four deterministic scenarios, inspect real routes/poles/ROW/parcel/electrical results on the map, and download reports derived from persisted results.

The release gate does **not** require ML ranking, nonlinear pandapower load flow, CAD/BIM exports, or mesh topology. Deterministic scoring and the existing linear electrical screen are sufficient provided their limitations are visible in the UI and reports.

## Dependencies from the Python/GIS workstream

The Java and frontend work below depends on the Python service exposing a single versioned result contract containing:

- constraint-aware route GeoJSON for each requested scenario;
- pole coordinates, types, spans, and counts;
- ROW corridor GeoJSON and parcel-intersection/compensation results;
- electrical screen results and violations;
- deterministic cost and score breakdowns.

Java should agree this contract and representative fixtures with the Python owner before adding persistence or UI fields. The current Python endpoint returns only refined route segments and a null estimated cost. Standalone pole, ROW, scoring, and electrical modules are not yet in that endpoint.

---

## Phase 0 — Make the stack testable

### Java/backend owner

- [ ] Repair the Windows Maven-wrapper launch path and document the supported JDK/Maven command.
- [ ] Ensure a clean `docker compose up --build` starts PostGIS, Java, Python, and the web server; add a readiness check for each service.
- [ ] Add a CI workflow that runs Java tests, Python quality checks/tests, frontend build, and Docker image builds.
- [ ] Add a sample `.env`/configuration guide without credentials.

### Frontend owner

- [ ] Keep `npm ci` and `npm run build` reproducible from a clean checkout.
- [ ] Add a frontend test runner and a small smoke-test suite before adding more UI behavior.

**Done when:** a clean checkout builds, tests, and starts the full system using documented commands.

---

## Phase 1 — Contract, project data, and authorization

### Java/backend owner

- [ ] Publish and version the Java↔Python optimisation request/response contract, including constraints, scenario configuration, cost results, poles, ROW, parcels, and electrical results.
- [ ] Send persisted project layers to Python: parcels, restricted areas, roads/reference lines, forest/environment layers, and relevant metadata/rates.
- [ ] Validate required project data before a job is created; return actionable validation errors for missing/invalid assets.
- [ ] Add migrations/entities/repositories for persisted poles, ROW/parcel impacts, electrical metrics/violations, scenario result metadata, and cost/score breakdowns.
- [ ] Make job execution reliably asynchronous and retain status/progress/failure information.
- [ ] Enforce authenticated project ownership/role authorization on project and optimisation endpoints. `permitAll` on all project paths is not safe for an external MVP.

### Frontend owner

- [ ] Keep the authenticated session flow consistent with the actual Java API (login, logout, token handling, expiry, and unauthorized responses).
- [ ] Build project setup forms for study boundary, WTG/substation data, electrical inputs, and required GIS-layer status.
- [ ] Make import outcomes explicit: accepted, rejected, unclassified, and persisted counts. Do not let a browser-only render imply that the backend import succeeded.
- [ ] Place demo data behind an intentional, visible demo mode. Production mode must never create `proj-default`, use synthetic project data, or show simulated success after an API failure.

**Done when:** an authorized user can create a project, import the golden GIS dataset, and see a clear pre-flight checklist before optimisation.

---

## Phase 2 — Persist and expose complete real optimisation results

### Java/backend owner

- [ ] Extend `PythonOptimisationResponse`, `OptimizationJobService`, and `RouteService` to save complete feeder results rather than only LineString segments.
- [ ] Preserve feeder/network identity so multiple MST edges do not appear as independent feeder summaries.
- [ ] Store route geometry, poles, ROW footprint, parcel impacts, compensation, electrical findings, cost, and score fields transactionally for each job/scenario.
- [ ] Return stable GeoJSON and tabular endpoints for routes, poles, ROW, parcels, electrical results, and score explanations.
- [ ] Replace hard-coded scenario comparison values with results from actual completed scenario jobs.
- [ ] Replace whole-parcel approximations with Python-generated ROW/parcel intersection results.
- [ ] Generate BOM, CSV, and PDF reports only from persisted values. Clearly label preliminary engineering assumptions.

### Frontend owner

- [ ] Render real route, pole, ROW, parcel-impact, and constraint layers with independent layer toggles and accessible legends.
- [ ] Render actual result metrics: route length, capex, poles, impacted parcels, compensation, voltage drop, loading, losses, violations, and deterministic score components.
- [ ] Display an explicit warning when a result is preliminary or violates engineering/spatial constraints.
- [ ] Replace synthetic elevation/profile visuals with returned data or label the profile unavailable until the backend supplies it.

**Done when:** a completed job exposes the same persisted result values through API, map, CSV, and PDF.

---

## Phase 3 — Four real scenarios and usable job UX

### Java/backend owner

- [ ] Support the four MVP scenarios: Balanced, Minimum Cost, Minimum Land Impact, and Minimum Environmental Impact.
- [ ] Decide and implement the job model: one job containing four scenario runs, or four linked scenario jobs. Persist scenario configuration/version and result provenance.
- [ ] Stream real stage progress and terminal failures through SSE; do not report a job complete until results are committed.
- [ ] Add a scenario comparison endpoint that returns only real scenario metrics and geometry references.

### Frontend owner

- [ ] Build an optimisation-settings screen for scenario, weights, feeder capacity, ROW width, span limits, voltage-drop limit, and candidate count.
- [ ] Show real SSE job stage/progress, retry guidance, and failure details.
- [ ] Build scenario comparison from API values and allow switching/overlaying the selected scenario's route layers.
- [ ] Ensure results have loading, empty, error, and keyboard-accessible states.

**Done when:** the golden project can run all four scenarios and their displayed differences come from real inputs/results.

---

## Phase 4 — Verification and release readiness

### Java/backend owner

- [ ] Add contract tests using a golden request/response fixture shared with Python.
- [ ] Add PostGIS migration and integration tests against a real database.
- [ ] Add an end-to-end test covering import → job → Python response → persistence → exports.
- [ ] Review error responses, audit logging, authorization, configuration, and input-size limits.

### Frontend owner

- [ ] Add tests for API error states, authentication, import validation, layer toggles, job progress, scenario comparison, and report downloads.
- [ ] Add a browser end-to-end test for login → import → optimise → inspect layers → download report.
- [ ] Validate responsive layout and popup escaping for untrusted GeoJSON properties.

### Shared release checklist

- [ ] Confirm repeatable results for the same golden inputs/configuration.
- [ ] Run a manual engineering review of routes, poles, ROW, parcel compensation, and electrical warnings.
- [ ] Publish demo instructions, supported-input specification, assumptions, and known limitations.
- [ ] Record the test command/results in [[Testing Status]].

**Done when:** CI and the manual golden-project acceptance test both pass without demo fallbacks.

## Priority order for this owner

1. Fix the runnable baseline and agree the shared contract.
2. Make Java persist/serve truthful result data and remove placeholder reports.
3. Make the frontend show that data honestly, including failures.
4. Add four-scenario comparison.
5. Automate the full browser-to-PostGIS-to-Python test and release review.

## Related notes

- [[Dashboard]]
- [[Backend]]
- [[Frontend]]
- [[Python Engine]]
- [[FastAPI Endpoints|FastAPI Microservice Specification]]
- [[Testing Status]]
- [[Scope]]
