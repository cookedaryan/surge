# ADR-007: Pandapower AC Load Flow Validation

**Status**: Accepted  
**Date**: 2026-08-12  

## Context

Surge pipelines generate physical feeder networks (`ProjectPNCNetwork`) connecting wind turbines to substations. The physical network generation logic (grouping, routing, topology) does not guarantee electrical validity under varying load conditions, reactive power requirements, and line losses. We need to validate these networks via AC Load-Flow.

## Decision

We will use **Pandapower** to build and validate the AC load-flow networks. 
We will integrate it as a standalone validator located at `app/electrical/load_flow`, downstream from physical PNC assembly.

We establish the following specific patterns to isolate Pandapower:

1. **Domain-Driven Configuration**: Surge provides explicit parameters (R, X, C, ampacity) for `LoadFlowCableType`. We do not rely on standard Pandapower catalog standard types, which are version-dependent and opaque to users.
2. **Positive Generator Convention**: WTG operating points are configured as positive `active_power_mw` injections, mapping seamlessly into Pandapower's `sgen` component.
3. **Graceful Non-Convergence**: The `runpp` solver is wrapped. If it throws `LoadflowNotConverged`, we catch the exception and return a valid result object with `converged = False` and an explicit `LOAD_FLOW_NOT_CONVERGED` violation. This avoids crashing the optimization pipeline.
4. **Deterministic Mappings**: The mapping between canonical domain IDs (e.g., `SEG-001`, `WTG-1`) and integer indices used in Pandapower (`res_line`, `res_bus`) is managed strictly by the builder, with full determinism achieved by sorting items lexicographically prior to creation.

## Consequences

*   **Positive**: The pipeline can rigorously analyze electrical constraint violations (voltage drops, thermal overloads) using a trusted solver.
*   **Positive**: The domain logic remains isolated from Pandapower's internal state.
*   **Neutral**: Performance overhead of Newton-Raphson solvers is non-trivial compared to simple linear heuristics, requiring careful architectural choices if we want to run thousands of load flows inside optimization loops. (Numba is disabled for stability).
