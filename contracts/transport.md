# C7 — Run ID, cancellation and handshake transport

Java calls Python; the browser never calls Python.

## Run ID

Java sends `X-Surge-Run-Id: job-<job UUID>` on every `POST /api/v1/optimise`. The value is the same as the request's `request_id`. Python uses it only to find the run to cancel; it never changes results.

## Outer timeout and cancellation

| Step | Owner | Behaviour |
|---|---|---|
| 1 | Java (WP4-9b, L2) | The job has an outer timeout (value set at G2). |
| 2 | Java | On timeout: close the HTTP call, then `POST /api/v1/runs/{run_id}/cancel`, then persist job status `TIMED_OUT`. The cancel call is best effort; a failure is logged, never retried in a loop. |
| 3 | Python (WP4-9a, L3) | The cancel endpoint marks the run cancelled. The run's guard raises `RunCancelledError` before the next unit of bounded work. |
| 4 | Python | Nothing below the endpoint catches `RunCancelledError`. The endpoint answers **409** with `{"detail": {"code": "CANCELLED", "message": ...}}`. No partial candidate is cached or published, and the next run inherits no state. |

Cancel endpoint responses:

| Status | Body `detail.code` | Meaning |
|---|---|---|
| 202 | — | Cancellation recorded |
| 404 | `RUN_NOT_FOUND` | No active run with that ID (already finished, or never started) |
| 501 | `NOT_IMPLEMENTED` | Stage 0 stub; cancellation not yet available |

Guard points, in order: `BEFORE_SEED_GENERATION`, `BEFORE_SEED_EVALUATION`, `BEFORE_CHILD_ROUTING`, `BEFORE_CHILD_EVALUATION`. The guard is cooperative: work already started finishes. Describe it as an admission deadline, never as a hard pre-emptive timeout.

## Admission deadline

`AdmissionDeadlineReached` is raised by the deadline guard (WP4-4, L2) and handled inside L2-owned search and orchestration code, which publishes only fully evaluated candidates plus termination reason `ADMISSION_DEADLINE_REACHED`. If it ever reaches the endpoint unhandled, the endpoint answers **503** with that code.

## Profile definition-hash handshake

| Step | Owner | Behaviour |
|---|---|---|
| 1 | Python (WP3-6a, L3) | `GET /api/v1/profiles/definition-hash` returns `{"definition_hash": "<sha256>", "metric_registry_version": "<v>", "contract_pack_version": "<v>"}`. Stage 0 stub answers 501 `NOT_IMPLEMENTED`. |
| 2 | Java (WP3-6b, L2) | At startup, when profiles are enabled, compare `definition_hash` with the configured expected hash. A mismatch or unreachable endpoint fails startup, not individual requests. |
| 3 | FRZ-1 | Sets the expected hash in Java configuration. It is a config value, not code. |

The hash algorithm is in `app/contracts/canonical_json.py` and `app/contracts/profiles.py::definition_set_hash`. Java must reproduce `profiles/hash-vector/expected.sha256` from `profiles/hash-vector/definitions.json`; `profiles/hash-vector/canonical.json` holds the exact bytes hashed, for debugging.

## Contract errors

Request-contract rejections answer **422** (or **413** for `PAYLOAD_TOO_LARGE`) with `{"detail": {"code": "<ContractErrorCode>", "message": "..."}}`. Existing V0 validation errors keep their current shape.
