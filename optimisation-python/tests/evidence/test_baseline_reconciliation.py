"""WP0B-9: count reconciliation on baseline evidence, version 1.

The V0 goldens are real engine output captured at ``demo-opt-base``, so they
are the baseline the equations must hold over.
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.evidence.baseline_reconciliation import (
    C4_EQUATIONS,
    BaselineView,
    EquationResult,
    Outcome,
    Reason,
    reconcile_baseline,
    reconcile_record,
    reconcile_run,
)
from scripts.evidence.harness import (
    COLD_DEFINITION,
    Environment,
    MeasurementRecord,
    Revisions,
    RunMeasurement,
    StackTimings,
)

ROOT = Path(__file__).resolve().parents[2]
GOLDENS = sorted((ROOT / "tests/fixtures/v0_golden").glob("*.golden.json"))
ADDITIVE = ROOT.parent / "contracts/fixtures/response/additive-blocks.json"
SUCCESS = "SYN-4-SPREAD-30.golden.json"
NO_FEASIBLE = "SYN-1-CLUSTERED-8.golden.json"


def golden(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (ROOT / "tests/fixtures/v0_golden" / name).read_text()
    )
    return data


def java_summary(response: dict[str, Any]) -> dict[str, Any]:
    """The summary Java stores, per ``OptimizationJobService.buildResultSummary``."""
    result = response.get("recommended_result") or {}
    summary: dict[str, Any] = {
        "metrics": response.get("metrics") or {},
        "workflowStatus": response.get("workflow_status"),
        "candidates": response.get("candidates") or [],
        "recommendation": response.get("recommendation"),
        "failures": response.get("failures") or [],
    }
    for key, source in (
        ("networkSummary", "network_summary"),
        ("electricalSummary", "electrical_summary"),
        ("poleSummary", "pole_summary"),
        ("spatialConstraintSummary", "spatial_constraint_summary"),
        ("feeders", "feeders"),
        ("violations", "violations"),
    ):
        if source in result:
            summary[key] = result[source]
    return summary


def features(response: dict[str, Any], key: str) -> int | None:
    layer = response.get(key)
    return len(layer["features"]) if layer else None


def by_equation(results: list[EquationResult]) -> dict[str, EquationResult]:
    return {r.equation: r for r in results}


def outcome(results: list[EquationResult], prefix: str) -> EquationResult:
    (match,) = [r for r in results if r.equation.startswith(prefix)]
    return match


# --- the baseline holds ---------------------------------------------------------------


@pytest.mark.parametrize("path", GOLDENS, ids=lambda p: p.name)
def test_every_v0_golden_reconciles(path: Path) -> None:
    results = reconcile_baseline(
        BaselineView.from_v1_response(json.loads(path.read_text()))
    )
    assert [r for r in results if r.outcome is Outcome.VIOLATED] == []
    assert len({r.equation for r in results}) == len(results)


def test_a_successful_v0_run_checks_everything_but_search() -> None:
    results = reconcile_baseline(BaselineView.from_v1_response(golden(SUCCESS)))
    unavailable = [r for r in results if r.outcome is Outcome.NOT_AVAILABLE]
    assert {r.equation for r in unavailable} == set(C4_EQUATIONS)
    assert {r.reason for r in unavailable} == {Reason.SEARCH_EVIDENCE_ABSENT}
    routes = outcome(results, "persisted route features")
    assert (routes.left, routes.right) == (30, 30)


def test_a_run_with_no_recommendation_says_why_the_network_is_not_counted() -> None:
    results = reconcile_baseline(BaselineView.from_v1_response(golden(NO_FEASIBLE)))
    network = [r for r in results if r.reason is Reason.NO_RECOMMENDED_RESULT]
    assert len(network) == 4
    assert outcome(results, "recommendation present").outcome is Outcome.HOLDS


def test_java_does_not_persist_generation_or_search_evidence() -> None:
    response = golden(SUCCESS)
    view = BaselineView.from_java_summary(
        java_summary(response),
        persisted_routes=features(response, "feeder_routes_geojson"),
        persisted_poles=features(response, "poles_geojson"),
    )
    results = reconcile_baseline(view)
    assert [r for r in results if r.outcome is Outcome.VIOLATED] == []
    unavailable = {
        r.equation: r.reason for r in results if r.outcome is Outcome.NOT_AVAILABLE
    }
    assert unavailable == {
        "candidates listed = generation.accepted_candidate_count": (
            Reason.NOT_PERSISTED_BY_JAVA
        ),
        **dict.fromkeys(C4_EQUATIONS, Reason.NOT_PERSISTED_BY_JAVA),
    }


def test_unread_persisted_layers_are_reported_not_assumed() -> None:
    view = BaselineView.from_java_summary(
        java_summary(golden(SUCCESS)), persisted_routes=None, persisted_poles=None
    )
    results = reconcile_baseline(view)
    assert (
        outcome(results, "persisted route features").reason
        is Reason.RESULT_NOT_RETRIEVED
    )
    assert (
        outcome(results, "persisted pole features").reason
        is Reason.RESULT_NOT_RETRIEVED
    )


# --- each equation catches its own defect ---------------------------------------------


def corrupt(name: str, change: Any) -> list[EquationResult]:
    response = copy.deepcopy(golden(name))
    change(response)
    return reconcile_baseline(BaselineView.from_v1_response(response))


def violated(results: list[EquationResult]) -> set[str]:
    return {r.equation for r in results if r.outcome is Outcome.VIOLATED}


def test_a_dropped_candidate_is_caught() -> None:
    results = corrupt(SUCCESS, lambda r: r["candidates"].pop())
    assert "candidates listed = generation.accepted_candidate_count" in violated(
        results
    )


def test_a_failure_nobody_reported_is_caught() -> None:
    results = corrupt(NO_FEASIBLE, lambda r: r["failures"].pop())
    assert violated(results) == {
        "candidates with an execution failure = candidates named in failures"
    }


def test_a_failure_reported_against_the_wrong_candidate_is_caught() -> None:
    # Same number on both sides, different candidates: only the sets differ.
    def swap(r: dict[str, Any]) -> None:
        r["failures"][0]["scenario_id"] = "SCN-999"

    results = corrupt(NO_FEASIBLE, swap)
    assert violated(results) == {
        "candidates with an execution failure = candidates named in failures"
    }
    broken = outcome(results, "candidates with an execution failure")
    assert (broken.left, broken.right) == (2, 2)


def test_an_eligible_candidate_that_failed_electrically_is_caught() -> None:
    def invalid(r: dict[str, Any]) -> None:
        r["candidates"][1]["electrical_status"] = "INVALID"

    assert violated(corrupt(SUCCESS, invalid)) == {
        "eligible candidates <= feasible candidates",
        "eligible outside complete feasible = 0",
    }


def test_a_recommendation_outside_the_eligible_set_is_caught() -> None:
    def ineligible(r: dict[str, Any]) -> None:
        rid = r["recommendation"]["recommended_scenario_id"]
        next(c for c in r["candidates"] if c["scenario_id"] == rid)["eligible"] = False

    assert "recommendations outside eligible = 0" in violated(
        corrupt(SUCCESS, ineligible)
    )


def test_a_missing_recommendation_with_eligible_candidates_is_caught() -> None:
    def drop(r: dict[str, Any]) -> None:
        r["recommendation"] = None

    assert violated(corrupt(SUCCESS, drop)) == {
        "recommendation present = (eligible >= 1)"
    }


@pytest.mark.parametrize(
    ("layer", "equation"),
    [
        ("feeder_routes_geojson", "persisted route features = network segment_count"),
        ("poles_geojson", "persisted pole features = pole total_poles"),
    ],
)
def test_a_lost_persisted_feature_is_caught(layer: str, equation: str) -> None:
    assert violated(corrupt(SUCCESS, lambda r: r[layer]["features"].pop())) == {
        equation
    }


def test_pole_classes_that_do_not_add_up_are_caught() -> None:
    def extra(r: dict[str, Any]) -> None:
        r["recommended_result"]["pole_summary"]["junction_poles"] += 1

    assert violated(corrupt(SUCCESS, extra)) == {
        "terminal + angle + intermediate + junction poles = total_poles"
    }


def test_a_headline_feeder_count_that_disagrees_is_caught() -> None:
    def more(r: dict[str, Any]) -> None:
        r["metrics"]["feeder_count"] += 1

    assert violated(corrupt(SUCCESS, more)) == {
        "metrics.feeder_count = network feeder_count"
    }


# --- C4 equations run when search evidence exists -------------------------------------


def with_search(counts: dict[str, int]) -> list[EquationResult]:
    response = copy.deepcopy(golden(SUCCESS))
    search = json.loads(ADDITIVE.read_text())["search_evidence"]
    response["search_evidence"] = {**search, "counts": counts}
    return reconcile_baseline(BaselineView.from_v1_response(response))


def test_search_counts_are_reconciled_with_the_c4_checker() -> None:
    counts = json.loads(ADDITIVE.read_text())["search_evidence"]["counts"]
    results = by_equation(with_search(counts))
    assert all(results[eq].outcome is Outcome.HOLDS for eq in C4_EQUATIONS)


def test_a_search_count_that_does_not_add_up_is_caught() -> None:
    counts = json.loads(ADDITIVE.read_text())["search_evidence"]["counts"]
    counts["duplicates"] += 1
    results = by_equation(with_search(counts))
    broken = results[C4_EQUATIONS[0]]
    assert broken.outcome is Outcome.VIOLATED
    assert (broken.left, broken.right) == (20, 21)


# --- blinding -------------------------------------------------------------------------


def record(
    summary: dict[str, Any] | None, *, routes: int, poles: int
) -> MeasurementRecord:
    return MeasurementRecord(
        record_id="MSR-TEST",
        created_at="2026-09-28T00:00:00+00:00",
        blinded=False,
        project_input_sha256="0" * 64,
        import_counts={"wtgsImported": 30},
        revisions=Revisions(revision="abc", clean_worktree=True, lockfile_sha256={}),
        environment=Environment(
            host_os="test",
            docker_server_version=None,
            docker_cpus=None,
            docker_memory_gb=None,
            optimiser_python_version=None,
            backend_java_version=None,
            cold_definition=COLD_DEFINITION,
        ),
        stack=StackTimings(compose_up_s=[1.0], image_ids={}),
        poll_interval_s=0.5,
        runs=[
            RunMeasurement(
                request_variant="Balanced",
                kind="cold",
                job_id="job-1",
                job_status="COMPLETED",
                submitted_to_terminal_s=1.0,
                submitted_to_persisted_s=1.5,
                persisted_route_features=routes,
                persisted_pole_features=poles,
                result_summary=summary,
            )
        ],
    )


def test_the_published_report_names_no_candidate_rank_or_score() -> None:
    response = golden(SUCCESS)
    report = reconcile_record(record(java_summary(response), routes=30, poles=406))
    assert report["violations"] == 0
    text = json.dumps(report)
    for candidate in response["candidates"]:
        assert candidate["scenario_id"] not in text
    for word in ("rank", "score", "recommended_scenario_id", "total_route_length"):
        assert word not in text


def test_reconciliation_refuses_the_blinded_record() -> None:
    raw = record(java_summary(golden(SUCCESS)), routes=30, poles=406)
    with pytest.raises(ValueError, match="raw record"):
        reconcile_record(raw.blinded_copy())
    with pytest.raises(ValueError, match="raw record"):
        reconcile_run(raw.blinded_copy().runs[0])


def test_a_persisted_count_off_by_one_fails_the_record() -> None:
    report = reconcile_record(
        record(java_summary(golden(SUCCESS)), routes=29, poles=406)
    )
    assert report["violations"] == 1
