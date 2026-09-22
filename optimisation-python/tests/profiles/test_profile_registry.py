"""WP3-4: the profile registry holds the §7 structure, with placeholder values.

Exit evidence: four versioned placeholder definitions with the draft 0.6 §7
structure — Balanced has non-zero land, environment and cost terms; Minimum Land
uses a lexicographic tolerance band. The structural rules are asserted here so a
FRZ-1 value change cannot quietly break the shape the claim depends on.
"""

from decimal import Decimal

from app.contracts.codes import ProfilePolicyMode
from app.contracts.profiles import (
    ALLOWED_PROFILE_VERSIONS,
    ProfileDefinition,
    ProfileDefinitionSet,
    ProfileId,
    definition_set_hash,
)
from app.optimisation.profiles.metrics import KNOWN_METRICS
from app.optimisation.profiles.registry import (
    PLACEHOLDER_DEFINITIONS,
    definition_for,
    registry_hash,
)
from app.presentation.explanation import explain_candidates

# The four scoring groups, as the V0 scorer groups the same quantities. Balanced
# must carry a non-zero term in each.
_GROUPS: dict[str, frozenset[str]] = {
    "physical": frozenset({"total_route_length_m"}),
    "spatial": frozenset(
        {
            "total_traversal_cost",
            "affected_parcel_count",
            "road_crossing_count",
            "soft_constraint_overlap_length_m",
            "owner_interaction_count",
            "affected_parcel_row_area_m2",
            "environmental_overlap_m2",
        }
    ),
    "infrastructure": frozenset({"physical_pole_count"}),
    "electrical": frozenset(
        {"total_active_loss_mw", "maximum_loading_percent", "voltage_margin_pu"}
    ),
}


def _definition(profile_id: ProfileId) -> ProfileDefinition:
    definition = definition_for(profile_id.value, "1")
    assert definition is not None
    return definition


def _weights(definition: ProfileDefinition) -> dict[str, Decimal]:
    return {term.metric: Decimal(term.weight) for term in definition.terms}


# --- Coverage of the C6 allow-list ------------------------------------------------


def test_exactly_one_definition_per_allow_listed_profile_version() -> None:
    expected = {
        (profile_id.value, version)
        for profile_id, versions in ALLOWED_PROFILE_VERSIONS.items()
        for version in versions
    }
    actual = [
        (item.profile_id.value, item.version)
        for item in PLACEHOLDER_DEFINITIONS.definitions
    ]
    assert len(actual) == len(set(actual)), "duplicate profile version"
    assert set(actual) == expected


def test_unknown_profiles_and_versions_have_no_definition() -> None:
    # None, never a substituted Balanced: WP3-1 must never fall back to it.
    assert definition_for("balanced", "2") is None
    assert definition_for("not_a_profile", "1") is None


def test_every_value_is_marked_placeholder_until_frz1() -> None:
    assert all(item.placeholder for item in PLACEHOLDER_DEFINITIONS.definitions)


def test_every_term_names_a_known_metric() -> None:
    for definition in PLACEHOLDER_DEFINITIONS.definitions:
        for term in definition.terms:
            assert term.metric in KNOWN_METRICS, (definition.profile_id, term.metric)


def test_every_definition_is_explainable() -> None:
    # The scoring explanation validates terms before it scores anything, so an
    # empty cohort is enough to prove a definition is internally consistent.
    for definition in PLACEHOLDER_DEFINITIONS.definitions:
        explanation = explain_candidates([], definition)
        assert explanation.profile_id == definition.profile_id.value


def test_a_metric_normalises_the_same_way_in_every_profile() -> None:
    # A shared range per metric means the same raw value never scores differently
    # merely because a different profile is asking.
    seen: dict[str, tuple[str, str, str]] = {}
    for definition in PLACEHOLDER_DEFINITIONS.definitions:
        for term in definition.terms:
            shape = (term.direction.value, term.reference_min, term.reference_max)
            assert seen.setdefault(term.metric, shape) == shape, term.metric


# --- The §7 structure --------------------------------------------------------------


def test_balanced_has_nonzero_land_environment_and_cost_terms() -> None:
    # R2-C4: without these, Balanced's regret envelope on exactly these metrics
    # would be luck rather than design.
    weights = _weights(_definition(ProfileId.BALANCED))

    assert weights.get("affected_parcel_row_area_m2", Decimal(0)) > 0
    assert weights.get("environmental_overlap_m2", Decimal(0)) > 0
    assert weights.get("lifecycle_cost", Decimal(0)) > 0


def test_balanced_has_a_nonzero_term_in_every_scoring_group() -> None:
    weights = _weights(_definition(ProfileId.BALANCED))

    for group, metrics in _GROUPS.items():
        assert any(weights.get(metric, Decimal(0)) > 0 for metric in metrics), group


def test_minimum_land_puts_row_area_first_with_a_tolerance_band() -> None:
    # R2-C6: primary means lexicographic priority. Parcel count and owner
    # interactions break ties only inside the declared ROW-area band.
    terms = {
        term.metric: term for term in _definition(ProfileId.MINIMUM_LAND_IMPACT).terms
    }

    primary = terms["affected_parcel_row_area_m2"]
    assert primary.lexicographic_rank == 1
    assert primary.tolerance is not None and Decimal(primary.tolerance) > 0

    assert terms["affected_parcel_count"].lexicographic_rank == 2
    assert terms["owner_interaction_count"].lexicographic_rank == 3


def test_minimum_land_ranks_are_a_strict_order() -> None:
    ranks = [
        term.lexicographic_rank
        for term in _definition(ProfileId.MINIMUM_LAND_IMPACT).terms
    ]
    assert sorted(ranks) == list(range(1, len(ranks) + 1))  # type: ignore[type-var]


def test_minimum_environment_puts_environmental_overlap_first() -> None:
    terms = {
        term.metric: term
        for term in _definition(ProfileId.MINIMUM_ENVIRONMENTAL_IMPACT).terms
    }
    assert terms["environmental_overlap_m2"].lexicographic_rank == 1


def test_minimum_cost_is_cost_aware_with_lifecycle_cost_as_its_only_term() -> None:
    # §7: modelled lifecycle-cost weight 1.0; engineering enters as feasibility plus
    # a deterministic tie-break, never as a weighted term.
    definition = _definition(ProfileId.MINIMUM_COST)

    assert definition.policy_mode == ProfilePolicyMode.COST_AWARE
    assert _weights(definition) == {"lifecycle_cost": Decimal(1)}
    assert definition.tie_breaks[-1] == "candidate_id"


def test_every_profile_ends_in_a_deterministic_tie_break() -> None:
    for definition in PLACEHOLDER_DEFINITIONS.definitions:
        assert definition.tie_breaks[-1] == "candidate_id", definition.profile_id


# --- The handshake hash ------------------------------------------------------------


def test_the_registry_hash_is_the_c6_definition_hash() -> None:
    assert registry_hash() == definition_set_hash(PLACEHOLDER_DEFINITIONS)


def test_the_registry_hash_does_not_depend_on_definition_order() -> None:
    reordered = ProfileDefinitionSet(
        definitions=list(reversed(PLACEHOLDER_DEFINITIONS.definitions))
    )
    assert definition_set_hash(reordered) == registry_hash()


def test_the_registry_hash_changes_when_any_value_changes() -> None:
    # The handshake exists to catch a Java/Python definition mismatch, so a single
    # changed weight anywhere must change it.
    first = PLACEHOLDER_DEFINITIONS.definitions[0]
    changed_term = first.terms[0].model_copy(update={"weight": "0.5"})
    changed = ProfileDefinitionSet(
        definitions=[
            first.model_copy(update={"terms": [changed_term, *first.terms[1:]]}),
            *PLACEHOLDER_DEFINITIONS.definitions[1:],
        ]
    )
    assert definition_set_hash(changed) != registry_hash()
