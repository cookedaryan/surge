# ADR-003: Integrate ML Route Ranking & Surrogate Scoring

* Status: **Accepted**
* Date: 2026-08-04

## Context
Multi-objective spatial routing requires searching high-dimensional solution spaces. Evaluating complex load flow and pole placement on thousands of candidate paths is computationally expensive.

## Decision
Train a lightweight machine learning surrogate model (XGBoost / LightGBM) to pre-score and rank candidate path corridors before full electrical and pole placement solver execution.

## Consequences
- **Positive**: Accelerates optimization turnaround time by 5x-10x.
- **Negative**: Requires feature engineering and offline model retraining pipelines.
