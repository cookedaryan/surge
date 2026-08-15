"""Tests for deterministic search caching and fingerprinting."""

from app.optimisation.search_cache import (
    CandidateEvaluationCache,
    CandidateEvaluationOutcome,
)


def _outcome() -> CandidateEvaluationOutcome:
    return CandidateEvaluationOutcome(
        load_flow_result=None,
        engineering_assessment=None,
        cost_assessment=None,
        cable_sizing=None,
        repair_log=(),
        execution_failure=None,
    )


def test_candidate_evaluation_cache_isolates_evaluation_contexts() -> None:
    cache = CandidateEvaluationCache()
    outcome = _outcome()

    cache.put("design", "context-a", outcome)

    assert cache.get("design", "context-a") is outcome
    assert cache.get("design", "context-b") is None
    assert cache.get("other-design", "context-a") is None


def test_candidate_evaluation_cache_evicts_oldest_entry() -> None:
    cache = CandidateEvaluationCache(max_entries=1)

    cache.put("first", "context", _outcome())
    cache.put("second", "context", _outcome())

    assert cache.get("first", "context") is None
    assert cache.get("second", "context") is not None
