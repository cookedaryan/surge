# Land Acquisition & Route Decision Engine — implementation analysis

**Status date:** 2026-08-16
**Question:** what is needed to (a) implement land parcels properly, (b) minimise contact with
landowners, (c) let the engine decide *buy the land* versus *span over it at maximum pole span*,
subject to the other constraints — and where, if anywhere, does machine learning belong.
**Method:** direct source reading of `optimisation-python/app/`, `backend-java/src/main/`, the
`cadastral_parcels` schema, and the commits merged up to `2e04fbc`.

---

## 1. The headline

Most of the commercial land engine **already exists in Python and is unreachable from the
application.** It was merged as PY-034/035/036 and is fully tested. What is missing is not the
algorithm — it is the data to feed it, the transport to reach it, and one genuinely absent
capability (the span-versus-buy trade).

Before writing anything new, the cheapest large win is connecting what is already built.

---

## 2. What already exists

### 2.1 Commercial land model — `app/land/models.py`

Far richer than the database behind it:

| Concept | Values |
| --- | --- |
| `LandAvailabilityStatus` | `AVAILABLE`, `NEGOTIABLE`, `UNAVAILABLE`, `UNKNOWN` |
| `LandTransactionMode` | `PURCHASE`, `LEASE`, `EASEMENT` |
| `LandPriceStatus` | `QUOTED`, `ESTIMATED`, `UNKNOWN` |
| `LandTransactionTerms` | upfront cost, annual cost, term years, price date |
| `ParcelCommercialProfile` | parcel id, **owner id**, availability, several transaction options |

### 2.2 Decision engine — `app/land/decision.py`

For each affected parcel it values every transaction option on **present value** — a proper
annuity factor over the lifecycle analysis period at the configured discount rate — and selects
the lowest-PV feasible option. So "purchase outright" versus "lease for 25 years" versus
"easement" is already an apples-to-apples comparison rather than a comparison of a capital sum
against a rent.

It also refuses to pretend: an option with `UNKNOWN` price is marked infeasible rather than
costed at zero, and a parcel whose status is `UNAVAILABLE` disqualifies the candidate.

### 2.3 Owner-contact minimisation — already an objective

`CandidateLandAssessment.owner_interaction_count` counts **distinct owners**, deduplicated by
`owner_id`, falling back to a parcel proxy when owner identity is unknown (recorded honestly as
`OwnerInteractionBasis.PARCEL_PROXY`). It is wired into candidate scoring as
`ScoringMetric.OWNER_INTERACTION_COUNT` with its own spatial sub-weight.

**The objective you asked for is implemented.** It just cannot be driven, because no owner data
reaches it.

### 2.4 Pole micro-siting — `app/algorithms/pole_micro_siting.py` (PY-035)

Slides movable intermediate poles along the routed corridor to reduce parcel burden, ranking
candidate positions by owner interactions first, then parcel count, and rejecting any position
that violates `min_span_m` / `max_span_m`.

This is *adjacent to* the span-versus-buy question but is not it — see §4.

---

## 3. What is missing to make it work

### 3.1 The database has almost none of the required data

`cadastral_parcels` currently holds:

```
parcel_id, owner_name (free text), acquisition_cost_per_m2, geometry, source_folder
```

Against what the engine expects, that is missing:

- **`owner_id` — a stable owner identity.** This is the single most important gap. Owner-contact
  minimisation is *only* meaningful if two parcels belonging to the same person can be recognised
  as one conversation. Free-text `owner_name` cannot do that: "R. Kumar", "Ramesh Kumar" and
  "Ramesh Kumar S/o Krishna" are three owners to a string comparison and one person in reality.
  Without owner ids the engine silently falls back to `PARCEL_PROXY`, which counts parcels and
  calls them owners — the metric still produces a number, and the number is wrong.
- **Availability status.** No way to record "this owner will not sell".
- **Transaction options.** One `acquisition_cost_per_m2` cannot express purchase versus lease
  versus easement, nor a term, nor whether the figure is a real quote or a planning estimate.
- **Price provenance.** No `price_date`, no quoted/estimated flag. A three-year-old estimate and
  a signed quote currently look identical.

### 3.2 The transport does not exist

`land_context` is defined on the **v2** request schema only
(`app/schemas/v2/optimise.py:294`). Java calls **`/api/v1/optimise`**
(`PythonOptimizationClient.java:23`) and sends parcels merely as soft-constraint polygons with a
`cost_weight`. So today the entire land engine receives nothing.

This is the same class of problem as PY-030/031 cable sizing and electrical repair, which are also
v2-only and also unreachable. **Java moving to v2 unlocks all of it at once** and should be treated
as one piece of work rather than three.

### 3.3 There is no way to enter the data

Parcels arrive by KMZ import with geometry and sometimes a name. There is no UI to set owner
identity, availability, or commercial terms, and no import format that carries them. Whatever the
engine can model, someone has to be able to type in.

---

## 4. The span-versus-buy decision — genuinely not built

This is the one capability that does not exist in any form.

### 4.1 What is missing conceptually

The engine can decide *which* parcels to cross and *what commercial instrument* to use. It cannot
decide **not to touch a parcel at all by flying over it**. That decision needs three things it
does not have:

**A. Span cost as a function of length.** `PoleCostItem` prices a pole by *type* — terminal,
angle, intermediate, junction — with a flat `installed_cost_each`. A 400 m crossing span is not the
same object as a 120 m tangent pole: it needs taller structures, heavier conductor tension,
different foundations. Until structure cost varies with span length and height, the optimiser has
no way to know that spanning costs money, so "span everything" would always look free.

**B. The physical envelope.** Sag, ground clearance at mid-span, conductor tension and wind/ice
loading all bound how far you can actually fly. `max_span_m` today is a single configured number,
not a computed limit from conductor type, tension, temperature and terrain. Spanning decisions made
against a flat number will be wrong wherever the ground rises mid-span — and note that
**elevation data does not exist anywhere in the system** (the profile chart was removed today
precisely because it was fabricated). Mid-span ground clearance cannot be computed without it.

**C. Partial-crossing semantics.** A span that flies over a parcel without a pole in it may still
require an overhead easement — legally and commercially very different from freehold purchase, and
usually much cheaper. The model has `EASEMENT` as a mode, so the vocabulary exists; what is missing
is the geometric distinction between *pole footprint inside the parcel* and *conductor overhead
only*, which is what determines which instrument applies.

### 4.2 The shape of the fix

The decision is a per-parcel comparison, evaluated during candidate assessment:

```
cost_of_crossing  = land PV (purchase | lease | easement, whichever is lowest feasible)
                  + owner-interaction penalty
cost_of_spanning  = Δ structure cost (taller/stronger poles either side)
                  + Δ conductor cost
                  + overhead easement PV, if the jurisdiction requires one
feasible_to_span  = required_span ≤ min(max_span_from_conductor_physics, max_span_config)
                    AND mid-span clearance ≥ statutory minimum
```

Take the cheaper feasible option; record which and why. That last clause matters — you already have
a decision-report model (PY-036) to carry the justification, and "we chose to span parcel 47 rather
than negotiate, saving X" is exactly the kind of statement the report exists to make.

Note this is **deterministic optimisation, not learning**. Every term is either measurable or
quotable.

---

## 5. Where machine learning actually belongs

Honest answer: **not in the buy-versus-span decision.** That is a constrained optimisation with a
well-defined objective and hard physical limits. A model that "learns" it would be less accurate,
unexplainable, and impossible to defend to a landowner or a regulator — and you would still need
the cost model underneath it to generate training data.

There are three places ML genuinely helps, all of which need data you do not have yet:

**1. Predicting acquisition cost and negotiation difficulty.** The real uncertainty is not
arithmetic, it is *what will this owner actually accept, and how long will it take*. That is a
prediction problem — features like parcel size, land use, owner type (individual/corporate/
inherited-co-owned), distance to road, prior transactions nearby. Needs a history of concluded
negotiations.

**2. Learning the cost surface from built routes.** Where crews actually could and could not build
is richer than any hand-set `cost_weight`. Needs as-built routes versus planned routes.

**3. Learning-to-rank candidates.** Where engineers consistently override the recommendation, their
preference encodes tacit knowledge. Needs a log of recommendations made and choices taken.

**All three are blocked on the same thing: outcome data.** The high-value move now is to
**instrument for it** — record every recommendation, every override with its reason, and every
concluded land deal against its estimate. Do that today and ML becomes possible in a year. Skip it
and you will still have no dataset then.

One improvement that looks like ML but is not: `owner_interaction_count` treats every owner as
equally costly. Weighting by *expected difficulty* — co-ownership count, absentee status, prior
refusals — would sharpen the objective considerably and needs only a field, not a model.

---

## 6. Recommended sequence

1. **Move Java to the v2 endpoint.** One piece of work that unlocks the land engine, cable sizing
   and electrical repair together. Nothing else on this list is reachable until it is done.
2. **Extend the parcel model:** `owner_id` first, then availability status, then transaction
   options with price provenance. Migration plus ingestion plus admin UI.
3. **Send `land_context`** from Java, built from the extended parcel data.
4. **Surface it:** the land decision per parcel, chosen instrument, and owner-interaction count
   belong in the BOM report and the decision panel. The report structure added today has room.
5. **Then build span-versus-buy**, in this order: span-dependent structure cost → conductor
   physics for the true span limit → easement-versus-freehold geometry → the comparison itself.
6. **Instrument for outcomes** throughout, so ML has a dataset when you want one.

Steps 1–4 make the existing engine real. Step 5 is the new capability. Step 6 is what makes step 7
possible later.

---

## 7. Two honest caveats

**Elevation blocks part of this.** Mid-span ground clearance cannot be computed without terrain
data, and there is none in the system. Long spans over rising ground are exactly where the
clearance limit binds. Either accept conservative span limits that ignore terrain, or source a DEM
first.

**Garbage in.** The reference project's only parcel, `PSS Land`, has no acquisition rate at all —
the BOM reports 11,475 m² of corridor overlap and $0.00 of compensation, correctly, because no rate
exists. A sophisticated land engine fed the same data will produce sophisticated zeroes. The data
collection process matters at least as much as the algorithm.
