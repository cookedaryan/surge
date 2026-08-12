# Electrical Feeder Screening

> [!note] Implementation status: Standalone — SURGE-PY-013
> The deterministic screening engine is implemented and tested under `app/electrical`. It is not invoked by `OptimisationService`, returned by `/api/v1/optimise`, or persisted by Java.

## Purpose

Electrical feeder screening answers a preliminary question: at one configured operating point, does the proposed radial collector network exceed its conductor ampacity, cumulative voltage-deviation, or substation-capacity limits?

It is a fast analytical proxy intended to reject obviously unsuitable layouts and provide deterministic metrics for later candidate scoring. It is not a nonlinear power-flow solution or final engineering approval.

## Components

- `models.py` defines immutable conductor/configuration inputs and segment, turbine, feeder, violation, and network results.
- `voltage_drop.py` contains pure balanced three-phase current, series-impedance, and linear voltage-change calculations.
- `feeder_validation.py` reconciles project, topology, and route inputs; roots each tree at the substation; aggregates downstream power; and builds the result hierarchy.

Keeping primitives separate from network orchestration makes formula assumptions directly testable and prevents graph/GIS validation from being hidden inside numerical helpers.

## Input Contract

`validate_collector_network(topology, routing, project, config)` requires:

- One projected CRS whose first two axes are measured in metres.
- Positive finite WTG capacities and, when supplied, a positive finite substation capacity.
- At least one feeder, with unique feeder IDs.
- One connected undirected tree per feeder containing the project substation exactly once.
- Every project WTG assigned to exactly one feeder, with no unknown topology nodes.
- `node_ids` and `mst_edges` that exactly describe the corresponding graph.
- Exactly one refined physical route for each feeder/edge pair and no extra routes.
- Valid finite LineStrings whose lengths match `refined_length_m` and whose endpoints match the declared project nodes.
- A routing aggregate whose `total_refined_length_m` equals the sum of its routes.

Contract failures raise `ValueError`; they are not electrical violations because no trustworthy electrical result can be calculated from inconsistent inputs.

## Calculation Flow

1. Multiply each installed WTG capacity by `operating_factor` to obtain screened active power.
2. Root every feeder tree at the substation.
3. Traverse child nodes before parents and sum downstream operating power on every edge.
4. Calculate nominal-voltage balanced three-phase current:

   $$I = \frac{P}{\sqrt{3}V_{LL}\operatorname{pf}}$$

5. Convert conductor resistance/reactance per kilometre to segment impedance using refined route length.
6. Calculate linear voltage change:

   $$\Delta V = \sqrt{3}I(R\cos\phi \pm X\sin\phi)$$

   The plus sign represents lagging power factor and the minus sign represents leading power factor. Positive change is a voltage drop; negative change is a rise.
7. Accumulate segment changes from the substation to every WTG and compare the absolute percentage deviation with the configured limit.
8. Return segment/turbine telemetry, feeder/network maxima, validity flags, and deterministic violations.

`operating_factor` is applied consistently to segment downstream power, turbine and feeder active-power results, and the substation-capacity check. Installed capacity remains the basis for validating the topology's declared `total_capacity_mw`.

## Violations

- `AMPACITY_EXCEEDED`: nominal-voltage segment current exceeds conductor ampacity.
- `VOLTAGE_LIMIT_EXCEEDED`: a WTG's absolute cumulative voltage deviation exceeds the configured percentage.
- `SUBSTATION_CAPACITY_EXCEEDED`: total operating WTG power exceeds the supplied substation MW capacity.

Limit violations are returned rather than raised so a later candidate-scoring stage can reject or penalize an otherwise structurally valid network.

## Engineering Boundary

The proxy assumes balanced steady-state operation, fixed nominal voltage for current calculation, one feeder-wide power factor, and series impedance proportional to route length. It does not calculate conductor losses when aggregating downstream power, voltage-dependent current, shunt admittance, phase imbalance, transformers or taps, reactive-power variation, fault levels, protection coordination, thermal derating, harmonics, or reliability.

Pandapower integration remains required for the full load-flow requirement. Results from this module must be labelled preliminary screening values.

## Related Notes

- [[Python Engine]]
- [[Overview & Layout]]
- [[Feeder Planning]]
- [[Routing]]
- [[Testing Status]]
