# Consumption Gap — Ticket Plan

**Status date:** 2026-08-17
**Source:** the Java & Frontend Gap Analysis of the same date, re-verified against the tree at
`710f75f` and reordered by dependency rather than by priority.
**Why reorder:** the source list is ordered by severity, and two of its three HIGH items cannot be
started. Working the list top-down would stall on the second ticket.

---

## Corrections to the source analysis

**E-1 is already done** — Python side, at `710f75f`. Exhausted repair now returns the unresolved
violations with measured value against limit, every conductor upgrade attempted with loading before
and after, and the largest conductor available. What remains is Java persisting it and the frontend
showing it, which is really E-4's scope. The analysis was written against the tree before that
commit.

**C-2 and F-1 are blocked, and the blocker is not in the list.** Both say "use Python's real
`total_capex`". Python only computes costs when the request carries a `costing_config`
(`domain_mapping.py:370`), and **Java never sends one** — so `candidates[].cost` is absent from
every response the application has ever received. There is no real cost to switch to yet. A cost
catalogue has to exist first, and it needs commercial rates nobody has entered. That is ticket
**P-1** below, and it gates four other tickets.

**F-1 is also mis-sequenced.** Removing the `length × $80` fallback before P-1 lands does not
reveal real costs; it replaces every cost in the product — BOM totals, scenario comparison, route
popups — with "N/A". That may well be the right call, but it is a visible regression to choose
deliberately, not a side effect of a cleanup ticket.

**Path correction:** the frontend fallbacks are in `web-map-next/src/lib/map/SurgeMapEngine.ts`,
not `web-map-next/src/map/`. All six were confirmed present:

| Line | Fallback |
| --- | --- |
| 76 | WTG capacity `|| 3.0` MW |
| 104 | Substation capacity `|| 100` MW |
| 201 | Poles `|| ceil(length / 150)` |
| 210 | Cost `|| length × 80` |
| 273 | Parcel owner `|| "Private Owner"` |
| 274 | Parcel rate `|| 100` /m² |

---

## Phase 0 — Prerequisites that need data, not code

These gate everything downstream. Both are data-entry problems; the code around them is small.

### P-1 · Cost catalogue — **blocks C-1, C-2, C-3, C-4, F-1**
Java must send `costing_config`, which needs values nobody has supplied:

- **Catalogue:** conductor installed cost per km per circuit (per cable type), pole installed cost
  each (per class: terminal / angle / intermediate / junction), land policy (fixed cost per
  affected parcel, variable basis, variable rate)
- **Lifecycle:** currency, price basis date, analysis period in years, discount rate, annual
  operating hours, loss load factor, energy price per MWh

Model it exactly as the cable catalogue was: a table with a `data_provenance` column
(`VERIFIED` / `INDICATIVE` / `UNKNOWN`) so unentered rates cannot masquerade as real ones, and
surface that provenance wherever the money is shown. Seeding with indicative figures is acceptable;
presenting them as verified is not.
**Effort:** 1 day for the plumbing. The rates are a business input.

### P-2 · Verify the cable catalogue's indicative values — **quality gate, blocks nothing**
The catalogue seeded at `V15` carries five ACSR conductors marked `INDICATIVE`: real conductor
identities with published typical parameters, not readings from the datasheets this project will
buy from. Every loss, voltage drop and utilisation figure now rests on them. Replacing the five
rows with verified values is a data edit, no code.
**Effort:** hours, once someone has the datasheets.

---

## Phase 1 — Finish repair diagnostics end to end

### E-1b · Persist repair diagnostics on the job — **already done, no code written**
The premise was wrong. Java does not drop `execution_failure.details`: it stores the candidate list
raw, so the diagnostics have been landing complete in `result_summary_json` since the Python change.
Verified against job `b52bc643` — all six keys present on all three candidates, unresolved
violations and conductor ceiling included.
**Actual:** 0 days.

### E-4 · Diagnostics panel for failed runs — **done** at `0d6cfc2`
Per candidate: the buses that stayed over limit with measured against limit, the conductor upgrades
attempted with the loading each moved, and the catalogue ceiling. Zero attempts reads "None
attempted" rather than an empty list — repair upgrades conductors to clear overloads, so no attempt
on a voltage failure is itself the finding.

Also fixed a defect in E-3's violation list: it printed `measured_value` raw, and real values arrive
as `1.0599745548368775`. That path had never rendered a real value, because the only successful run
had no violations — worth remembering as a shape of bug this codebase produces.
**Actual:** 0.5 day · **Layer:** Frontend

### E-6 · Say why repair attempted no upgrades — **done** at `497a321`
Implemented differently from how this ticket described it, because the ticket's diagnosis was wrong.
It proposed inferring the reason from the violation codes — set `no_upgrade_reason` when every
unresolved violation is a voltage code — on the belief that repair only upgrades conductors for
overloads. It does not: `_find_next_voltage_upgrade` attempts voltage upgrades too.

The actual cause is narrower. The overvoltage branch searches only conductors of at least equal
ampacity and requires no more capacitance, and larger conductors carry more capacitance, so it finds
nothing. Inferring that from violation codes would have produced a plausible sentence that was not
the real reason.

So the reason is recorded where it is known: `RepairStatus.REPAIR_EXHAUSTED` is returned from eight
places, and each now carries a `RepairExhaustionReason`. The diagnostics surface both the code and a
sentence that explains rather than restates it. A completeness test fails if a new enum member is
added without one, because the silent `null` is the exact failure this ticket existed to remove.
**Actual:** 0.5 day · **Layer:** Python + Frontend

---

## Phase 2 — Show the data already persisted

**Start here for visible progress.** These need no new plumbing and no new data — the values are
already in the database or the API.

### E-2 · Cable type and utilisation on route popups *(needs nothing)*
`generated_routes` has carried `cable_type_id` and `cable_utilisation_pct` since `21d998e`, and the
BOM exports show them. The map does not. Cheapest real win on the list.
**Effort:** 0.5 day · **Layer:** Frontend

### F-2 · Remove the frontend fallbacks *(needs nothing)*
The six above. Show the real value or say "Unknown" — a popup asserting 3.0 MW for a turbine whose
capacity was never imported is worse than one admitting it does not know. **Excludes the cost
fallback on line 210**, which belongs with F-1 in Phase 3.
**Effort:** 0.5 day · **Layer:** Frontend

### E-3 · Per-feeder electrical breakdown — **done** at `71a0e36`
This ticket's premise was wrong: the per-feeder results were *not* in `result_summary_json`.
`buildResultSummary` pulled four summaries out of `recommended_result` and dropped both `feeders`
and `violations`, so the Java side was work, not just exposure. Both are now forwarded and shown —
a collapsible per-feeder table whose header reports the invalid count without being opened, and a
violation list naming the bus, the measured value and the limit.
**Actual:** 0.5 day · **Layer:** Java + Frontend

### R-1 · Candidate comparison on success, not only on failure — **done** at `4032805`
The candidate list *was* already stored in full. Shown on success in rank order with the
recommended row marked and each candidate's length, losses, poles and loading beside its benefit
score. Absolute values rather than the engine's `baseline_comparisons` deltas: reading those as
improvements needs per-metric knowledge of which direction is better, which the panel does not have.
**Actual:** 0.5 day · **Layer:** Frontend

---

## Phase 3 — Costs *(all need P-1)*

Strict order — F-1 before C-2 would blank every cost in the product.

### C-1 · Parse Python's `cost_summary` and persist it
**Effort:** 1 day · **Layer:** Java

### F-1 · Remove the `length × $80` fallback
`RouteService.java:176`. Only after C-1, so removal reveals real costs instead of blanks. Where a
run has no costing, show "Not costed" rather than a number.
**Effort:** 0.5 day · **Layer:** Java

### C-2 · Real CAPEX in the BOM panel
**Effort:** 0.5 day · **Layer:** Java + Frontend

### C-3 · Lifecycle cost breakdown — conductor / pole / land CAPEX plus loss OPEX
**Effort:** 1 day · **Layer:** Frontend

---

## Phase 4 — Land *(needs `owner_id` on parcels)*

The parcel model still has free-text `owner_name` and one `acquisition_cost_per_m2`. Until it
carries `owner_id`, availability and transaction options, the land engine returns proxy-counted
owners and `UNKNOWN` price status — so these tickets would display honest but empty results. See
`Land Acquisition and Route Decision Engine.md` §3.1.

### L-1 · Parse `candidates[].land` and expose via the Java API
The per-parcel decisions have been in the response since `491ae64`.
**Effort:** 0.5 day · **Layer:** Java

### L-2 · Parcel decision table — parcel, owner, instrument, present value, price basis
**Effort:** 1 day · **Layer:** Frontend

---

## Phase 5 — Polish

| # | Task | Layer | Effort |
| --- | --- | --- | --- |
| E-5 | Forward `derating_factor` and `parallel_count` so the UI can say "Twin ACSR Panther (2×)" | Java + Frontend | 0.5 day |
| M-1 | Parse engineering metrics into the API response | Java | 0.5 day |
| M-2 | Show traversal cost, environmental overlap, road crossings in the decision card | Frontend | 0.5 day |
| R-2 | Structured recommendation reason details rather than string messages | Frontend | 0.5 day |
| R-3 | Score breakdown chart | Frontend | 1 day |
| C-4 | Detailed BoQ line-item table *(needs P-1)* | Frontend | 1.5 days |
| L-3 | Converge the two right-of-way implementations *(needs Phase 4)* | Java | 1 day |

---

## Suggested working order

1. ~~**E-2, F-2**~~ — done at `1095ddf`.
2. ~~**E-3, R-1**~~ — done at `71a0e36` and `4032805`.
3. ~~**E-1b, E-4**~~ — done at `0d6cfc2`; E-1b needed no code.

**Phases 1 and 2 are complete, E-6 included.** Everything remaining needs either a business input
(P-1's rates, P-2's datasheets) or a schema change (`owner_id`) — except Phase 5 polish.

**Worth noting for whoever picks up the next ticket:** four of the five tickets in this batch had
inaccurate premises. E-3 was labelled "needs nothing" and needed Java work; E-1b was scoped as Java
work and needed none; E-6's stated cause was not the real one. The plan's labels are a starting
point, not a finding — check the payload before estimating.

4. **P-1** — start collecting rates now; it gates all of Phase 3.
5. **Phase 3** in strict order: C-1 → F-1 → C-2 → C-3.
6. **`owner_id` migration**, then Phase 4.
7. **Phase 5** as capacity allows.

Phase 5's **M-1/M-2** are now partly moot: the candidate engineering metrics R-1 renders are the
same ones M-1 was to parse, so M-2 shrinks to showing traversal cost and environmental overlap for
the recommended candidate.

## Totals

| | Tickets | Effort |
| --- | --- | --- |
| Phase 0 prerequisites | 2 | 1 day + business input |
| Phases 1–4 | 12 | ~9 days |
| Phase 5 | 7 | ~5.5 days |
| **Total** | **21** | **~15.5 days** |

Close to the source analysis's ~15 days, but with the cost-catalogue prerequisite made explicit and
E-1 removed as already delivered.

---

## The theme worth naming

Nearly every ticket here is the same shape: **Python computes something real, and it stops at a
boundary.** Cable sizing sat unread for weeks. Land decisions reached the response as a single
count. Repair knew exactly which segment defeated it and said "REPAIR_EXHAUSTED".

Two boundaries account for most of the remaining work — Java not parsing what it receives, and the
frontend not showing what Java holds. Neither needs new algorithms. What it does need is that the
placeholders be removed as the real values arrive, not left beside them: a fallback that survives
next to real data is indistinguishable from real data in a report.
