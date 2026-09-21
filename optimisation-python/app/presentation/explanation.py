"""Scoring explanation for the V1 response. Owned by L3 (WP2-7).

Publishes why candidates ranked as they did: for each candidate and each metric a
profile scores, the raw value, the fixed reference range, the normalised value, the
weight and the weighted contribution, matching the C2 ``scoring_explanation`` shape.

Normalisation is against the profile's **fixed** reference range, never the cohort's
own minimum and maximum. A cohort min-max would let removing a losing candidate
change every other candidate's score, which WP3-3's remove-a-loser invariant forbids.

The block stays absent for V0: without a resolved profile there is no set of terms
to explain against. Until WP3-4 lands a profile registry, no definition is available
for any profile, so the hook returns ``None`` on every request the product can make
today. WP3-4 plugs its registry in through ``definitions``.
"""

from collections.abc import Callable, Sequence
from decimal import Decimal

from app.contracts.codes import MetricDirection
from app.contracts.profiles import MetricTerm, ProfileDefinition
from app.contracts.resolution import ResponseContext
from app.contracts.response import (
    CandidateExplanation,
    MetricContribution,
    ScoringExplanation,
)
from app.optimisation.engineering_metric_models import CandidateEngineeringMetrics
from app.optimisation.workflow_models import (
    CandidateWorkflowResult,
    OptimisationWorkflowResult,
)

DefinitionLookup = Callable[[str, str], ProfileDefinition | None]

# A metric name in a profile term is the field name of the evidence it reads, so the
# explanation, the metric registry and the evidence record share one vocabulary and
# nothing has to be registered in the V0 ``ScoringMetric`` enum. Registering there
# would change the V0 response's key set, which the V0 goldens forbid.
_ENGINEERING_METRICS: frozenset[str] = frozenset(
    {
        "total_route_length_m",
        "total_traversal_cost",
        "affected_parcel_count",
        "owner_interaction_count",
        "road_crossing_count",
        "soft_constraint_overlap_length_m",
        "environmental_overlap_m2",
        "affected_parcel_row_area_m2",
        "physical_pole_count",
        "total_active_loss_mw",
        "maximum_loading_percent",
        "voltage_margin_pu",
    }
)
_LIFECYCLE_COST = "lifecycle_cost"

KNOWN_METRICS: frozenset[str] = _ENGINEERING_METRICS | {_LIFECYCLE_COST}


def _no_registered_definitions(profile_id: str, version: str) -> None:
    """Stand-in until WP3-4's registry exists: no profile has a definition yet."""
    return None


def build_scoring_explanation(
    workflow_result: OptimisationWorkflowResult,
    context: ResponseContext,
    *,
    definitions: DefinitionLookup = _no_registered_definitions,
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

    Eligible candidates with a complete score are ranked by total score, highest
    first. Ties are broken by candidate ID so the ranking is deterministic; the
    profile's own ``tie_breaks`` are policy values that FRZ-1 freezes and that
    WP3-3 applies.
    """
    _validate_terms(definition.terms)

    explained = [
        _explain_candidate(candidate, definition.terms) for candidate in candidates
    ]
    ranked_ids = [
        item.candidate_id
        for item in sorted(
            (
                item
                for item in explained
                if item.eligible and item.total_score is not None
            ),
            key=lambda item: (-(item.total_score or 0.0), item.candidate_id),
        )
    ]
    ranks = {candidate_id: rank for rank, candidate_id in enumerate(ranked_ids, 1)}

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
    single outlier cannot dominate a weighted sum.
    """
    return float(_normalise(_decimal(raw_value), term))


def _normalise(raw_value: Decimal, term: MetricTerm) -> Decimal:
    # Decimal throughout, converting to float only at the response boundary. The
    # profile stores weights and ranges as decimal strings so that hashing is exact;
    # doing the arithmetic in binary floats would publish contributions such as
    # 0.15000000000000002 that disagree with a recomputation from their own inputs,
    # and the G0 claim is that every recommendation reproduces from its evidence.
    minimum = Decimal(term.reference_min)
    maximum = Decimal(term.reference_max)
    span = maximum - minimum
    if term.direction == MetricDirection.MINIMISE:
        normalised = (maximum - raw_value) / span
    else:
        normalised = (raw_value - minimum) / span
    return max(Decimal(0), min(Decimal(1), normalised))


def _decimal(value: float) -> Decimal:
    """The float's shortest round-tripping decimal, not its full binary expansion."""
    return Decimal(repr(value))


def _explain_candidate(
    candidate: CandidateWorkflowResult,
    terms: Sequence[MetricTerm],
) -> CandidateExplanation:
    evaluation = candidate.evaluation
    eligible = evaluation is not None and evaluation.assessment.eligible
    metrics = evaluation.assessment.metrics if evaluation is not None else None
    lifecycle_cost = evaluation.lifecycle_cost if evaluation is not None else None

    scored = [
        _contribution(term, _raw_value(term.metric, metrics, lifecycle_cost))
        for term in terms
    ]
    contributions = [contribution for contribution, _ in scored]
    weighted = [value for _, value in scored]
    complete = eligible and all(value is not None for value in weighted)
    total_score = (
        float(sum((value for value in weighted if value is not None), Decimal(0)))
        if complete
        else None
    )
    return CandidateExplanation(
        candidate_id=candidate.scenario.scenario_id,
        eligible=eligible,
        total_score=total_score,
        contributions=contributions,
    )


def _contribution(
    term: MetricTerm, raw_value: float | None
) -> tuple[MetricContribution, Decimal | None]:
    """One published contribution, plus its exact weighted value for the total."""
    weight = Decimal(term.weight)
    normalised = (
        _normalise(_decimal(raw_value), term) if raw_value is not None else None
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


def _raw_value(
    metric: str,
    metrics: CandidateEngineeringMetrics | None,
    lifecycle_cost: float | None,
) -> float | None:
    """The candidate's value for ``metric``, or ``None`` when it has none.

    ``None`` means the candidate could not supply the evidence, for example because
    its metrics failed to extract. It is not a zero and is never scored as one.
    """
    if metric == _LIFECYCLE_COST:
        return lifecycle_cost
    if metrics is None:
        return None
    return float(getattr(metrics, metric))


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
