# C12 — WP5 V0 decision

Status: **confirmed by the owner on 2026-09-17 (Stage 0 close-out)**

Draft 0.6 WP5 requires one of:

- **(a)** the new generation schedule (retired or gated personalities, explicit `k+1`) runs only behind a flag, so V0 stays byte-equivalent; or
- **(b)** V0 intentionally changes and its golden output is re-baselined.

## Decision

**Option (a).** The new schedule runs only when `Settings.new_generation_schedule_enabled` is true, which is when the profiles flag or the search flag is on (C5). With both flags off, generation is exactly today's five-entry schedule.

## Why

- L1 captures V0 golden responses at `demo-opt-base` in parallel with L3's WP5 work. Option (b) would make those goldens a moving target owned by two levels.
- The `k+1` candidate matters to the Minimum Cost story, which needs the profile flag anyway; the search-only cut (profiles off, search on) also gets it because search enables the new schedule.
- Rollback stays a flag flip.

## Consequences

- WP5-2 (L3) gates, and does not delete, `scenarios._apply_long_edge_penalty`; L1's WP5-1 test imports it.
- Choosing (b) later is a CCR that also re-captures L1's goldens.
