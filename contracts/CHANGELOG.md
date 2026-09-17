# Contract pack changelog

Every contract change after `demo-opt-base` is recorded here, newest first, with its CCR link.

## 1.0.0 — 2026-09-17 — Stage 0

Initial contract pack (CON-1) and seams (CON-2) for the SURGE demo optimisation split. No behaviour change: V1 responses for every Python test fixture are byte-identical to `a313d2f`.

Close-out before the `demo-opt-base` tag:

- C12 option (a) and `MAX_V1_REQUEST_BYTES` = 10 MiB confirmed by the owner.
- Seam-sufficiency sign-off found one gap: `orchestrator.py` rebuilt `ScenarioGenerationConfig` field by field, so a generation setting added for WP5-2 would never reach the generator. It now forwards `config.scenario` whole, overriding only `project_id` and `solver_options`. Behaviour-neutral; new frozen symbol, guarded by a seam test.
