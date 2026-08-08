# Explainable Engineering Decisions

> [!warning] Implementation status: Planned
> Current responses contain only feeder count, zero route length, no cost, and a projection message.

## What Explainability Means Here

Explainability is the ability to trace a result back to inputs, constraints, algorithms, and cost components. It is broader than explaining an ML model. A deterministic solver also needs an audit trail showing why a path was feasible and why it scored better than alternatives.

## Intended Explanation Record

- input dataset and parameter versions
- selected CRS and transformation metadata
- feeder assignments and capacity utilization
- topology edges and route algorithm/version
- hard constraints checked and clearance margins
- raw cost, land, environmental, and electrical metrics
- scenario weights and normalized values
- rejected alternatives with explicit rejection reasons
- ML model/version and contribution, if ML is later introduced

## Design Principle

Store raw engineering metrics before calculating a combined score. A statement such as “route A scored 0.82” is not actionable unless users can see the underlying length, parcel area, voltage drop, losses, pole count, constraint margins, and assumptions.

## Related Notes

- [[Routing]]
- [[Cost Model]]
- [[ML Ranking]]
