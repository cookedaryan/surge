"""The metric vocabulary profile terms may name. Owned by L3 (WP2-7, WP3-4, WP3-3).

A metric name in a profile term is the field name of the evidence it reads, so the
profile registry, the scoring explanation, profile selection and the evidence record
share one vocabulary and nothing is registered in the V0 ``ScoringMetric`` enum.
Registering there would change the V0 response's key set, which the V0 goldens
forbid.

Kept apart from the registry, the explanation and selection so that each can import
it without importing the others.
"""

from app.contracts.codes import MetricDirection
from app.optimisation.engineering_metric_models import CandidateEngineeringMetrics

ENGINEERING_METRICS: frozenset[str] = frozenset(
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
LIFECYCLE_COST = "lifecycle_cost"

KNOWN_METRICS: frozenset[str] = ENGINEERING_METRICS | {LIFECYCLE_COST}

# Which way is better, per metric. One source, so a metric used as a scored term in
# one profile and as a tie-break in another is judged the same way in both. Higher
# is better only for voltage margin; every other metric is a cost or an impact.
_MAXIMISED: frozenset[str] = frozenset({"voltage_margin_pu"})


def direction_of(metric: str) -> MetricDirection:
    if metric not in KNOWN_METRICS:
        raise ValueError(f"Unknown metric: {metric}")
    if metric in _MAXIMISED:
        return MetricDirection.MAXIMISE
    return MetricDirection.MINIMISE


def raw_value(
    metric: str,
    metrics: CandidateEngineeringMetrics | None,
    lifecycle_cost: float | None,
) -> float | None:
    """A candidate's value for ``metric``, or ``None`` when it has none.

    ``None`` means the candidate could not supply the evidence, for example because
    its metrics failed to extract. It is not a zero and is never scored as one.
    """
    if metric == LIFECYCLE_COST:
        return lifecycle_cost
    if metrics is None:
        return None
    return float(getattr(metrics, metric))
