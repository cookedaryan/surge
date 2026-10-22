# SURGE demo optimization execution plan

Date: 17 September 2026  
Status: Proposed execution/worktree plan; no implementation authority  
Technical source of truth: [SURGE demo optimization work plan — draft 0.6](SURGE%20demo%20optimization%20work%20plan.md)  
Planning head: `a313d2f287aaf811ddafe765029423a361fece31`

## Verdict

Worktrees are parallel development lanes, never whole merge units. Work may finish in a different order, but only complete, dependency-safe package PRs merge, in the authoritative sequence. Integration binds and verifies pre-defined contracts; it does not invent cache, evidence, profile, flag, or privacy semantics.

This document plans execution only. It neither replaces the technical specification nor changes the published scope, acceptance gates, or supported claim.

## Success criteria and non-negotiable rules

The execution succeeds when the selected delivery cut reaches the source plan's acceptance gates with a reproducible evidence record, passing cross-stack compatibility and a rehearsed rollback path.

- Complete the entire WP0B baseline before behaviour work is merged. Raw/blinded baseline variance and the current topology count are captured before behaviour changes; later merged reruns supplement, never replace, that baseline.
- Merge package PRs only in the authoritative order in this plan. A branch must pass independently and preserve old payloads; no branch may rely on a later branch to become valid.
- Both profiles and search remain independently deployable and default off. Missing profile fields retain V0 behaviour; explicit unsupported versions fail closed.
- Do not expose golden-project winner identities, ranks, or policy scores until the policy/range/tolerance/tie-break freeze is committed.
- Assign one exclusive owner for every shared file or interface at a time. Rebase and hand over ownership explicitly before the next package changes it.
- The scoring owner uses synthetic fixtures until policy freeze. Golden data establishes variance and baseline evidence, not tuning results.
- Java transport, privacy/retention/display/export decisions, and profile contract field names are resolved at their gates—not deferred to integration.
- Release-candidate core-behaviour freeze and final bundle recording are milestones, not ledger tasks. The freeze precedes WP6B; the real validated bundle is recorded only after the WP6B validator and serving path exist.

## Gate timeline

| Sequence | Gate or milestone | Required result and effect if not met |
|---:|---|---|
| 1 | WP0A | Reconfirm findings and TRD feeder/segment semantics at implementation HEAD. Trigger conditional WP0C only when semantics are wrong or undefined. |
| 2 | G1 — golden data and privacy | Approve the sanitised snapshot, catalogue, retention/display/export rules and four request variants; complete the Java identity/mode transport probe after WP0A. If unsupported, rename/drop the scenario; never silently substitute synthetic data. G1 completes before WP0B. |
| 3 | Complete WP0B | Freeze raw baseline evidence: request diff, evidence/canonicaliser machinery, catalogue preflight, baseline counts and blinded distributions. No behaviour package has merged before this point. |
| 4 | G0 and G4 decisions | Select the strong/weak claim, effect sizes, tolerances and Balanced envelope, and decide whether the shared cohort is recorded acceptance evidence or optional live WP5B. Default to recorded evidence. Build mechanisms and synthetic tests beforehand, but do not choose policy values from golden winners. |
| 5 | FRZ-1 — policy freeze | After G0, G4 and the blinded baseline distributions, commit metric direction/definitions, reference ranges, weights, tolerances, tie-breaks, generation differences and profile versions. Only then may golden-result winners be unblinded. |
| 6 | G2 — runtime envelope | Lock demo machine/images, cold-run definition, job timeout, runtime/headroom and execution surface before WP4 begins. Otherwise search remains disabled. |
| 7 | G3 — Recorded Demo decision | Approve storage, serving, retention and on-screen wording before WP6B. Otherwise the delivery is live-only. |
| 8 | WP6A integration gate | Merge and verify all selected packages, including optional WP5B when G4 selected a live cohort. |
| 9 | RC core-behaviour freeze | Freeze the integrated code and hashes that WP6B must validate and serve. |
| 10 | WP6B | Implement and verify re-record guards, bundle validation, normal read-path serving and explicit frontend state. |
| 11 | Record final validated bundle | Record only after WP6B passes, from the frozen revision, with validated request/profile/code/image/catalogue/schema/winner hashes. |

## Shared-interface freeze before branching

Agree these names, versions, null/error semantics, additive rollout shape, and test-vector ownership before creating post-baseline branches. The owning package defines the contract; consumers implement against it.

| Interface | Owning package | Consuming packages | Freeze rule |
|---|---|---|---|
| Evidence schema and count vocabulary | WP0B | WP1, WP4, WP5, WP2, WP3, WP5B, WP6A/B/C, UI/export | Define seed/child/routed/evaluated/eligible/excluded/cache-hit counts and reconciliation equations once. |
| V1 request submodels and error shape | WP3, with G1 transport probe | WP2, WP4, Java DTO/client, frontend | Additive fields only; missing means V0; unknown explicit versions reject consistently. |
| Profile/version/hash/flag fields | WP3 | WP0B, WP4, WP5, WP5B, WP6A/B, Java and frontend | Python owns definitions; Java allow-lists IDs/versions and verifies definition hash. |
| Fingerprint versions and canonicalisation | WP0B | WP1, WP4, WP5, WP5B, WP6A/B/C | Topology, geometry and final-design identities have separate versions and golden vectors. |
| Solver options, status, wall time and gap result | WP4 | WP5, evidence, Java job lifecycle, UI explanation | Time/node limit semantics, status vocabulary, and whether a limit invalidates rehearsal are fixed together. |
| Frontend live/recorded result state | WP6B | WP6A, Java read path, UI store/results | Explicit operator switch; persistent recorded label before load; clear recorded state before live render. |
| Privacy, masking, export and retained-bundle rules | G1 decision, implemented by WP6A/WP6B | Java persistence, API, UI, reports and exports | Decide allowed display separately from storage; mask landowner data unless explicitly approved. |

## Mechanically auditable task ledger

Scope count: **69 core tasks** for the fallback-protected recommended scope; **+1** conditional WP0C task; **+1** conditional WP2 transport task; **+3** optional live-cohort tasks = **74 maximum**. RC code freeze and bundle recording are milestones, not extra tasks.

Conditions use `—` when unconditional. “Exit evidence” is the reviewable artefact or test result required before its package PR may merge.

### Phase 0 — base on the integration branch

This phase contains all findings verification, the complete no-behaviour evidence baseline, and the G1 transport probe. It is completed and merged before creating behaviour-package PRs. Later merged reruns are retained beside this baseline rather than overwriting it.

| ID | Phase / lane | Deliverable | Condition | Dependencies | Owner surface | Exit evidence |
|---|---|---|---|---|---|---|
| WP0A-1 | Base / both | Boot lockfile environment and clean Compose start | — | — | Compose, lockfiles, deployment scripts | Clean-start log and targeted build test. |
| WP0A-2 | Base / both | Reverify F1–F11, P1 and E1 | — | Base environment boot | Python, Java, frontend probes/tests | Finding matrix with source/test evidence: confirmed, amended, or struck. |
| WP0A-3 | Base / both | Verify TRD §6.3 feeder/segment identity and decide conditional repair | — | Findings re-verification | Python response, Java persistence, BOM/export | Contract probe and recorded decision to close or trigger WP0C. |
| WP2-1 | Base / Java | Run G1 identity and mode transport probe | G1 in progress; before WP0B | WP0A | Java V1 DTO/client, Python parser | Proof that source ID/type/soft-hard mode survives Java → V1, or a failure triggering transport work. |
| WP0B-1 | Base / Python | Catalogue pricing preflight | G1 | WP0A | Catalogue/cost inputs | Priced-conductor, pole and land-component report. |
| WP0B-2 | Base / Python | Count current distinct topology fingerprints | G1 | WP0A | Baseline runner/canonicaliser | Baseline count; fewer than three moves generation onto critical path. |
| WP0B-3 | Base / Java | Capture four serialised request variants and allowed field diff | G1 | WP0A | Java request DTO/client | Retained request artefacts and allow-list diff. |
| WP0B-4 | Base / Python | Version the evidence schema | G1 | WP0A | Evidence record/schema | Schema version, field dictionary and consumer fixture. |
| WP0B-5 | Base / Python | Canonicalise topology fingerprints | G1 | Evidence-schema foundation | Topology identity code | Versioned golden vectors and deterministic repeat test. |
| WP0B-6 | Base / Python | Canonicalise final-design fingerprints | G1 | Evidence-schema foundation | Final conductor/design identity | Versioned golden vectors including installed conductor fields. |
| WP0B-7 | Base / Python | Canonicalise geometry fingerprints | G1 | Evidence-schema foundation | Geometry identity code | CRS/precision/orientation vectors and repeat test. |
| WP0B-8 | Base / both | Establish cold/warm measurement harness | G1 | WP0A | Java job timing, Python runner, Compose | Reproducible timing procedure and raw measurement record. |
| WP0B-9 | Base / both | Reconcile baseline evidence counts | G1 | Evidence schema and measurement harness | Evidence runner and Java/Python results | Checked count equations and stable reason codes. |
| WP0B-10 | Base / both | Publish blinded raw metric distributions | G1 | Complete baseline evidence set | Evidence runner/report | Variance/distribution report with no policy winners/ranks/scores. |
| WP0B-11 | Base / Python | Build controlled-cohort runner | G1 | Evidence schema and fingerprint canonicalisers | Cohort union/dedup/exclusion module | Injected required-metric set, deterministic representative and exclusion-code tests. |
| FRZ-1 | Policy freeze / scoring owner | Commit policy/ranges/tolerances/tie-breaks before unblinding | G0, G4 | Complete WP0B, including blinded distributions | Profile registry and evidence record | Timestamped commit/hash and access-controlled unblinding record. |

### Conditional baseline correction

| ID | Phase / lane | Deliverable | Condition | Dependencies | Owner surface | Exit evidence |
|---|---|---|---|---|---|---|
| WP0C-1 | Base / cross-stack | Repair feeder/segment identity contract | Only if feeder/segment verification finds wrong/undefined semantics | Findings verification | Python response, Java DTO/persistence, UI, BOM/export | One feature-to-routed-segment contract plus cross-language fixture. |

### Post-baseline package ledger

| ID | Phase / lane | Deliverable | Condition | Dependencies | Owner surface | Exit evidence |
|---|---|---|---|---|---|---|
| WP1-1 | WT-A truth/search | Restore land assessment in cache entries | F3/F4 confirmed | Complete WP0B | `search_cache.py`, evaluation cache | Cache payload includes land assessment. |
| WP1-2 | WT-A truth/search | Label candidate sizing initial-only | F3 confirmed | Complete WP0B | Python result/presentation models | API/presentation assertion for explicit initial-only label. |
| WP1-3 | WT-A truth/search | Version cache context and reject old cache entries | F4 confirmed | Cache payload restoration | `search_cache.py`, cache context | Pipeline/schema/metric/typed-layer version test: older entry never hits. |
| WP1-4 | WT-A truth/search | Prove cache hit/miss semantic equality | F4 confirmed | Cache payload and versioning | Cache/evaluation tests | Equality on land, owner basis, parcel areas, engineering and eligibility. |
| WP1-5 | WT-A truth/search | Publish repairs and final conductor per segment | F3 confirmed | Complete WP0B | Result builder, output schema | Repair log and installed conductor IDs in Python response fixture. |
| WP2-2 | WT-C metrics/profiles | Preserve legacy scoring defaults | — | Complete WP0B | `scoring.py`, scoring tests | V0/default regression fixture passes. |
| WP2-3 | WT-C metrics/profiles | Add Java transport for typed ID/type/mode | Only if transport probe fails | G1, transport probe | Java DTO/client/parser contract | Java-to-Python transport fixture passes. |
| WP2-4 | WT-C metrics/profiles | Carry typed forest/environment identity into ROW and metrics | F7 confirmed | G0, complete WP0B, transport result | Land/ROW/parser/metric modules | End-to-end typed identity and soft/hard mode fixture. |
| WP2-5 | WT-C metrics/profiles | Add affected-parcel ROW-area metric | F7 confirmed | Typed identity path | Metric registry/scoring | Canonical raw metric and deterministic area fixture. |
| WP2-6 | WT-C metrics/profiles | Add unique environmental-overlap metric | F7 confirmed | Typed identity path | Metric registry/scoring | Canonical raw metric and unique-overlap fixture. |
| WP2-7 | WT-C metrics/profiles | Emit raw, normalised and weighted contributions | F7 confirmed | Both canonical spatial metrics | Scoring evidence/output | Contribution record fixture with explicit ranges. |
| WP2-8 | WT-C metrics/profiles | Prove land/environment ranking causality | F7 confirmed | Canonical metrics and contributions | Synthetic scoring fixtures | Synthetic-only rank-change tests. |
| WP3-1 | WT-C metrics/profiles | Return stable invalid-input errors | G0 | WP2 | V1 schema/error contract | Unknown/invalid/non-finite/out-of-range cases tested. |
| WP3-2 | WT-C metrics/profiles | Prove omitted profile is V0 | G0 | WP2 | V1 request/scoring regression | Omitted-profile V1 equals V0 fixture. |
| WP3-3 | WT-C metrics/profiles | Support fixed reference ranges and remove-a-loser test | G0 | WP2 | Profile/scoring registry | Fixed-range mechanism and non-winner-removal invariant. |
| WP3-4 | WT-C metrics/profiles | Build profile registry mechanism | G0 | WP2 | Python profile registry | Versioned placeholder registry; actual values await policy freeze. |
| WP3-5 | WT-C metrics/profiles | Add Java allow-list and serialisation | G0 | Profile mechanism | Java request DTO/client | Four allowed IDs/versions serialize; unknown versions fail closed. |
| WP3-6 | WT-C metrics/profiles | Add definition-hash startup handshake | G0 | Profile registry and Java allow-list | Python registry, Java startup | Mismatch fails deployment/startup test. |
| WP3-7 | WT-C metrics/profiles | Echo and persist effective hashes/flags | G0 | Profile contract | Python output, Java persistence | Profile/policy/metric/generation/flag fields persisted and returned. |
| WP3-8 | WT-C metrics/profiles | Independently recompute Minimum Cost | G0 | Catalogue preflight, WP2 | Costing/scoring fixtures | BOM × catalogue + valued-loss recomputation within tolerance. |
| WP3-9 | WT-C metrics/profiles | Maintain cross-language contract fixtures | G0 | Java profile contract; conditional identity repair if triggered | Python/Java contract tests | Serialised consumer fixture, including feeder contract when applicable. |
| WP4-1 | WT-A truth/search | Add default-off search activation | G2 | WP1 | Search settings/API | Search flag disabled by default and server-controlled. |
| WP4-2 | WT-A truth/search | Preserve legacy behaviour with search off | G2 | Default-off activation | Search regression tests | Search-off compatibility fixture. |
| WP4-3 | WT-A truth/search | Bound seed, child, archive, proposal, routed-proposal, evaluation and rounds | G2 | WP1 | `candidate_search.py`, evidence | Each cap enforced/reported separately. |
| WP4-4 | WT-A truth/search | Check admission deadline before routing | G2 | Search caps | Candidate search/routing boundary | Forced guard test shows no new route starts after expiry. |
| WP4-5 | WT-A truth/search | Screen and deduplicate before top-N truncation | G2 | Search caps | Search shortlist/dedup | Structural-reject/duplicate regression test. |
| WP4-6 | WT-A truth/search | Bound grouping MILPs and record telemetry | G2 | WP1 | `wtg_grouping.py`, solver result/evidence | Time/node options plus status/wall-time/gap fixture. |
| WP4-7 | WT-A truth/search | Publish lineage, counts, cache hits and termination reason | G2 | Search caps, deadline, truncation and solver result | Search result/evidence schema | Evidence reconciliation fixture. |
| WP4-8 | WT-A truth/search | Test forced deadline with no partial publication | G2 | Admission guard and public search evidence | Search failure path | Stable termination and no partial candidate assertion. |
| WP4-9 | WT-A truth/search | Define Java outer timeout and worker cancellation | G2 | Bounded search result | Python client, job service/lifecycle | Forced timeout proves cancellation, abandoned compute, clean next cold run. |
| WP5-1 | WT-B generation | Preserve monotone-transform MST regression | F2/F6 confirmed | Complete WP0B | Generation/grouping tests | Test confirms old transform leaves audited MST edge sets unchanged. |
| WP5-2 | WT-B generation | Retire/gate ineffective personalities and record V0 decision | F2/F6 confirmed | Complete WP0B | Generation configuration/search flags | Explicit gated-V0 or intentional-rebaseline decision and regression. |
| WP5-3 | WT-B generation | Generate deterministic capacity-valid extra-feeder candidate | F2/F6 confirmed | Complete WP0B, WP4 solver interface | Generation/grouping API | Deterministic `k+1` fixture. |
| WP5-4 | WT-B generation | Record extra-feeder acceptance/failure evidence | F2/F6 confirmed | Extra-feeder candidate | Generation evidence/fixtures | Golden and synthetic success/failure evidence. |
| WP5B-1 | Optional live cohort / cross-stack | Split evaluation context from scoring context | Only if G4 selects live cohort | WP2 through WP5, policy freeze | Cache context and metric bundle | Same physics/land/cost/layer/pole inputs restore raw metrics across policies. |
| WP5B-2 | Optional live cohort / cross-stack | Run generation configurations, union/deduplicate and score all policies | Only if G4 selects live cohort | Context split, policy freeze | Cohort service/scoring | Common cohort and final-design deduplication test. |
| WP5B-3 | Optional live cohort / cross-stack | Persist/reference live cohort ID and hash | Only if G4 selects live cohort | Live cohort construction | Java persistence, API, UI/export | Results/exports reference one cohort hash. |
| WP6A-1 | Integration / frontend | Ship claim copy, cost disclosure and non-claims | G0 | Selected WP packages | UI claim content | Copy review matched to frozen claim. |
| WP6A-2 | Integration / frontend | Display raw values, ranges and contributions | G0 | WP2, WP3 | Result explainer/types | UI fixture shows metric evidence separate from generation penalties. |
| WP6A-3 | Integration / cross-stack | Apply landowner masking | G1 display decision | WP2, WP3 | Java/API/UI/export | API/report/UI/export masking test. |
| WP6A-4 | Integration / cross-stack | Verify deployment and independent rollback order | Selected cut | Selected WP packages | Deployment/database/flags | Compatibility and rollback runbook test, including current Java/new frontend. |
| WP6A-5 | Integration / cross-stack | Exercise clean Compose smoke and failure paths | Selected cut | Deployment/rollback verification | Full request/job/result path | Success, no-feasible, optimiser-failure and parse-failure smoke evidence. |
| WP6A-6 | Integration / cross-stack | Verify final conductor/repair truth end to end | Selected cut | Candidate truth and smoke paths | Python, Java persistence, UI/export | One final design agrees across electrical config, costing, response, GeoJSON, persistence and export. |
| WP6A-7 | Integration / cross-stack | Complete compatibility matrix | Selected cut | Integration deployment, smoke and truth verification | Python/Java/frontend releases | Supported and intentionally unsupported combinations recorded. |
| WP6B-1 | Recorded mode / Java | Force re-record when any validated hash changes | G3; RC freeze | Integrated release | Bundle metadata/validator | Hash-change rejection/re-record test. |
| WP6B-2 | Recorded mode / Java | Validate bundle mechanism | G3; RC freeze | Integrated release and re-record guard | Java bundle validator | Request/profile/code/image/catalogue/schema/winner validation test. |
| WP6B-3 | Recorded mode / Java | Serve validated bundle through normal read path | G3; RC freeze | Bundle validator | Java read service/job lifecycle | Read-path contract and invalid-bundle failure test. |
| WP6B-4 | Recorded mode / frontend | Provide explicit switch, persistent banner and state clearing | G3; RC freeze | Normal recorded read path | Frontend types/store/results | Recorded label-before-load and live-state-clear test. |
| WP6C-1 | Release gate / cross-stack | Run three clean cold rehearsals | Selected cut | Integrated release; recorded path if in scope | Compose, evidence runner | Stable fingerprints/counts and G2 runtime/headroom results. |
| WP6C-2 | Release gate / cross-stack | Rehearse live failure and rollback | Selected cut | Integrated release | Flags/deployment/read path | No stale success shown; independent rollback evidence. |
| WP6C-3 | Release gate / cross-stack | Drill Recorded Demo mode | Only if in scope | Recorded Demo path | Bundle/operator/UI | Explicit switch, persistent label and return-to-live drill. |
| WP6C-4 | Release gate / cross-stack | Finalise operator runbook, triggers and ownership | Selected cut | Rehearsals and applicable recorded drill | Runbook/release evidence | Named operators, triggers, rollback and non-claims reviewed. |
| WP7-1 | Documentation / docs | Refresh TRD status and feeder-identity status | Selected cut | WP6C | TRD | Implemented/partial/planned evidence-aligned update. |
| WP7-2 | Documentation / docs | Refresh PRD optimisation status | Selected cut | WP6C | PRD | Status snapshot matches release. |
| WP7-3 | Documentation / docs | Refresh APP-FLOW labels/screens | Selected cut | WP6C | APP-FLOW | Preliminary/planned labels match shipped UI. |
| WP7-4 | Documentation / docs | Refresh root README and architecture/status docs | Selected cut | WP6C | README/architecture docs | Published claim, non-claims and operating mode agree. |
| WP7-5 | Documentation / docs | Audit maturity labels and final links | Selected cut | Other documentation updates | Documentation set | Link/status audit with no post-gate behaviour change. |

## Post-baseline worktrees and ownership

Create these branches only after Phase 0 has merged and shared-interface freeze is recorded. They are lanes for development and review, not branches to merge wholesale.

| Worktree | Scope | Exclusive ownership | Handover / restriction |
|---|---|---|---|
| WT-A — truth/search | WP1, then WP4 | Python cache/search/workflow: `app/optimisation/search_cache.py`, `app/optimisation/candidate_search.py`, `app/api/v1/endpoints/optimise.py`, `app/presentation/result_builder.py`, search-related `app/schemas/optimise.py`; solver work in `app/algorithms/wtg_grouping.py`; Java `PythonOptimizationClient`, `OptimizationJobService`, job DTO/lifecycle for outer timeout/cancellation | WT-A exclusively owns `wtg_grouping.py` until the WP4 solver result/options interface is merged. It also owns search fields in the shared request DTO during its package PR. |
| WT-B — generation | WP5 | Scenario-generation schedule, personality settings, `k+1` implementation and its fixtures, after solver handover | WT-B may begin non-shared fixture/schedule work in parallel. It rebases after the WT-A solver interface lands before changing grouping code. It must not edit `candidate_search.py` without agreed coordinated ownership with WT-A. |
| WT-C — metrics/profiles | Remaining WP2, then WP3 | Python `app/optimisation/scoring.py`, `scoring_models.py`, metric/profile registry and fixtures; agreed cross-language profile contract; Java `PythonOptimisationRequest`/response DTOs and profile allow-list; frontend shared types for profile/explanation only | Use synthetic fixtures until policy freeze. WP-C owns scoring/profile semantics and must not change cache policy or evidence vocabulary owned by other packages. |

### Shared hotspots and serialization rules

| Hotspot | First owner | Next owner / rule |
|---|---|---|
| `app/algorithms/wtg_grouping.py` | WT-A for bounded solver/status/gap interface | WT-B rebases after the merged interface and then owns generation-only changes. |
| `app/optimisation/candidate_search.py` | WT-A | WT-B does not edit it without a jointly reviewed, time-boxed ownership transfer. |
| `app/schemas/optimise.py` and Java V1 DTOs | Package introducing each frozen submodel | Reserve field names before branching; merge serially in package order; additive optional fields only. |
| Java Python client/job lifecycle | WT-A for cancellation; WT-C for profile serialisation | Do not combine changes in one unreviewed branch; package PRs land in authoritative order. |
| `web-map-next/src/lib/store/uiStore.ts`, optimisation result types and `resultParts.tsx` | WT-C owns profile/explanation types; WP6A/WP6B integration owns claim/masking/recorded presentation | Recorded/live state names freeze before WP6B. No simultaneous edits; sequence integration UI PRs after contract packages. |
| Evidence/cache/profile hash fields | WP0B evidence owner and WP3 profile owner | Integration only binds already-defined fields; it must not introduce meaning or fallback behaviour. |

Suggested branch names: `codex/base-evidence`, `codex/truth-search`, `codex/generation`, `codex/metrics-profiles`, `codex/integration-release`, and `codex/recorded-demo`. Use short-lived package branches such as `codex/wp4-search-bounds` when review or ownership needs a narrower PR.

## Package PR and merge sequence

The merge sequence is mandatory; concurrent development completion does not grant merge permission.

1. Baseline: WP0A and all WP0B work, including the G1 transport probe.
2. Conditional WP0C, immediately after baseline only if triggered.
3. Policy freeze: FRZ-1 after G0, G4 and the blinded baseline, before golden winner unblinding or behaviour-package merges.
4. Candidate truth: WP1.
5. Bounded search: WP4.
6. Generation diversity: WP5.
7. Claim metrics: WP2.
8. Versioned profiles: WP3.
9. Optional live cohort: WP5B, only if G4 selected it.
10. Cross-stack integration: WP6A.
11. RC core-behaviour freeze milestone.
12. Recorded Demo implementation: WP6B, only when included and after the freeze.
13. Final validated bundle recording milestone, after WP6B passes.
14. Rehearsal/release gate: WP6C.
15. Documentation: WP7.

Each package PR supplies its contract fixtures, deployment/rollback statement, and narrow verification before it merges. A deferred/optional package is omitted cleanly; later packages must not silently recreate its unfinished semantics.

## Integration and release plan

Integration begins from the merged package sequence, not from three worktree heads. It will:

1. Re-run evidence/count reconciliation, baseline-vs-merged distributions, topology counts, cache equivalence and canonical fingerprints on the merged result. Preserve Phase 0 artefacts as the before-change record.
2. Bind the already-frozen evidence, profile, fingerprint, solver, flag and frontend-state contracts across Python, Java and frontend; reject mismatches rather than repairing their meaning in integration.
3. Verify cross-stack final conductor and repair truth from Python final electrical configuration through costing, response, GeoJSON, Java persistence, UI and exports.
4. Verify privacy masking across API, reports, UI, export and retained bundle against G1’s display/export decision.
5. Run the compatibility matrix for current/new Python, Java and frontend combinations, including current Java with new frontend, and record intentionally unsupported combinations.
6. Exercise clean smoke and failure paths: no eligible candidate, optimiser failure, deadline, outer timeout, contract/hash mismatch, and rollback without stale live or recorded data.
7. Run WP6A. If G4 chose live cohort, complete optional WP5B before WP6A and verify its cohort hash through UI/export.
8. Freeze the release candidate's selected core behaviour and hashes; then execute WP6B if fallback protection is selected.
9. After WP6B's validator and normal read path pass, record and validate the final bundle from the frozen revision. Never treat a pre-validator recording as the release bundle.
10. Execute WP6C rehearsals and WP7 documentation refresh.

## Verification matrix

| Package / surface | Required verification | Release evidence |
|---|---|---|
| Phase 0 evidence | Clean Compose, request-diff, canonicaliser vectors, baseline counts/distributions, catalogue preflight, blinded report | Retained baseline artefact with hashes and no winner unblinding. |
| Cache/truth | Old cache rejection, hit/miss semantic equality, repair/final-conductor output fixtures | Matching cache and output records. |
| Search/generation | Cap, pre-routing deadline, dedup-before-truncation, solver status/gap, forced deadline, old-MST and `k+1` fixtures | Reconciled search evidence and stable termination reason. |
| Metrics/profiles | Typed transport, raw/range/contribution fixtures, synthetic causal ranking, V0 equivalence, invalid-version errors, hash handshake, independent cost recomputation | Frozen profile contract and passing cross-language fixtures. |
| Java lifecycle | Outer timeout/cancellation, no inherited worker state, tolerant DTO rollout | Job lifecycle failure-path evidence. |
| Frontend | Explanation values/ranges/contributions, masking, live/recorded state clear, persistent banner | Component/integration tests and captured UX evidence. |
| Integration | Cross-stack conductor truth, privacy/export, compatibility matrix, Compose smoke/failure paths | Signed release checklist. |
| Final release | Three cold rehearsals, stable identities/counts, G2 headroom, rollback drill, recorded-mode drill when included | Rehearsal records, operator runbook, final documentation audit. |

## Rollback rules

- Keep profile and search flags independently disabled by default and independently rollbackable.
- Roll back frontend before Java; use additive/tolerant DTO and persistence changes so an old consumer remains valid during the sequence.
- Roll back or block enablement for contract parse errors, definition/evidence hash mismatch, non-reconciling counts, a rehearsal deadline or material solver limit, missing final-design truth, unstable fingerprints, or failed privacy masking.
- Recorded mode never auto-activates. An invalid or stale bundle is rejected; a hash change requires re-recording from the current RC.

## Critical path

```text
WP0A → G1/WP2-1 probe → complete WP0B → FRZ-1 → WP1 → WP4 → WP5 → WP2 → WP3
G0 + G4 ──────────────────────────────────┘                              │
G2 ─────────────────────────────────────────────────→ WP4               ├→ WP6A → RC core freeze
                                                    G4 live only → WP5B ┘             │
G3 ───────────────────────────────────────────────────────────────────────────────→ WP6B
                                                                                      ↓
                                                            final bundle → WP6C → WP7
```

WT-B can perform non-shared generation work after baseline while WT-A completes truth/search; WT-C can build metric/profile mechanisms after the relevant gates. These are parallelisable lanes, not independent dependency chains, and all package PRs still merge on the path above.

## Risks and owner decisions

| Risk | Preventive decision / owner | Response |
|---|---|---|
| Gate slips waste parallel work | G0/G1/G2/G4 owners decide before their latest package start | Stop affected work at the gate; retain synthetic mechanism work, but do not promote it as delivery evidence. |
| Stale recorded bundle | G3 owner and release owner | Validate all hashes and winner fingerprints; re-record after every frozen-input change. |
| Shared-source conflict | Worktree/package owner | Enforce exclusive owner table, package PRs and explicit rebase/handover. |
| Blinding breach or golden-data overfit | Scoring approver | Restrict golden winner results until policy freeze; restart acceptance for each new profile version. |
| Personal-data leakage | Data/security owner under G1 | Apply agreed masking consistently to API, report, UI, export and bundle; block release on mismatch. |
| Timeout/cancellation semantic drift | Engineering lead / WT-A | Test Java outer timeout, Python cancellation, compute abandonment and clean next cold run; never label cooperative deadline as hard pre-emption. |
| Baseline variance/topology shortfall | Evidence owner | Preserve the blinded result, move required generation work onto critical path, narrow claim or acquire approved data. |
| Integration becomes a semantic repair queue | Integration owner | Return missing/ambiguous contract work to its owning package; integration verifies and binds only. |

## Completion checklist

- The selected cut’s packages have merged in sequence, each with narrow tests and rollout notes.
- Required gates are recorded; golden winners remained blinded until policy freeze.
- Final evidence reconciles counts and references versioned fingerprints, policies, flags and hashes.
- Cross-stack truth, privacy, compatibility, smoke/failure, rollback and rehearsal evidence are retained.
- Recorded Demo, if selected, is explicit, valid, labelled and rehearsed.
- Documentation is refreshed only after the release gate and does not alter released behaviour.
