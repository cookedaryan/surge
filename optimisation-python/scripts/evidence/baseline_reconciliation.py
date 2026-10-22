"""Count reconciliation on baseline evidence. Owned by L2 (WP0B-9).

Checks the count equations that the fields present today can support, over a
run the WP0B-8 harness measured. It reads the raw record, because the counts
live in the result summary, and it publishes equation results only: which
equations hold, the two sides of each, and never a candidate identity, rank or
score. ``recommended ∈ eligible`` is reported as a count of misplaced
recommendations (0 or 1), not by naming the recommendation.

An equation whose inputs do not exist yet is not skipped silently. It is
reported ``NOT_AVAILABLE`` with one of the stable reason codes below, so a
later run that gains the field shows up as a change rather than as a new line.

Reason codes, version 1 (harness codes, not C3 contract codes)
--------------------------------------------------------------
``SEARCH_EVIDENCE_ABSENT``
    The run produced no C2 ``search_evidence``, so the C4 search equations have
    no counts. True of every V0 run: search is disabled.
``NOT_PERSISTED_BY_JAVA``
    Python produces the field, but Java's result summary does not keep it.
    Today that is ``generation`` and ``search_evidence``.
``NO_RECOMMENDED_RESULT``
    The run recommended nothing, so there is no network to count.
``RESULT_NOT_RETRIEVED``
    The harness did not read the persisted routes or poles back.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from app.contracts.reconcile import reconcile_counts
from app.contracts.response import SearchCounts
from scripts.evidence.harness import MeasurementRecord, RunMeasurement

RECONCILIATION_VERSION = "1"


class Outcome(StrEnum):
    HOLDS = "HOLDS"
    VIOLATED = "VIOLATED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class Reason(StrEnum):
    SEARCH_EVIDENCE_ABSENT = "SEARCH_EVIDENCE_ABSENT"
    NOT_PERSISTED_BY_JAVA = "NOT_PERSISTED_BY_JAVA"
    NO_RECOMMENDED_RESULT = "NO_RECOMMENDED_RESULT"
    RESULT_NOT_RETRIEVED = "RESULT_NOT_RETRIEVED"


# The five C4 equations in app.contracts.reconcile, by the name they report.
C4_EQUATIONS = (
    "child_proposals = duplicates + structural_rejects + cache_hits"
    " + routed_not_evaluated + child_evaluations",
    "routed_proposals = cache_hits + routed_not_evaluated + child_evaluations",
    "seed_evaluations + child_evaluations = executed_evaluations",
    "executed_evaluations = successful_evaluations + evaluation_failures",
    "eligible <= feasible",
)


@dataclass(frozen=True)
class EquationResult:
    equation: str
    outcome: Outcome
    left: int | None = None
    right: int | None = None
    reason: Reason | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "equation": self.equation,
            "outcome": self.outcome.value,
            "left": self.left,
            "right": self.right,
            "reason": self.reason.value if self.reason else None,
        }


def _compare(
    equation: str, left: int, right: int, *, at_most: bool = False
) -> EquationResult:
    holds = left <= right if at_most else left == right
    return EquationResult(
        equation, Outcome.HOLDS if holds else Outcome.VIOLATED, left, right
    )


def _missing(equation: str, reason: Reason) -> EquationResult:
    return EquationResult(equation, Outcome.NOT_AVAILABLE, reason=reason)


@dataclass(frozen=True)
class BaselineView:
    """The fields reconciliation reads, whichever side of the wire they came from."""

    candidates: Sequence[Mapping[str, Any]]
    failures: Sequence[Mapping[str, Any]]
    recommended_id: str | None
    network_summary: Mapping[str, Any] | None
    pole_summary: Mapping[str, Any] | None
    metrics: Mapping[str, Any]
    generation: Mapping[str, Any] | None
    search_evidence: Mapping[str, Any] | None
    persisted_routes: int | None
    persisted_poles: int | None
    missing_reason: Reason

    @classmethod
    def from_java_summary(
        cls,
        summary: Mapping[str, Any],
        *,
        persisted_routes: int | None,
        persisted_poles: int | None,
    ) -> BaselineView:
        recommendation = summary.get("recommendation") or {}
        return cls(
            candidates=summary.get("candidates") or [],
            failures=summary.get("failures") or [],
            recommended_id=recommendation.get("recommended_scenario_id"),
            network_summary=summary.get("networkSummary"),
            pole_summary=summary.get("poleSummary"),
            metrics=summary.get("metrics") or {},
            generation=None,
            search_evidence=None,
            persisted_routes=persisted_routes,
            persisted_poles=persisted_poles,
            missing_reason=Reason.NOT_PERSISTED_BY_JAVA,
        )

    @classmethod
    def from_v1_response(cls, response: Mapping[str, Any]) -> BaselineView:
        recommendation = response.get("recommendation") or {}
        result = response.get("recommended_result") or {}
        routes = response.get("feeder_routes_geojson")
        poles = response.get("poles_geojson")
        return cls(
            candidates=response.get("candidates") or [],
            failures=response.get("failures") or [],
            recommended_id=recommendation.get("recommended_scenario_id"),
            network_summary=result.get("network_summary"),
            pole_summary=result.get("pole_summary"),
            metrics=response.get("metrics") or {},
            generation=response.get("generation"),
            search_evidence=response.get("search_evidence"),
            persisted_routes=len(routes["features"]) if routes else None,
            persisted_poles=len(poles["features"]) if poles else None,
            missing_reason=Reason.SEARCH_EVIDENCE_ABSENT,
        )


def _feasible(candidate: Mapping[str, Any]) -> bool:
    return (
        not candidate.get("execution_failure")
        and candidate.get("electrical_status") == "VALID"
    )


def reconcile_baseline(view: BaselineView) -> list[EquationResult]:
    results: list[EquationResult] = []
    ids = [str(c.get("scenario_id")) for c in view.candidates]
    eligible = {
        i for i, c in zip(ids, view.candidates, strict=True) if c.get("eligible")
    }
    feasible = {i for i, c in zip(ids, view.candidates, strict=True) if _feasible(c)}

    # Candidate accounting.
    equation = "candidates listed = generation.accepted_candidate_count"
    if view.generation is None:
        results.append(_missing(equation, view.missing_reason))
    else:
        accepted = int(view.generation["accepted_candidate_count"])
        results.append(_compare(equation, len(ids), accepted))

    failed = {
        i
        for i, c in zip(ids, view.candidates, strict=True)
        if c.get("execution_failure")
    }
    reported = {str(f["scenario_id"]) for f in view.failures if f.get("scenario_id")}
    equation = "candidates with an execution failure = candidates named in failures"
    result = _compare(equation, len(failed), len(reported))
    if failed != reported:
        result = EquationResult(equation, Outcome.VIOLATED, len(failed), len(reported))
    results.append(result)

    results.append(
        _compare(
            "eligible candidates <= feasible candidates",
            len(eligible),
            len(feasible),
            at_most=True,
        )
    )
    results.append(
        _compare("eligible outside complete feasible = 0", len(eligible - feasible), 0)
    )

    # Recommendation, reported without naming it.
    results.append(
        _compare(
            "recommendation present = (eligible >= 1)",
            int(view.recommended_id is not None),
            int(bool(eligible)),
        )
    )
    if view.recommended_id is not None:
        results.append(
            _compare(
                "recommendations outside eligible = 0",
                int(view.recommended_id not in eligible),
                0,
            )
        )

    # The recommended network, as summarised and as persisted.
    network = view.network_summary
    poles = view.pole_summary
    for equation, persisted, summary_value in (
        (
            "persisted route features = network segment_count",
            view.persisted_routes,
            network.get("segment_count") if network else None,
        ),
        (
            "persisted pole features = pole total_poles",
            view.persisted_poles,
            poles.get("total_poles") if poles else None,
        ),
    ):
        if summary_value is None:
            results.append(_missing(equation, Reason.NO_RECOMMENDED_RESULT))
        elif persisted is None:
            results.append(_missing(equation, Reason.RESULT_NOT_RETRIEVED))
        else:
            results.append(_compare(equation, persisted, int(summary_value)))

    equation = "terminal + angle + intermediate + junction poles = total_poles"
    if not poles:
        results.append(_missing(equation, Reason.NO_RECOMMENDED_RESULT))
    else:
        parts = sum(
            int(poles.get(key, 0))
            for key in (
                "terminal_poles",
                "angle_poles",
                "intermediate_poles",
                "junction_poles",
            )
        )
        results.append(_compare(equation, parts, int(poles["total_poles"])))

    equation = "metrics.feeder_count = network feeder_count"
    if not network:
        results.append(_missing(equation, Reason.NO_RECOMMENDED_RESULT))
    else:
        results.append(
            _compare(
                equation,
                int(view.metrics.get("feeder_count", 0)),
                int(network["feeder_count"]),
            )
        )

    # C4 search equations.
    if view.search_evidence is None:
        results.extend(_missing(eq, view.missing_reason) for eq in C4_EQUATIONS)
    else:
        counts = SearchCounts.model_validate(view.search_evidence["counts"])
        violated = {v.equation: v for v in reconcile_counts(counts)}
        for eq in C4_EQUATIONS:
            v = violated.get(eq)
            results.append(
                EquationResult(eq, Outcome.VIOLATED, v.left, v.right)
                if v
                else EquationResult(eq, Outcome.HOLDS)
            )
    return results


def reconcile_run(run: RunMeasurement) -> list[EquationResult]:
    if run.result_summary is None:
        raise ValueError(
            f"run {run.job_id} has no result summary: reconciliation needs the raw "
            "record, not the blinded one"
        )
    view = BaselineView.from_java_summary(
        run.result_summary,
        persisted_routes=run.persisted_route_features,
        persisted_poles=run.persisted_pole_features,
    )
    return reconcile_baseline(view)


def reconcile_record(record: MeasurementRecord) -> dict[str, Any]:
    """Return the publishable reconciliation report for a raw record."""
    if record.blinded:
        raise ValueError("reconciliation needs the raw record, not the blinded one")
    runs: list[dict[str, Any]] = []
    violated = 0
    for run in record.runs:
        results = reconcile_run(run)
        violated += sum(1 for r in results if r.outcome is Outcome.VIOLATED)
        runs.append(
            {
                "request_variant": run.request_variant,
                "kind": run.kind,
                "job_status": run.job_status,
                "equations": [r.as_json() for r in results],
            }
        )
    return {
        "reconciliation_version": RECONCILIATION_VERSION,
        "record_id": record.record_id,
        "project_input_sha256": record.project_input_sha256,
        "violations": violated,
        "runs": runs,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WP0B-9 baseline count reconciliation")
    parser.add_argument("raw_record", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    record = MeasurementRecord.model_validate_json(
        args.raw_record.read_text(encoding="utf-8")
    )
    report = reconcile_record(record)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{report['violations']} violated equation(s); report: {args.out}")
    return 1 if report["violations"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
