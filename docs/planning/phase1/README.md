# Phase 1 record — SURGE demo optimisation merge queue

Date: 18 September 2026
Main: `6601234` · Base tag: `demo-opt-base`
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
| 4 | — | L3 `wp5-generation` | — | Branch written, unrebased. Ungated. See §3 |
| 5, 6 | — | WP2 metrics and transport, WP3 profiles | — | **Unblocked by the G0 decision of 2026-09-18**; WP2-3 also carries G1's transport clause |

Every merged PR was rebased onto main before merging, per the queue rule, and CI was green on the rebased head. Tasks delivered: WP2-2, WP3-2, WP4-2, WP5-1 (L1); WP0B-7, WP0B-6, WP0B-11 (L3); WP1-1 … WP1-5 (L2).

## 2. State of merged main

| Check | Result |
|---|---|
| Python suite on merged main (`6601234`) | **1443 passed** |
| Trial integration before any merge: all four level branches plus the CCR, merged in queue order | **1478 passed**, no textual conflict |
| L1 ownership check | Pass, 14 paths |
| L2 ownership check | Pass, 6 paths |
| L3 ownership check | Pass, 6 paths |
| CI on each rebased head | Python, Java, web map, container builds, ownership — all pass |

The V0 goldens merged in slot 1 have since held green through two runtime PRs, which is the first live evidence that the characterisation suite does the job the L1 plan §4.1 claims for it.

**One behaviour note on WP1-5.** `design_truth` is emitted only when a profile is resolved or search is enabled, so it stays absent from V0 responses and from every request the product can make today. The repair log and final installed conductors therefore remain user-invisible until slot 3 or slot 6 lands. This is consistent with L1's search-off golden, which asserts no additive block is present with both flags off, and it is recorded in #36. Java persistence of the final conductor (WP6A-6) depends on those fields.

## 3. Open work and stragglers

**L2 `baseline-measurement`, slot 1, not opened.** Slots 1 and 2 merged without it. Under the queue rules that is allowed — no PR may rely on a later PR, and a gated slot does not block a ready one — but it makes this PR a straggler that must rebase onto everything above it and keep the V0 goldens green. Two of its tasks need no gate and can ship now: WP0B-5, the topology fingerprint canonicaliser, and the tooling half of WP0B-8, whose harness may be built on synthetic data (only its golden runs wait on G1).

**L3 `wp5-generation`, slot 4, unrebased.** Ungated, so it is the next package that can merge. It could not have passed before #34, because the old S5 seam test asserted the `NotImplementedError` that WP5-3 replaces.

**L1's remaining Phase 1 work.** WP6A-1 was unblocked by the G0 decision of 2026-09-18 and can now be built as the `wp6a-claim-copy` PR, which merges at Stage 2 step S2-4, not in Phase 1. WP0B-1 still waits on G1. The WP6C-4 runbook skeleton and the WP7 documentation change list are drafted in the L1 worktree and stay unmerged until their Stage 2 steps.

## 4. Gate status

| Gate | Owners | Blocks | Latest date (draft 0.6 §5) | Status |
|---|---|---|---|---|
| G0 — stage claim | Demo owner + scoring approver | Slots 5 and 6, then FRZ-1 and Stage 2 | WP2 start | **Decided 2026-09-18: weak claim.** See [`contracts/decisions/g0-claim.md`](../../../contracts/decisions/g0-claim.md) |
| G1 — golden data | Project owner + data/security owner | WP0B-1; WP0B-3, 8, 9, 10 golden runs; WP0B-2 | WP0B start — **passed** | Undecided, and circular. See below |
| G2 — runtime envelope | Project owner + engineering lead | All of slot 3 | WP4 start — **now** | Undecided |
| G4 — cohort surface | Demo owner + engineering lead | S2-3 | WP2 start | Undecided; default is recorded evidence |

G0 is now decided, so slots 5 and 6 are open and slot 4 is ungated. What remains gate-blocked is slot 3 (G2) and WP0B-1 (G1).

**G1 is circular as written.** Its transport clause requires a probe proving Java carries parcel and forest/environment identity plus soft/hard mode. That probe failed in Stage 0 ([stage0/README.md §4](../stage0/README.md)). The fix is WP2-3, which the L2 plan gates on G1 — so G1 waits on the work that G1 gates.

*Proposed resolution, for the G1 owners:* split the gate. Decide the data half now — snapshot, catalogue revision, sanitisation, retention and display rules — and treat the transport clause as satisfied when WP2-3 lands in slot 5. This changes no contract file, so it is an owner decision recorded here and in `contracts/decisions/`, not a CCR.

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
| ANN-a | OSM `type` → `CanonicalFeatureType` mapping table, with Annigeri's real values as test vectors | L3, inside WP2-4 | G0, as WP2-4 already is | None |
| ANN-b | Annigeri-derived geometry vectors for the WP0B-7 fingerprint tests | L3 | None | None |
| ANN-c | `ANN-1` corpus fixture: real avoidance geometry, declared-synthetic layout inside SRIPL13, provenance split per layer | Level owning the consuming task | None | **CCR for the ownership glob** (§5.5) |
| ANN-d | Name Annigeri the candidate golden site; issue §5.3 as G1's input list | G1 owners | — | — |

## 6. Known limits of this record

- Test counts are from the repository venv on the author's machine, not from CI. CI conclusions are quoted separately and are per-check, not per-count.
- The 1478-test trial integration was run before the branches were rebased; merged main is the authoritative figure.
- The Annigeri assessment reads the shipped files only. It does not establish provenance, licensing terms as actually granted, or whether a turbine layout and cadastre exist elsewhere for the same site.
- Gate status reflects what is recorded in the repository. An owner decision taken but not written down is not visible here.
