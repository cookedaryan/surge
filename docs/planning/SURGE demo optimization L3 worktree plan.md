# SURGE demo optimization — L3 worktree plan

Date: 17 September 2026
Status: Final execution split; planning only, no implementation authority
Level: **L3 — contracts, identity and claim semantics**
Worktrees: `demo-opt/base` (Stage 0), then `demo-opt/l3-semantics` (Phase 1)
Planning head: `a313d2f287aaf811ddafe765029423a361fece31`
Sibling files: [L1 worktree plan](SURGE%20demo%20optimization%20L1%20worktree%20plan.md) · [L2 worktree plan](SURGE%20demo%20optimization%20L2%20worktree%20plan.md)

---

## 1. Shared frame

> This section is identical in the L1, L2 and L3 files. Change all three together.

**Sources.** The technical source of truth is [draft 0.6](SURGE%20demo%20optimization%20work%20plan.md). Its gates G0–G4, acceptance gates, evidence contract, rollback rules and §11 package order are unchanged. This split replaces the worktree layouts in the [execution plan](SURGE%20demo%20optimization%20execution%20plan.md) ("Plan 2") and in the lane-ledger review ("Plan 1"). The decisions that reconcile them are in [L3 §10](SURGE%20demo%20optimization%20L3%20worktree%20plan.md#10-decisions-reconciling-plan-1-and-plan-2).

**What a level is.** A level is one worktree, and its complexity band is set by its hardest task. Tasks are first grouped by dependency, and each group goes to the band of its hardest task. A task may move **up** a band to stay with its chain. It moves **down** only when it was split and the hard part stayed in the higher band (WP3-9b, WP4-9b). A split by the original tags alone cannot work, because at least 12 dependency edges cross tags (L3 §10, row 2).

**Timeline.**

```
Stage 0 — shared base: one worktree, sequential, led by the contract authority
          WP0A-1..3 · WP2-1 probe · WP0B-4 · CON-1 contract pack · CON-2 seams
          merge to main, tag demo-opt-base
                 │
     ┌───────────┼───────────┐
     L1          L2          L3        Phase 1: parallel worktrees branched from demo-opt-base;
     │           │           │         no level depends on another level
     └───────────┼───────────┘
                 │  package PRs merge through one queue, in draft 0.6 §11 order
Stage 2 — release train on main, sequential
          re-verify · FRZ-1 · (WP5B) · WP6A · RC freeze · WP6B · bundle · WP6C · WP7
```

**Independence rules for Phase 1.**

1. A level uses only the `demo-opt-base` tag, owner gate decisions and its own commits. It never uses another level's branch, PR, output or artefact.
2. A level edits only the paths in its `contracts/ownership/L<n>.globs`. The CI ownership check fails any PR that touches another path.
3. Everything under `contracts/` and every item on the frozen list (L3 §3.3) is read-only. If a contract is wrong or missing, raise a contract change request (CCR). The contract authority lands the fix on main, and all three levels rebase. A CCR is the only sanctioned cross-level event, and each one is logged in `contracts/CHANGELOG.md`.
4. When a seam's real implementation belongs to another level, test against the contract fixture or inject a fake. Never call a stub that raises `NotImplementedError`.
5. The merge queue orders merges, not work. A finished PR waits for its slot, but no level waits to start.
6. Gates block tasks, not levels. When a gate slips, the level moves to its ungated tasks and the draft 0.6 §5 default applies.

**Merge queue.** When its slot opens, each PR rebases onto main. It must then pass the full Python, Java and frontend suites, the V0 golden suite, contract-fixture conformance and count reconciliation. No PR may rely on a later PR.

| Slot | Package (§11 order) | PRs, by level |
|---|---|---|
| 0 | Base | Stage 0 (WP0C-1 was not triggered) |
| 1 | Baseline evidence | L1 `baseline-characterisation` · L2 `baseline-measurement` · L3 `baseline-identity` |
| 2 | WP1 candidate truth | L2 `wp1-truth` |
| 3 | WP4 bounded search | L2 `wp4-search` · L2 `wp4-java-timeout` · L3 `wp4-cancellation` |
| 4 | WP5 generation | L3 `wp5-generation` |
| 5 | WP2 claim metrics | L3 `wp2-metrics` · L2 `wp2-java-transport` (active: the WP2-1 probe failed) |
| 6 | WP3 profiles | L3 `wp3-profiles` · L2 `wp3-java-profiles` |
| 7+ | Stage 2 | Release train below |

If G2 has not passed, slot 3 is skipped and search stays disabled. If G0 has not passed, slots 5 and 6 wait. Neither case blocks a later slot that is ready, because no Phase 1 PR depends on another package's code.

**Stage 2 release train.** Every step starts from merged main. Stage 2 exists to verify the merged whole, so it is sequential and the Phase 1 independence rules do not apply. A defect found in Stage 2 goes back as a fix PR to the level that owns the path.

| Step | Work | Executor | Starts when |
|---|---|---|---|
| S2-1 | Blinded re-run on merged main: baseline-vs-merged distributions and counts, reconciliation, cache miss/hit equivalence, fingerprint stability, cohort build with exclusion counts and distinct eligible topologies, golden `k+1` evidence, golden cost recomputation | L2 runs it as evidence operator; L3 reviews it as release captain | Slot 6 merged |
| S2-2 | FRZ-1: policy freeze commit, Java expected definition hash, unblinding record | L1 records it; the scoring approver decides | S2-1 passes; G0; G4 |
| S2-3 | WP5B-1 → WP5B-2 → WP5B-3 | L3, L3, L2 | FRZ-1; only if G4 = live |
| S2-4 | Merge WP6A-1, WP6A-2, WP6A-3 | L1, L2, L2 | FRZ-1, and S2-3 if it runs |
| S2-5 | WP6A-4 → WP6A-5 | L2 | S2-4 |
| S2-6 | WP6A-6 → WP6A-7 | L3 | WP6A-5 |
| M1 | Release-candidate core-behaviour freeze | Release captain | WP6A-7 |
| S2-7 | Merge WP6B: 6B-2 → 6B-1 → 6B-3 → 6B-4 | L2 | M1; G3 |
| M2 | Record the final validated bundle | Release captain | S2-7 passes |
| S2-8 | WP6C-1 → WP6C-2 | L2 | M2, or M1 when live-only |
| S2-9 | WP6C-3 (only if recorded mode is in scope) → WP6C-4 | L1 | WP6C-2 |
| S2-10 | WP7-1..7-4 → WP7-5 | L1 | WP6C-4 |

**Ledger.** Unconditional tasks, with conditional tasks in brackets.

| | Stage 0 | L1 | L2 | L3 | Total |
|---|---:|---:|---:|---:|---:|
| Phase 1 | — | 6 | 31 | 18 | 55 |
| Stage 2 | — | 8 | 4 [+1] | 2 [+2] | 14 [+3] |
| Stage 0 | 7 | — | — | — | 7 |
| **Total** | **7** | **14** | **35 [+1]** | **20 [+2]** | **76 [+3] = 79** |

The 80 planned tasks are Plan 2's 74, plus CON-1 and CON-2, plus four splits (WP3-6, WP3-7, WP3-9, WP4-9) that each add one task. Stage 0 settled two conditions: the WP2-1 probe failed, so WP2-3 is now unconditional, and WP0A-3 closed WP0C, which leaves the ledger. The only remaining conditional tasks are the three WP5B tasks (G4 = live). RC freeze and bundle recording are milestones, not tasks.

**Indicative effort.** Pro-rated from the draft 0.6 package estimates, before contingency.

| Stream | Engineer-days |
|---|---|
| Stage 0 | 2–3 (WP0C not triggered) |
| L1 | Phase 1: 1–2 · Stage 2: 1.5–2.5 |
| L2 | Phase 1: 5.5–10 (includes WP2-3; +1–2.5 if WP6B is pre-built) · Stage 2: 1.5–3 |
| L3 | Phase 1: 4.5–8 · Stage 2: 1–2 (+3.5–5.5 if WP5B) |

Calendar time ≈ Stage 0 + max(L2, L3) + Stage 2. L1 is light on purpose, because backfilling it with L2 work is exactly what recreates cross-level coupling. L1 can use spare time to draft the WP6C-4 runbook and the WP7 change list, but neither draft merges before its Stage 2 step.

---

## 2. Mission

L3 owns the work where a subtle mistake would invalidate either the claim or the contract the other levels build on:

- **Stage 0 contract authority.** Builds the shared base and resolves every CCR during Phase 1.
- **Canonical identity.** Geometry and final-design fingerprints, and the controlled-cohort runner.
- **Generation.** Gates the ineffective personalities and adds the explicit `k+1` candidate.
- **Claim metrics.** Carries typed environment identity from the parser through to metrics, adds both canonical spatial metrics, and computes their contributions.
- **Scoring semantics.** Profile registry, fixed reference ranges, stable errors, the Python half of the handshake and echo, and Python producer conformance.
- **Search cancellation.** Python worker cancellation and state isolation.
- **Stage 2.** Release captain, cross-stack truth, and the compatibility matrix.

L3 is also the **scoring owner**. It uses synthetic fixtures only until FRZ-1 and never runs golden-project measurement. That work belongs to L2 as evidence operator, which keeps the draft 0.6 §4.3 blinding separation intact.

---

## 3. Stage 0 — shared base (runs before any level worktree exists)

Stage 0 is not a level. It is the common ancestor every level consumes. It runs in one worktree, and L1 and L2 executors may staff it, but L3 leads as contract authority. It makes **no behaviour change**.

**As built** on branch `demo-opt/base`. Results and evidence are in the [Stage 0 record](stage0/README.md); the contract index is [contracts/README.md](../../contracts/README.md). This section describes what exists, not a proposal.

### 3.1 Tasks

| ID | Task | Tag | Depends on | Exit evidence | Result |
|---|---|---|---|---|---|
| WP0A-1 | Boot the lockfile environment; clean Compose start | L1 | — | Clean-start log and targeted build test | See Stage 0 record §1 |
| WP0A-2 | Re-verify F1–F11, P1, E1 | L2 | WP0A-1 | Finding matrix. A struck or amended finding removes or amends its Phase 1 tasks in these three files **before branching** | All confirmed, none struck; F7/G1 amended by WP2-1 |
| WP0A-3 | Verify TRD §6.3 feeder/segment identity; trigger or close WP0C | L2 | WP0A-2 | Contract probe plus a recorded decision; C11 fixture drafted | TRD stale; C11 holds in Python and Java; **WP0C closed** |
| WP2-1 | G1 Java transport probe: source ID, type, soft/hard mode | L1 | WP0A-1 | Pass drops WP2-3; failure activates WP2-3 in L2 | **Failed**: mode survives, type and cadastral ID do not; **WP2-3 active** |
| WP0B-4 | Evidence schema v1 with executable reconciliation checks | L2 | WP0A-2 | C4 artefacts; example record validates; equations run as tests | Done |
| CON-1 | Contract pack (§3.2) | L3 | WP0A-2, WP0A-3, WP2-1, WP0B-4 | C1–C12 committed; every fixture validates against its schema | Done |
| CON-2 | No-behaviour seams and ownership CI (§3.3) | L2 | CON-1 | Stage 0 exit (§3.4) | Done |
| WP0C-1 | *(Conditional)* Repair the feeder/segment identity contract across stack | L3 | WP0A-3 triggered | One Feature = one routed segment under one feeder across Python, Java DTO/persistence, UI and BOM/export; C11 is final | Not triggered |

### 3.2 CON-1 contract pack

CON-1 freezes names, shapes, null semantics, codes and fixtures. It does **not** freeze values. Policy values are set at FRZ-1, and cap and timeout values at G2.

Python models in `optimisation-python/app/contracts/` are authoritative. Every JSON artefact under `contracts/` is generated from them by `python -m scripts.contracts.export_contracts`, and a test fails on drift.

| ID | Artefact | Freezes | Consumed in Phase 1 by |
|---|---|---|---|
| C1 | V1 request additions: `app/contracts/request.py`, `contracts/request-rules.json`, `contracts/schemas/v1-request-*.schema.json`, `contracts/fixtures/request/` | `profile {id, version}`; typed identity as avoidance-feature properties `{source_id, feature_type, routing_mode}`; allow-listed generation settings Java may send; maximum payload size; absent = V0; explicit unknown version = reject | L1 WP3-2, WP4-2 · L2 WP0B-3, WP2-3, WP3-5 · L3 WP2-4, WP3-1, WP3-4 |
| C2 | V1 response additions: `app/contracts/response.py`, `contracts/response-rules.json`, `contracts/schemas/v1-response-*.schema.json`, `contracts/fixtures/response/additive-blocks.json` | Blocks `design_truth` (final conductor per segment, repair actions, sizing-basis label), `search_evidence`, `solver_runs`, `scoring_explanation` (raw, reference range, normalised, weight, contribution, with generation penalties separate), `effective_profile` (IDs, hashes, flags) and `termination`. A block is **absent** when not produced. Also freezes the diagnostic/timestamp exclusion list for golden comparison | L1 goldens · L2 WP1, WP4, WP3-7b, WP6A-2 · L3 WP0B-6, WP2-7, WP3-7a |
| C3 | Code registry: `app/contracts/codes.py`, exported to `contracts/codes.json` | Request error codes; termination reasons; evaluation failure, incompleteness and exclusion codes; `k+1` outcome codes; Java job states including `TIMED_OUT` and `CANCELLED` | All levels |
| C4 | Evidence schema v1 (WP0B-4): `app/contracts/evidence.py`, `app/contracts/reconcile.py`, `contracts/schemas/evidence-v1.schema.json`, `contracts/fixtures/evidence/` | §8 field dictionary; count vocabulary; the four reconciliation equations as executable checks; fingerprint value format and canonicaliser-version fields; `Fingerprinter` protocol; solver telemetry fields | L2 baseline, WP4-7, WP3-8 · L3 WP0B-6/7/11, WP5-4 |
| C5 | Flags and gating: `app/core/config.py` | `SURGE_PROFILES_ENABLED` and `SURGE_SEARCH_ENABLED` (`Settings.surge_profiles_enabled`, `surge_search_enabled`), default off and server-side only. Generation-schedule gating rule: **new schedule only when either flag is on**, so both-off stays V0 | L1 WP4-2 · L2 WP4-1 · L3 WP5-2, WP3-7a |
| C6 | Profile contract: `app/contracts/profiles.py`, `app/contracts/canonical_json.py`, `contracts/profiles/` | Four profile IDs and versions; definition-file schema, which is the FRZ-1 values format; canonical-JSON + SHA-256 definition-hash algorithm with a test vector | L2 WP3-5, WP3-6b · L3 WP3-4, WP3-6a |
| C7 | Transport: `contracts/transport.md` | Run-ID header; cancel path; definition-hash path; Java outer-timeout semantics (close the call, then call cancel) | L2 WP4-9b, WP3-6b · L3 WP4-9a, WP3-6a |
| C8 | Recorded mode: `app/contracts/recorded_bundle.py`, `contracts/recorded-mode.json`, `contracts/schemas/recorded-bundle-v1.schema.json` | Bundle manifest (request, profile, code, image, catalogue and schema hashes, plus winner fingerprints); frontend live/recorded state names | L2 WP6B |
| C9 | Persistence: `contracts/persistence.md` | Flyway reservations in merge order — V21 WP4-9b, V22 WP2-3, V23 WP3-7b, V24 WP5B-3, V25 WP6A-3, V26 WP6B (main is at V20) — plus column names for hashes, flags, termination and cohort ID. Changes are expand/contract | L2 |
| C10 | Ownership: `contracts/ownership/L{1,2,3}.globs`, `contracts/frozen.txt` | Paths per level (§6 in each file); frozen files and symbols (§3.3) | All levels |
| C11 | Feeder/segment identity: `contracts/fixtures/feeder-segment-identity.json` | One Feature = one routed segment under one feeder, from WP0A-3 or WP0C-1 | L2 WP3-9b · L3 WP3-9a |
| C12 | WP5 V0 decision: `contracts/decisions/wp5-v0.md` | Option **(a)**, gate the new schedule, confirmed by the owner. Option (b), intentional re-baseline, is a CCR | L1 goldens · L3 WP5-2 |

### 3.3 CON-2 seams and frozen list

A seam is a no-behaviour code shape that lets two levels implement opposite sides of an interface without editing the same file.

| ID | Seam | Implemented in Phase 1 by |
|---|---|---|
| S1 | Contract models live in frozen `app/contracts/`. `app/schemas/optimise.py` only attaches them: `OptimisationRequest.profile` and the six optional response blocks. `app/gis/constraints.py::ConstraintLayer` gains optional `source_id` and `feature_type`, passed through unvalidated from avoidance-feature properties | L2, L3 |
| S2 | `app/api/v1/endpoints/optimise.py` calls `resolve_profile()` in `app/optimisation/profiles/resolve.py` (L3; the stub returns V0 when the field is absent and raises `PROFILE_NOT_SUPPORTED` when present) and `resolve_search_activation()` in `app/optimisation/search_activation.py` (L2; the stub returns disabled). Each returns a resolution from `app/contracts/resolution.py` whose `configure` transforms the workflow config. `ContractError` maps to `{"detail": {"code", "message"}}` | L3, L2 |
| S3 | `app/schemas/legacy_mapping.py::to_legacy_api_response` (frozen) fills the response blocks from hooks that receive the workflow result and a `ResponseContext`: `presentation/design_truth.py` and `presentation/search_evidence.py` (L2: design truth, search evidence, solver runs, termination) and `presentation/explanation.py` and `presentation/profile_echo.py` (L3). Stubs return `None`, so blocks stay absent | L2, L3 |
| S4 | `app/optimisation/run_guard.py` (frozen) defines `RunGuard`, `CompositeRunGuard`, `build_run_guard`, and the stop signals `AdmissionDeadlineReached` and `RunCancelledError`. A guard **raises** to stop, so each owner reacts in its own files. `deadline_guard.py` (L2) and `cancellation.py` (L3) are null guards. Checks run at `BEFORE_SEED_GENERATION` and `BEFORE_SEED_EVALUATION` in `orchestrator.py` and `BEFORE_CHILD_ROUTING` and `BEFORE_CHILD_EVALUATION` in `candidate_search.py`. The orchestrator's broad `except Exception` re-raises stops. The endpoint maps `RunCancelledError` to 409 and an unhandled stop to 503 | L2, L3 |
| S5 | `app/algorithms/solver_models.py` (L2) defines `SolverOptions` and `SolverTelemetry`. Stage 0 **already records** status, wall time and gap for every MILP solve but applies no limits. Options travel `OptimisationConfig.solver` → `ScenarioGenerationConfig.solver_options` → `group_wtgs(solver_options=...)`; telemetry returns as `FeederGroupingResult.solver_runs` and `ScenarioGenerationResult.solver_runs` (both excluded from equality). A non-null `feeder_count` raises until WP5-3. **Region ownership:** L2 owns `_run_milp` and the `_solve_milp_*` bodies; L3 owns the feeder-count selection in `group_wtgs` | L2, L3 |
| S6 | Stubs `app/evidence/fingerprints/topology.py` (L2), `geometry.py` and `final_design.py` (L3), and `app/evidence/cohort.py` (L3), typed against `app/contracts/evidence.py::Fingerprinter` | L2, L3 |
| S7 | `app/api/v1/router.py` registers `POST /runs/{run_id}/cancel` and `GET /profiles/definition-hash`. Handlers live in `endpoints/runs.py` and `endpoints/profiles.py` (L3) and answer 501 `NOT_IMPLEMENTED` | L3 |
| S8 | `app/contracts/metric_registry_version.py` (L3, the one editable file under `app/contracts/`); `EVIDENCE_SCHEMA_VERSION` in `app/contracts/evidence.py`; the pipeline version in `search_cache.py` (L2). WP1-3 adds all three to the cache context | L2, L3 |
| S9 | `web-map-next/src/features/optimization/ResultsSheet.tsx` (L2) mounts `ClaimDisclosure.tsx` (L1; the stub renders nothing) at the top of the Decision tab | L1 |
| S10 | `scripts/ci/check_ownership.py` and the `ownership` job in `.github/workflows/ci.yml`, which runs on PRs from `demo-opt/l<n>-*` branches | — |

**Frozen paths.** The authoritative list is `contracts/frozen.txt`; the ownership check enforces it. In summary: `contracts/**`, `app/contracts/**` except `metric_registry_version.py`, `app/schemas/optimise.py`, `app/schemas/legacy_mapping.py`, `app/api/v1/endpoints/optimise.py`, `app/api/v1/router.py`, `app/core/config.py`, `app/optimisation/run_guard.py`, `app/optimisation/workflow_models.py`, `scripts/contracts/**`, `tests/contracts/**`, the Python dependency files, `scripts/ci/**`, `.github/workflows/**`, and these planning documents.

**Frozen symbols.** These live in owned files, but another level relies on them:

| Symbol | Owner file (level) | Relied on by |
|---|---|---|
| `scenarios._apply_long_edge_penalty(graph, alpha)` | L3 | L1 WP5-1 |
| `group_wtgs` signature and `FeederGroupingResult.solver_runs` | shared regions | L2 WP4-6, L3 WP5-3 |
| Solver option threading in `scenarios.py` and `orchestrator.py` | L3, L2 | L2 WP4-6 |
| `orchestrator.py` forwards the whole `config.scenario` (overriding only `project_id` and `solver_options`) to `generate_pnc_scenarios`; guarded by `test_orchestrator_forwards_every_generation_setting` | L2 | L3 WP5-2 |
| Guard checks in `candidate_search.py` and `orchestrator.py` | L2 | L3 WP4-9a |
| `METRIC_REGISTRY_VERSION` name | L3 | L2 WP1-3 |
| `ClaimDisclosure` mount in `ResultsSheet.tsx` | L2 | L1 WP6A-1 |

### 3.4 Stage 0 exit

- All existing Python, Java and web-map-next suites pass unchanged.
- V1 responses for every fixture in `optimisation-python/tests/fixtures/` are byte-identical before and after Stage 0, apart from the C2 exclusion list.
- Every contract fixture validates against its schema, and the C6 hash vector reproduces.
- **Seam-sufficiency sign-off.** Each level lead walks every one of their Phase 1 tasks and confirms that its owned paths plus the frozen artefacts are enough. Any gap becomes a new seam before the tag. `orchestrator.py` (L2) and `candidate_evaluation.py` (L3) get explicit checks for WP5 schedule selection, WP1-1 land assessment and WP2-4 parsing.
- The WP0A-2 amendments are applied to the three level files.
- Merge to main and tag `demo-opt-base`.

---

## 4. Phase 1 tasks

"Tag" is the Plan 1 complexity tag, where ↑ means the task moved up to stay with its chain. Every input comes from Stage 0 (Cn/Sn), a gate, or another L3 task.

### 4.1 Identity and cohort — PR `baseline-identity`, slot 1

| ID | Task | Tag | Gate | Inputs | Exit evidence |
|---|---|---|---|---|---|
| WP0B-7 | Geometry fingerprint canonicaliser | L3 | — | C4 format and version field; S6 `geometry.py` | Declared CRS, axis order, units, precision quantisation, orientation and empty-geometry rules; versioned golden vectors; repeat-determinism test |
| WP0B-6 | Final-design fingerprint | L2↑ | — | WP0B-7; C2 `design_truth` fixture | Geometry fingerprint + final installed conductors + versioned installed fields; vectors prove that changing only a conductor changes the fingerprint |
| WP0B-11 | Controlled-cohort runner | L3 | — | WP0B-6; C4 exclusion codes and `Fingerprinter` protocol | Union → dedup by final-design fingerprint → keep the lowest sorted candidate ID and record discarded lineages → exclusion counts per code, checked against the maximum rate. The distinct-topology count uses an **injected** fingerprinter; tests inject required-metric sets |

### 4.2 Search cancellation — PR `wp4-cancellation`, slot 3

| ID | Task | Tag | Gate | Inputs | Exit evidence |
|---|---|---|---|---|---|
| WP4-9a | Python worker cancellation and state isolation (split from WP4-9) | L3 | G2 | C3 `cancelled`; C7 run ID and cancel path; S4 `cancellation.py`; S7 route stub | A cancel request makes the guard stop at the next check; no partial candidate is cached or published; the next run in the same process inherits no state (public cache API only). Tests use a null deadline guard and never L2's deadline guard |

### 4.3 Generation — PR `wp5-generation`, slot 4

| ID | Task | Tag | Gate | Inputs | Exit evidence |
|---|---|---|---|---|---|
| WP5-2 | Gate ineffective personalities; record the V0 decision | L2↑ | F2/F6 confirmed | C5 gating rule; C12; frozen `_apply_long_edge_penalty` | New schedule sits behind the C5 rule; the transform is gated, not deleted; decision record written. If C12 chose (b), the golden re-baseline goes through a CCR |
| WP5-3 | Deterministic, capacity-valid `k+1` candidate | L3 | F2/F6 confirmed | S5, L3 region only | `feeder_count` override implemented; schedule emits a `k+1` candidate when capacity-valid; `solver_options` pass through untouched, since limits belong to L2; deterministic fixture |
| WP5-4 | `k+1` acceptance/failure evidence | L2↑ | F2/F6 confirmed | WP5-3; C3 `k+1` codes; C4 | Synthetic success and failure fixtures (infeasible `k+1`; `k+1` duplicating the `k` topology). Golden-project evidence is produced blinded in S2-1 |

### 4.4 Claim metrics — PR `wp2-metrics`, slot 5

| ID | Task | Tag | Gate | Inputs | Exit evidence |
|---|---|---|---|---|---|
| WP2-4 | Typed forest/environment identity through parser → ROW → metrics | L3 | F7; G0 | C1 typed-identity fixture; S1 `ConstraintLayer` fields | Aliases map to canonical types without collapsing; source ID, type and soft/hard mode reach ROW analysis and metric inputs; end-to-end fixture. The centreline-only hard-violation check stays unchanged and disclosed |
| WP2-5 | `affected_parcel_row_area_m2` canonical metric | L2↑ | F7; G0 | WP2-4 | Deterministic area fixture; `METRIC_REGISTRY_VERSION` bumped |
| WP2-6 | Unique `environmental_overlap_m2` canonical metric | L2↑ | F7; G0 | WP2-4 | Overlapping layers are counted once |
| WP2-7 | Raw, normalised and weighted contributions | L2↑ | F7; G0 | WP2-5, WP2-6; C2 `scoring_explanation`; S3 `explanation.py` | Output equals the C2 fixture shape, with explicit ranges |
| WP2-8 | Land/environment causal-ranking fixtures | L2↑ | F7; G0 | WP2-7 | Synthetic end-to-end: changing only the land or environment input changes rank as declared; zero weight removes the effect |

### 4.5 Profiles — PR `wp3-profiles`, slot 6

| ID | Task | Tag | Gate | Inputs | Exit evidence |
|---|---|---|---|---|---|
| WP3-4 | Profile registry mechanism | L2↑ | G0 | C6; S2 `resolve.py` | Four versioned placeholder definitions with the §7 structure: Balanced has non-zero land, environment and cost terms; Minimum Land uses a lexicographic tolerance band. Values stay placeholders until FRZ-1 |
| WP3-3 | Fixed reference ranges; remove-a-loser invariant | L3 | G0 | WP3-4, WP2-7 | No cohort min–max normalisation; removing any non-winner leaves every profile's winner unchanged |
| WP3-1 | Stable errors for invalid inputs | L1↑ | G0 | WP3-4; C3; S2 handler | Unknown profile, version or metric, non-finite, out-of-range and oversized payload all map to stable codes; never falls back to Balanced |
| WP3-6a | Python definition-hash endpoint (split from WP3-6) | L2↑ | G0 | WP3-4; C6 vector; C7; S7 | Endpoint returns the C6 hash; the test vector reproduces |
| WP3-7a | Echo effective profile, hashes and both flags (split from WP3-7) | L2↑ | G0 | WP3-4; C2 `effective_profile`; C5; S3 `profile_echo.py` | Profile ID/version, policy hash, metric-registry version, generation-settings hash and both flag states match the C2 shape |
| WP3-9a | Python producer conformance (split from WP3-9) | L3 | G0 | WP3-6a, WP3-7a, WP2-7; C1, C2, C11 | Python round-trips every contract fixture in canonical JSON, including the feeder/segment fixture |

---

## 5. Execution order and gates

```
demo-opt-base ─► 0B-7 → 0B-6 → 0B-11                         no gate: start here
              ─► 5-2 → 5-3 → 5-4                              F2/F6 confirmed
              ─► 2-4 → {2-5, 2-6} → 2-7 → 2-8                 G0 (and G4 recorded)
              ─► 3-4 → 3-3 → 3-1 → 3-6a → 3-7a → 3-9a         G0; 3-3 after 2-7
              ─► 4-9a                                          G2
```

If G0 slips, finish identity, generation and WP4-9a first. No claim-aligned policy work starts until G0 passes. If G2 slips, WP4-9a is deferred along with the rest of slot 3.

---

## 6. Ownership (`contracts/ownership/L3.globs`)

Python paths are relative to `optimisation-python/`.

- `app/optimisation/scoring.py`, `scoring_models.py`, `engineering_metrics.py`, `engineering_metric_models.py`, `candidate_evaluation.py`
- `app/optimisation/scenarios.py`, `scenario_builder.py`, `scenario_models.py`
- `app/optimisation/profiles/**`, `app/optimisation/cancellation.py`
- `app/gis/constraints.py`, `app/gis/preprocessing.py`, `app/gis/row_analysis.py`, `app/land/**`
- `app/presentation/explanation.py`, `app/presentation/profile_echo.py`
- `app/api/v1/endpoints/runs.py`, `app/api/v1/endpoints/profiles.py`
- `app/contracts/metric_registry_version.py`
- `app/evidence/fingerprints/geometry.py`, `app/evidence/fingerprints/final_design.py`, `app/evidence/cohort.py`
- `app/algorithms/wtg_grouping.py`, **feeder-count selection region of `group_wtgs` only**
- Tests for the above: `tests/test_optimisation_scoring.py`, `tests/test_scenarios.py`, `tests/test_row_analysis.py`, `tests/test_land_decision.py`, `tests/test_constraints.py`, `tests/test_engineering_metrics.py`, `tests/test_candidate_evaluation_defects.py`, and new `tests/evidence/test_{geometry,final_design,cohort}*.py`, `tests/profiles/**`, `tests/generation/**`, `tests/test_cancellation*.py`

L3 edits nothing in `backend-java/` or `web-map-next/`. Where this list and `contracts/ownership/L3.globs` differ, the globs file wins.

---

## 7. Dependency audit

| L3 task | Something it might seem to need from another level | Why it does not |
|---|---|---|
| WP0B-6 | Final conductor IDs published by L2 WP1-5 | The canonicaliser consumes the C2 `design_truth` shape, and its tests use the C2 fixture |
| WP0B-11 | L2's topology canonicaliser | The fingerprinter is injected through the C4 protocol; real wiring is exercised in S2-1 |
| WP4-9a | L2's deadline guard and cache changes | S4 composite guard, tested with a null deadline guard; only the public cache API is used |
| WP5-3 | L2's MILP limits (WP4-6) | S5 threads `solver_options` through unchanged; limits change solver behaviour, not the feeder-count contract |
| WP5-2 | L1's V0 goldens | C12 fixes the V0 decision in Stage 0, and L3 keeps V0 by construction (C5 gate) |
| WP2-4 | L2's Java transport (WP2-3) | Python reads the C1 fixture; Java serialisation is proven separately against the same fixture |
| WP2-7, WP3-7a | A change to the response builder | S3 hooks in `explanation.py` and `profile_echo.py` are L3-owned; the frozen `legacy_mapping.py` already calls them |
| WP1-3 impact | L2 must bump the cache version when metrics change shape | L3 bumps `METRIC_REGISTRY_VERSION`, which the cache context already reads (S8) |
| WP3-3 | L2's blinded distributions (WP0B-10) | Ranges are placeholders until FRZ-1 in Stage 2 |
| WP3-6a | L2's Java handshake | The C6 hash vector is the shared oracle |
| WP3-9a | L2's Java consumer tests | Both sides test against the same frozen fixtures |

---

## 8. PRs

| PR | Slot | Tasks | Rollback statement |
|---|---|---|---|
| `baseline-identity` | 1 | WP0B-7, WP0B-6, WP0B-11 | Library and tests only; no runtime path |
| `wp4-cancellation` | 3 | WP4-9a | Cancel route returns `not_implemented` on revert; the null guard is restored |
| `wp5-generation` | 4 | WP5-2, WP5-3, WP5-4 | Both flags off = V0 schedule |
| `wp2-metrics` | 5 | WP2-4 … WP2-8 | Legacy defaults unchanged; the metric-registry version bump invalidates caches |
| `wp3-profiles` | 6 | WP3-4, WP3-3, WP3-1, WP3-6a, WP3-7a, WP3-9a | Profile flag off = V0; an explicit profile fails closed |

Each PR carries narrow tests, contract conformance, and a statement that V0 goldens pass with both flags off.

---

## 9. Stage 2 tasks owned by L3

| ID / role | Task | Tag | Starts when | Exit evidence |
|---|---|---|---|---|
| Release captain | Review S2-1 blinded output against §9 gates; declare M1 and M2 | — | Slot 6 merged | Signed S2-1 review; M1 tag; M2 bundle hash |
| WP5B-1 *(if G4 = live)* | Split the evaluation context from the scoring context | L3 | FRZ-1 | Same physics, land, cost, layer and pole inputs restore raw metrics across policies |
| WP5B-2 *(if G4 = live)* | Run all generation configs; union, dedup, and score under four policies | L3 | WP5B-1 | Common cohort and final-design dedup test |
| WP6A-6 | Final conductor and repair truth end to end | L3 | WP6A-5 | One final design agrees across electrical config, costing, Python response, GeoJSON, Java persistence, UI and export, binding only C2 fields |
| WP6A-7 | Compatibility matrix | L3 | WP6A-6 | Current/new Python × Java × frontend, including current Java with new frontend; unsupported combinations recorded |

---

## 10. Decisions reconciling Plan 1 and Plan 2

| # | Topic | Plan 1 | Plan 2 | Final decision | Why |
|---:|---|---|---|---|---|
| 1 | Worktree basis | Dependency lanes A/B/C; says the split "doesn't sort by complexity" | Domain lanes WT-A/B/C; "not independent dependency chains" | Three complexity levels over dependency groups, plus a thin Stage 0 and a sequential Stage 2 | Both drafts keep cross-lane waits: Lane B rebases onto WP4 and WP3-7 onto WP4 (Plan 1); WT-B waits for the WT-A solver handover (Plan 2) |
| 2 | Split by original tag | — | — | Rejected | Cross-tag edges: 0B-2(L1)→0B-5(L2) · 0B-6(L2)→0B-7(L3) · 0B-11(L3)→0B-5/0B-6(L2) · 3-1(L1)→3-4(L2) · 3-3(L3)→2-7(L2) · 2-5/2-6(L2)→2-4(L3) · 5-3(L3)→4-6(L2) · 5-4(L2)→5-3(L3) · 4-9(L3)→4-4/4-7(L2) · 6B-1(L1)→6B-2(L2) · FRZ-1(L1)→0B-10(L2) · WP7(L1)→WP6C(L2) |
| 3 | Contract freeze | CON-1 freezes names only (L2) | Owning packages (WP3, WP4, WP6B) define contracts | CON-1 freezes names, shapes, codes, fixtures, the hash vector, migration numbers and ownership (L3), and CON-2 adds no-behaviour seams | Names alone leave shapes, null semantics and file placement to be found at merge; Plan 2's owners would write contracts after branching |
| 4 | WP0B-4 evidence schema | Base | Phase 0 | Stage 0 | Every level writes or reads evidence |
| 5 | Shared hotspots | Owner table plus rebases | Exclusive owner plus time-boxed handovers | Per-level submodules behind frozen attachment files; region ownership only in `wtg_grouping.py` | A handover is a cross-level dependency |
| 6 | Solver API | WP4-6 owns it; Lane B consumes after merge | WT-A owns it until merged | S5 seam: L2 adds limits and telemetry, L3 adds the feeder-count override | Removes the WP5 → WP4 wait |
| 7 | WP4-9 | One L3 task | One task | WP4-9a Python cancellation (L3); WP4-9b Java outer timeout plus persisted **and rendered** job state (L2) | Separates the stacks; WP6A-5 becomes verification only |
| 8 | WP3-6, WP3-7, WP3-9 | Single tasks | Single tasks | "a" = Python (L3), "b" = Java (L2) | L2 owns all of `backend-java`; fixtures and hash vector are frozen in Stage 0 |
| 9 | FRZ-1 position | After WP3 | Before WP1 merges | After slot 6 and S2-1, before any golden winner is unblinded | The definition hash needs WP2 metrics and the WP3 registry to exist; §4.3 requires freeze before unblinding, not before behaviour merges |
| 10 | Blinding separation | Not addressed | Scoring owner works on synthetic data | Every golden run before FRZ-1 belongs to L2 (evidence operator); L3 (scoring owner) sees blinded reports only | Keeps the §4.3 operator/owner separation |
| 11 | WP5 V0 decision | Taken in WP5-2 | Taken in WP5-2 | Taken in Stage 0 (C12); default is (a) gate | L1's V0 goldens need the answer before branching |
| 12 | WP6B order | 6B-1 last | 6B-2 depends on 6B-1 | 6B-2 → 6B-1 → 6B-3 → 6B-4 | The re-record guard compares the validator's hashes |
| 13 | WP6C numbering | 6C-1 drill, 6C-2 runbook, 6C-3 cold, 6C-4 failure | 6C-1 cold, 6C-2 failure, 6C-3 drill, 6C-4 runbook | Plan 2 IDs; Plan 1 tags matched by description | Plan 2 is the auditable ledger |
| 14 | Java expected definition hash | — | — | A config value set at FRZ-1 | The real value exists only after the freeze |
| 15 | WP6B timing | Draft early, merge in slot | After RC freeze | Pre-built in L2 Phase 1 against C8; merged at S2-7 after M1 | Shortens Stage 2 and still honours R2-B6 |
| 16 | Migrations | — | — | V21–V26 reserved in merge order (C9) | Parallel Java work would otherwise collide on Flyway numbers |
| 17 | Ledger | 70 / 75, arithmetic correct | 69 / 74, arithmetic correct | 75 / 80 | +CON-2 and +4 splits; Plan 1's +1 is CON-1 |
