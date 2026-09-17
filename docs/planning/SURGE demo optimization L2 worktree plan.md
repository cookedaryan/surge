# SURGE demo optimization — L2 worktree plan

Date: 17 September 2026
Status: Final execution split; planning only, no implementation authority
Level: **L2 — engine bounds, stack bindings and baseline measurement**
Worktree: `demo-opt/l2-engine-bindings`, branched from tag `demo-opt-base`
Planning head: `a313d2f287aaf811ddafe765029423a361fece31`
Sibling files: [L1 worktree plan](SURGE%20demo%20optimization%20L1%20worktree%20plan.md) · [L3 worktree plan](SURGE%20demo%20optimization%20L3%20worktree%20plan.md) (holds Stage 0 and the contract pack)

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

L2 owns well-specified work that is broad and exacting but whose semantics are already fixed by draft 0.6 and the Stage 0 contracts:

- **Evidence operator.** Captures and measures the blinded baseline and runs every golden-project measurement before FRZ-1, including S2-1.
- **Candidate truth.** Cache completeness, cache versioning, and publishing repairs and final conductors (WP1).
- **Bounded search.** Activation, caps, the admission deadline, truncation order, solver bounds and telemetry, and public evidence (WP4, Python side).
- **Java and frontend bindings.** Everything in `backend-java/`, plus `web-map-next/` except L1's `ClaimDisclosure.tsx`: the outer timeout and job state, typed-identity transport, the profile allow-list, the handshake, persistence, and Java conformance.
- **Independent checks and UI.** Minimum Cost recomputation, the explanation UI, landowner masking, and a pre-built Recorded Demo mode.

L2 has the most tasks. It may run two sub-branches inside its own ownership (`l2-py` for baseline, WP1 and WP4; `l2-java-web` for Java, UI and WP6B). They are still one level and share one set of ownership globs.

**Blinding rule.** L2 publishes distributions, counts and reconciliation only. It never computes or shares winner identities, ranks or policy scores for the golden project before FRZ-1, and raw golden outputs stay access-controlled.

---

## 3. Entry criteria (from Stage 0, not from another level)

| Stage 0 artefact | Used by |
|---|---|
| WP0A-1 clean environment; WP0A-2 finding matrix (F1a, F3, F4, F5, F11 confirmed; [Stage 0 record](stage0/README.md)) | All tasks; finding conditions |
| WP2-1 probe result: **failed**, so WP2-3 is active (Java sends `routing_mode` but not the restriction type or cadastral parcel ID) | WP2-3 |
| C1 request additions and fixtures | WP0B-3, WP2-3, WP3-5, WP3-9b |
| C2 response additions and fixtures | WP1-2, WP1-5, WP4-7, WP3-7b, WP3-9b, WP6A-2, WP6A-3 |
| C3 codes, including `TIMED_OUT` and `CANCELLED` | WP4-7, WP4-8, WP4-9b, WP3-5 |
| C4 evidence schema and reconciliation checker | WP0B-5, WP0B-8, WP0B-9, WP0B-10, WP4-3, WP4-7, WP3-8 |
| C5 flag keys | WP4-1, WP3-7b |
| C6 profile IDs and hash test vector | WP3-5, WP3-6b |
| C7 run-ID header, cancel path, definition-hash path | WP4-9b, WP3-6b |
| C8 recorded bundle manifest and UI state names | WP6B |
| C9 Flyway reservations V21, V22, V23, V25, V26 | WP4-9b, WP2-3, WP3-7b, WP6A-3, WP6B |
| C11 feeder/segment fixture | WP3-9b |
| S1 response models in `app/contracts/response.py`; `ConstraintLayer.source_id` and `feature_type` | WP1-3, WP1-5, WP4-7 |
| S2 `search_activation.py` stub returning a `SearchActivation` | WP4-1 |
| S3 hooks `presentation/design_truth.py` and `presentation/search_evidence.py` (design truth, search evidence, solver runs, termination) | WP1-2, WP1-5, WP4-6, WP4-7 |
| S4 guard checks and `deadline_guard.py`; `AdmissionDeadlineReached` is raised by your guard and caught in your search/orchestration code | WP4-4, WP4-8 |
| S5 `solver_models.py`, `_run_milp` and the `_solve_milp_*` region. Telemetry is **already recorded**; WP4-6 applies the limits, stops treating `LIMIT_REACHED` as infeasible, and publishes `solver_runs` | WP4-6 |
| S6 `fingerprints/topology.py` stub | WP0B-5 |
| S8 `METRIC_REGISTRY_VERSION` name (value owned by L3) | WP1-3 |
| S9 `ClaimDisclosure` mount in `ResultsSheet.tsx`, which must stay | WP6A-2, WP6B-4 |
| Java probe tests `FeederSegmentIdentityContractTest` and `OptimizationJobServiceTest.stage0TransportProbe_*` | WP2-3 replaces the probe; WP3-9b extends C11 |

---

## 4. Phase 1 tasks

"Tag" is the Plan 1 complexity tag. ↑ means the task moved up to stay with its chain; "split" means a Java half kept at L2 while the hard Python half stayed in L3.

### 4.1 Baseline measurement — PR `baseline-measurement`, slot 1

Every measurement runs against images built from **`demo-opt-base`**, not against this worktree's head, so the baseline predates all behaviour change.

| ID | Task | Tag | Gate | Inputs | Exit evidence |
|---|---|---|---|---|---|
| WP0B-3 | Capture the four serialised request variants and their allowed diff | L2 | G1 | C1 allow-list | New Java test serialises the four scenario requests for the golden snapshot; artefacts retained; diff shows only allow-listed fields differ |
| WP0B-8 | Cold/warm measurement harness | L2 | G1 for golden runs; tooling can start on synthetic data | C4 timing fields | Clean Compose, empty caches, Java submission → persisted, retrievable result; image pull/build reported separately; raw measurement record |
| WP0B-5 | Topology fingerprint canonicaliser | L2 | — | C4; S6 `topology.py` | Sorted logical nodes/edges and feeder membership, independent of transient IDs and serialisation order; versioned golden vectors; repeat test |
| WP0B-2 | Distinct topology count at baseline | L1↑ | G1 | WP0B-5, WP0B-3, WP0B-8 | Count on the golden project. Fewer than three is reported to the WP5 owner as a priority signal only, since WP5 is already running in L3 |
| WP0B-9 | Count reconciliation on baseline evidence | L2 | G1 | C4 checker; WP0B-8 runs | Equations hold over the fields present today; stable reason codes where a field does not exist yet |
| WP0B-10 | Blinded raw-metric distributions | L2 | G1 | WP0B-8, WP0B-9 | Per-metric distributions for each request variant, including raw ROW and overlap spread; no winners, ranks or policy scores; access record |

### 4.2 Candidate truth — PR `wp1-truth`, slot 2

| ID | Task | Tag | Gate | Inputs | Exit evidence |
|---|---|---|---|---|---|
| WP1-1 | `land_assessment` in cache entries | L1↑ | F4 | `search_cache.py` | The cached payload includes land assessment |
| WP1-3 | Version the cache context; reject older entries | L2 | F4 | WP1-1; S8 constants; S1 typed layer fields | The context includes the pipeline, evidence-schema and metric-registry versions plus typed layer identity; changing any one never hits an older entry. The evaluation/scoring split is **not** touched, because that is WP5B |
| WP1-4 | Prove cache hit/miss semantic equality | L2 | F4 | WP1-1, WP1-3 | Equal on land decisions, owner basis, per-parcel areas, engineering and eligibility; only C2 exclusions may differ |
| WP1-2 | Label candidate sizing as initial-only | L1↑ | F3 | C2 `design_truth.sizing_basis` | Presentation assertion |
| WP1-5 | Publish repair actions and the final conductor per segment | L2 | F3 | C2 `design_truth` | The repair log reaches the response; the Python response fixture matches the C2 shape |

### 4.3 Bounded search, Python — PR `wp4-search`, slot 3

| ID | Task | Tag | Gate | Inputs | Exit evidence |
|---|---|---|---|---|---|
| WP4-1 | Default-off, server-controlled search activation | L1↑ | G2 | C5; S2 `search_activation.py` | Disabled by default; no client field enables it |
| WP4-3 | Caps on seeds, children, archive, proposals, routed proposals, evaluations and rounds | L2 | G2 | C4 counts | Each cap enforced and reported separately |
| WP4-4 | Admission deadline checked before routing | L2 | G2 | S4 `deadline_guard.py` and guard checks | Forced-expiry test: no new route starts after expiry |
| WP4-5 | Screening and dedup before top-N truncation | L2 | G2 | WP4-3 | Structural rejects and duplicates no longer consume the shortlist |
| WP4-6 | Bound grouping MILPs; publish solver telemetry | L2 | G2 | S5, `_run_milp` and `_solve_milp_*` region only | Time/node limits from settings applied in `_run_milp`; a `LIMIT_REACHED` solve is reported, never treated as infeasible; `build_solver_runs` publishes status, wall time and gap per solve. Feeder-count selection is not touched |
| WP4-7 | Publish lineage, counts, cache hits and termination reason | L2 | G2 | WP4-3 … WP4-6; C3; C4 checker | A search evidence fixture reconciles under the C4 equations |
| WP4-8 | Forced-deadline test with no partial publication | L2 | G2 | WP4-4, WP4-7 | Stable termination; no partial candidate published or cached |

### 4.4 Java bindings

| ID | Task | Tag | Gate | Inputs | Exit evidence | PR, slot |
|---|---|---|---|---|---|---|
| WP4-9b | Java outer timeout, plus persisted **and rendered** job state (split from WP4-9) | L2 split | G2 | C3 job states; C7; C9 V21 | On timeout Java closes the Python call, calls the cancel path, persists `TIMED_OUT`, and `RunProgress`/`useJobProgress` render it without stale success. Tests mock the Python client | `wp4-java-timeout`, 3 |
| WP2-3 | **Active** (WP2-1 failed): Java transport of typed ID, type and mode | L2 | G1 | C1 typed-identity fixture; C9 V22 | Every avoidance feature carries `source_id` (cadastral `parcel_id` for parcels) and `feature_type` (restriction type mapped to `CanonicalFeatureType`); serialisation equals the C1 fixture; the Stage 0 probe test is replaced | `wp2-java-transport`, 5 |
| WP3-5 | Java allow-list and serialisation | L2 | G0 | C6 IDs; C1 | The four IDs/versions serialise to the C1 fixtures; unknown values fail closed; browser → Java accepts only a profile ID | `wp3-java-profiles`, 6 |
| WP3-6b | Java startup definition-hash handshake (split from WP3-6) | L2 split | G0 | C6 vector; C7; WP3-5 | A mismatch fails startup (tested against a mocked endpoint serving the C6 vector); the expected hash is config, set at FRZ-1 | `wp3-java-profiles`, 6 |
| WP3-7b | Persist and return effective hashes and both flags (split from WP3-7) | L2 split | G0 | C2 `effective_profile`; C9 V23 | Persisted and returned in job/result DTOs; old rows still readable (expand/contract) | `wp3-java-profiles`, 6 |
| WP3-9b | Java consumer conformance (split from WP3-9) | L2 split | G0 | C1, C2, C11 fixtures | Java reads every response fixture, including the feeder/segment fixture, and writes every request fixture in canonical JSON | `wp3-java-profiles`, 6 |

### 4.5 Independent check, UI and recorded mode

| ID | Task | Tag | Gate | Inputs | Exit evidence | PR, slot |
|---|---|---|---|---|---|---|
| WP3-8 | Independent Minimum Cost recomputation | L2 | G0 | C4 cost fields; costing catalogue at base | `app/evidence/cost_recompute.py`: BOM × catalogue + valued losses match reported lifecycle cost within tolerance on synthetic fixtures; the golden check runs in S2-1 | `wp3-java-profiles`, 6 |
| WP6A-2 | Show raw values, reference ranges and contributions, with generation penalties labelled separately | L2 | G0 | C2 `scoring_explanation` fixture | Component tests driven by the fixture | `wp6a-explanation`, S2-4 |
| WP6A-3 | Mask landowner data across API, Python report, Java report/export and UI | L2 | G1 display decision | C2; C9 V25 if persistence changes | Masking test on every surface | `wp6a-masking`, S2-4 |
| WP6B-2 | Bundle validator | L2 | G3 | C8; C4 | Validates request, profile, code, image, catalogue and schema hashes plus winner fingerprints | `wp6b-recorded`, S2-7 |
| WP6B-1 | Re-record guard | L1↑ | G3 | WP6B-2 | Any hash change rejects the bundle and requires re-recording | `wp6b-recorded`, S2-7 |
| WP6B-3 | Serve the validated bundle through the normal read path | L2 | G3 | WP6B-2; C9 V26 | New `recorded` package; read-path contract and invalid-bundle failure tests. The WP4-9b timeout code is not edited | `wp6b-recorded`, S2-7 |
| WP6B-4 | Explicit mode switch, persistent banner, state clearing | L2 | G3 | C8 state names; WP6B-3 | The label shows before recorded data loads; live state clears before render | `wp6b-recorded`, S2-7 |

WP6B is an optional **pre-build**. It is developed against C8 in Phase 1 and merges only at S2-7, after the RC freeze (R2-B6). If G3 has not passed, it is not started.

---

## 5. Execution order and gates

```
demo-opt-base ─► 0B-3 → 0B-8 → 0B-5 → 0B-2 → 0B-9 → 0B-10         G1 (tooling can start on synthetic data)
              ─► 1-1 → 1-3 → 1-4 ; 1-2 ; 1-5                         F3/F4 confirmed; no gate
              ─► 4-1 → 4-3 → {4-4, 4-5, 4-6} → 4-7 → 4-8 ; 4-9b      G2
              ─► 3-5 → 3-6b → 3-7b → 3-9b ; 3-8 ; 6A-2               G0
              ─► 2-3                                                 active: the probe failed
              ─► 6A-3                                                G1 display decision
              ─► 6B-2 → 6B-1 → 6B-3 → 6B-4                           G3; optional pre-build
```

If G2 slips, WP4 and WP4-9b are not started, search stays disabled, and slot 3 is skipped. If G0 slips, the WP3 Java bindings, WP3-8 and WP6A-2 wait, while baseline, WP1 and WP6A-3 continue.

---

## 6. Ownership (`contracts/ownership/L2.globs`)

Python paths are relative to `optimisation-python/`.

- `backend-java/**`, including reserved migrations `V21__*`, `V22__*`, `V23__*`, `V25__*`, `V26__*`
- `web-map-next/**` **except** `src/features/optimization/ClaimDisclosure.tsx` and its test (L1). The `ClaimDisclosure` mount in `ResultsSheet.tsx` must stay in place
- `app/optimisation/search_cache.py`, `candidate_search.py`, `search_models.py`, `orchestrator.py`, `search_activation.py`, `deadline_guard.py`
- `app/presentation/**` **except** `explanation.py` and `profile_echo.py` (L3)
- `app/schemas/v2/**`
- `app/algorithms/solver_models.py`; `app/algorithms/wtg_grouping.py`, **`_run_milp`, `_solve_milp_assignment` and `_solve_milp_balance` bodies only**
- `app/evidence/fingerprints/topology.py`, `app/evidence/cost_recompute.py`, `scripts/evidence/**`
- `app/reporting/**`
- `docker-compose.yml`, only where the measurement harness needs it
- Tests for the above: `tests/test_search_*.py`, `tests/test_wtg_grouping.py`, `tests/test_presentation.py`, `tests/test_decision_report.py`, `tests/test_engineering_report.py`, `tests/test_optimise.py`, `tests/test_optimisation_orchestrator.py`, `tests/api/**`, `tests/search/**`, and new `tests/evidence/test_topology*.py`, `tests/evidence/test_cost_recompute*.py`

Keep these frozen symbols intact: guard checks and the `RunGuardStop` re-raise in `candidate_search.py` and `orchestrator.py`, solver-option threading in `orchestrator.py`, the `group_wtgs` signature, and the `ClaimDisclosure` mount. Where this list and `contracts/ownership/L2.globs` differ, the globs file wins.

---

## 7. Dependency audit

| L2 task | Something it might seem to need from another level | Why it does not |
|---|---|---|
| WP1-3 | L3's typed-identity parser | Typed fields reach `ConstraintLayer` through the S1 pass-through in Stage 0 |
| WP1-3 | L3's metric-registry version changes | The cache context reads the S8 constant by name; L3 bumping it invalidates caches without editing L2 files |
| WP4-4, WP4-8 | L3's cancellation guard | The S4 composite guard; L2 tests use the null cancellation guard |
| WP4-6 | L3's `k+1` feeder-count override | Separate S5 regions; limits apply to whichever feeder count is requested |
| WP4-7 | L3's baseline code or evidence runner | The reconciliation checker is C4, from Stage 0 |
| WP0B-2 | L3's fingerprint work | The topology canonicaliser is L2's own WP0B-5 |
| WP0B-10 | Anything scoring-related | Raw metrics already exist at base (F7); no policy is applied |
| WP2-3, WP3-5, WP3-9b | L3's Python producer | Both sides are tested against the same frozen C1/C2/C11 fixtures |
| WP3-6b | L3's hash endpoint | The C6 test vector is the shared oracle; the endpoint is mocked |
| WP3-8 | L3's profile registry | Recomputes lifecycle cost from the BOM and catalogue, independent of scoring |
| WP6A-2 | L3's contribution code (WP2-7) | Built against the C2 `scoring_explanation` fixture |
| WP6B | RC freeze / merged release | Built against C8; only the merge waits for S2-7 |
| WP4-9b | L3's Python cancellation (WP4-9a) | The C7 transport contract, with the Python client mocked; the live path is verified in WP6A-5 |

---

## 8. PRs

| PR | Slot | Tasks | Rollback statement |
|---|---|---|---|
| `baseline-measurement` | 1 | WP0B-3, WP0B-8, WP0B-5, WP0B-2, WP0B-9, WP0B-10 | Tooling and tests only |
| `wp1-truth` | 2 | WP1-1, WP1-3, WP1-4, WP1-2, WP1-5 | Additive response blocks; the pipeline version bump invalidates old caches |
| `wp4-search` | 3 | WP4-1, WP4-3 … WP4-8 | Search flag off = legacy; flag rolls back independently |
| `wp4-java-timeout` | 3 | WP4-9b | V21 is additive; the old frontend ignores the new state |
| `wp2-java-transport` | 5 | WP2-3 (conditional) | Nullable DTO fields; V22 is additive |
| `wp3-java-profiles` | 6 | WP3-5, WP3-6b, WP3-7b, WP3-9b, WP3-8 | Profile flag off = V0; V23 is expand-only |
| `wp6a-explanation`, `wp6a-masking` | S2-4 | WP6A-2, WP6A-3 | Frontend rolls back before Java |
| `wp6b-recorded` | S2-7 | WP6B-2, WP6B-1, WP6B-3, WP6B-4 | Recorded mode never auto-activates; V26 is additive |

---

## 9. Stage 2 tasks owned by L2

| ID / role | Task | Tag | Starts when | Exit evidence |
|---|---|---|---|---|
| Evidence operator (S2-1) | Blinded re-run on merged main (see shared frame) | — | Slot 6 merged | Blinded report handed to the release captain; baseline artefacts preserved alongside it |
| WP5B-3 *(if G4 = live)* | Persist and reference the live cohort ID and hash | L2 | WP5B-2 | Results and exports reference one cohort hash; V24 |
| WP6A-4 | Verify deployment order and independent rollback | L2 | S2-4 | Compatibility and rollback runbook test, including current Java with new frontend |
| WP6A-5 | Clean Compose smoke and failure paths | L2 | WP6A-4 | Success, no-feasible, optimiser failure, parse failure, deadline, outer timeout and hash mismatch, with no stale live or recorded data shown |
| WP6C-1 | Three clean cold rehearsals | L2 | M2, or M1 if live-only | Stable fingerprints and counts; G2 runtime and headroom with median and maximum |
| WP6C-2 | Live failure and rollback rehearsal | L2 | WP6C-1 | No stale success shown; profile and search flags roll back independently |
