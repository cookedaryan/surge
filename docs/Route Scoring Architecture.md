# Route Scoring Architecture

## Purpose
The route scoring engine (`app/algorithms/route_scoring.py`) provides preliminary multi-criteria spatial and constructability scoring for engineering network alternatives. It evaluates candidate networks against predefined criteria, normalizes their performance metrics, and determines an overall ranking based on configurable weights.

This module was delivered under SURGE-PY-012. It is now a **legacy/preliminary compatibility scorer**. The canonical SURGE-PY-027 recommendation boundary is `app.optimisation.scoring`, which unifies spatial and electrical metrics into a single multi-objective score.

See [Multi-Objective Candidate Scoring](Multi-Objective%20Candidate%20Scoring.md) for the canonical scoring engine.

## Candidate Scope
Currently, the module strictly scores `NetworkCandidateMetrics`. It expects to compare complete alternative networks representing the same engineering decision under the same `comparison_group_id`. It does not support mixed-scope evaluation (e.g., scoring a single route segment against a full feeder) because that produces meaningless relative rankings.

## Normalization & Relativity
The engine uses **deterministic min-max normalization**, with the following consequences for explainability:
- **Relative Scores**: Normalized values are inherently relative to the cohort of candidates being evaluated.
- **Sensitivity**: Adding or removing a feasible candidate can change the normalized score for every candidate in the group.
- **Incomparable Cohorts**: Scores computed across different jobs or different comparison groups are mathematically incomparable.
- **Single Candidate Cohorts**: If only one feasible candidate is provided, its min and max bounds are identical, meaning all criteria are treated as constants, and its total normalized score will inherently evaluate to `0.0` regardless of the weights applied.
- **Bounded Range**: Total scores are tightly bounded within `[0.0, 1.0]`.

To ensure full auditability, the exact `NormalizationRange` used to bind the cohort is returned alongside the raw metrics inside the output model. 

## Deduplication Aggregation
Metrics such as ROW footprint area, environmental area overlap, and cadastral parcel hits are inherently non-additive across route segments (e.g., overlapping corridors or parcels that touch multiple feeders). The route scorer expects the caller to have already resolved identity deduplication prior to invoking `evaluate_network_candidates`. 

> **Note on poles:** SURGE-PY-023 adds a network-level endpoint merge pass. The
> compatibility field remains named `generated_pole_record_count`, but a caller
> scoring output from the pole-placement pipeline should populate it from the
> deduplicated `CollectorPoleResult.total_poles`, which represents distinct
> physical structures. Callers constructing `NetworkCandidateMetrics` directly
> remain responsible for supplying a deduplicated value.

## Constraint Failures
Candidates that trigger exclusionary constraints are recorded via `hard_violation_ids`. 
If a candidate has one or more hard violations:
- It is immediately marked `feasible = False`.
- It is excluded from the cohort normalization boundaries, ensuring extreme violation quantities do not compress the scale for feasible candidates.
- It receives an empty normalized criteria set and a `None` total score.
- The raw metrics and `rejection_reasons` are preserved in the result for diagnostics.
