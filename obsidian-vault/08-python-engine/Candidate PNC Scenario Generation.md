# Candidate PNC Scenario Generation

**Ticket:** SURGE-PY-017  
**Module:** `optimisation-python/app/optimisation/`  
**Status:** Implemented  
**Depends on:** PY-014 (PNC Network Assembly)

---

## Overview

PY-017 extends the Surge pipeline from a single PNC network output to a small,
configurable set of materially different, valid PNC network candidates:

```
Project Input
     ↓
generate_pnc_scenarios()
     ↓
┌──────────────┬──────────────┬──────────────┐
│ SCN-001      │ SCN-002      │ SCN-003      │
│ BASELINE     │ ALT GROUPING │ BALANCED     │
└──────────────┴──────────────┴──────────────┘
```

Candidate ranking and scoring are deferred to **PY-018**.

Focused verification on 2026-08-12 passed all 65 scenario tests and strict mypy
checking. Ruff found one import-order issue in `app/optimisation/__init__.py`;
the implementation was left untouched during this documentation-only update.
The canonical ticket boundary is defined in [[Surge MVP Ticket Plan]].

---

## Package Structure

```
app/optimisation/
├── __init__.py           # public surface
├── scenario_models.py    # all domain models and enumerations
└── scenarios.py          # generate_pnc_scenarios() + fingerprinting
```

---

## Entry Point

```python
from app.optimisation import generate_pnc_scenarios, ScenarioGenerationConfig

result = generate_pnc_scenarios(
    project_data=project,
    feeder_capacity_mw=50.0,
    cost_surface=cost_surface,
    config=ScenarioGenerationConfig(candidate_count=3),
)

for scn in result.candidates:
    print(scn.scenario_id, scn.strategy, scn.topology_fingerprint)
```

---

## Deterministic Parameter Schedule

The generator applies a fixed ordered list of five parameter personalities.
Requesting `N` candidates iterates the first `N` entries in order (plus any
extras needed to replace duplicates):

| ID     | Strategy                      | Grouping Seed | MILP Objective     | Edge-Weight Profile    |
|--------|-------------------------------|---------------|--------------------|------------------------|
| PS-001 | `baseline`                    | 42            | minimize_distance  | default                |
| PS-002 | `alternative_grouping`        | 17            | minimize_distance  | default                |
| PS-003 | `balanced_feeders`            | 42            | balance_wtg_count  | default                |
| PS-004 | `long_edge_penalty`           | 42            | minimize_distance  | long_edge_penalty (α=2)|
| PS-005 | `alternative_grouping_balanced` | 7           | balance_wtg_count  | default                |

**Determinism guarantee:** given identical project data, feeder capacity, cost
surface, and `ScenarioGenerationConfig`, the function always returns the same
candidates in the same order with the same fingerprints.

---

## Strategy Mechanics

### PS-001 — Baseline

Runs the existing Surge pipeline unmodified.  Identical to the pre-PY-017
single-network output.

### PS-002 — Alternative Grouping

Passes `random_state=17` to `group_wtgs()`.  This changes the KMeans centroid
initialisation, which changes the MILP objective function, producing a different
(but still valid) feeder partition.

### PS-003 — Balanced Feeders

Passes `objective=GroupingObjective.BALANCE_WTG_COUNT` to `group_wtgs()`.
This activates `_solve_milp_balance()`, a new MILP formulation that minimises
the maximum absolute deviation of per-feeder WTG count from the ideal equal
split (`n / k`), subject to the same capacity constraint.

```
Objective: minimise t
Subject to:
  sum_i x_ij == 1                for each turbine i
  sum_i P_i * x_ij <= C          for each feeder j (capacity)
  sum_i x_ij - ideal <= t        balance upper bound
  ideal - sum_i x_ij <= t        balance lower bound
```

### PS-004 — Long-Edge Penalty

Applies a non-uniform convex amplification to graph edge weights before MST
construction:

```
w' = w * (1 + alpha * w / w_max)
```

where `alpha = 2.0` and `w_max` is the maximum finite edge weight.  Unlike
uniform scaling (`w' = k * w`), this transformation applies a larger relative
penalty to longer edges, which **can** change the MST.  The base graph is never
mutated; a copy is created.

### PS-005 — Alternative Grouping + Balanced

Combines `random_state=7` with `BALANCE_WTG_COUNT` to produce a fifth distinct
personality for `candidate_count=5`.

---

## Modifications to `wtg_grouping.py`

`group_wtgs()` now accepts two optional keyword-only parameters:

| Parameter     | Type               | Default                          | Description |
|---------------|--------------------|----------------------------------|-------------|
| `random_state`| `int`              | `42`                             | KMeans seed |
| `objective`   | `GroupingObjective`| `GroupingObjective.MINIMIZE_DISTANCE` | MILP objective |

Default values preserve historical baseline behaviour.

A new private function `_solve_milp_balance()` implements the balance MILP.

---

## Duplicate Suppression

Duplicate suppression happens **before** physical routing (A\*) using a topology
fingerprint computed from feeder WTG memberships and MST edges.  This avoids
running expensive A\* on topologies that are structurally identical to an
already-accepted candidate.

If the pre-routing fingerprint matches, the attempt is recorded as
`DUPLICATE_TOPOLOGY` and the next parameter set is tried.

After assembly, a final network fingerprint is also checked.

---

## Topology Fingerprint Schema

```
"v1:" + sha256(canonical_json(feeder_records))
```

Each feeder record:
```json
{
  "wtgs": ["wtg:T01", "wtg:T02"],
  "edges": ["substation:SUB1:wtg:T01", "wtg:T01:wtg:T02"]
}
```

Feeder records are sorted by canonical content, not feeder ID.  Equivalent
partitions with different feeder IDs produce the same fingerprint.

---

## Domain Models

### `ScenarioGenerationConfig`

| Field             | Type  | Default | Constraint |
|-------------------|-------|---------|-----------|
| `candidate_count` | `int` | `3`     | `[1, 5]`, not `bool` |
| `base_seed`       | `int` | `42`    | `>= 0`, not `bool` |
| `project_id`      | `str` | `"PROJECT"` | non-blank |

### `PNCScenario`

| Field                  | Type                  | Description |
|------------------------|-----------------------|-------------|
| `scenario_id`          | `str`                 | `SCN-001`, sequential from accepted |
| `strategy`             | `str`                 | Named strategy from `ScenarioStrategy` |
| `parameters`           | `ScenarioParameters`  | Full algorithm-input record |
| `network`              | `ProjectPNCNetwork`   | Assembled network |
| `topology_fingerprint` | `str`                 | `v1:<sha256>` |
| `comparison_group_id`  | `str`                 | Shared across all candidates in one run |
| `feeder_count`         | `int`                 | Validated against `network.feeder_count` |
| `wtg_count`            | `int`                 | Validated against `network.wtg_count` |
| `segment_count`        | `int`                 | Validated against `network.segment_count` |
| `total_route_length_m` | `float`               | Validated against `network.total_route_length_m` |
| `route_length_by_feeder`| `dict[str, float]`   | Per-feeder cable length |
| `wtg_count_by_feeder`  | `dict[str, int]`      | Per-feeder WTG count |

### `ScenarioGenerationResult`

| Field                    | Type                    | Description |
|--------------------------|-------------------------|-------------|
| `requested_candidate_count` | `int`                | From `config.candidate_count` |
| `candidates`             | `tuple[PNCScenario, ...]`| Accepted candidates |
| `attempts`               | `tuple[ScenarioAttempt, ...]`| Full diagnostic record |
| `comparison_group_id`    | `str`                   | Shared identifier |

### `AttemptOutcome` values

| Value                | Meaning |
|----------------------|---------|
| `accepted`           | Candidate assembled and accepted |
| `duplicate_topology` | Topology fingerprint already accepted |
| `routing_failed`     | A\* routing failed (`RouteNotFoundError`) |
| `assembly_failed`    | PNC assembly failed (`PNCAssemblyError`, `ValueError`) |
| `grouping_failed`    | WTG grouping failed (`ValueError`) |

---

## Error Model

| Error                     | Raised when |
|---------------------------|-------------|
| `NoValidScenarioError`    | Zero candidates produced from all attempts |
| `InvalidScenarioConfigError` | `ScenarioGenerationConfig` validation fails |

Fewer candidates than requested is **not** an error; `NoValidScenarioError` is
only raised when the count is zero.  Unexpected exceptions always propagate.

---

## Out of Scope

- Candidate ranking and scoring (deferred to **PY-018**)
- Electrical feasibility (PY-015)
- Mutation of finished networks
- More than 5 candidate personalities (extend `PARAMETER_SCHEDULE` in
  `scenario_models.py` and increment the fingerprint schema version)
