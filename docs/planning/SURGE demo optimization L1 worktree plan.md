# SURGE demo optimization — L1 worktree plan

Date: 17 September 2026
Status: Final execution split; planning only, no implementation authority
Level: **L1 — characterisation, preflight, copy and release documentation**
Worktree: `demo-opt/l1-foundations`, branched from tag `demo-opt-base`
Planning head: `a313d2f287aaf811ddafe765029423a361fece31`
Sibling files: [L2 worktree plan](SURGE%20demo%20optimization%20L2%20worktree%20plan.md) · [L3 worktree plan](SURGE%20demo%20optimization%20L3%20worktree%20plan.md) (holds Stage 0 and the contract pack)

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

L1 owns self-contained, low-ambiguity work that protects the demo without changing engine behaviour:

- **V0 characterisation.** Golden tests that pin today's legacy behaviour, so every later package must keep it: scoring defaults (WP2-2), omitted profile (WP3-2) and search off (WP4-2).
- **Generation invariant.** The audited result that the old monotone transform leaves MST edge sets unchanged (WP5-1).
- **Catalogue preflight.** Every installed conductor, pole and land component is priced (WP0B-1).
- **Claim copy.** The verbatim G0 claim, the Minimum Cost disclosure and the §17 non-claims in the UI (WP6A-1).
- **Stage 2.** Recording the FRZ-1 commit, the recorded-mode drill, the operator runbook, and the documentation refresh (WP7).

L1 writes tests, a report script and static copy. It changes no runtime Python, Java or data path. A needed runtime change means the task has been mis-scoped: raise a CCR, and do not edit another level's file.

---

## 3. Entry criteria (from Stage 0, not from another level)

| Stage 0 artefact | Used by |
|---|---|
| WP0A-1 clean environment | All tasks |
| WP0A-2 finding matrix: F2 confirmed, 100/100 MSTs unchanged ([Stage 0 record](stage0/README.md)) | WP5-1 |
| C1 "absent = V0" rule (`contracts/request-rules.json`) | WP3-2, WP4-2 |
| C2 rules: additive blocks absent when not produced, and `golden_comparison_exclusions` (`contracts/response-rules.json`) | WP3-2, WP4-2 |
| C3 `CatalogueIncompletenessCode` (`contracts/codes.json`) | WP0B-1 |
| C5 flags `Settings.surge_profiles_enabled` and `surge_search_enabled` (env `SURGE_PROFILES_ENABLED`, `SURGE_SEARCH_ENABLED`) | WP4-2 |
| C12 WP5 V0 decision (default: option (a), gate) | WP2-2, WP3-2, WP4-2 |
| Frozen symbol `scenarios._apply_long_edge_penalty(graph, alpha)` | WP5-1 |
| S9 `ClaimDisclosure.tsx` exists as a stub that renders nothing, already mounted at the top of the Decision tab | WP6A-1 |

**Early start allowed.** WP5-1 and WP6A-1 consume only a frozen symbol and G0 text, so they may be drafted before Stage 0 merges. Rebase onto `demo-opt-base` before opening a PR. If WP0A-2 strikes F2, drop WP5-1.

---

## 4. Phase 1 tasks

### 4.1 Characterisation and preflight — PR `baseline-characterisation`, slot 1

| ID | Task | Tag | Gate | Inputs | Exit evidence |
|---|---|---|---|---|---|
| WP0B-1 | Catalogue pricing preflight | L1 | G1 (catalogue revision and golden snapshot) | C3 incompleteness codes | `optimisation-python/scripts/catalogue_preflight.py` reports every installable conductor, pole and land component for the golden snapshot as priced or missing, with a stable code; its test runs on a synthetic catalogue in CI. The report feeds FRZ-1 and S2-1 |
| WP2-2 | Characterise V0 scoring defaults | L1 | — | Base code; C12 | `tests/regression/v0/test_scoring_defaults.py` pins default scoring policy values and the `app/schemas/legacy_mapping.py` weight mapping for the four legacy scenarios; fails on any change |
| WP3-2 | Characterise omitted-profile V1 = V0 | L1 | — | C1 V0 fixtures; C2 rules; C12 | `tests/fixtures/v0_golden/` captured at `demo-opt-base` for `constraint_demo_project_v2.json`, `mvp_demo_project_v2.json` and the `corpus/SYN-*` fixtures (capture script records the base SHA). `tests/regression/v0/test_v1_response_golden.py` requires every V0 field equal: exact for IDs, fingerprints, statuses and counts, and within the §8 default tolerance for floats. Only C2 additive blocks and exclusion-list fields are ignored |
| WP4-2 | Characterise search-off legacy behaviour | L1 | — | C5 flag keys; WP3-2 golden files | Same goldens with both flag keys explicitly false; also asserts no `search_evidence` block is present |
| WP5-1 | Monotone-transform MST invariance regression | L1 | F2 confirmed | Frozen `_apply_long_edge_penalty` | `tests/test_generation_mst_invariance.py`: for 100 seeded graphs and a declared set of `alpha` values, the MST edge set after the transform equals the original |

On `demo-opt-base` these tests pass trivially. Their value comes at merge time: every later package PR must keep them green. A package that intentionally changes a V0 value needs a CCR that amends C12 or C2 and re-captures the golden. It must never edit the golden quietly.

### 4.2 Claim copy — PR `wp6a-claim-copy`, merges at S2-4

| ID | Task | Tag | Gate | Inputs | Exit evidence |
|---|---|---|---|---|---|
| WP6A-1 | Claim copy, Minimum Cost disclosure and published non-claims | L1 | G0 (strong or weak claim chosen, verbatim) | Draft 0.6 executive summary claim text, §7 disclosure, §17 non-claims; S9 mount | `web-map-next/src/features/optimization/ClaimDisclosure.tsx` renders static copy with no dependency on result payloads. `ClaimDisclosure.test.tsx` asserts every string verbatim. A copy-review sign-off against the G0 record is attached to the PR |

---

## 5. Execution order and gates

```
demo-opt-base ─► 2-2 → 3-2 → 4-2        no gate: start here
              ─► 5-1                    F2 confirmed
              ─► 0B-1                   G1
              ─► 6A-1                   G0
              ─► drafts (not merged)    WP6C-4 runbook skeleton; WP7 change list from draft 0.6
```

If G1 slips, WP0B-1 waits and the rest continues. If G0 slips, WP6A-1 waits; draft 0.6 says no claim-aligned delivery starts without G0.

---

## 6. Ownership (`contracts/ownership/L1.globs`)

- `optimisation-python/tests/regression/v0/**`
- `optimisation-python/tests/fixtures/v0_golden/**`
- `optimisation-python/tests/test_generation_mst_invariance.py`
- `optimisation-python/scripts/catalogue_preflight.py`, `optimisation-python/tests/test_catalogue_preflight.py`
- `web-map-next/src/features/optimization/ClaimDisclosure.tsx`, `ClaimDisclosure.test.tsx`
- Local drafts for Stage 2 (runbook, WP7 change list). They stay in this worktree until their Stage 2 step

L1 never edits `ResultsSheet.tsx` (the mount is frozen and L2-owned), runtime Python modules, `backend-java/` or `contracts/`.

---

## 7. Dependency audit

| L1 task | Something it might seem to need from another level | Why it does not |
|---|---|---|
| WP2-2, WP3-2, WP4-2 | The profile code (L3) and search activation (L2) they guard | They pin **today's** V0 output at `demo-opt-base`; the flag keys and "absent = V0" rule come from Stage 0 (C1, C2, C5) |
| WP3-2, WP4-2 | Knowing whether WP5 changes V0 | C12 fixed that decision in Stage 0 |
| WP5-1 | L3's WP5-2 personality gating | Tests a frozen pure function; L3 must gate the transform, not delete it |
| WP0B-1 | L2's measurement harness or L3's cohort runner | Reads the catalogue and golden snapshot directly; codes come from C3 |
| WP6A-1 | L2's explanation UI or result types | Static copy mounted through the frozen S9 slot; no payload fields |
| Stage 2 drafts | Released behaviour | Drafts are not merged; the final text is written in S2-9 and S2-10 from merged main |

---

## 8. PRs

| PR | Slot | Tasks | Rollback statement |
|---|---|---|---|
| `baseline-characterisation` | 1 | WP0B-1, WP2-2, WP3-2, WP4-2, WP5-1 | Tests and a report script only; no runtime path |
| `wp6a-claim-copy` | S2-4 | WP6A-1 | Frontend-only; rolls back before Java |

---

## 9. Stage 2 tasks owned by L1

Each starts from merged main at its release-train step.

| ID | Task | Tag | Starts when | Exit evidence |
|---|---|---|---|---|
| FRZ-1 | Record the policy freeze. The scoring approver sets metric directions and definitions, fixed reference ranges, weights, tolerances, tie-breaks, the Balanced envelope, allowed generation differences and profile versions. L1 commits the values in the C6 definition format, sets the Java expected definition hash in config, and records the unblinding | L1 | S2-1 passes; G0; G4; WP0B-10 blinded report; WP0B-1 preflight | Timestamped commit hash in the evidence record; handshake passes on main; access-controlled unblinding log; profile version count recorded (at most three per profile) |
| WP6C-3 | Recorded Demo mode drill *(only if recorded mode is in scope)* | L1 | WP6C-2 | Explicit switch, persistent label before load, clean return to live |
| WP6C-4 | Finalise operator runbook, triggers and ownership | L1 | WP6C-3, or WP6C-2 if live-only | Named operators; rollback triggers from draft 0.6 §10; §7 disclosure; §17 non-claims; when G4 = recorded, the statement that cross-profile comparison rests on the recorded cohort |
| WP7-1 | Refresh TRD (`docs/architecture/TRD.md`) | L1 | WP6C-4 | §§2.2, 3.3, 4.1–4.2, 5, 6.3, 10, 11 match the release; DEM requirement removed or marked future; feeder-identity status updated |
| WP7-2 | Refresh PRD optimisation status (`docs/product/PRD.md` §10) | L1 | WP6C-4 | Status snapshot matches the release |
| WP7-3 | Refresh APP-FLOW (`docs/product/APP-FLOW.md` screens 4–6) | L1 | WP6C-4 | Preliminary and planned labels match the shipped UI |
| WP7-4 | Refresh root README and architecture/status docs (`README.md`, `docs/architecture/Python Engine - Architecture.md`) | L1 | WP6C-4 | Published claim, non-claims and operating mode agree |
| WP7-5 | Audit maturity labels and links | L1 | WP7-1 … WP7-4 | Every status uses Implemented / Partial / Planned; no broken links; no UI or behaviour change after the release gate |
