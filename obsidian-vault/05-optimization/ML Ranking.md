# Machine-Learning Route Ranking

> [!warning] Implementation status: Planned
> Scikit-learn is installed, but there is no training dataset, feature pipeline, model artifact, inference module, or evaluation result.

## Intended Role

Machine learning may prioritize already feasible route candidates or approximate expensive evaluation steps. It must not override hard engineering, environmental, or authorization constraints.

A **surrogate model** approximates a slower calculation. A **ranking model** orders candidates rather than predicting a physical value directly. These roles require different labels and evaluation metrics and should not be conflated.

## Required Inputs and Evidence

- versioned candidate features and units
- traceable labels from solver results or engineer decisions
- train/validation/test separation by project to avoid spatial leakage
- baseline comparison against deterministic ranking
- calibration, failure analysis, and drift monitoring
- model version recorded with every scored result

## Why ML Is Deferred

The deterministic routing, electrical, pole, ROW, and lifecycle-cost pipeline must first produce trustworthy labels. Training earlier would teach a model to reproduce placeholders or synthetic assumptions rather than validated engineering decisions.

## Related Notes

- [[Routing]]
- [[Explainability]]
- [[ADR-003 ML Ranking]]
