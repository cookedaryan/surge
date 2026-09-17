# Stage 0 record — SURGE demo optimisation shared base

Date: 17 September 2026
Branch: `demo-opt/base`, from `a313d2f287aaf811ddafe765029423a361fece31`
Plan: [L3 worktree plan §3](../SURGE%20demo%20optimization%20L3%20worktree%20plan.md) · Contracts: [contracts/README.md](../../../contracts/README.md)

This is the evidence that Stage 0 met its exit criteria. Tag `demo-opt-base` only after §6 is complete.

---

## 1. WP0A-1 — environment boot

| Check | Environment | Result |
|---|---|---|
| Python lockfile install | Python 3.11.9, `uv pip install -r requirements.lock.txt`; the audit probe reports **no pin mismatches** | Pass |
| Python suite at `a313d2f` (pristine `git archive` export) | same venv | **622 passed** |
| Java `mvnw verify` at `a313d2f` | `eclipse-temurin:21-jdk` container (no local JDK) | **279 tests, 0 failures, 0 errors** |
| Frontend `npm ci`, `npm run test`, `npm run build` at `a313d2f` | `node:20` container, matching CI | **130 passed**; build succeeds |
| Frontend on the host's Node 26 | — | 94 failures: Node 26's built-in `localStorage` shadows jsdom's (`localStorage.clear` undefined in `src/test/setup.ts`). **Environmental, not a regression.** Use Node 20 as CI does |
| Clean Compose start | Isolated project `surge-stage0`, renamed containers, remapped ports, throwaway secrets; see note | **Open — network.** The frontend image built. After 19 minutes Docker Desktop could no longer resolve `registry-1.docker.io` ("no such host"), so the backend's `mvnw dependency:go-offline` and the `postgis/postgis:16-3.4` pull failed. No application code was involved. Re-run when the registry is reachable |

Note on Compose: a developer stack (`surge-optimizer-python` on :8000) and a host Postgres on :5432 were already running. The check runs as a separate project with [compose.stage0-override.yml](compose.stage0-override.yml), which renames containers, remaps ports to 55432, 18080, 18000 and 13000, and disables restart, so it neither stops nor reuses anything. The failed attempt's project resources were removed with `down -v`; the developer stack was not touched. To re-run from the repository root in Git Bash:

```bash
export APP_JWT_SECRET="$(python -c 'import secrets;print(secrets.token_urlsafe(48))')" DB_PASSWORD="$(python -c 'import secrets;print(secrets.token_urlsafe(24))')" SURGE_BOOTSTRAP_ADMIN_PASSWORD="$(python -c 'import secrets;print(secrets.token_urlsafe(24))')"
docker compose -p surge-stage0 -f docker-compose.yml -f docs/planning/stage0/compose.stage0-override.yml up -d --build --wait --wait-timeout 420
curl -fsS http://localhost:18000/api/v1/health && curl -fsS http://localhost:18080/actuator/health && curl -fsS -o /dev/null http://localhost:13000/
docker compose -p surge-stage0 -f docker-compose.yml -f docs/planning/stage0/compose.stage0-override.yml down -v
```

## 2. WP0A-2 — findings re-verified

`git diff --stat f50f717 a313d2f -- optimisation-python/app backend-java/src web-map-next/src` is empty: no implementation file changed between the audit baseline and the planning head. The audit probe was re-run on this branch ([surge_audit_probes.py](surge_audit_probes.py) → [surge_audit_probe_results.json](surge_audit_probe_results.json)); its results match the audit.

| Ref | Status | Evidence |
|---|---|---|
| F1a search unreachable | **Confirmed** | Probe `api_controls.search_request_field: false`; `CandidateSearchConfig.enabled` defaults to `False` |
| F1b micro-siting unreachable | **Confirmed** | Probe `micro_siting_request_field: false` |
| F2 ineffective personalities | **Confirmed** | 100/100 MST edge sets unchanged; PS-004 and PS-005 `duplicate_topology`; balanced seed change gives equal memberships |
| F3 repair and final conductor not published | **Confirmed** | Real repair SMALL → LARGE, final 1.00456 pu, but presentation repair log length 0 and no cable type on segment GeoJSON |
| F4 cache hit drops land | **Confirmed** | `SCN-S1-001` land present on miss, absent on hit |
| F5 truncation before screening | **Confirmed** | `candidate_search.py`: `nsmallest` shortlist is taken before duplicate and structural checks; seeds outside the evaluation budget |
| F6 no economic conductor choice | **Confirmed** | `app/electrical/cable_sizing.py` has no price or cost input |
| F7 environment identity collapses | **Confirmed and amended** | `constraints.py` maps `forest` and `environmental` to `RESTRICTED_AREA`; `ScoringMetric` has no overlap or ROW-area metric. **Amendment from WP2-1:** the Java request also drops the restriction type and the cadastral parcel ID (§4) |
| F8 poles required at zero weight | **Confirmed** | Probe `NO_FEASIBLE_CANDIDATE` with `POLE_CONFIG_MISSING` when `pole=None` |
| F9 one operating point | **Confirmed** | Source unchanged; non-claim |
| F10 land routing proxies | **Confirmed** | Source unchanged; non-claim |
| F11 uncapped routing, unbounded MILP | **Confirmed** | Child routing (`materialize_candidate_design`) precedes cache lookup and budget check; `milp` had no limit and no status reporting before Stage 0 |
| P1 scenario label not a policy | **Confirmed** | `schemas/v2/domain_mapping.py` builds `LEGACY_COMPATIBILITY`; Java `ScenarioProfile` sends four differentiated legacy weight and constraint configurations |
| E1 test gaps | **Confirmed** | Cache tests check hit counts, not semantic equality; no cohort, cross-stack truth or cold-runtime test |

No finding is struck, so no Phase 1 task is removed.

Observed in passing and outside Stage 0 scope: `RouteService` still fabricates `electricalLossesKw` (length × 0.005) and `poleCount` when a route feature lacks them. It does not affect feeder identity. Record it for WP6A-6.

## 3. WP0A-3 — TRD §6.3 feeder identity: **WP0C closed**

TRD §6.3 is stale. Current behaviour:

- Python V1 emits one `pnc_segment` Feature per routed segment, with `segment_id`, `feeder_id` and `feederName` equal to `feeder_id` (`schemas/legacy_mapping.py::_legacy_route_collection`).
- Java `RouteService.saveRoutesFromGeoJson` persists one `generated_routes` row per Feature with that `feederName` and `segmentId`.
- `ReportService.rollUpByFeeder` aggregates the BOM by `feederName`.

Executable evidence against the shared fixture `contracts/fixtures/feeder-segment-identity.json` (C11):

- Python: `tests/contracts/test_seams.py::test_v1_route_features_carry_one_segment_under_one_feeder`
- Java: `FeederSegmentIdentityContractTest` — **pass**

WP0C-1 is not triggered. WP7-1 corrects TRD §6.3 in Stage 2.

## 4. WP2-1 — G1 Java transport probe: **failed, WP2-3 active**

`OptimizationJobServiceTest.stage0TransportProbe_modeSurvivesButTypedIdentityIsNotSent` — **pass**, which documents the gap:

| Identity | Sent to Python today |
|---|---|
| Soft/hard mode | Yes, as `routing_mode` |
| Constraint handle | Yes, as `constraint_id` (`restricted-<db id>`, `parcel-<db id>`) |
| Forest/environment type | **No.** Every restricted area is `constraint_type: restricted_area`; the persisted `restrictionType` (for example `PROTECTED_AREA`) is not sent |
| Cadastral parcel ID | **No.** Parcels are named only by their database ID |

WP2-3 (L2) sends C1 `source_id` and `feature_type` and replaces the probe test. G1 cannot pass on transport until it lands.

## 5. What was built

| ID | Deliverable | Where |
|---|---|---|
| WP0B-4 | Evidence record v1, `Fingerprinter` protocol, executable reconciliation | `app/contracts/evidence.py`, `app/contracts/reconcile.py`, `contracts/schemas/evidence-v1.schema.json` |
| CON-1 | Contract pack C1–C12 | `app/contracts/`, `contracts/` ([index](../../../contracts/README.md)) |
| CON-2 | Seams S1–S10 | L3 plan §3.3 |
| Tests | Contract pack, seams, ownership map | `optimisation-python/tests/contracts/` |
| CI | `ownership` job for `demo-opt/l<n>-*` PRs | `.github/workflows/ci.yml`, `scripts/ci/check_ownership.py` |

Changes to existing files, all behaviour-neutral:

- `wtg_grouping.py`: `_run_milp` records telemetry; new `feeder_count` (reserved) and `solver_options` keywords.
- `scenarios.py`, `scenario_models.py`, `workflow_models.py`, `orchestrator.py`: solver options in and telemetry out; guard checks.
- `orchestrator.py` (close-out, from seam sign-off): forwards `config.scenario` whole to the generator instead of rebuilding it field by field, so a WP5-2 schedule setting reaches `generate_pnc_scenarios`. Guarded by `test_seams.py::test_orchestrator_forwards_every_generation_setting`.
- `candidate_search.py`: guard checks before child routing and evaluation.
- `schemas/optimise.py`, `schemas/legacy_mapping.py`: C1 and C2 attachments and response hooks.
- `api/v1/endpoints/optimise.py`, `api/v1/router.py`: resolvers, run guard, run-ID header, reserved routes.
- `core/config.py`: C5 flags.
- `gis/constraints.py`: typed identity pass-through.
- `tests/test_scenarios.py`: two `group_wtgs` fakes accept the new `solver_options` keyword.
- Java: two probe tests. Frontend: `ClaimDisclosure` stub and mount.

## 6. Exit criteria

| Criterion (L3 plan §3.4) | Status | Evidence |
|---|---|---|
| Existing Python, Java and frontend suites pass | **Pass** | Final run on this branch: Python **688 passed** (622 existing + 66 new), ruff and mypy clean, contract `--check` clean · Java `mvnw verify` **281 tests, 0 failures** (279 existing + 2 probes) · Frontend **130 passed**, build succeeds (Node 20) |
| V1 responses byte-identical before and after Stage 0 | **Pass** | 7 requests (four scenarios on the stub project, two V1-mapped fixtures, one invalid input): status codes and bodies identical to `a313d2f` |
| Contract fixtures validate; C6 hash vector reproduces | **Pass** | `tests/contracts/test_contract_pack.py`, including a fresh-interpreter drift check |
| WP0A-1 clean Compose start | **Open** | Blocked by registry DNS failure on the Stage 0 machine; re-run command in §1 |
| Seam-sufficiency sign-off by the three level leads | **Pass** | Signed off 2026-09-17 by the owner acting as L1, L2 and L3 lead. The three flagged checks: WP1-1 land assessment is restored entirely in `search_cache.py` (L2), where `CandidateEvaluationOutcome` drops it; WP2-4 parsing is covered because `avoidance_geojson` reaches `gis/constraints.py` (L3) with its properties intact; **WP5-2 schedule selection had a gap**, closed in §5 (`orchestrator.py` now forwards `config.scenario` whole) |
| WP0A-2 amendments applied to the level files | **Pass** | WP2-3 active, WP0C closed, ledger updated in all three plans |
| Owner decisions recorded | **Pass** | 2026-09-17: C12 option (a) confirmed (`contracts/decisions/wp5-v0.md`); `MAX_V1_REQUEST_BYTES` = 10 MiB confirmed. Python after close-out: **689 passed**, ruff, mypy and contract `--check` clean |
| Merge to main and tag `demo-opt-base` | **Open** | After review |

## 7. Known limits of this record

- The Compose check, once it completes, proves images build and services become healthy from a clean start. It does not run an optimisation job end to end; that is WP0B-8's harness.
- `.github/workflows/ci.yml` is edited on this branch, so the new `ownership` job and the contract tests run in CI only after this PR is opened. They were run locally.
- The audit probe was re-run on this branch, not on `a313d2f`. Because Stage 0 is byte-identical on V1 and adds only null seams, results are the same, and they match the audit's published values.
- Region ownership in `wtg_grouping.py` is not enforceable by path; reviewers check it.
