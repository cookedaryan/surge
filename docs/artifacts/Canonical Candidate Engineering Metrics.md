# Canonical Candidate Engineering Metrics (SURGE-PY-026)

SURGE-PY-026 adds a candidate-level engineering boundary without changing the
SURGE-PY-018 recommendation policy. Every candidate that completes load-flow
execution receives a `CandidateEngineeringAssessment` before cohort scoring.

## Canonical quantities

A complete `CandidateEngineeringMetrics` contains:

- physical route length and preserved refined traversal cost;
- unique affected soft-parcel count, road crossings, summed soft centreline
  overlap, and unique environmental ROW-overlap area;
- deduplicated physical pole count;
- active electrical loss, maximum cable loading, and voltage operating margin.

The voltage margin is the smaller of the lower-limit and upper-limit margins.
It may be negative for a converged candidate outside configured limits. That
does not alter PY-018 eligibility or ranking behavior.

## Availability and failures

The metrics object is all-or-nothing. If a required extraction phase fails,
`metrics` is `None`, `engineering_metrics_available` is false, and
`extraction_failures` provides stable reason codes. Other successfully
created evidence, including hard-exclusion IDs and a cached pole result, is
retained.

A missing pole configuration is reported as `POLE_CONFIG_MISSING`; it is not
represented as a zero pole count. Load-flow execution failures do not receive
an engineering assessment because no load-flow result exists.

Engineering extraction failures are candidate diagnostics and do not change
the established PY-018 recommendation workflow. Winner packaging still treats
a winner-level pole-placement failure as a workflow failure.

## Workflow position

```text
candidate generation
  -> load-flow execution
  -> canonical engineering metric extraction
  -> unchanged PY-018 scoring and recommendation
  -> winner presentation packaging
```

Pole placement now runs for each electrically evaluated candidate when a pole
configuration is available. The selected candidate reuses its cached
`CollectorPoleResult`, avoiding duplicate winner computation.

## Deliberate scope

PY-026 stores truthful raw engineering quantities. It does not add new scoring
weights, change recommendation eligibility, calculate monetary cost, or replace
the standalone preliminary constructability scorer. Unified engineering scoring
remains follow-up work.
