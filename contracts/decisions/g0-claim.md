# G0 — stage claim

Status: **confirmed by the owner on 2026-09-18**

Draft 0.6 §5 requires G0 to fix the claim form verbatim, the minimum land and environment effect
sizes, the tolerances, and the Balanced regret or percentile threshold — all before unblinding.

## Decision

**The weak form is claimed.** Verbatim, from the draft 0.6 executive summary:

> For this frozen demo project and declared search budget, SURGE generated and evaluated a
> measured set of feasible alternatives. Each of the four named profiles ranked the same
> deduplicated comparison cohort using the metrics its name promises, and each profile's
> recommendation improves that profile's named objective against Balanced by at least the
> pre-declared margin. Every published recommendation can be reproduced from the recorded
> evidence.

This is the text WP6A-1 renders and the runbook quotes. It is never paraphrased.

### Pre-declared margins and tolerances

Lower is better for every metric below. `B` is the Balanced winner's value, `P` the value for the
profile's own winner.

| # | Threshold | Definition | Value |
|---|---|---|---|
| 1 | Minimum Land Impact margin | `(B − P) / B` on `affected_parcel_row_area_m2` | **≥ 0.05** |
| 2 | Minimum Environmental Impact margin | `(B − P) / B` on unique forest/environment overlap area | **≥ 0.05** |
| 3 | Minimum Cost selection tolerance | `(P − min_cohort) / min_cohort`, modelled lifecycle cost | **≤ 0.005** |
| 4 | Minimum Cost recomputation tolerance | `abs(reported − recomputed) / reported`, where recomputed is BOM × catalogue + valued losses (R2-C7) | **≤ 0.01** |
| 5 | Balanced envelope | maximum regret `(B − P) / abs(P)` on **each** named specialised metric | **≤ 0.10** |

**Degenerate bases.** Thresholds 1, 2 and 5 are relative, so they are undefined when the
denominator is zero. If `B` is zero for a metric, the margin counts as met only when `P` is zero
too, and the evidence must state that the metric does not differentiate on this project. A zero
base is never reported as a pass on the strength of a relative margin.

**Metric identity.** Each margin is evaluated on the frozen definition of its metric at FRZ-1,
over the deduplicated comparison cohort, using the same evidence the UI publishes.

## Why

- **Weak over strong.** The strong form needs four distinct final-design fingerprints. Nothing
  measured yet shows the cohort separates that cleanly, and a claim that fails on stage is worse
  than a narrower claim that holds. The weak form still asserts the thing that matters: each
  profile beats Balanced on the objective its name promises.
- **5% on land and environment.** Large enough to be visible and to survive routing noise, small
  enough that a correct policy should clear it on one frozen 8–12 turbine project. One number for
  both keeps the runbook and the stage wording simple.
- **0.5% selection, 1% recomputation.** The recomputation re-derives quantities independently, so
  it gets the looser band; selection stays tight so a visibly different design cannot tie with the
  winner.
- **10% Balanced regret.** Pairs with the 5% specialised margins: Balanced stays close on every
  axis without winning any. Balanced now carries land, environment and lifecycle-cost terms
  (R2-C4), so the envelope is a design requirement rather than luck.

**Set before unblinding, deliberately.** These numbers were chosen before WP0B's blinded
distributions exist. That is the §4.3 anti-overfitting rule: thresholds are not read off the
golden winners. If a threshold later proves unreachable, the honest move is to record the miss and
re-decide it as a new owner decision, not to quietly loosen it after seeing the results.

## Consequences

- **Unblocks WP6A-1 (L1).** `ClaimDisclosure.tsx` renders the weak-form text above, the §7 Minimum
  Cost disclosure and the §17 non-claims, with `ClaimDisclosure.test.tsx` asserting every string
  verbatim. The copy review attached to that PR checks against this record.
- **Unblocks the G0-gated packages** in merge-queue slots 5 and 6 (WP2 metrics and transport, WP3
  profiles), and is a precondition for FRZ-1 at Stage 2 step S2-2.
- **Acceptance evidence** must report each of the five numbers above per profile, not a verdict
  alone.
- Thresholds 1, 2 and 5 also decide the §7 profile acceptance rows; threshold 4 is WP3-8's
  independent recomputation.
- The strong-form rule about four distinct final-design fingerprints (R2-C10) does **not** apply.
  §7's separate requirement still does: the Balanced winner must not be identical to every
  specialised winner (R2-B13).
- Changing any value here later is a new owner decision recorded the same way, and it invalidates
  any acceptance evidence already produced under the old value.

## Still open

- G1 (golden data), G2 (runtime envelope), G3 (recorded run) and G4 (cohort surface) are
  undecided. The claim text above assumes nothing about them.
- FRZ-1 still freezes the policy values themselves — metric directions and definitions, reference
  ranges, weights, tie-breaks and profile versions. This record fixes acceptance thresholds only.
