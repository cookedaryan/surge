# Candidate PNC Scenario Generation

**Ticket:** SURGE-PY-017  
**Module:** `optimisation-python/app/optimisation/`  
**Status:** Implemented  
**Depends on:** SURGE-PY-014

## Purpose

SURGE-PY-017 changes the optimiser from producing one PNC to producing a small,
configurable set of deterministic and structurally valid alternatives. Its
public internal entry point is `generate_pnc_scenarios()`.

Input consists of prepared `ProjectSpatialData`, the original feeder capacity,
a prepared `CostSurface`, and `ScenarioGenerationConfig`. Accepted candidates
contain complete `ProjectPNCNetwork` objects. Candidate count is configurable
from 1 through 5 and defaults to 3.

## Completion boundary

PY-017 owns:

- deterministic parameter personalities, scenario IDs, and ordering;
- real-pipeline grouping, MST topology, routing, refinement, and PNC assembly;
- duplicate-topology/network suppression;
- per-attempt diagnostics;
- preservation of feeder-capacity constraints; and
- PNC integrity for every accepted candidate.

Fewer candidates than requested is a valid outcome when fewer unique networks
exist. Zero accepted candidates is an explicit scenario-generation failure.

PY-017 does not perform pandapower analysis, scoring, recommendation,
orchestration, public API integration, or raw constraint-layer ingestion. Those
boundaries remain with PY-018 through PY-020 or post-MVP work.

Focused verification on 2026-08-12 passed all 65 scenario tests and strict mypy
checking. Ruff found one import-order issue in `app/optimisation/__init__.py`;
the implementation was left untouched during this documentation-only update.

See [Surge MVP Ticket Plan](Surge%20MVP%20Ticket%20Plan.md) for the canonical
sequence and [the Obsidian implementation note](../obsidian-vault/08-python-engine/Candidate%20PNC%20Scenario%20Generation.md)
for the detailed parameter schedule and model descriptions.
