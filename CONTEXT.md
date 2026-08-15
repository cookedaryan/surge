# SURGE Project Context

Implementation status and the progress record across the SURGE platform. Newest first.

**Last updated:** 2026-08-15

---

## 1. Where the project stands

A working end-to-end MVP. A real site survey goes in as a `.kmz`, and a complete 33 kV collector
network comes out — feeders, route geometry, classified poles, an AC load flow, a bill of materials,
and an explanation of why that route won — rendered on the map and exportable.

Verified repeatedly against a real dataset (Uravakonda: 38 route segments, 606 poles, 69.99 km
network) rather than only against fixtures.

| Component | State |
| --- | --- |
| Java backend | 112 source files, 209 tests, Flyway V1–V13 |
| Python optimiser | 79 source files, ~489 tests |
| Web map | 65 source files, 26 tests |
| CI | Four jobs — Java, Python, frontend, container builds |

**Not production-ready.** Three deployment blockers are tracked in
[§5.7 of the gap closure plan](docs/MVP%20Gap%20Closure%20Plan.md): credential defaults that ship
insecure, no brute-force protection on login, and no TLS. Several areas have never had a security
review at all.

---

## 2. Architecture

Three services plus PostGIS. The frontend reaches the backend through an nginx proxy on the same
origin; the optimiser is never exposed to the browser.

**Java backend** (Spring Boot 3.3.2, Java 21) owns persistence, asset ingest and classification,
job orchestration, reporting, accounts and the audit log. Optimisation runs asynchronously on a
dedicated executor with progress pushed over SSE.

**Python optimiser** (FastAPI) does the computation: capacity-constrained feeder grouping, MST
topology, A\* routing over a terrain and constraint cost surface, pole placement and classification,
pandapower AC load flow, candidate scoring.

**Web map** (React 18, TypeScript, Vite, Leaflet, TanStack Query, Zustand) is the operator
interface. Canvas-rendered vector layers, because a completed run places several hundred poles.

### Decisions worth knowing

- **Everyone sees everything.** Deliberate. The tool is for a handful of people at one company, so
  there is no per-project ownership — roles gate *actions*, not *data*.
- **Scenarios change the optimiser's inputs, not just its scoring.** See §4.1.
- **Terminal job events are emitted after transaction commit.** See §3.2.
- **Tokens are checked against the account on every request.** See §3.1.

---

## 3. 2026-08-15 — Security

### 3.1 Tokens now answer to the account behind them (`5d66566`)

Found after briefly exposing the app over a Cloudflare tunnel. Two independent holes:

The **JWT signing key defaulted to a constant written into `JwtTokenProvider`**. This repository is
public, so that constant was readable by anyone, and knowing it is enough to mint a token for any
user and any role without ever seeing a password — no login attempt, no lockout, nothing to notice.
An instance nobody had explicitly configured looked secure and was wide open.

The **authentication filter trusted the token outright and never read the database**. Tokens last a
day and cannot be recalled, so every administrative action was cosmetic against anyone already
holding one: a disabled account kept working, a demoted administrator kept administering, a password
reset locked nobody out. For a system whose access control *is* the admin panel, the panel was
decorative.

**Fixed.** No default signing key — the service refuses to start without `APP_JWT_SECRET`, rejects
the burned placeholder by name, and rejects keys under 32 bytes. The filter resolves the account,
refuses disabled and deleted users, takes authorities from the row rather than the token claim, and
rejects tokens predating the account's last credentials change (`V13`, backdated to `created_at` so
deploying it signs nobody out). `User` bumps the marker from its own setters so a caller cannot
forget.

All three filter guards are mutation-checked: neutering each one fails exactly the test covering it.

**Burned:** the old signing constant, and `engineer`/`engineer123` from the removed demo seeding —
both in public git history at `12d5be5`. Treat as compromised wherever reused.

**Follow-on (`7047f0d`):** the required Compose variable broke the container build job, since
Compose interpolates before building and CI has no `.env`. CI now supplies a throwaway build-time
value; the guard still holds for anyone starting the stack.

---

## 4. 2026-08-15 — Correctness and delivery

### 4.1 Results announced before they were readable (`05e576f`)

**Symptom:** a run finished, the UI reported success and showed the decision summary, but the map
stayed empty. Reloading showed the whole network, so the data was being produced and stored
correctly.

**Cause:** `executeJob` is `@Transactional` and runs the entire pipeline in one transaction, so the
routes and poles it writes are invisible to other connections until commit. It pushed the terminal
SSE event from *inside* that transaction. The browser reacted immediately, fetched the results on
other connections, and legitimately got nothing — then cached the empty answer. Measured live: the
client received `feats=0` for both routes and poles while the database already held 38 routes and
606 poles for that same job.

**Fixed.** `completeAfterCommit` defers the announcement to an `afterCompletion` hook. A rollback is
reported as failure rather than dropped, which previously would have left the client on a progress
bar forever. The frontend also loads the finished run into cache *before* pointing the map at it —
switching first and invalidating afterwards could not work, because the query for the new job did
not exist yet and the invalidation had nothing to refetch.

Also switched Leaflet to `preferCanvas`: 606 poles were 606 SVG elements to create, style and reflow
on every result change.

**Method note.** The tests pin the *ordering*, not the end state — asserting only that the right
data ends up cached passes against the broken sequence.

### 4.2 Earlier the same day

| Work | Commit |
| --- | --- |
| Asynchronous job execution — jobs queue and run on a dedicated executor, progress over SSE, stale-job sweeper | `f45a9f2` |
| Frontend contrast, touch targets, type scale (WCAG) | `18cab33` |
| BOM PDF/CSV exports fixed — `window.open` cannot send an `Authorization` header, so exports broke the moment auth was enforced; replaced with fetch + blob. Map legend removed | `70967aa` |
| Frontend, contract and browser end-to-end test coverage — the frontend had no test runner at all | `cffe157` |
| Real electrical losses and real land impact — BOM used the wrong loss figure; ROW used whole parcel area instead of actual corridor intersection | `eb81f76` |
| Audit log records what users actually do | `19b97aa` |
| Admin panel for account management | `8ae6db9` |
| Authentication required across the API | `12d5be5` |
| Four scenarios produce genuinely distinct results | `54abd87` |

### 4.3 The scenario correction

Tier 1 assumed scoring weights alone would differentiate the four scenarios. They do not — weights
reorder candidates that a single cost surface already produced, so all four returned the same
network relabelled. `ScenarioProfile` therefore carries constraint cost multipliers and clearance
buffers as well, changing what the optimiser is asked to solve rather than only how the answer is
ranked.

---

## 5. 2026-08-13 to 08-14 — Data correctness

Pole placement wired end-to-end (Python → Java → frontend), with routes linked to real per-segment
pole counts so the map popup and BOM agree (`c9ecb26`, `3aa397b`). Voltage and spatial constraints
forwarded to Python instead of a hardcoded 33 kV, and the decision summary surfaced (`881ee80`).
Map layers split by pole class and constraint type, and fabricated scenario-comparison data removed
(`14d5828`). "Run optimization" now blocks proactively with confirmed asset counts rather than
failing downstream (`2c5aec8`). Canonical candidate engineering metrics landed as SURGE-PY-026
(`0d0744d`).

---

## 6. Recurring lessons

Kept because each cost real time and each recurred.

**Verify against the running system.** Unit tests could not have caught: MockMvc performing no ERROR
dispatch while the live server did (403 in tests, 401 in production), a stale container bundle on
`:3000` serving a three-hour-old build, or the transaction-visibility race in §4.1.

**Two builds serve the frontend.** `:3000` is the container; `:5174` is Vite. A fix was reported as
working on 5174 while 3000 still served the broken version. Rebuild before testing on 3000.

**Test the ordering when ordering is the bug.** End-state assertions pass against broken sequences.

**Mutation-check new guards.** Used repeatedly this session; caught tests that would have passed
against the original defect.

**The automation browser pane is not a normal browser.** It runs hidden, `document.hidden` is true
and `requestAnimationFrame` never fires, so Leaflet's canvas renderer cannot repaint and CSS
transitions never advance. This produced one phantom bug report and made one timing measurement
worthless. Check layer state instead of pixels there.

---

## 7. Known gaps

**Deployment blockers** — credential defaults, login rate limiting, TLS. See §5.7 of the gap plan.

**Never security-reviewed** — the KMZ upload path (archive and XML handling on 25 MB untrusted
files), cross-user project access, the export endpoints.

**Carried follow-ups** — two right-of-way area implementations still need converging (PostGIS vs
PY-028's `ParcelEngineeringExposure`); `ROLE_VIEWER` is only enforced on registration; the audit log
is unpaginated; integration tests use H2 rather than Testcontainers against real PostGIS; the
browser E2E suite is not in CI; ROW corridor polygons and score components are not surfaced in the
UI; progress percentages are fixed pipeline points (10/35/70/85), not real solver progress.

**Post-MVP** — raw terrain and restriction rasterisation, ML candidate ranking, electrical repair.

---

## Appendix — early Python engine log (2026-08-08)

Preserved from the original context file.

**SURGE-PY-003 — preprocessing wired into `/api/v1/optimise`.** Validation failure handling for
empty and invalid GeoJSON; integration tests for empty WTG collections, missing substations and
invalid polygon geometries. End-to-end WGS84 ingestion, UTM projection and validation went live.

**SURGE-PY-004 — NetworkX collector graph layer.** `app/algorithms/route_graph.py`, a Euclidean
undirected candidate topology generator. The MST work needed a deterministically sized graph space
with metric Cartesian distances before GIS penalty surfaces were overlaid.

**SURGE-PY-005 — capacity-constrained WTG grouping.** `app/algorithms/wtg_grouping.py` using KMeans
with greedy rebalancing, so feeders obey `feeder_capacity_mw` and cables are not overloaded.

Subsequently: SURGE-PY-014 PNC assembly, PY-015 pandapower AC load flow, PY-016 map-ready result
packaging, PY-017 deterministic candidate scenario generation, PY-019 orchestration, PY-026
canonical candidate engineering metrics, PY-028 lifecycle cost model. See
[`docs/Surge MVP Ticket Plan.md`](docs/Surge%20MVP%20Ticket%20Plan.md).
