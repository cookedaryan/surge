# AC Load Flow Validation

## Overview

Surge uses **Pandapower** to validate the automatically assembled `ProjectPNCNetwork` for AC load-flow convergence and electrical constraints.

This module answers: *“The PNC network has been generated physically — is it electrically feasible?”*

It sits downstream of PNC assembly (`app/pnc/assembly.py`) and does not alter or optimize the network; it acts as a final validator.

## Pipeline position

```text
Constraints / Route Processing
        ↓
Automatic PNC Network Assembly
        ↓
┌─────────────────────┐
│ AC Load-Flow Solver │ ← (Pandapower integration)
└─────────────────────┘
```

## Models & Configuration

The module defines explicit domain configurations to preserve exact physical and electrical assumptions independently of standard library catalogs.

*   **`LoadFlowCableType`**: Immutable representation of cable parameters (resistance, reactance, capacitance, ampacity, parallel runs, derating).
*   **`LoadFlowConfig`**: Master configuration for a simulation run, mapping segments to cable types and defining system boundaries (voltage limits, nominal kV).
*   **`WTGOperatingPoint`**: Defines explicit P (MW) and Q (MVar) for every turbine. Uses positive generation sign convention.

## Sign Conventions

Pandapower's `sgen` component uses positive values for generation and negative for load. 
Therefore, `WTGOperatingPoint.active_power_mw` > 0 means the turbine is generating active power and injecting it into the grid.

## AC Load-Flow Solver (`analysis.py`)

The load-flow solver runs Pandapower's Newton-Raphson solver (`runpp`).

### Graceful Non-Convergence

Load-flow failures (non-convergence) do not raise Python exceptions to the orchestrator. They are structurally caught and returned as a valid `LoadFlowNetworkResult` where:
*   `converged = False`
*   `is_valid = False`
*   `violations = [LoadFlowViolation(code="LOAD_FLOW_NOT_CONVERGED")]`

This lets the optimisation workflow retain the candidate and explain the
failure instead of crashing. Under SURGE-PY-018, a non-converged candidate is
infeasible and cannot be recommended; it remains in comparison output with the
explicit convergence violation.

### Deterministic Builder (`builder.py`)

The translation from the physical `ProjectPNCNetwork` to `pandapowerNet` is fully deterministic:
*   Node and Segment IDs are lexicographically sorted prior to injection.
*   Mappings (`node_to_bus`, `segment_to_line`, etc.) are returned explicitly to allow perfect reverse-lookup of Pandapower index back to Surge Domain IDs.
