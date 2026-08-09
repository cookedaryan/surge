# ADR-003: Allow ML-Assisted Candidate Ranking

- **Status**: Accepted direction; implementation deferred
- **Date**: 2026-08-04

## Context

Detailed route evaluation may eventually include raster routing, pole placement, ROW intersections, and power flow. If many candidates are generated, fully evaluating every candidate may be expensive.

## Decision

Permit a versioned machine-learning model to prioritize candidates or act as a surrogate for an expensive scoring stage, but only after deterministic feasibility checks and a validated baseline exist. ML must never bypass hard engineering or environmental constraints.

## Why Defer Implementation

No trustworthy training dataset exists yet because the deterministic route and engineering stages are incomplete. A speedup claim cannot be made until a representative benchmark compares model-assisted and deterministic pipelines at equal solution quality.

## Consequences

- **Positive**: A future model may reduce the number of expensive candidates requiring full evaluation.
- **Positive**: The deterministic solver remains the safety and correctness boundary.
- **Negative**: Requires versioned features, representative labels, project-level data splitting, monitoring, and retraining governance.
- **Negative**: Adds another artifact whose output must be explained and reproduced.

## Implementation Status

Scikit-learn is installed, but there is no model, training pipeline, dataset, inference module, or benchmark. XGBoost and LightGBM are not current dependencies.
