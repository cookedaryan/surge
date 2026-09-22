"""Profile definition registry. Owned by L3 (WP3-4).

Four versioned definitions, one per allow-listed profile, in the C6 format and with
the structure draft 0.6 §7 requires of each profile. **Every value here is a
placeholder until FRZ-1**: weights, reference ranges and tolerances were not read
off any golden result, which is the §4.3 anti-overfitting rule, and they will be
replaced wholesale by the frozen values. What is not a placeholder is the shape:

- **Minimum Cost** runs cost-aware, with modelled lifecycle cost as its only
  weighted term. Engineering enters as feasibility plus a deterministic tie-break.
- **Minimum Land Impact** puts ``affected_parcel_row_area_m2`` first with a
  tolerance band; parcel count and owner interactions rank second and third, so
  they break ties only inside that band (R2-C6). Recording the lexicographic
  structure is this task; applying it to selection is WP3-3.
- **Minimum Environmental Impact** puts unique environmental overlap first, with
  soft-constraint overlap as the applicable secondary metric.
- **Balanced** carries non-zero physical, spatial, infrastructure and electrical
  terms **and** non-zero land, environment and lifecycle-cost terms (R2-C4), so its
  regret envelope on those metrics is a design property rather than luck.

A metric name is the evidence field it reads, the vocabulary the scoring
explanation (WP2-7) validates against. The registry checks itself at import: a
definition that names an unknown metric, or leaves an allow-listed profile version
without a definition, fails loudly before any request is served.
"""

from app.contracts.codes import MetricDirection, ProfilePolicyMode
from app.contracts.profiles import (
    ALLOWED_PROFILE_VERSIONS,
    MetricTerm,
    ProfileDefinition,
    ProfileDefinitionSet,
    ProfileId,
    definition_set_hash,
)
from app.optimisation.profiles.metrics import KNOWN_METRICS

_MINIMISE = MetricDirection.MINIMISE
_MAXIMISE = MetricDirection.MAXIMISE

# Placeholder reference ranges, one per metric, shared by every profile that scores
# it so the same raw value normalises identically everywhere. Round numbers chosen
# to bracket plausible demo values, not fitted to any result.
_RANGES: dict[str, tuple[str, str]] = {
    "total_route_length_m": ("0", "100000"),
    "total_traversal_cost": ("0", "1000000"),
    "affected_parcel_row_area_m2": ("0", "50000"),
    "affected_parcel_count": ("0", "100"),
    "owner_interaction_count": ("0", "100"),
    "environmental_overlap_m2": ("0", "50000"),
    "soft_constraint_overlap_length_m": ("0", "10000"),
    "physical_pole_count": ("0", "2000"),
    "total_active_loss_mw": ("0", "5"),
    "maximum_loading_percent": ("0", "100"),
    "voltage_margin_pu": ("0", "0.1"),
    "lifecycle_cost": ("0", "1000000000"),
}

# Higher is better only for voltage margin; every other metric is a cost or impact.
_DIRECTIONS: dict[str, MetricDirection] = {"voltage_margin_pu": _MAXIMISE}

_ENGINEERING_TIE_BREAKS = ["total_route_length_m", "candidate_id"]


def _term(
    metric: str,
    weight: str,
    *,
    lexicographic_rank: int | None = None,
    tolerance: str | None = None,
) -> MetricTerm:
    reference_min, reference_max = _RANGES[metric]
    return MetricTerm(
        metric=metric,
        direction=_DIRECTIONS.get(metric, _MINIMISE),
        weight=weight,
        reference_min=reference_min,
        reference_max=reference_max,
        lexicographic_rank=lexicographic_rank,
        tolerance=tolerance,
    )


PLACEHOLDER_DEFINITIONS = ProfileDefinitionSet(
    definitions=[
        ProfileDefinition(
            profile_id=ProfileId.MINIMUM_COST,
            version="1",
            policy_mode=ProfilePolicyMode.COST_AWARE,
            terms=[_term("lifecycle_cost", "1")],
            tie_breaks=_ENGINEERING_TIE_BREAKS,
        ),
        ProfileDefinition(
            profile_id=ProfileId.MINIMUM_LAND_IMPACT,
            version="1",
            policy_mode=ProfilePolicyMode.UNIFIED_ENGINEERING,
            terms=[
                _term(
                    "affected_parcel_row_area_m2",
                    "0.6",
                    lexicographic_rank=1,
                    tolerance="25",
                ),
                _term("affected_parcel_count", "0.25", lexicographic_rank=2),
                _term("owner_interaction_count", "0.15", lexicographic_rank=3),
            ],
            tie_breaks=_ENGINEERING_TIE_BREAKS,
        ),
        ProfileDefinition(
            profile_id=ProfileId.MINIMUM_ENVIRONMENTAL_IMPACT,
            version="1",
            policy_mode=ProfilePolicyMode.UNIFIED_ENGINEERING,
            terms=[
                _term("environmental_overlap_m2", "0.7", lexicographic_rank=1),
                _term("soft_constraint_overlap_length_m", "0.3", lexicographic_rank=2),
            ],
            tie_breaks=_ENGINEERING_TIE_BREAKS,
        ),
        ProfileDefinition(
            profile_id=ProfileId.BALANCED,
            version="1",
            policy_mode=ProfilePolicyMode.UNIFIED_ENGINEERING,
            terms=[
                # Physical, spatial, infrastructure and electrical groups ...
                _term("total_route_length_m", "0.1"),
                _term("total_traversal_cost", "0.1"),
                _term("physical_pole_count", "0.1"),
                _term("total_active_loss_mw", "0.1"),
                _term("maximum_loading_percent", "0.05"),
                _term("voltage_margin_pu", "0.05"),
                # ... plus the land, environment and cost terms R2-C4 requires.
                _term("affected_parcel_row_area_m2", "0.15"),
                _term("environmental_overlap_m2", "0.15"),
                _term("lifecycle_cost", "0.2"),
            ],
            tie_breaks=_ENGINEERING_TIE_BREAKS,
        ),
    ]
)

_BY_KEY: dict[tuple[str, str], ProfileDefinition] = {
    (definition.profile_id.value, definition.version): definition
    for definition in PLACEHOLDER_DEFINITIONS.definitions
}


def definition_for(profile_id: str, version: str) -> ProfileDefinition | None:
    """The definition for an allow-listed profile version, or ``None``.

    ``None`` is not a fallback: callers must treat it as "no such definition", and
    resolution refuses unknown profiles before any lookup (WP3-1). Nothing here ever
    substitutes Balanced for a profile it does not know.
    """
    return _BY_KEY.get((profile_id, version))


def registry_hash() -> str:
    """The C6 definition hash of this registry: the Python half of the handshake."""
    return definition_set_hash(PLACEHOLDER_DEFINITIONS)


def _check_registry() -> None:
    expected = {
        (profile_id.value, version)
        for profile_id, versions in ALLOWED_PROFILE_VERSIONS.items()
        for version in versions
    }
    if len(_BY_KEY) != len(PLACEHOLDER_DEFINITIONS.definitions):
        raise RuntimeError("Profile registry holds a duplicate profile version")
    if set(_BY_KEY) != expected:
        raise RuntimeError(
            "Profile registry does not match the C6 allow-list: "
            f"missing {sorted(expected - set(_BY_KEY))}, "
            f"unexpected {sorted(set(_BY_KEY) - expected)}"
        )
    for definition in PLACEHOLDER_DEFINITIONS.definitions:
        for term in definition.terms:
            if term.metric not in KNOWN_METRICS:
                raise RuntimeError(
                    f"{definition.profile_id.value} names unknown metric {term.metric}"
                )


_check_registry()
