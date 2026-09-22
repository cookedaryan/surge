"""The metric vocabulary profile terms may name. Owned by L3 (WP2-7, WP3-4).

A metric name in a profile term is the field name of the evidence it reads, so the
profile registry, the scoring explanation and the evidence record share one
vocabulary and nothing is registered in the V0 ``ScoringMetric`` enum. Registering
there would change the V0 response's key set, which the V0 goldens forbid.

Kept apart from both the registry and the explanation so that each can import it
without importing the other.
"""

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
