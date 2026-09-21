# Phase 1 record — SURGE demo optimisation merge queue

Created: 18 September 2026 · Updated: 21 September 2026
Main: `2159c4a` · Base tag: `demo-opt-base`
Plans: [L1](../SURGE%20demo%20optimization%20L1%20worktree%20plan.md) · [L2](../SURGE%20demo%20optimization%20L2%20worktree%20plan.md) · [L3](../SURGE%20demo%20optimization%20L3%20worktree%20plan.md) · Stage 0: [stage0/README.md](../stage0/README.md) · Contracts: [contracts/README.md](../../../contracts/README.md)

This is the running record of what the merge queue has actually merged, what is gate-blocked, and the assessment of the Annigeri dataset against G1. The three worktree plans are the signed-off reference and are not edited; where this record proposes a change to them, it says so and names the decision needed.

---

## 1. Merge queue progress

| Slot | PR | Branch | Merged as | State |
|---|---|---|---|---|
| — | [#34](https://github.com/cookedaryan/surge/pull/34) CCR #33, S5 `feeder_count` seam | `ccr/s5-feeder-count-seam` | `075be24` | **Merged.** Issue #33 closed |
| 1 | [#35](https://github.com/cookedaryan/surge/pull/35) L1 baseline characterisation | `demo-opt/l1-baseline-characterisation` | `e31c65d` | **Merged** |
| 1 | [#37](https://github.com/cookedaryan/surge/pull/37) L3 baseline identity | `demo-opt/l3-baseline-identity` | `997f300` | **Merged** |
| 1 | — | L2 `baseline-measurement` | — | **Not opened.** See §3 |
| 2 | [#36](https://github.com/cookedaryan/surge/pull/36) L2 candidate truth and cache identity | `demo-opt/l2-wp1-truth` | `6601234` | **Merged** |
| 3 | — | L2 `wp4-search`, L2 `wp4-java-timeout`, L3 `wp4-cancellation` | — | **Skipped while G2 is undecided** (L-plans §1) |
| 4 | [#39](https://github.com/cookedaryan/surge/pull/39) L3 WP5 generation | `demo-opt/l3-wp5-generation` | `b95e6f2` | **Merged** |
| 5 | [#42](https://github.com/cookedaryan/surge/pull/42) L2 WP2-3 Java transport of typed identity | `demo-opt/l2-wp2-java-transport` | `4215e4d` | **Merged** |
| 5 | [#43](https://github.com/cookedaryan/surge/pull/43) L3 WP2-4 typed identity through parser, ROW and metrics | `demo-opt/l3-wp2-metrics` | `f7f96a6` | **Merged** |
| — | [#45](https://github.com/cookedaryan/surge/pull/45) CCR #44, metric registry version 2 | `ccr/metric-registry-v2` | `6b283ae` | **Merged.** Issue #44 closed |
| 5 | [#46](https://github.com/cookedaryan/surge/pull/46) L3 WP2-5, WP2-6 canonical land and environment areas | `demo-opt/l3-wp2-metrics` | `2159c4a` | **Merged** |
| 5 | — | L3 WP2-7, WP2-8 | — | **Next.** WP2-7 needs a CCR amending C2 before it can register metrics (§3) |
| 6 | — | L3 `wp3-profiles`, L2 `wp3-java-profiles` | — | **Open**, unstarted |
| — | [#38](https://github.com/cookedaryan/surge/pull/38) this record · [#40](https://github.com/cookedaryan/surge/pull/40) G0 decision · [#41](https://github.com/cookedaryan/surge/pull/41) refresh | `docs/phase1-record` · `contracts/g0-claim` · `docs/phase1-refresh` | `d9f5031` · `a0ecfc8` · `54cd560` | **Merged.** Documentation branches; the ownership job does not run on them |

Every merged PR was rebased onto main before merging, per the queue rule, and CI was green on the rebased head. Tasks delivered: WP2-2, WP3-2, WP4-2, WP5-1 (L1); WP0B-7, WP0B-6, WP0B-11, WP5-2, WP5-3, WP5-4 (L3); WP1-1 … WP1-5, WP2-3 (L2); WP2-4, WP2-5, WP2-6 (L3).

**Slot 5 is four tasks deep.** Typed identity now runs end to end: Java sends it (#42), Python canonicalises it, carries it through ROW analysis and classifies constraints by it (#43), and the canonical land and environment areas are computed from it (#46). Slot 3 still waits on G2.

## 2. State of merged main

| Check | Result |
|---|---|
| Python suite on merged main | **1498 passed** at `2159c4a`, after slot 5's WP2-6 |
| Python suite after slot 4 | **1478 passed** at `b95e6f2` |
| Python suite after slot 2, before slot 4 | **1443 passed** at `6601234` |
| Trial integration before any merge: all four level branches plus the CCR, merged in queue order | **1478 passed**, no textual conflict |
| L1 ownership check | Pass, 14 paths |
| L2 ownership check | Pass, 6 paths (slot 2), 4 paths (slot 5, `backend-java/` only) |
| L3 ownership check | Pass, 6 paths (slot 1), 7 paths (slot 4), 6 and 3 paths (slot 5) |
| CI on each rebased head | Python, Java, web map, container builds, ownership — all pass. #42 was the first Java compile of its branch: this machine has no JDK, so CI was the verification, and the PR said so |

The V0 goldens merged in slot 1 have since held green through six runtime PRs, including slot 4's generation change, which is the live evidence that the characterisation suite does the job the L1 plan §4.1 claims for it. Slot 4's own claim — both flags off means the V0 schedule — rests on those goldens rather than on a test it ships itself.

**The goldens and the contract pack have each blocked a real change, correctly.** During WP2-5 and WP2-6, registering the new metrics in `ScoringMetric` added keys to `recommendation.normalization_ranges` and `recommendation.baseline_comparisons` in the V0 response. No value moved — a new metric carries weight 0.0 — but the key set did, and the goldens failed on it at once. Separately, bumping `METRIC_REGISTRY_VERSION` failed `test_contract_pack.py`, because the constant is exported into frozen `contracts/` artefacts; that became CCR #44. Both are the guardrails working as designed, and both are recorded here so later tasks inherit them rather than rediscover them.

**One behaviour note on WP1-5.** `design_truth` is emitted only when a profile is resolved or search is enabled, so it stays absent from V0 responses and from every request the product can make today. The repair log and final installed conductors therefore remain user-invisible until slot 3 or slot 6 lands. This is consistent with L1's search-off golden, which asserts no additive block is present with both flags off, and it is recorded in #36. Java persistence of the final conductor (WP6A-6) depends on those fields.

## 3. Open work and stragglers

**L2 `baseline-measurement`, slot 1, not opened.** Slots 1 and 2 merged without it. Under the queue rules that is allowed — no PR may rely on a later PR, and a gated slot does not block a ready one — but it makes this PR a straggler that must rebase onto everything above it and keep the V0 goldens green. Two of its tasks need no gate and can ship now: WP0B-5, the topology fingerprint canonicaliser, and the tooling half of WP0B-8, whose harness may be built on synthetic data (only its golden runs wait on G1).

**Slot 5: WP2-7 and WP2-8 remain, and WP2-7 opens with a CCR.** WP2-7 publishes raw, normalised and weighted contributions in the C2 `scoring_explanation` shape. It cannot simply register `AFFECTED_PARCEL_ROW_AREA` and `ENVIRONMENTAL_OVERLAP` in `ScoringMetric`: scoring enumerates every member into the V0 body, so that changes the V0 key set (§2). It needs a **CCR amending C2**, with the contributions placed in the `scoring_explanation` additive block rather than the V0 body. That is a design constraint on the task, known before it starts. After slot 5, L3's chain continues into slot 6: WP3-4 → WP3-3 → WP3-1 → WP3-6a → WP3-7a → WP3-9a, the long pole to FRZ-1.

**Slot 6: open and unstarted.** Neither `wp3-profiles` nor `wp3-java-profiles` has a branch.

**Findings from slot 5, owned elsewhere, not yet actioned:**

| Finding | Where | Owner | Consequence |
|---|---|---|---|
| The response's spatial summary still collapses identity. `result_builder.py` keeps its own private copy of the routing-class mapping, separate from the one WP2-4 fixed | `app/presentation/result_builder.py` | L2 | Once typed identity flows, the summary in the response and the metrics disagree about whether a feature is a forest |
| `HT_LINE` maps onto the ROW class `environmental` | `_row_layer_type` in `app/optimisation/engineering_metrics.py` | L3 | `environmental_overlap_m2` still counts power-line crossings. Correcting it moves metric inputs for requests that send no identity, so it is a V0 change needing its own task and likely a golden re-capture through a CCR |
| KMZ ingest collapses forest identity before storage. `AssetService.restrictionTypeFor` maps FOREST, SANCTUARY and WILDLIFE all to `PROTECTED_AREA` | `backend-java/.../AssetService.java` | L2 | A reserve forest is stored as a protected area, so the transport in #42 faithfully sends the wrong class. Fixing it changes stored data |

**L1's remaining Phase 1 work.** WP6A-1 was unblocked by the G0 decision of 2026-09-18 and can now be built as the `wp6a-claim-copy` PR, which merges at Stage 2 step S2-4, not in Phase 1. WP0B-1 still waits on G1. The WP6C-4 runbook skeleton and the WP7 documentation change list are drafted in the L1 worktree and stay unmerged until their Stage 2 steps.

## 4. Gate status

| Gate | Owners | Blocks | Latest date (draft 0.6 §5) | Status |
|---|---|---|---|---|
| G0 — stage claim | Demo owner + scoring approver | Slots 5 and 6, then FRZ-1 and Stage 2 | WP2 start | **Decided 2026-09-18: weak claim.** See [`contracts/decisions/g0-claim.md`](../../../contracts/decisions/g0-claim.md) |
| G1 — golden data | Project owner + data/security owner | WP0B-1; WP0B-3, 8, 9, 10 golden runs; WP0B-2 | WP0B start — **passed** | **Transport clause satisfied in code by #42.** Data half undecided. See below |
| G2 — runtime envelope | Project owner + engineering lead | All of slot 3 | WP4 start — **now** | Undecided |
| G4 — cohort surface | Demo owner + engineering lead | S2-3 | WP2 start | Undecided; default is recorded evidence |

**G2 is the only gate still holding an entire slot**, and G1 the only one holding named tasks. No owner decision has been recorded on G1, G2 or G4 since the G0 record landed on 18 September.

**G1's circularity is resolved in code.** Its transport clause required a probe proving Java carries parcel and forest/environment identity plus soft/hard mode. That probe failed in Stage 0 ([stage0/README.md §4](../stage0/README.md)), and the fix, WP2-3, was itself gated on G1. WP2-3 went ahead as the G1-enabling fix and merged in #42: every avoidance feature now carries `source_id` (the cadastral `parcel_id` for parcels) and `feature_type`, and the Stage 0 probe test is replaced by its positive form. Mode still survives, as it always did.

*Still needed from the G1 owners:* record that the transport clause is satisfied by #42, so the gate is resolved on paper and not only in code, and decide the data half — snapshot, catalogue revision, sanitisation, retention and display rules. None of that needs engineering. One caveat belongs in that record: the KMZ ingest collapse in §3 means a forest imported through KMZ is still stored, and therefore sent, as a protected area.

**G2 is the cheapest unblock.** It is a set of facts, not a research result: demo date, named hardware and images, cold-run definition, outer job timeout, maximum end-to-end runtime, required headroom, and whether the demo recomputes per click or once per project. Recording it opens all of slot 3 across two levels.

## 5. Annigeri dataset — assessment against G1

Assessed 18 September 2026 from `Annigeri Dataset/` at the repository root. **It is not currently a golden project, and it is not currently in the repository's data path.**

### 5.1 What it contains

| Layer | Features | CRS | Measure |
|---|---|---|---|
| `Anigeri_Phase1,2,3` | 4 polygons | EPSG:32643 | `Annigeri SRIPL13`, `SRIPL12`, `NTPC`, `Polygon Measure`; 460 km² |
| `Anigeri_for_clip` | 1 polygon | EPSG:32643 | SRIPL13, 454 km² |
| `Ann_roads` | 765 lines | EPSG:4326 | 468 km; 9 `type` values; 5 state-highway refs |
| `Ann_waterways` | 11 lines | EPSG:4326 | 39 km; `stream`, `river`; two named |
| `Ann_railways` | 16 lines | EPSG:4326 | 43 km; `rail`, `platform` |
| `Ann_natural` | 15 polygons | EPSG:4326 | water, 19 ha |
| `Ann_landuse` | 3 polygons | EPSG:4326 | `reservoir`, `residential`, 181 ha |
| `Ann_buildings` | 5 polygons | EPSG:4326 | 3,712 m² |
| `annigeri_DEM.tif` | 438 × 344, int16 | EPSG:4326 | ~90 m postings, 620–739 m, nodata 0, **63% masked** |

The vector layers are an Overpass extract; `OSM tags query.txt` is the query that produced them. `name`, `maxspeed` and `width` are empty throughout. What is populated is `osm_id` and `type`.

### 5.2 What it can improve now

1. **Avoidance realism.** Every fixture in the repository today carries exactly **two** avoidance features, one `ROAD` and one `RESTRICTED_AREA`, both synthetic. Annigeri offers roughly 800 real features. Finding F11 records that scalability is unmeasured, and the claim depends on the golden project showing metric variance; two synthetic boxes cannot produce it.
2. **Typed identity (WP2-4, WP2-3).** Their exit evidence requires aliases to map onto `CanonicalFeatureType` without collapsing, with a stable `source_id` per feature. `osm_id` is a genuine stable upstream identity and the `type` values are real aliases: 9 road classes, `rail`/`platform`, `stream`/`river`, `water`/`reservoir`, `residential`. Today that mapping is tested only against invented inputs.
3. **Coordinate realism.** Current fixtures sit at (-1.0, 52.0), in the United Kingdom, while the product targets Karnataka. Annigeri forces a real EPSG:4326 → EPSG:32643 reprojection and gives the WP0B-7 geometry fingerprint — which requires an EPSG-coded projected CRS with metre east/north axes — a real UTM 43N vector rather than a synthetic one.

### 5.3 What it lacks for G1

| Missing | Consequence |
|---|---|
| Turbine layout and substation point | `wtg_geojson` and `substation_geojson` are required. The phase polygons are site boundaries only. Inventing a layout is the silent synthetic substitution G1 forbids |
| Cadastre: parcel polygons, owner identities, prices | `land_context` cannot be built, so Minimum Land Impact has no real basis; owner interactions fall back to the parcel-count proxy. The 5-building layer is not a settlement proxy |
| Catalogue revision priced for the site | WP0B-1's preflight and the Minimum Cost metric both need it |
| Data hygiene | `Polygon Measure` appears to be a scratch measurement polygon left in the layer |

**The inversion worth noting:** the dataset contains no personal data, so G1's sanitisation, retention and display half is trivial to approve against it today. That question only reappears when cadastre is added. This supports naming Annigeri the **candidate golden site** now and turning the table above into G1's input list, instead of leaving the gate open against an unnamed dataset.

### 5.4 The DEM is out of scope

Nothing in the engine reads elevation; the only occurrence is a docstring in `app/algorithms/cost_function.py`. WP7-1 already plans to remove or mark future the TRD's DEM requirement. On the merits, 90 m postings with 63% nodata over a 460 km² site are too coarse for pole placement or slope-aware routing, which would need ≤10 m. **Recommendation: park it. Do not open terrain work while the plan is gate-blocked.**

### 5.5 Two blockers before any Annigeri code

- **Nobody owns the fixture corpus.** The ownership globs cover `optimisation-python/tests/fixtures/v0_golden/**` for L1 and nothing else under `tests/fixtures/`. `corpus/**` is unowned, so in Phase 1 no level may add an Annigeri fixture. `contracts/ownership/` is frozen, so this needs a **CCR**. Related: the golden capture script refuses to run unless `app` matches `demo-opt-base`, so any Annigeri fixture that ever joins the golden set must be captured at that tag.
- **Licence.** OSM data is ODbL. Fixtures derived from it carry attribution and share-alike obligations, and `tests/fixtures/corpus/PROVENANCE.md` would need a `REAL_SOURCE` row — it would be the first fixture in the corpus entitled to one, and the synthetic layout half must stay labelled `SYNTHETIC`.

### 5.6 Proposed work, for owner decision

Numbered as proposals, not plan tasks; none is authorised by this record.

| Ref | Proposal | Suggested owner | Gate | Prerequisite |
|---|---|---|---|---|
| ANN-a | OSM `type` → `CanonicalFeatureType` mapping, with Annigeri's real values as test vectors | L3 | None | WP2-4 merged in #43 with alias tables in Java and Python, but **without** these vectors. Checking them against Annigeri shows two real gaps: OSM uses `residential` both as a road class (`Ann_roads`) and a land use (`Ann_landuse`), and a context-free alias maps both to `settlement`; and `CanonicalFeatureType` has **no railway class**, so Annigeri's 16 rail lines have no correct identity by any path: Java's `LineType` has no railway either, an unmapped value becomes `restricted_area` if a railway is stored as a restricted area, and Python resolves `rail` or `railway` to no identity. The first is a mapping fix; the second needs a CCR amending C1 |
| ANN-b | Annigeri-derived geometry vectors for the WP0B-7 fingerprint tests | L3 | None | None |
| ANN-c | `ANN-1` corpus fixture: real avoidance geometry, declared-synthetic layout inside SRIPL13, provenance split per layer | Level owning the consuming task | None | **CCR for the ownership glob** (§5.5) |
| ANN-d | Name Annigeri the candidate golden site; issue §5.3 as G1's input list | G1 owners | — | — |

## 6. Known limits of this record

- Test counts are from the repository venv on the author's machine, not from CI. CI conclusions are quoted separately and are per-check, not per-count.
- The 1478-test trial integration was run before the branches were rebased; merged main is the authoritative figure.
- The Annigeri assessment reads the shipped files only. It does not establish provenance, licensing terms as actually granted, or whether a turbine layout and cadastre exist elsewhere for the same site.
- Gate status reflects what is recorded in the repository. An owner decision taken but not written down is not visible here.
- This is a running record and goes stale the moment the queue moves. It is accurate as of `2159c4a` on 21 September 2026; none of the §5.6 proposals has been actioned.
