# SURGE demo optimization work plan — draft 0.6 (final)

Date: 17 September 2026
Status: Planning only; no production changes
Supersedes: draft 0.5 (17 September 2026)

| Item | Value |
|---|---|
| Audit baseline | `f50f717c9b2fed06a77bd2ffa12137cb5531b42d` |
| Current planning head | `a313d2f287aaf811ddafe765029423a361fece31` |
| Delta inspection | `git diff --stat f50f717..a313d2f` — audit and documentation artifacts only; no implementation file behind a §2 finding is touched |

The §2 findings are current by source-delta inspection at this planning head. WP0A re-runs the relevant probes and tests at the eventual implementation head before any behaviour work starts.

Review sources reconciled in this draft: **R1** = scope-expansion review of 0.4; **R2** = code-checked review of 0.4 (item IDs A1–A9, B1–B14, C1–C12, D1–D5, E).

---

## What changed in draft 0.6

Draft 0.5 was a presentation pass that preserved 0.4's technical content unchanged. This draft applies the review findings, most of which are corrections rather than additions.

**Scope-changing corrections (verified against source):**

- The evaluation cache context hashes the scoring policy, so candidates generated under different profiles cannot be restored into one common metric bundle. WP5B now requires splitting the evaluation context from the scoring context (R2-A1).
- Child routing runs before both the cache lookup and the evaluation-budget check, so it is uncapped work that neither the evaluation cap nor the admission deadline bounds. WP4 adds a routed-proposal cap and a pre-routing deadline check (R2-A3).
- The grouping MILPs have no time limit and report no solver status or optimality gap; WP5's `k+1` adds another solve. WP4 adds solver bounds and telemetry (R2-A4).
- Retiring ineffective personalities changes default seed generation, which contradicts the "omitted profile = legacy V0" regression gate. WP5 now carries an explicit either/or decision (R2-A5).
- The plan asserted that TRD §6.3's feeder-identity gap is already resolved in code, without evidence. That assertion is now a WP0A verification item with a conditional work package behind it (R1-§1, scoped down).

**Claim-validity corrections:**

- Cohort min–max normalisation makes a frozen policy meaningless: adding or removing any candidate can reorder winners. Acceptance now requires fixed, versioned reference ranges (R2-C1).
- Balanced must meet a regret envelope on land, environment and cost metrics it does not currently score. Balanced now carries non-zero terms for each (R2-C4).
- Minimum Cost acceptance at weight 1.0 was tautological. An independent cost recomputation check is added (R2-C7).
- Hard-violation IDs test route centrelines, not the ROW envelope; the TRD §10 evidence row was overclaiming (R2-A8).
- The strong and weak claims are now written verbatim (R2-B14); the strong claim's fingerprint choice is settled (R2-C10); "not identical to all specialised winners" is disambiguated (R2-B13).

**Sequencing corrections:** one canonical order derived from the cuts (R2-B1); cut 2's search claim reconciled with the rollout order (R2-B2); UI copy moved out of WP7 into WP6A so the release gate is not invalidated after the fact (R2-B5); WP6B made dependent on the code freeze (R2-B6).

**Additions:** audit traceability matrix (R1-§9); explicit non-claims section absorbing R1's proposed WP5C as content rather than a work package; personal-data handling for landowner evidence (R2-D3); gate latest-decision dates and default outcomes (R2-D5); a new gate G4 on whether the shared cohort must run live.

**Not adopted:** R1's WP0C as an unconditional 1–2 day package (made conditional instead); R1's proposal to extend WP1 across the stack (cross-stack truth stays in WP6A, so lanes remain clean); R1's river-crossing metric (no profile requires it; moved to roadmap); R1's WP5C as a work package (non-claims are written, not engineered).

---

## Executive summary

**Goal.** Deliver a defensible SURGE demo on the active web-map-next → Java → Python V1 path in which the engine generates multiple feasible network alternatives under bounded, server-controlled search; four versioned policies rank a controlled candidate cohort; the published design, repair history, land/environment evidence, lifecycle-cost basis, search provenance and score contributions are visible and reproducible; and a live failure can be replaced by an explicitly labelled recorded run.

**Supported claim (strong form, verbatim).**

> For this frozen demo project and declared search budget, SURGE generated and evaluated a measured set of feasible alternatives. Each of the four named profiles ranked the same deduplicated comparison cohort using the metrics its name promises, and the four recommendations are four distinct designs. Every published recommendation can be reproduced from the recorded evidence.

**Supported claim (weak form, verbatim).**

> For this frozen demo project and declared search budget, SURGE generated and evaluated a measured set of feasible alternatives. Each of the four named profiles ranked the same deduplicated comparison cohort using the metrics its name promises, and each profile's recommendation improves that profile's named objective against Balanced by at least the pre-declared margin. Every published recommendation can be reproduced from the recorded evidence.

G0 selects which form is claimed. Under the strong form the four winners must have four distinct **final-design** fingerprints, so a Minimum Cost winner differing from another winner only in conductor selection satisfies it (R2-C10).

**Explicit non-claims.** Global optimality, general project-scale performance, terrain-aware routing, economic optimisation of every conductor and feeder decision, N-1 compliance, protection coordination, or engineering certification. The full list is §17.

**Effort.** Recommended scope (live shared-cohort deferred, §12 cut 5) is **15–27.5 engineer-days** before contingency. Full scope including the live cohort is **18.5–33**. Conditional WP0C adds 1–2 if triggered. Carry 25–35 % uncertainty until G0–G4 and WP0B complete. With contingency, plan against roughly **19–37 engineer-days** for the recommended scope. External approvals and data waits are excluded.

**Immediate next actions.** Owners decide G0 claim strength, G1 golden data and G4 cohort surface. Execute WP0A, then WP0B. No behaviour change until those pass.

---

## Glossary

| Term | Meaning in this plan |
|---|---|
| Shared comparison cohort | One frozen set of fully evaluated, deduplicated, evidence-complete candidates that every profile ranks. Cross-profile winner claims are valid only on this cohort. |
| Final-design fingerprint | Canonical identity of an installed design: geometry fingerprint plus final conductor assignments plus other versioned installed fields. Used for deduplication and for the strong claim. |
| Profile / policy | Server-owned, versioned scoring configuration: weights, metric definitions, fixed reference ranges, tie-breaks. Clients select only an allow-listed ID. |
| Personality / generation configuration | Settings influencing candidate generation (seeds, search parameters). Distinct from scoring policy. |
| Admission deadline | Monotonic wall-clock guard preventing the start of another unit of bounded work after expiry. Cooperative, not pre-emptive. |
| Recorded Demo mode | Operator-activated fallback serving a validated evidence bundle. Never automatic, always visibly labelled. |
| V0 behaviour | The current legacy-compatible request/response behaviour produced when no profile fields are sent and both flags are off. |

---

## 1. Outcome and supported claim

Prepare a defensible SURGE demo in which the active web-map-next → Java → Python V1 path:

- generates multiple feasible network alternatives under bounded, server-controlled search;
- ranks a controlled candidate cohort under four versioned policies;
- publishes the installed conductor design, repair history, land/environment evidence, lifecycle-cost basis, search provenance and score contributions; and
- can reproduce the recommendation, or deliberately switch to a visibly labelled recorded run.

The claim texts are in the Executive summary and are frozen at G0. The delivery makes no claim beyond them.

---

## 2. Verified starting point

The system already has a deterministic integrated pipeline: capacity-constrained feeder grouping, per-feeder MST topology, constraint-aware routing, Pandapower validation, conductor repair, land and lifecycle assessment, unified and cost-aware scoring, bounded candidate search, Java persistence, and UI explanation/export surfaces.

Finding IDs F1–F11 are the audit's own. P1 and E1 are plan-derived and marked as such (R2-A6).

### Current gaps and delivery treatment

| Ref | Current gap | Treatment |
|---|---|---|
| F1a | Beam search is implemented but defaults off, is unreachable through **either** API (V1 is the demo path; v2 is equally unreachable and out of scope), has no wall-clock guard, and its lineage/statistics are absent from the public response. | WP4 |
| F1b | Pole micro-siting is implemented internally but unreachable through the API. | Deferred; the demo must not imply it is active |
| F2 | Two scheduled personalities add no independent topology diversity: `f(w)=w*(1+alpha*w/w_max)` preserves edge order and therefore the MST (100/100 unchanged edge sets in the audited probe), and the balance MILP does not consume its KMeans centroid seed. Duplicate scheduled topologies were observed. | WP5 |
| F3 | Repaired physics and costing use the final conductor configuration, but the orchestrator omits the repair log from presentation, selected segment output lacks final conductor IDs, and candidate summaries expose initial sizing. | WP1 (Python), WP6A (stack) |
| F4 | Cache entries omit `land_assessment`; a hit can differ semantically from a miss. | WP1 |
| F5 | Search is bounded and geographically heuristic; no optimality certificate. Top-N truncation also happens **before** structural screening and deduplication, so rejects and duplicates can consume the proposal shortlist (R2-A7). | Truncation ordering fixed in WP4; the heuristic nature is accepted and disclosed (§17) |
| F6 | Cable sizing and repair are ampacity/feasibility driven and never see prices; grouping returns the first capacity-feasible feeder count before economics. | WP5 plus the mandatory Minimum Cost disclosure (§7) |
| F7 | Forest/environment aliases collapse to a generic restricted-area type; raw environmental overlap and per-parcel ROW areas exist but are not canonical `ScoringMetric`s. Hard-violation IDs test route centrelines, not the ROW envelope. | WP2; centreline limitation disclosed (§17) |
| F8 | Canonical metrics require poles even at zero pole weight. | Accepted: V1 supplies a default pole configuration. Revisit only if the demo moves to v2 |
| F9 | One electrical operating point; no N-1, protection or dispatch study. | Outside demo scope; non-claim |
| F10 | Land routing penalties are proxies, not exact acquisition optimisation. | Accepted: generation inputs are disclosed separately from ranking evidence |
| F11 | Scalability and reproducibility are unmeasured; child routing is uncapped and the MILPs have no time limit or solver telemetry. | WP4 bounds and telemetry; WP0B/G2 runtime envelope; production scale is a non-claim |
| P1 *(plan-derived)* | V1 maps legacy weights to `LEGACY_COMPATIBILITY`; the scenario label is not a canonical policy selector. Java does send four differentiated legacy weight/constraint configurations, so the selector is not cosmetic, but it cannot rank on land, environmental or lifecycle terms. | WP3 |
| E1 *(plan-derived)* | Tests cover deterministic fixtures and many component behaviours, but not full cache equivalence, a controlled cross-profile cohort, final installed design truth across the stack, production-like cold runtime, or the complete Java/UI round trip. | WP0B, WP6 |
| TRD §6.3 | The TRD records a feeder-identity mismatch between the Python response and Java `RouteService`. The plan's working assertion is that current behaviour is intentional and correct (`feederName` emitted, one row per segment with `segmentId`, BOM/export aggregating by `feederName`) and that the TRD is stale. **That assertion is unverified.** | WP0A verifies it; WP0C activates only if it fails |

---

## 3. Delivery and trust-boundary decisions

- Keep the demo on the active web-map-next → Java → Python V1 path. The legacy web-map is not a delivery surface.
- Extend V1 additively. Missing profile fields mean V0 behaviour. An explicit unknown profile or version is rejected with a stable error and never silently falls back to Balanced.
- Clients select only an allow-listed profile ID. Java and Python resolve immutable server-owned weights, metric definitions, fixed reference ranges and generation settings. Arbitrary client weights, budgets and profile definitions are not accepted on the demo path.
- **One source of truth for profile definitions** (R2-B11). Definitions live in Python. Java holds only allow-listed IDs and versions plus a definition hash, and a startup handshake compares that hash against the Python service. A mismatch fails the deployment rather than the request. The trust rules apply per hop: browser → Java accepts only a profile ID; Java → Python may additionally send allow-listed generation settings.
- Echo the effective profile version, policy hash, metric-registry version, generation-settings hash and feature-flag state in evidence.
- Keep profile selection and search activation behind independent, default-off deployment flags (R2-B10):

  | Profiles | Search | Supported | Meaning |
  |---|---|---|---|
  | off | off | Yes | V0 behaviour; the regression baseline |
  | on | off | Yes | Profile-native ranking over seed candidates |
  | off | on | Yes | Bounded search under legacy scoring; cut 2's claim |
  | on | on | Yes | Full demo configuration |

  Both flags roll back independently. §10's deployment order sequences enablement; it does not make the search-only combination unsupported.
- Treat routing penalties as candidate-generation inputs and scoring metrics as recommendation evidence. Explanations must not merge them.
- Restore cache and selected-output truth before search can be enabled.
- Bound all search work by deterministic count, round, archive **and routed-proposal** limits, plus a monotonic admission deadline checked **before routing**, plus an outer Java job timeout for hung work. Cooperative deadline checking is not described as a hard pre-emptive timeout. State explicitly what happens to the Python worker when the Java job times out: the request is cancelled and its compute abandoned, and the next cold run must not inherit its state.
- Bound every MILP solve with a time or node limit and record solver status and optimality gap. A hit limit that could change the result fails the rehearsal, under the same rule as the admission deadline.
- On exhaustion, publish only fully evaluated candidates plus a stable termination reason. If no eligible candidate exists, return a stable failure; never publish a partial candidate.
- A live failure remains a failure. Recorded Demo mode is entered only by explicit operator action and is labelled before recorded results appear.

---

## 4. Acceptance architecture

### 4.1 Frozen input and controlled request differences

Freeze one sanitised project-input snapshot, catalogue, dependency images and demo-machine specification. The four Java-serialised requests are not byte-identical: they may differ only in the declared profile ID/version and allow-listed generation settings. Record a field-level diff proving that project geometry, electrical inputs, catalogue, data identities and all non-policy settings are unchanged.

### 4.2 Shared comparison cohort

Cross-profile claims use one controlled cohort, built by: running every pre-declared profile-native generation configuration under fixed deterministic budgets; unioning all fully evaluated candidates; deduplicating by the versioned final-design fingerprint; applying identical engineering-feasibility rules; excluding any candidate missing a metric required by any profile, with stable incompleteness reason codes; and ranking that same cohort under all four frozen policies.

Three rules make the cohort trustworthy:

- **Exclusion reporting (R2-C8).** Publish exclusion counts per reason code and a maximum acceptable exclusion rate. `k+1` candidates silently losing lifecycle cost would otherwise hollow out the Minimum Cost story without anyone noticing.
- **Deterministic deduplication representative (R2-C9).** When several lineages share one final-design fingerprint, keep the lowest sorted candidate ID and record the discarded lineages.
- **Cohort identity.** Every displayed winner references the same cohort hash.

Profile-native end-to-end runs remain operational evidence for latency, request mapping and displayed results. They are not, by themselves, evidence that scoring weights caused cross-profile winner differences.

**Where the cohort runs is a decision, not a given (G4).** The cohort can be produced by the WP0B evidence runner and published as recorded acceptance evidence, with the live demo showing profile-native runs; or it can be implemented in the live Java → V1 path (WP5B). The first is materially cheaper and supports both claim forms, provided the runbook states that cross-profile comparison rests on the recorded cohort and that live winners may differ because the live candidate set differs. The second is the stronger demo. See §12.

### 4.3 Policy freeze, reference ranges and anti-overfitting

**Fixed reference ranges are mandatory (R2-C1).** Cohort min–max normalisation makes a frozen policy meaningless, because adding or removing any candidate can reorder winners. Acceptance requires fixed, versioned reference ranges per metric. A regression test asserts that removing a non-winning candidate from the cohort does not change any profile's winner.

**Blinding procedure (R2-C2).** WP0B may measure whether raw metrics have usable variance. The WP0B operator publishes metric distributions and count reconciliation only; winner identities, ranks and scores under any candidate policy are withheld. The scoring owner then freezes metric definitions and directions, reference ranges, weights, tolerances, tie-breaks, Balanced envelopes and allowed generation differences, as a timestamped commit whose hash is recorded in the evidence. Unblinding happens after that commit.

**Retune budget (R2-C3).** Each retune creates a new profile version and restarts acceptance. At most three versions per profile may be produced before the delivery is reported as failing its claim; the version count is disclosed in investor-facing evidence regardless.

Focused synthetic fixtures prove metric causality. The golden project is a pass/fail demonstration, not tuning data.

### 4.4 Fingerprints

- **Topology fingerprint** — sorted logical nodes/edges and feeder membership, independent of transient IDs and serialisation order.
- **Geometry fingerprint** — ordered projected features after declared CRS, axis order, units, precision quantisation, direction/orientation and empty-geometry rules.
- **Final-design fingerprint** — geometry fingerprint plus final installed conductor assignments and other explicitly versioned installed fields. **This is the fingerprint the strong claim uses** (R2-C10).

Each canonicaliser has its own version and golden test vectors. `SCN-001` appearing twice is not evidence of the same design.

---

## 5. Gates and owner decisions

Every gate carries a latest-decision date, set by back-scheduling from the demo date once G2 fixes it, and a default outcome if it slips (R2-D5).

| Gate | Owner | Required decision / evidence | Default if it slips |
|---|---|---|---|
| G0 — stage claim | Demo owner + scoring approver | Strong or weak claim, verbatim; minimum land/environment effect sizes; tolerances; Balanced regret/percentile thresholds. All frozen before unblinding. | Truth and evidence work continues; no claim-aligned policy delivery starts. Latest date: WP2 start |
| G1 — golden data | Project owner + data/security owner | Exact project snapshot, four serialised request variants, catalogue revision, sanitisation and retention rules, and a transport probe proving Java carries parcel and forest/environment identity plus soft/hard mode. Also what may be **displayed**, not only stored (R2-D3). | Rename or drop the unsupported scenario; synthetic data cannot silently replace the golden project. Latest date: WP0B start |
| G2 — runtime envelope | Project owner + engineering lead | Demo date, named hardware and images, cold-run definition, outer job timeout, maximum end-to-end runtime, required headroom, and whether the demo recomputes per click or once per project (R2-D2). | Search stays disabled; ship the measured seed-only cut. Latest date: WP4 start |
| G3 — recorded run | Demo owner + data/security owner | Recorded-bundle storage, serving path, retention, on-screen wording. | Delivery is live-only and cannot claim fallback protection. Latest date: WP6B start |
| G4 — cohort surface | Demo owner + engineering lead | Is the shared cohort produced as recorded acceptance evidence, or implemented in the live path (WP5B)? | Recorded evidence; WP5B is not started. Latest date: WP2 start |

---

## 6. Work packages and dependency order

| Order | Work package | Lane | Estimate | Depends on | Exit condition |
|---:|---|---|---:|---|---|
| 0A | Re-verify findings at implementation HEAD | Both | 0.5–1 d | None | Lockfile environment boots and a clean Compose start succeeds (R2-B7); targeted tests and probes re-run; F1–F11, P1 and E1 confirmed, amended or struck with source/test evidence; **the TRD §6.3 feeder-identity assertion is verified against Java persistence, BOM aggregation and export code**, and WP0C is either triggered or closed with evidence |
| 0B | Freeze and measure evidence baseline | Both | 1.5–2.5 d | G1; WP0A | Four serialised request variants and their allowed diff; versioned evidence schema and canonicalisers; cohort runner; current cold/warm measurements; count reconciliation; blinded metric distributions; **catalogue preflight** confirming every installed conductor, pole and land component is priced (R2-B9); **count of distinct topology fingerprints on the golden project today** — if fewer than three, WP5 moves onto the critical path and the cuts reorder (R2-C11). No behaviour change |
| 0C | Cross-service feeder/segment identity contract | Both | 1–2 d *(conditional)* | WP0A finding | Only if WP0A shows the current semantics are wrong or undefined: fix one Feature = one routed segment under one feeder across Python response, Java DTO and persistence, UI and BOM/export, with a cross-language contract fixture. If WP0A confirms the assertion, this closes at zero cost and the fixture is added inside WP3 |
| 1 | Restore candidate and selected-output truth | Python | 1–2 d | WP0A confirms F3/F4 | Cache hit/miss equality covers land decisions, owner basis and per-parcel areas; API and presentation publish successful repair actions and final installed conductor ID per segment; initial sizing is explicitly labelled initial-only. The cache context gains metric-registry and evidence-schema versions and typed layer identity, and the pipeline version bumps whenever the cached payload shape changes, with a test that an older-version cache never hits (R2-A2) |
| 2 | Add typed land/environment metrics | Python + conditional Java | 2–4.5 d | WP0A confirms F7; WP0B variance; G0 | Source ID, canonical feature type and soft/hard mode survive Java → V1 → parser → ROW analysis → metrics; `affected_parcel_row_area_m2` and unique `environmental_overlap_m2` become canonical metrics with raw, normalised and weighted contributions; legacy defaults unchanged. The 0.5–1.5 d Java transport task is owned by the WP2 lead and triggered by the G1 probe result (R2-B8) |
| 3 | Add the versioned V1 profile contract | Both | 2–3.5 d | WP2; G0; WP0B catalogue preflight | Allow-listed profile ID/version maps to immutable canonical configs; Java serialises all four; missing fields preserve V0; unknown explicit versions fail closed; effective hashes returned and persisted; startup definition-hash handshake passes; cross-language fixtures pass |
| 4 | Expose bounded search and evidence | Both | 2–3 d | WP0A confirms F1a/F5/F11; WP1; G2 | Default-off server activation; caps cover seeds and children and report them separately; archive, proposal, **routed-proposal**, evaluation and round limits; admission deadline checked **before routing**; structural screening and deduplication applied **before** top-N truncation; MILP time/node limits with solver status and gap recorded; outer Java timeout with defined worker cancellation; public lineage, counts, cache hits and termination reason; forced-deadline test proves termination and absence of partial output; legacy-off behaviour compatible |
| 5 | Replace ineffective personalities and add explicit `k+1` generation | Python | 1.5–2.5 d | WP0A confirms F2/F6; WP0B | An explicit capacity-valid extra-feeder candidate is generated deterministically; acceptance and failure evidenced on golden and synthetic fixtures; a regression test preserves the audited result that the old monotone transform leaves MST edge sets unchanged. **Decide and record one of:** (a) the new schedule is gated behind the profile/search flag so V0 stays byte-equivalent, or (b) V0 intentionally changes and its golden output is re-baselined (R2-A5). WP5 is mandatory for any claim that feeder-count economics were considered |
| 5B | Live shared-cohort comparison | Both | 3.5–5.5 d *(only if G4 selects live)* | WP2–WP5; G4 | **Split the evaluation context from the scoring context** so raw metrics cache under physics, land, cost, layers and poles while rescoring happens under the policy (R2-A1) — the current context hashes policy mode and all weights, so a common metric bundle does not exist today. Then the live path runs all approved generation configurations, unions and deduplicates by final-design fingerprint, scores that cohort under all four policies, and persists a cohort ID/hash that UI and exports reference |
| 6A | Cross-stack integration, claim copy and rollout verification | Cross-stack | 2–3 d | Required WPs for the selected cut; WP5B if live cohort | Final conductor IDs and repair actions agree across final electrical config, costing, Python output, GeoJSON, Java persistence, UI and exports; compatibility matrix and deployment/rollback order pass, including Java-rollback-with-new-frontend (R2-D1); clean Compose smoke and failure paths pass; **UI claim copy, disclosures and non-claims ship here, not in WP7** (R2-B5) |
| 6B | Build Recorded Demo mode | Java + frontend | 1–2.5 d | G3; WP6A; **release-candidate code freeze** (R2-B6) | Versioned bundle validates request, profile, code, image, catalogue and schema hashes plus winner fingerprints; Java serves it through the normal read path; UI requires an explicit mode switch and shows a persistent recorded-run banner; switching back clears recorded state before live data renders; any hash change forces a re-record |
| 6C | Rehearse and release-gate | Cross-stack | 1–2 d | WP6A; WP6B if in scope | Three clean cold rehearsals meet G2 with stable fingerprints and counts; live failure and rollback rehearsal passes; recorded-mode drill passes when in scope; runbook has named operators, triggers and rollback rules |
| 7 | Refresh documentation | Docs | 0.5–1 d | WP6C | TRD §§2.2, 3.3, 4.1–4.2, 5, 6.3, 10, 11; PRD §10 status snapshot; APP-FLOW screens 4–6 preliminary and planned labels; root README and architecture/status docs; maturity labels Implemented / Partial / Planned. Documentation only — no UI or behaviour change after the release gate |

### Effort summary

| Lane | Range (engineer-days) |
|---|---|
| Python-heavy | 7.5–13 |
| Java / cross-stack | 5.5–10.5 |
| Frontend + docs | 2–4 |
| **Recommended scope** (cut 5, live cohort deferred) | **15–27.5** |
| Full scope (adds WP5B) | 18.5–33 |
| Conditional WP0C, if triggered | +1–2 |

Carry 25–35 % uncertainty until G0–G4 and WP0B complete. With contingency the recommended scope is roughly **19–37 engineer-days**. Once G2 fixes the demo date, back-schedule a latest start date for each cut and each gate (R2-D4/D5). Calendar time can be shorter through non-overlapping lanes; external approvals and data waits are excluded.

### Critical path

```
G1 → WP0A → WP0B → WP1 → WP2 → WP3 → WP6A → WP6C → WP7
                        ↘ WP4 (after WP1 + G2)
                        ↘ WP5 (after WP0B)
G4 (live) ─────────────→ WP5B → WP6A
G3 ────────────────────→ WP6B → WP6C
```

WP3 and parts of WP2, WP4 and WP6A sit in the Java lane. If Java availability is the binding constraint, §12 cut 2 is entirely Python-lane and can proceed alone.

---

## 7. Scenario policy contract

Every profile ranks the same cohort under fixed, versioned reference ranges. All candidates use identical feasibility rules and must carry complete evidence for every active comparative metric.

| Profile | Canonical policy | Required terms | Acceptance |
|---|---|---|---|
| Minimum Cost | Cost-aware; modelled lifecycle-cost weight 1.0; engineering is feasibility plus deterministic tie-break | Versioned modelled lifecycle cost with named components, currency and basis date, study horizon, discount and escalation, loss-value assumptions | Selects the lowest modelled lifecycle cost in the cohort within declared tolerance, **and** an independent recomputation (BOM × catalogue + valued losses) matches the reported lifecycle cost within tolerance (R2-C7) |
| Minimum Land Impact | Unified engineering | `affected_parcel_row_area_m2` primary; affected parcel count and owner interactions secondary. **Primary means lexicographic priority**: parcel count and owner interactions break ties only within the declared ROW-area tolerance band (R2-C6) | Improves the frozen land objective versus Balanced by the G0 margin; focused fixtures prove the land term changes rank; the cost delta versus Balanced is displayed (R2-C5) |
| Minimum Environmental Impact | Unified engineering | Unique forest/environment overlap area, plus any explicitly applicable water or soft-overlap metric | Typed identity and mode survive the round trip; overlap varies across the cohort; improves the frozen environmental objective versus Balanced by the G0 margin; focused fixtures prove causality; the cost delta versus Balanced is displayed |
| Balanced | Unified engineering | Non-zero physical, spatial, infrastructure and electrical groups, **plus non-zero land, environmental and lifecycle-cost terms** (R2-C4) | Meets the pre-declared G0 maximum-regret or percentile envelope on each named specialised metric, **and** its winner is not identical to **every** specialised winner — at least one specialised profile selects a different design (R2-B13) |

Balanced previously carried no land, environment or cost terms while being required to stay within a regret envelope on exactly those metrics. Bounded regret would have been luck rather than design; hence the added terms.

**Minimum Cost disclosure**, mandatory in the runbook, UI explanation and any investor-facing description:

> SURGE selects the lowest modelled lifecycle cost among the generated, fully evidenced candidates. Conductor selection is driven by electrical suitability rather than installed price or loss economics. Except for the explicit `k+1` alternative, feeder generation is not an economic optimiser.

Routing penalties may differ only as versioned generation settings and are displayed separately from the metrics that rank the cohort.

---

## 8. Evidence contract

The evidence record stores:

- sanitised project-input hash and all four serialised requests, with an allow-listed field diff;
- Java, Python and frontend revisions; clean-repository proof or a retained content-addressed source artefact; lockfile hashes; container image digests; OS and runtime versions; host specification; cold/warm definition;
- profile ID/version, policy hash, metric-registry version, generation-settings hash, feature flags, catalogue ID/version/currency/basis date and complete cost assumptions; profile version count produced during tuning;
- requested seeds, seed outcomes, child proposals, **routed proposals**, duplicates, structural rejects, cache hits, executed evaluations, evaluation failures, feasible and eligible counts, exclusion counts per reason code, archive size, rounds and termination reason;
- **MILP solver status, wall time and optimality gap per solve**;
- topology, geometry and final-design fingerprints plus canonicaliser versions;
- lineage, mutation type and discarded duplicate lineages;
- stable failure, rejection and incompleteness codes;
- raw engineering, land, environment and lifecycle values; eligibility; fixed reference ranges; weights; contributions; tie-breaks; rank and winner;
- total wall time, available stage timings, **routing time separately**, outer-timeout and admission-deadline state, repeatability result.

Avoid the overloaded word "generated" in machine evidence; §1 and §12 use it only in prose (R2-E). Tested reconciliation equations:

- `child proposals = duplicates + structural rejects + cache hits + routed proposals not evaluated + executed child evaluations`
- `seed evaluations + child evaluations = executed evaluations`
- `executed evaluations = successful evaluations + evaluation failures`
- eligible candidates are a subset of fully evaluated or cache-restored feasible candidates with complete comparative evidence.

**Run counts (R2-B12).** The three cold rehearsals of §9 each execute all four profile-native requests and therefore satisfy the "at least three cold runs per profile" requirement. No additional runs are needed. Cohort scoring evidence and one same-process cache miss/hit equivalence run are retained separately.

Exact equality is required for deterministic IDs, fingerprints, statuses, count-limited search results and counts. Floating values use one declared default tolerance with justified per-metric overrides. Declared thresholds that must carry numbers rather than adjectives (R2-C12): the non-uniform pole-span criterion, the maximum request payload size, the maximum cohort exclusion rate, and each metric's tolerance.

---

## 9. Hard acceptance gates

### Correctness and compatibility

- WP0A confirms every implemented finding at the delivery commit.
- An omitted-profile V1 request is regression-equivalent to V0, under whichever WP5 option was chosen and recorded.
- Each profile ID/version resolves to the expected policy hash on both sides, and the startup definition-hash handshake passes. Labels alone are not authoritative.
- Invalid or unknown versions and metrics, non-finite numbers, out-of-range values and oversized payloads fail with stable errors.
- Cache hit/miss outputs match on engineering, land, cost, repair, final conductors, eligibility and recommendation semantics. Only explicitly excluded diagnostics and timestamps may differ. An older-version cache never hits.
- Final conductor IDs and repair actions agree across final electrical config, costing, Python candidate and selected output, GeoJSON, Java persistence, UI and exports.
- Search is server-controlled, disabled by default, and bounded across seeds, children and routed proposals. Structural screening and deduplication precede top-N truncation. No partial candidate is published.
- Every MILP solve reports status and gap, and no acceptance run hits a solver limit in a way that could change the result.
- Candidate-count terms reconcile under the evidence schema.

### Claim validity

- Cross-profile acceptance ranks the same deduplicated cohort, identified by cohort hash.
- Metric definitions, fixed reference ranges, weights, tolerances and tie-break rules are frozen as a timestamped commit before winner unblinding; removing a non-winning candidate does not change any winner.
- Every profile uses the metrics named by its label; a constant or absent required metric fails that profile.
- Forest/environment ID, canonical type and soft/hard mode survive Java → V1 → Python and are visible in evidence.
- Focused fixtures prove land and environment causal ranking behaviour.
- The cohort contains at least three distinct eligible topology fingerprints.
- Under the strong claim, the four winners have four distinct **final-design** fingerprints. Distinct candidate IDs are insufficient.
- Minimum Cost selects the lowest modelled lifecycle cost, passes independent recomputation, and publishes the §7 disclosure and cost basis.
- Balanced meets the frozen G0 envelope; the threshold is not adjusted after seeing results.
- Cohort exclusion counts per reason code are published and below the declared maximum rate.
- Explanations show raw values, reference ranges and weighted contributions; generation penalties are labelled separately.

### Determinism, runtime and failure handling

- Repeatability evidence uses deterministic count and round limits and completes before the admission deadline. A fired deadline fails that rehearsal and it is not claim evidence.
- A separate forced-deadline and outer-timeout test verifies termination, worker cancellation and absence of partial output.
- One cold rehearsal means a clean Compose start with empty application caches, execution of all four profile-native requests plus cohort scoring, measured from accepted Java job submission to persisted and retrievable result. Image pull and build time are reported separately. Time to first visible result per user action is reported alongside total batch time (R2-D2).
- Three cold rehearsals produce stable fingerprints and counts and each finishes within G2 with the required headroom; median and maximum are reported.
- A no-feasible-candidate or forced optimiser failure remains visibly failed and never shows prior live or recorded success data.

### TRD §10 evidence

| Expected behaviour | Required evidence |
|---|---|
| At least two feeders | Feeder count in the golden record |
| Avoid hard exclusions | No accepted candidate's route **centreline** intersects a hard exclusion. The engine does not test the full ROW envelope; that limitation is a published non-claim (R2-A8) |
| At least three valid alternatives | Three distinct eligible topology fingerprints in the cohort |
| Different scenario recommendations | G0 winner and final-design fingerprint evidence, or quantified weak-claim margins |
| Non-uniform pole spans | Winner span distribution against the declared numeric threshold |
| ROW–parcel intersections | Per-parcel area on cache miss and hit |
| Reject an electrically invalid candidate | Stable electrical failure in the golden run, or an adversarial fixture if WP0B shows the golden project produces none |
| Explain Balanced | Raw values, reference ranges, weights and contributions |

TRD §10's DEM requirement is removed or marked future, because the engine has no terrain input.

---

## 10. Rollout, rollback and recorded-mode state

Test the supported component matrix before enabling behaviour: current/new Python against current/new Java, and current/new Java against current/new frontend, including **current Java with new frontend** (R2-D1). Record intentionally unsupported combinations. Use expand/contract database changes if persistence changes.

Deployment order:

1. Deploy additive Python schema and response support with both flags off.
2. Deploy tolerant Java DTO, persistence and recorded-bundle support.
3. Deploy frontend fields, claim copy and explicit Recorded Demo mode.
4. Enable versioned profiles for the demo deployment.
5. Enable search. Search may be enabled independently of profiles for the cut 2 claim; for the profile-aligned claim, enable it only after profile and cohort evidence passes (R2-B2).

Rollback profile and search flags independently. Frontend rolls back before Java. Rollback triggers: contract parse errors, evidence-hash mismatch, non-reconciling counts, a deadline or solver limit firing in rehearsal, missing final-design truth, unstable fingerprints, or a failed definition-hash handshake.

Recorded Demo mode never activates automatically. The operator switches mode under the runbook rule; the UI shows a persistent "Recorded run" label before loading the validated bundle, and clears recorded state before live data can render.

---

## 11. Pull-request sequence

Derived from the §12 cut order, which is the single canonical priority order (R2-B1).

1. **Baseline evidence** — WP0A/0B re-verification, TRD §6.3 verification, request diff, canonicalisers, catalogue preflight, blinded measurements. No behaviour change.
2. **Candidate truth** — cache completeness, context versioning, final repair and conductor publication.
3. **Search reachability** — default-off activation, routed-proposal and evaluation caps, admission deadline before routing, screening before truncation, MILP bounds and telemetry, lineage and statistics.
4. **Generation diversity** — retire or gate ineffective personalities, explicit `k+1`, recorded V0 decision.
5. **Claim metrics** — typed environmental identity, ROW and environment metrics, score evidence.
6. **V1 profiles** — allow-listed versioned Python contract, Java profiles, definition-hash handshake, cross-language fixtures.
7. **Live comparison cohort** — only if G4 selects live: context split, union, deduplication, four-policy scoring, cohort-hash persistence.
8. **Integration, claim copy and recorded mode** — persistence, UI, exports, compatibility matrix, failure paths, validated bundle.
9. **Release gate and docs** — cold rehearsals, runbook, TRD/PRD/APP-FLOW/README refresh.

*(Conditional PR: cross-service identity contract, inserted after PR 1 only if WP0A triggers WP0C.)*

Each PR passes its own suite and preserves old payloads. No PR relies on a later PR to restore a passing branch. Database compatibility, deployment order and rollback are stated in every cross-stack PR.

---

## 12. Delivery cuts

| Cumulative effort | Work packages | Defensible stage claim |
|---|---|---|
| 3–5.5 d | WP0A, WP0B, WP1 | "The baseline is measured, and **the Python API publishes** the design that was actually installed and repaired." Cross-stack truth is not yet verified (R2-B4). No optimisation-profile claim |
| 6.5–11 d | + WP4, WP5 | "The engine performs bounded search and produced N distinct **feasible** alternatives on the demo project." N is measured. No objective-specific claim (R2-B3). Entirely Python-lane |
| 10.5–19 d | + WP2, WP3 | The versioned profile machinery ranks a controlled cohort on promised metrics. Acceptance evidence, not yet a live stage claim |
| 14–25 d | + WP6A, WP6C, WP7 | **Recommended base.** The weak or strong claim, with cross-profile comparison resting on recorded cohort evidence and live profile-native runs on stage |
| 15–27.5 d | + WP6B | **Recommended target.** As above, fallback-protected with explicit Recorded Demo mode |
| 18.5–33 d | + WP5B | The cohort is computed live, so the on-stage comparison and the acceptance evidence are the same artefact |

Cuts are cumulative only when dependencies and gates pass. A short schedule reduces the stage claim; it does not waive correctness gates.

---

## 13. Risks and mitigations

| Risk | Early check | Mitigation |
|---|---|---|
| Findings moved before implementation | WP0A | Strike or amend affected work and re-estimate before coding |
| TRD §6.3 assertion is wrong and route persistence is untrustworthy | WP0A verification | WP0C activates; re-plan the cut with +1–2 days |
| Golden data unavailable or restricted | G1 | Controlled storage with hashes; no silent synthetic substitution |
| Java cannot retain forest/environment identity | G1 transport probe | WP2's conditional Java task, or drop/rename the scenario |
| Golden metrics have no variance | WP0B blinded distribution | Fail the profile gate; acquire valid data or narrow the claim |
| Fewer than three distinct topologies exist today | WP0B fingerprint count | WP5 moves to critical path; cuts reorder |
| Policy overfits the golden result | Freeze commit before unblinding | New version and full acceptance restart per retune; at most three versions per profile |
| Landowner data is personal data shown to investors | G1 display decision | Approve what may be displayed, not only stored; mask owner identity in UI and recorded bundle unless explicitly cleared |
| Lifecycle catalogue or cost basis incomplete | WP0B preflight | Stable incompleteness codes; excluded from the cohort with a reported exclusion rate; complete the catalogue |
| Every seed is ineligible | Baseline failure distribution | Improve seed feasibility or ship the no-search cut; search cannot recover from an empty feasible frontier |
| Winners move with cohort composition | Fixed reference ranges; remove-a-loser test | Never compare winners from different cohorts |
| Uncapped routing or unbounded solver blows the runtime envelope | WP4 routed-proposal cap and MILP limits | Deadline checked before routing; solver status and gap in evidence; a fired limit fails the rehearsal |
| Cross-stack fields drift | Serialised consumer fixtures, definition-hash handshake | Additive DTOs, fail-closed explicit versions, independent flags |
| Recorded bundle mistaken for live or stale success | Explicit state transition and hash validation | No auto-fallback; persistent label; state cleared on mode change; re-record on any hash change |
| Clean stack fails on demo day | WP0A Compose build; WP6C rehearsals | Fix the build before behaviour work; keep a validated recorded mode if G3 permits |
| Output overstates engineering scope | WP6A claim-copy review | Publish §17 prominently in UI and runbook |

---

## 14. Assumptions

- The audit-baseline implementation files remain unchanged until WP0A re-verification.
- Golden project data with usable metric variance can be obtained and approved under G1.
- Demo hardware and images can be locked under G2 before search is enabled.
- Named owners for G0–G4 are available on the critical path.
- Parallelisation across Python, Java and frontend lanes is organisationally feasible; if not, cut 2 is the Python-only path.
- No new external dependency (terrain, N-1, structural engineering) enters the demo claim.

---

## 15. Inputs needed from owners

- Demo date, staffing by lane, demo-machine specification, runtime limit and headroom.
- Exact golden project snapshot, serialised-request handling rules, sanitisation approval, recorded-bundle retention approval, and what landowner evidence may be **displayed**.
- G0 claim choice, minimum land and environment effect sizes, tolerances, and numeric Balanced and weak-claim thresholds, frozen before unblinding.
- G4 decision: recorded cohort evidence, or live cohort (WP5B).
- Named approvers for profile policy and cost basis, data handling, acceptance wording, and Recorded Demo mode.
- Owner for the G1 Java transport probe, and the named owner of the profile definition source of truth.
- Whether feeder-count economics must be claimed; if yes, WP5 is mandatory.

---

## 16. Definition of Done

- All §9 gates pass at the delivery commit.
- Three cold rehearsals meet the G2 envelope with stable fingerprints and counts.
- Published UI, exports and evidence match the frozen claim text and carry the §17 non-claims and the §7 disclosure.
- Recorded Demo mode, if in scope, is validated, explicitly activated and labelled.
- TRD, PRD §10, APP-FLOW, README, runbook and UI copy are consistent with shipped behaviour.
- Profile and search rollback paths have been rehearsed.

---

## 17. Published non-claims

These appear in the runbook and in UI claim copy, not only in this plan.

- The search is bounded and heuristic. There is no optimality certificate and no proof of a local optimum.
- No free junction or Steiner node search; PNC nodes are the substation and the WTGs.
- No alternate-route search for an unchanged topology; one deterministic route per edge and surface.
- No economic conductor optimisation; conductor choice is driven by electrical suitability.
- No extra-feeder generation beyond the explicit `k+1` candidate.
- Search cannot recover from an all-infeasible seed frontier.
- Hard-exclusion checking tests route centrelines, not the full ROW or clearance envelope.
- Pole micro-siting exists internally and is **not** active in the demo.
- ML pre-ranking is trained offline and is **not** part of the runtime path.
- Results are candidate comparisons under declared heuristics on one frozen project: not global optimality, not general project-scale performance, not N-1 or protection compliance, not engineering certification.

---

## 18. Roadmap exclusions

- Route-cost-informed topology — MST currently uses geometric edge cost rather than routed-corridor cost. Needs its own benchmark and design after the demo.
- Runtime ML-assisted search — the pre-ranker is offline-trained; on the audited corpus Ridge improved recall and capture but reduced rank correlation against the heuristic baseline.
- Micro-siting API activation.
- Terrain and DEM integration, including slope-aware surfaces and study-boundary clipping.
- N-1, protection, dispatch and operating-envelope analysis.
- Pareto or joint optimisation across assignment, topology, routing and conductor selection.
- Structural pole engineering: sag, clearance, pole class, foundations.
- General cable-economic optimisation.
- Additional spatial metrics not required by any profile: river crossing count, and unique ROW footprint area as a separate scored term.

---

## 19. Audit traceability

| Finding | Work package | Acceptance evidence |
|---|---|---|
| F1a search unreachable | WP4 | Default-off activation; public lineage, counts, termination reason |
| F1b micro-siting unreachable | Deferred | Published non-claim; no demo activation |
| F2 ineffective personalities | WP5 | Unchanged-MST regression preserved; explicit `k+1`; recorded V0 decision |
| F3 repair and conductor publication | WP1, WP6A | Final conductor ID and repair log across Python, persistence, UI, exports |
| F4 cache drops land | WP1 | Cache hit/miss semantic equality including land evidence |
| F5 heuristic search, truncation order | WP4 + §17 | Screening and deduplication before truncation; non-claims published |
| F6 economics not a conductor optimiser | WP5 + §7 | Minimum Cost disclosure; independent cost recomputation |
| F7 environmental identity incomplete | WP2 | Typed identity and mode; canonical metrics with contributions |
| F8 poles required at zero weight | Accepted on V1 | Demo supplies pole configuration |
| F9 one operating point | Non-claim | No N-1, protection or dispatch claim |
| F10 land routing proxies | Non-claim | Generation inputs separated from ranking evidence |
| F11 scalability, uncapped routing, unbounded MILP | WP4, WP0B, G2 | Routed-proposal cap, MILP limits and telemetry, runtime envelope |
| P1 scenario label not a policy | WP3 | Versioned profile contract with definition-hash handshake |
| E1 test gaps | WP0B, WP6A, WP6C | Controlled cohort, cold runtime, full round trip |
| TRD §6.3 feeder identity | WP0A, WP0C if triggered | Verified semantics plus cross-language contract fixture |

---

End of draft 0.6