"""Profile-driven candidate ordering and winner selection. Owned by L3 (WP3-3).

Exit evidence for WP3-3: no cohort min-max normalisation, and removing any
non-winner leaves every profile's winner unchanged.

Both follow from one rule: **a candidate's ordering key is computed from that
candidate's own evidence and the profile definition, and nothing else.** When every
key is independent of the cohort, the order among any two candidates cannot depend
on which other candidates are present, so deleting a loser cannot promote anyone
past the winner.

- **Weighted profiles** order by total weighted score against the profile's fixed
  reference ranges (WP2-7), highest first. A cohort min-max would break the rule:
  removing the worst candidate moves the bottom of the range and rescores everyone.
- **Lexicographic profiles** (any term carries a ``lexicographic_rank``) compare
  terms in rank order. A term's tolerance is a band on a **fixed grid** anchored at
  the reference minimum, so two values in the same bucket tie on that term and the
  next rank decides. A band anchored to the cohort's best value would break the
  rule: removing the candidate that set the best value moves the band, admits a
  candidate that was outside it, and that candidate can then win on a lower rank.
  The cost of a fixed grid is a boundary effect - two values either side of a bucket
  edge differ on the primary even when they are close - and it is the price of the
  invariant.
- **Tie-breaks** follow the terms, in the definition's order; ``candidate_id`` sorts
  ascending and guarantees a total order.

A candidate is selectable only if it is eligible and supplies every metric its key
reads. Missing evidence never wins by default.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

from app.contracts.codes import MetricDirection
from app.contracts.profiles import MetricTerm, ProfileDefinition
from app.optimisation.engineering_metric_models import CandidateEngineeringMetrics
from app.optimisation.profiles.metrics import direction_of, raw_value

CANDIDATE_ID = "candidate_id"

OrderingKey = tuple[Decimal | str, ...]


@dataclass(frozen=True)
class CandidateEvidence:
    """What a profile may read about one candidate: identity and its own evidence."""

    candidate_id: str
    eligible: bool
    metrics: CandidateEngineeringMetrics | None
    lifecycle_cost: float | None


def is_lexicographic(definition: ProfileDefinition) -> bool:
    return any(term.lexicographic_rank is not None for term in definition.terms)


def ordering_key(
    evidence: CandidateEvidence, definition: ProfileDefinition
) -> OrderingKey | None:
    """The candidate's position under ``definition``; lower sorts first.

    ``None`` when the candidate cannot be ordered: ineligible, or missing a metric
    the key reads. Reads ``evidence`` and ``definition`` only, never the cohort.
    """
    if not evidence.eligible:
        return None
    if is_lexicographic(definition):
        head = _lexicographic_part(evidence, definition)
    else:
        head = _weighted_part(evidence, definition)
    if head is None:
        return None
    tail = _tie_break_part(evidence, definition)
    if tail is None:
        return None
    return head + tail


def rank_candidates(
    candidates: Sequence[CandidateEvidence], definition: ProfileDefinition
) -> dict[str, int]:
    """Ranks for every selectable candidate, 1 = winner. Others are absent."""
    keyed = [
        (key, item.candidate_id)
        for item in candidates
        if (key := ordering_key(item, definition)) is not None
    ]
    ordered = sorted(keyed, key=lambda pair: pair[0])
    return {candidate_id: rank for rank, (_, candidate_id) in enumerate(ordered, 1)}


def select_winner(
    candidates: Sequence[CandidateEvidence], definition: ProfileDefinition
) -> str | None:
    ranks = rank_candidates(candidates, definition)
    return next((cid for cid, rank in ranks.items() if rank == 1), None)


def weighted_total(
    evidence: CandidateEvidence, definition: ProfileDefinition
) -> Decimal | None:
    """Sum of normalised value x weight over the terms, or ``None`` if incomplete."""
    total = Decimal(0)
    for term in definition.terms:
        value = _raw(evidence, term.metric)
        if value is None:
            return None
        total += normalise(value, term) * Decimal(term.weight)
    return total


def normalise(value: Decimal, term: MetricTerm) -> Decimal:
    """Map a raw value onto [0, 1] against the term's fixed range; one is best."""
    minimum = Decimal(term.reference_min)
    maximum = Decimal(term.reference_max)
    span = maximum - minimum
    if term.direction == MetricDirection.MINIMISE:
        normalised = (maximum - value) / span
    else:
        normalised = (value - minimum) / span
    return max(Decimal(0), min(Decimal(1), normalised))


def _weighted_part(
    evidence: CandidateEvidence, definition: ProfileDefinition
) -> OrderingKey | None:
    total = weighted_total(evidence, definition)
    # Highest total first, so negate for an ascending sort.
    return None if total is None else (-total,)


def _lexicographic_part(
    evidence: CandidateEvidence, definition: ProfileDefinition
) -> OrderingKey | None:
    ranked = sorted(
        (term for term in definition.terms if term.lexicographic_rank is not None),
        key=lambda term: term.lexicographic_rank or 0,
    )
    parts: list[Decimal | str] = []
    for term in ranked:
        value = _raw(evidence, term.metric)
        if value is None:
            return None
        parts.append(_bucketed_badness(value, term))
    return tuple(parts)


def _bucketed_badness(value: Decimal, term: MetricTerm) -> Decimal:
    """Distance from the best end of the fixed range, bucketed by the tolerance.

    Lower is better for both directions. The bucket grid is anchored at the fixed
    reference bound, never at a cohort value, which is what keeps the key
    independent of the cohort.
    """
    if term.direction == MetricDirection.MINIMISE:
        badness = value - Decimal(term.reference_min)
    else:
        badness = Decimal(term.reference_max) - value
    if term.tolerance is None:
        return badness
    tolerance = Decimal(term.tolerance)
    if tolerance == 0:
        return badness
    return (badness / tolerance).to_integral_value(rounding=ROUND_FLOOR)


def _tie_break_part(
    evidence: CandidateEvidence, definition: ProfileDefinition
) -> OrderingKey | None:
    parts: list[Decimal | str] = []
    tie_breaks = list(definition.tie_breaks)
    # A total order needs a final unique key even when a definition omits it.
    if CANDIDATE_ID not in tie_breaks:
        tie_breaks.append(CANDIDATE_ID)
    for tie_break in tie_breaks:
        if tie_break == CANDIDATE_ID:
            parts.append(evidence.candidate_id)
            continue
        value = _raw(evidence, tie_break)
        if value is None:
            return None
        if direction_of(tie_break) == MetricDirection.MAXIMISE:
            value = -value
        parts.append(value)
    return tuple(parts)


def _raw(evidence: CandidateEvidence, metric: str) -> Decimal | None:
    value = raw_value(metric, evidence.metrics, evidence.lifecycle_cost)
    # The shortest round-tripping decimal, not the float's binary expansion.
    return None if value is None else Decimal(repr(value))
