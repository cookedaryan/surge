# C9 — Persistence reservations

`main` is at Flyway **V20**. Versions below are reserved in merge-queue order so parallel Java work never collides. A package that turns out not to need its migration leaves the number unused; Flyway tolerates gaps. Every change is expand/contract: add nullable columns, never rename or drop in the same release.

| Version | Package | Merge slot | Purpose |
|---|---|---|---|
| V21 | WP4-9b (L2) | 3 | Job outer-timeout state: `TIMED_OUT` status, `timed_out_at` |
| V22 | WP2-3 (L2, conditional) | 5 | Typed identity on persisted assets, if transport needs stored values |
| V23 | WP3-7b (L2) | 6 | Effective profile, hashes and flags on jobs |
| V24 | WP5B-3 (L2, conditional) | S2-3 | Live cohort ID and hash |
| V25 | WP6A-3 (L2) | S2-4 | Landowner masking, if persistence changes |
| V26 | WP6B (L2) | S2-7 | Recorded Demo bundle metadata |

## Column names

| Column | Table | Type | Source field |
|---|---|---|---|
| `status` value `TIMED_OUT` | `optimization_jobs` | existing enum string | `JobStatus.TIMED_OUT` |
| `timed_out_at` | `optimization_jobs` | `timestamptz` null | — |
| `termination_reason` | `optimization_jobs` | `varchar(64)` null | `termination.reason` |
| `profile_id` | `optimization_jobs` | `varchar(64)` null | `effective_profile.profile_id` |
| `profile_version` | `optimization_jobs` | `varchar(16)` null | `effective_profile.profile_version` |
| `policy_hash` | `optimization_jobs` | `char(64)` null | `effective_profile.policy_hash` |
| `definition_hash` | `optimization_jobs` | `char(64)` null | `effective_profile.definition_hash` |
| `metric_registry_version` | `optimization_jobs` | `varchar(16)` null | `effective_profile.metric_registry_version` |
| `generation_settings_hash` | `optimization_jobs` | `char(64)` null | `effective_profile.generation_settings_hash` |
| `profiles_enabled` | `optimization_jobs` | `boolean` null | `effective_profile.profiles_enabled` |
| `search_enabled` | `optimization_jobs` | `boolean` null | `effective_profile.search_enabled` |
| `cohort_id`, `cohort_hash` | `optimization_jobs` | `varchar(64)`, `char(64)` null | WP5B-3 |
| `cable_type_id` (existing, V14) | `generated_routes` | `varchar(100)` null | Today filled from candidate `cable_sizing`, which is the **initial** sizing (finding F3). From WP6A-6 it must hold `design_truth.segments[].final_cable_type_id`; no new column. |

Null in any of these columns means "recorded before this contract", never "false" or "absent profile".
