# Baseline evidence tooling (L2)

| Module | Task | What it produces |
|---|---|---|
| `harness.py` | WP0B-8 | A raw measurement record per project: cold and warm Java submissions, timed from outside the stack |
| `baseline_reconciliation.py` | WP0B-9 | Which count equations hold over that record, with a stable reason code for each that cannot be checked yet |

Both run on synthetic data today. **Golden runs wait on G1**: until its owners name the project snapshot, the catalogue revision and the sanitisation rules, no output of these tools is golden evidence, and none should be labelled as such.

## Blinding

The L2 plan's blinding rule applies to every golden run before FRZ-1. L2 publishes distributions, counts and reconciliation only, and never winner identities, ranks or policy scores.

- The **raw record** keeps each job's result summary, which carries ranks, scores and the recommendation. `write_records` refuses to write it anywhere inside the repository. Keep it in an access-controlled location and record who opened it.
- The **blinded record** is the raw record with every result summary removed. It is the only form to share.
- The **reconciliation report** is computed from the raw record but names no candidate. A recommendation outside the eligible set is reported as a count (0 or 1), never by its ID.

## Procedure, harness version 1

Measurements for the baseline run against images built from `demo-opt-base`, not a later head. Check that tag out into its own worktree and point the harness at it:

```bash
git worktree add ../surge-base demo-opt-base
```

```bash
python -m scripts.evidence.harness --repo ../surge-base --project-input <project.geojson> --raw-dir <access-controlled dir> --published-dir <dir>
```

Run it from `optimisation-python/` with the repository venv. By default it measures all four scenario variants, with one warm repeat each, on an isolated Compose project (`surge-evidence`, host ports 25432, 28080, 28000 and 23000, from `compose.evidence-override.yml`). It does not touch a developer stack.

1. **Images.** `pull` and `build` run once and are reported as `image_pull_build_s`. No run includes them.
2. **Cold start, per variant.** `down -v` removes the containers and the database volume, then `up --no-build --wait` starts the prebuilt images. Every application cache is empty, because none survives a container. Each start is timed into `compose_up_s`.
3. **Cold run.** The harness logs in as the bootstrap administrator, creates a project and imports the GeoJSON. It then submits the variant and polls until a terminal status. For a completed job, it reads the routes and poles back.
4. **Warm runs.** The same variant is submitted again on the same stack, with nothing restarted.
5. The stack is torn down with `down -v`.

Credentials are generated per run and never written to a record.

**Timings.** `submitted_to_persisted_s` runs from the job `POST` until the result can be **read back**, not until it is announced as done. The two used to differ: see §4.1 of `CONTEXT.md`. Its resolution is the poll interval, which the record carries. `server_queue_s` and `server_run_s` are Java's own timestamps, for comparison.

**Input.** A GeoJSON FeatureCollection that `POST /api/v1/projects/{id}/assets/geojson` accepts. The shape `GET .../assets/geojson` exports (`assetType`, `externalId`, `capacityMw`) round-trips. `project_input_sha256` is taken over the exact bytes submitted.

Then reconcile:

```bash
python -m scripts.evidence.baseline_reconciliation <raw record> --out <report.json>
```

It exits non-zero if any equation is violated.

## What reconciliation can check at baseline

Against the seven V0 goldens (real engine output captured at `demo-opt-base`), every checkable equation holds. What cannot be checked yet is reported, not skipped:

| Equation | At baseline |
|---|---|
| The five C4 search equations | `SEARCH_EVIDENCE_ABSENT` from Python (search is disabled), and `NOT_PERSISTED_BY_JAVA` through Java, which keeps no `search_evidence` in its result summary |
| Candidates listed = `generation.accepted_candidate_count` | Checked on a Python response. `NOT_PERSISTED_BY_JAVA` through Java, which drops `generation` |
| Network and pole counts, persisted vs summarised | `NO_RECOMMENDED_RESULT` when the run recommended nothing |

**Java keeps no search evidence in the job summary.** Once search is enabled, the C4 equations still cannot be checked from a Java job until something persists it. That belongs to WP4-7's consumer.
