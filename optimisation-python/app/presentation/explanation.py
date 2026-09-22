"""Scoring explanation for the V1 response. Owned by L3 (WP2-7).

Publishes why candidates ranked as they did: for each candidate and each metric a
profile scores, the raw value, the fixed reference range, the normalised value, the
weight and the weighted contribution, matching the C2 ``scoring_explanation`` shape.

Normalisation is against the profile's **fixed** reference range, never the cohort's
own minimum and maximum. A cohort min-max would let removing a losing candidate
change every other candidate's score, which WP3-3's remove-a-loser invariant forbids.

The block stays absent for V0: without a resolved profile there is no set of terms
to explain against. Definitions come from the WP3-4 registry. Resolution still refuses
every explicit profile until a profile drives winner selection (WP3-3) and invalid
inputs map to stable errors (WP3-1), so today no request reaches this with a profile.
"""

from collections.abc import Callable, Sequence
from decimal import Decimal

from app.contracts.profiles import MetricTerm, ProfileDefinition
from app.contracts.resolution import ResponseContext
from app.contracts.response import (
    CandidateExplanation,
    MetricContribution,
    ScoringExplanation,
)
from app.optimisation.profiles import registry, selection
from app.optimisation.profiles.metrics import KNOWN_METRICS, raw_value
from app.optimisation.workflow_models import (
    CandidateWorkflowResult,
    OptimisationWorkflowResult,
)

DefinitionLookup = Callable[[str, str], ProfileDefinition | None]

# The metric vocabulary lives in profiles.metrics so the registry can share it
# without importing this module. Re-exported here for callers of WP2-7.
__all__ = [
    "KNOWN_METRICS",
    "build_scoring_explanation",
    "explain_candidates",
    "normalise",
]


def build_scoring_explanation(
    workflow_result: OptimisationWorkflowResult,
    context: ResponseContext,
    *,
    definitions: DefinitionLookup = registry.definition_for,
) -> ScoringExplanation | None:
    profile = context.profile
    if profile.profile_id is None or profile.profile_version is None:
        return None
    definition = definitions(profile.profile_id, profile.profile_version)
    if definition is None:
        return None
    return explain_candidates(workflow_result.candidates, definition)


def explain_candidates(
    candidates: Sequence[CandidateWorkflowResult],
    definition: ProfileDefinition,
) -> ScoringExplanation:
    """Explain every candidate against one profile definition.

    Ranks are the order profile selection (WP3-3) puts candidates in, so the block
    explains the ranking that actually happened. For a weighted profile that is
    highest total first; for a lexicographic profile it follows the ranked terms and
    their tolerance bands, so a lower ``total_score`` can legitimately rank higher.
    Ties fall to the definition's ``tie_breaks`` and finally to candidate ID.
    """
    _validate_terms(definition.terms)

    evidence = [_evidence(candidate) for candidate in candidates]
    explained = [_explain_candidate(item, definition.terms) for item in evidence]
    ranks = selection.rank_candidates(evidence, definition)

    return ScoringExplanation(
        profile_id=definition.profile_id.value,
        # Reference ranges are frozen per definition version, so the version that
        # fixed them is the version of the ranges.
        reference_ranges_version=definition.version,
        candidates=[
            item.model_copy(update={"rank": ranks.get(item.candidate_id)})
            for item in explained
        ],
        # Generation penalties are routing inputs, shown apart from ranking evidence
        # (WP6A-2). This block publishes ranking evidence only.
        generation_penalties=[],
    )


def normalise(raw_value: float, term: MetricTerm) -> float:
    """Map a raw value onto [0, 1] against the term's fixed reference range.

    One is best. Values outside the range are clamped rather than extrapolated, so a
    single outlier cannot dominate a weighted sum. Arithmetic is Decimal, converting
    to float only here at the boundary: the profile stores weights and ranges as
    decimal strings so hashing is exact, and binary floats would publish values such
    as 0.15000000000000002 that disagree with a recomputation from their own inputs.
    """
    return float(selection.normalise(_decimal(raw_value), term))


def _decimal(value: float) -> Decimal:
    """The float's shortest round-tripping decimal, not its full binary expansion."""
    return Decimal(repr(value))


def _evidence(candidate: CandidateWorkflowResult) -> selection.CandidateEvidence:
    evaluation = candidate.evaluation
    return selection.CandidateEvidence(
        candidate_id=candidate.scenario.scenario_id,
        eligible=evaluation is not None and evaluation.assessment.eligible,
        metrics=evaluation.assessment.metrics if evaluation is not None else None,
        lifecycle_cost=evaluation.lifecycle_cost if evaluation is not None else None,
    )


def _explain_candidate(
    evidence: selection.CandidateEvidence,
    terms: Sequence[MetricTerm],
) -> CandidateExplanation:
    scored = [
        _contribution(
            term,
            raw_value(term.metric, evidence.metrics, evidence.lifecycle_cost),
        )
        for term in terms
    ]
    contributions = [contribution for contribution, _ in scored]
    weighted = [value for _, value in scored]
    complete = evidence.eligible and all(value is not None for value in weighted)
    total_score = (
        float(sum((value for value in weighted if value is not None), Decimal(0)))
        if complete
        else None
    )
    return CandidateExplanation(
        candidate_id=evidence.candidate_id,
        eligible=evidence.eligible,
        total_score=total_score,
        contributions=contributions,
    )


def _contribution(
    term: MetricTerm, raw_value: float | None
) -> tuple[MetricContribution, Decimal | None]:
    """One published contribution, plus its exact weighted value for the total."""
    weight = Decimal(term.weight)
    normalised = (
        selection.normalise(_decimal(raw_value), term)
        if raw_value is not None
        else None
    )
    weighted = normalised * weight if normalised is not None else None
    contribution = MetricContribution(
        metric=term.metric,
        direction=term.direction,
        raw_value=raw_value,
        reference_min=float(Decimal(term.reference_min)),
        reference_max=float(Decimal(term.reference_max)),
        normalised_value=float(normalised) if normalised is not None else None,
        weight=float(weight),
        weighted_contribution=float(weighted) if weighted is not None else None,
    )
    return contribution, weighted


def _validate_terms(terms: Sequence[MetricTerm]) -> None:
    """Reject a definition that cannot be explained, before anything is scored.

    An unknown metric name or an empty reference range is a defect in the profile
    definition, not a property of a candidate, so it fails loudly here rather than
    surfacing as a quietly missing contribution.
    """
    for term in terms:
        if term.metric not in KNOWN_METRICS:
            raise ValueError(f"Profile term names an unknown metric: {term.metric}")
        if Decimal(term.reference_max) <= Decimal(term.reference_min):
            raise ValueError(
                f"Reference range for {term.metric} must have max greater than min"
            )
