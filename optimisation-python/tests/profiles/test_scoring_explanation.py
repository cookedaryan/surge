"""WP2-7: raw, normalised and weighted contributions in the C2 shape.

Candidates are lightweight stand-ins: the explanation reads only a candidate's
scenario ID and its evaluation, so building full workflow results would test the
pipeline rather than the contribution arithmetic this task owns.
"""

import dataclasses
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.contracts.codes import MetricDirection, ProfilePolicyMode
from app.contracts.profiles import MetricTerm, ProfileDefinition, ProfileId
from app.contracts.resolution import (
    SEARCH_DISABLED,
    V0_PROFILE_RESOLUTION,
    ProfileResolution,
    ResponseContext,
)
from app.contracts.response import ScoringExplanation
from app.optimisation.engineering_metric_models import CandidateEngineeringMetrics
from app.presentation.explanation import (
    KNOWN_METRICS,
    build_scoring_explanation,
    explain_candidates,
    normalise,
)

_C2_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "contracts"
    / "fixtures"
    / "response"
    / "additive-blocks.json"
)


def _metrics(**overrides: float) -> CandidateEngineeringMetrics:
    values: dict[str, Any] = {
        "total_route_length_m": 1000.0,
        "total_traversal_cost": 1000.0,
        "affected_parcel_count": 1,
        "owner_interaction_count": 1,
        "road_crossing_count": 0,
        "soft_constraint_overlap_length_m": 0.0,
        "environmental_overlap_m2": 0.0,
        "physical_pole_count": 10,
        "total_active_loss_mw": 0.1,
        "maximum_loading_percent": 50.0,
        "voltage_margin_pu": 0.03,
        "affected_parcel_row_area_m2": 0.0,
    }
    values.update(overrides)
    return CandidateEngineeringMetrics(**values)


def _candidate(
    candidate_id: str,
    metrics: CandidateEngineeringMetrics | None,
    *,
    eligible: bool = True,
    lifecycle_cost: float | None = None,
) -> Any:
    return SimpleNamespace(
        scenario=SimpleNamespace(scenario_id=candidate_id),
        evaluation=SimpleNamespace(
            assessment=SimpleNamespace(eligible=eligible, metrics=metrics),
            lifecycle_cost=lifecycle_cost,
        ),
    )


def _term(
    metric: str,
    *,
    direction: MetricDirection = MetricDirection.MINIMISE,
    weight: str = "1",
    reference_min: str = "0",
    reference_max: str = "5000",
) -> MetricTerm:
    return MetricTerm(
        metric=metric,
        direction=direction,
        weight=weight,
        reference_min=reference_min,
        reference_max=reference_max,
    )


def _definition(*terms: MetricTerm) -> ProfileDefinition:
    return ProfileDefinition(
        profile_id=ProfileId.BALANCED,
        version="1",
        policy_mode=ProfilePolicyMode.UNIFIED_ENGINEERING,
        terms=list(terms),
    )


# --- The C2 fixture, reproduced from first principles ---------------------------


def test_reproduces_the_c2_fixture_contribution_exactly() -> None:
    fixture = json.loads(_C2_FIXTURE.read_text(encoding="utf-8"))
    expected = fixture["scoring_explanation"]["candidates"][0]["contributions"][0]

    explanation = explain_candidates(
        [
            _candidate(
                "SCN-001",
                _metrics(affected_parcel_row_area_m2=expected["raw_value"]),
            )
        ],
        _definition(
            _term(
                expected["metric"],
                weight=str(expected["weight"]),
                reference_min=str(expected["reference_min"]),
                reference_max=str(expected["reference_max"]),
            )
        ),
    )

    produced = explanation.candidates[0].contributions[0].model_dump(mode="json")
    assert produced == expected


def test_output_conforms_to_the_c2_model() -> None:
    # The C2 pydantic models are the contract: the committed schema is exported
    # from them and test_contract_pack.py holds the two together.
    explanation = explain_candidates(
        [_candidate("SCN-001", _metrics())],
        _definition(_term("affected_parcel_row_area_m2")),
    )
    dumped = explanation.model_dump(mode="json")
    assert ScoringExplanation.model_validate(dumped) == explanation


# --- Normalisation against fixed ranges ------------------------------------------


def test_minimise_and_maximise_point_the_right_way() -> None:
    minimise = _term("affected_parcel_row_area_m2", reference_max="100")
    maximise = _term(
        "voltage_margin_pu", direction=MetricDirection.MAXIMISE, reference_max="0.1"
    )

    assert normalise(0.0, minimise) == pytest.approx(1.0)
    assert normalise(100.0, minimise) == pytest.approx(0.0)
    assert normalise(0.1, maximise) == pytest.approx(1.0)
    assert normalise(0.0, maximise) == pytest.approx(0.0)


def test_values_outside_the_reference_range_are_clamped() -> None:
    term = _term("affected_parcel_row_area_m2", reference_max="100")

    assert normalise(-50.0, term) == 1.0
    assert normalise(10_000.0, term) == 0.0


def test_removing_a_loser_does_not_change_anyone_elses_score() -> None:
    # The reason ranges are fixed rather than taken from the cohort. Under a cohort
    # min-max, dropping the worst candidate moves the bottom of the range and so
    # rescores every survivor; WP3-3's remove-a-loser invariant forbids that.
    definition = _definition(_term("affected_parcel_row_area_m2"))
    full = explain_candidates(
        [
            _candidate("A", _metrics(affected_parcel_row_area_m2=1000.0)),
            _candidate("B", _metrics(affected_parcel_row_area_m2=2000.0)),
            _candidate("LOSER", _metrics(affected_parcel_row_area_m2=4900.0)),
        ],
        definition,
    )
    without_loser = explain_candidates(
        [
            _candidate("A", _metrics(affected_parcel_row_area_m2=1000.0)),
            _candidate("B", _metrics(affected_parcel_row_area_m2=2000.0)),
        ],
        definition,
    )

    def scores(explanation: ScoringExplanation) -> dict[str, float | None]:
        return {item.candidate_id: item.total_score for item in explanation.candidates}

    assert scores(without_loser) == {
        key: value for key, value in scores(full).items() if key != "LOSER"
    }


# --- Weights, totals and ranking ----------------------------------------------------


def test_total_is_the_sum_of_weighted_contributions() -> None:
    explanation = explain_candidates(
        [
            _candidate(
                "A",
                _metrics(
                    affected_parcel_row_area_m2=1250.0,
                    environmental_overlap_m2=2500.0,
                ),
            )
        ],
        _definition(
            _term("affected_parcel_row_area_m2", weight="0.2"),
            _term("environmental_overlap_m2", weight="0.3"),
        ),
    )

    candidate = explanation.candidates[0]
    assert [item.weighted_contribution for item in candidate.contributions] == [
        pytest.approx(0.15),
        pytest.approx(0.15),
    ]
    assert candidate.total_score == pytest.approx(0.30)


def test_ranks_highest_total_first_with_ties_broken_by_candidate_id() -> None:
    definition = _definition(_term("affected_parcel_row_area_m2"))
    explanation = explain_candidates(
        [
            _candidate("C", _metrics(affected_parcel_row_area_m2=1000.0)),
            _candidate("B", _metrics(affected_parcel_row_area_m2=500.0)),
            _candidate("A", _metrics(affected_parcel_row_area_m2=1000.0)),
        ],
        definition,
    )

    ranks = {item.candidate_id: item.rank for item in explanation.candidates}
    assert ranks == {"B": 1, "A": 2, "C": 3}


def test_ineligible_candidates_are_explained_but_never_ranked_or_scored() -> None:
    # Evidence is still shown, so a reviewer can see what disqualified candidates
    # looked like, but they take no score and no rank.
    explanation = explain_candidates(
        [
            _candidate("A", _metrics(affected_parcel_row_area_m2=100.0)),
            _candidate(
                "X",
                _metrics(affected_parcel_row_area_m2=0.0),
                eligible=False,
            ),
        ],
        _definition(_term("affected_parcel_row_area_m2")),
    )

    by_id = {item.candidate_id: item for item in explanation.candidates}
    assert by_id["X"].contributions[0].raw_value == 0.0
    assert by_id["X"].total_score is None
    assert by_id["X"].rank is None
    assert by_id["A"].rank == 1


def test_missing_evidence_is_null_never_zero() -> None:
    # A candidate whose metrics failed to extract must not score as if it had zero
    # land impact, which would make it look like the best candidate.
    explanation = explain_candidates(
        [_candidate("A", None, eligible=True)],
        _definition(_term("affected_parcel_row_area_m2")),
    )

    contribution = explanation.candidates[0].contributions[0]
    assert contribution.raw_value is None
    assert contribution.normalised_value is None
    assert contribution.weighted_contribution is None
    assert explanation.candidates[0].total_score is None
    assert explanation.candidates[0].rank is None


def test_lifecycle_cost_is_explained_from_the_evaluation() -> None:
    explanation = explain_candidates(
        [_candidate("A", _metrics(), lifecycle_cost=2_500_000.0)],
        _definition(_term("lifecycle_cost", reference_max="5000000")),
    )

    assert explanation.candidates[0].contributions[0].normalised_value == (
        pytest.approx(0.5)
    )


# --- Definition defects fail loudly -------------------------------------------------


def test_an_unknown_metric_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown metric"):
        explain_candidates(
            [_candidate("A", _metrics())], _definition(_term("not_a_metric"))
        )


def test_an_empty_reference_range_is_rejected() -> None:
    with pytest.raises(ValueError, match="max greater than min"):
        explain_candidates(
            [_candidate("A", _metrics())],
            _definition(
                _term(
                    "affected_parcel_row_area_m2",
                    reference_min="100",
                    reference_max="100",
                )
            ),
        )


def test_known_metrics_track_the_engineering_metric_fields() -> None:
    # Drift guard: a metric added to CandidateEngineeringMetrics, or renamed, must
    # be reflected here, or a profile naming it would be rejected as unknown.
    fields = {field.name for field in dataclasses.fields(CandidateEngineeringMetrics)}
    assert KNOWN_METRICS == fields | {"lifecycle_cost"}


# --- The response hook --------------------------------------------------------------


def _context(profile: ProfileResolution) -> ResponseContext:
    return ResponseContext(
        profile=profile,
        search=SEARCH_DISABLED,
        profiles_enabled=True,
        search_enabled=False,
    )


def _workflow(*candidates: Any) -> Any:
    return SimpleNamespace(candidates=candidates)


def test_the_block_stays_absent_for_v0() -> None:
    result = build_scoring_explanation(
        _workflow(_candidate("A", _metrics())),
        _context(V0_PROFILE_RESOLUTION),
        definitions=lambda profile_id, version: _definition(
            _term("affected_parcel_row_area_m2")
        ),
    )
    assert result is None


def test_the_block_stays_absent_until_a_registry_supplies_a_definition() -> None:
    # Today's state: WP3-4 has not landed a registry, so no profile has terms.
    result = build_scoring_explanation(
        _workflow(_candidate("A", _metrics())),
        _context(ProfileResolution(profile_id="balanced", profile_version="1")),
    )
    assert result is None


def test_the_block_is_published_once_a_definition_is_available() -> None:
    seen: list[tuple[str, str]] = []

    def lookup(profile_id: str, version: str) -> ProfileDefinition:
        seen.append((profile_id, version))
        return _definition(_term("affected_parcel_row_area_m2"))

    result = build_scoring_explanation(
        _workflow(_candidate("A", _metrics(affected_parcel_row_area_m2=1250.0))),
        _context(ProfileResolution(profile_id="balanced", profile_version="1")),
        definitions=lookup,
    )

    assert seen == [("balanced", "1")]
    assert result is not None
    assert result.profile_id == "balanced"
    assert result.candidates[0].rank == 1
