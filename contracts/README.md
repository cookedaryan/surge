# SURGE demo optimisation contract pack

Contract pack version **1.0.0**, frozen at tag `demo-opt-base`.

This directory is the shared base the three parallel worktree levels build against (see the [L3 worktree plan §3](../docs/planning/SURGE%20demo%20optimization%20L3%20worktree%20plan.md)). It fixes names, shapes, codes, fixtures and file ownership. It does **not** fix values: policy values arrive at FRZ-1 and cap and timeout values at G2.

## Source of truth

Python models in `optimisation-python/app/contracts/` are authoritative. Every JSON file here is generated from them:

```bash
cd optimisation-python
python -m scripts.contracts.export_contracts          # regenerate
python -m scripts.contracts.export_contracts --check  # verify, as the tests do
```

`tests/contracts/test_contract_pack.py` fails when a committed file differs from the generated one. Java and the frontend mirror these files. They never edit them.

## Index

| ID | Contract | Files |
|---|---|---|
| C1 | Additive V1 request fields | `request-rules.json`, `schemas/v1-request-*.schema.json`, `fixtures/request/`; Python `app/contracts/request.py` |
| C2 | Additive V1 response blocks | `response-rules.json`, `schemas/v1-response-*.schema.json`, `fixtures/response/additive-blocks.json`; Python `app/contracts/response.py` |
| C3 | Stable codes | `codes.json`; Python `app/contracts/codes.py` |
| C4 | Evidence record v1 and count reconciliation | `schemas/evidence-v1.schema.json`, `fixtures/evidence/`; Python `app/contracts/evidence.py`, `app/contracts/reconcile.py` |
| C5 | Deployment flags and generation-schedule gating | `optimisation-python/app/core/config.py` |
| C6 | Profile allow-list, definition format, definition hash | `profiles/allow-list.json`, `schemas/profile-definition-set.schema.json`, `profiles/hash-vector/`; Python `app/contracts/profiles.py`, `app/contracts/canonical_json.py` |
| C7 | Run ID, cancellation and handshake transport | [transport.md](transport.md) |
| C8 | Recorded Demo bundle and frontend modes | `recorded-mode.json`, `schemas/recorded-bundle-v1.schema.json`, `fixtures/recorded-bundle/`; Python `app/contracts/recorded_bundle.py` |
| C9 | Persistence reservations | [persistence.md](persistence.md) |
| C10 | Ownership and frozen paths | `ownership/L1.globs`, `ownership/L2.globs`, `ownership/L3.globs`, `frozen.txt`; check `scripts/ci/check_ownership.py` |
| C11 | Feeder/segment identity | `fixtures/feeder-segment-identity.json` |
| C12 | WP5 V0 decision | [decisions/wp5-v0.md](decisions/wp5-v0.md) |

## Rules that are easy to get wrong

- **Absent means V0.** An additive request field that is absent keeps today's behaviour. An additive response block that is not produced is **absent** from the JSON, not `null`, because the V1 endpoint serialises with `exclude_none`.
- **Explicit and unsupported means reject.** A present `profile` that cannot be honoured is refused with a `ContractErrorCode`. It never falls back to Balanced.
- **Canonical JSON has no floats.** Decimals in profile definitions are strings. Python and Java print doubles differently, and the definition hash must match byte for byte.
- **`LIMIT_REACHED` is not `INFEASIBLE`.** A solver limit says nothing about whether a feeder count is feasible.
- **Enums, not multi-value `Literal`s, in contract models.** `typing` caches `Literal` types regardless of value order, which makes the exported schemas depend on import order.

## Contract change requests (CCR)

A CCR is the only sanctioned cross-level event during Phase 1.

1. The level that needs the change opens an issue titled `CCR: <contract ID> <summary>` stating the problem, the proposed change and which levels it affects.
2. The contract authority (the Stage 0 lead) decides. A rejected CCR is closed with its reason.
3. An accepted CCR lands on `main` as one PR that changes the Python contract module, regenerates the artefacts, updates any affected seam or fixture, and adds an entry to [CHANGELOG.md](CHANGELOG.md). Additive changes bump the minor version; breaking changes bump the major version.
4. All three levels rebase onto that commit.

Frozen paths pass the ownership check only on the CCR PR's branch, which is not a level branch.
