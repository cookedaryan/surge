# Contract pack changelog

Every contract change after `demo-opt-base` is recorded here, newest first, with its CCR link.

## Unreleased — CCR: S5 feeder-count seam (pack version stays 1.0.0)

CCR: issue not yet opened (drafted by L3 for WP5-3). Seam test only, so `CONTRACT_PACK_VERSION` and the exported artefacts do not change.

- `tests/contracts/test_seams.py`: `test_feeder_count_override_is_reserved_for_wp5` asserted the Stage 0 `NotImplementedError`, so the WP5-3 implementation in L3's `group_wtgs` region could never pass it. It is replaced by `test_feeder_count_is_a_keyword_seam_that_defaults_to_the_minimum`, which fixes only the keyword-only `feeder_count` parameter and that `None` keeps the minimum capacity-feasible count. It passes before and after WP5-3.
- No schema, fixture, code registry or generated artefact changes. Affects L3 (WP5-3); L2 is unaffected because its S5 region is the MILP bodies.

## 1.0.0 — 2026-09-17 — Stage 0

Initial contract pack (CON-1) and seams (CON-2) for the SURGE demo optimisation split. No behaviour change: V1 responses for every Python test fixture are byte-identical to `a313d2f`.

Close-out before the `demo-opt-base` tag:

- C12 option (a) and `MAX_V1_REQUEST_BYTES` = 10 MiB confirmed by the owner.
- Seam-sufficiency sign-off found one gap: `orchestrator.py` rebuilt `ScenarioGenerationConfig` field by field, so a generation setting added for WP5-2 would never reach the generator. It now forwards `config.scenario` whole, overriding only `project_id` and `solver_options`. Behaviour-neutral; new frozen symbol, guarded by a seam test.
