"""WP3-7a: the response records the policy and flags that produced it.

Exit evidence: profile ID and version, policy hash, metric-registry version,
generation-settings hash and both flag states, in the C2 shape.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.contracts.metric_registry_version import METRIC_REGISTRY_VERSION
from app.contracts.profiles import PROFILE_SCENARIO_LABELS, ProfileId
from app.contracts.resolution import (
    SEARCH_DISABLED,
    V0_PROFILE_RESOLUTION,
    ProfileResolution,
    ResponseContext,
    SearchActivation,
)
from app.contracts.response import EffectiveProfile
from app.core.config import get_settings
from app.main import app
from app.optimisation.profiles import registry
from app.presentation.profile_echo import (
    build_effective_profile,
    generation_settings_hash,
    policy_hash,
)

_C2_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "contracts"
    / "fixtures"
    / "response"
    / "additive-blocks.json"
)
_PROJECT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "corpus" / "SYN-4-SPREAD-30.json"
)

_WORKFLOW: Any = None  # the echo reads the context only


def _context(
    *,
    profile: ProfileResolution = V0_PROFILE_RESOLUTION,
    profiles_enabled: bool = False,
    search_enabled: bool = False,
) -> ResponseContext:
    return ResponseContext(
        profile=profile,
        search=SearchActivation(enabled=search_enabled)
        if search_enabled
        else SEARCH_DISABLED,
        profiles_enabled=profiles_enabled,
        search_enabled=search_enabled,
    )


def _balanced() -> ProfileResolution:
    return ProfileResolution(profile_id="balanced", profile_version="1")


# --- Absent for V0 --------------------------------------------------------------


def test_the_block_is_absent_when_both_flags_are_off() -> None:
    assert build_effective_profile(_WORKFLOW, _context()) is None
    assert build_effective_profile(_WORKFLOW, _context(profile=_balanced())) is None, (
        "a profile cannot resolve with the flag off; the block stays absent"
    )


# --- Present whenever a flag is on ------------------------------------------------


def test_a_flag_on_without_a_profile_records_the_flags_and_nulls_the_rest() -> None:
    # The flag state is part of what produced the response, so it is recorded even
    # when no profile ranked the run. The profile fields are null, not invented.
    block = build_effective_profile(_WORKFLOW, _context(search_enabled=True))

    assert block is not None
    assert block.profile_id is None
    assert block.profile_version is None
    assert block.policy_hash is None
    assert block.generation_settings_hash is None
    assert block.profiles_enabled is False
    assert block.search_enabled is True
    assert block.metric_registry_version == METRIC_REGISTRY_VERSION


@pytest.mark.parametrize(
    ("profiles_enabled", "search_enabled"),
    [(True, False), (False, True), (True, True)],
)
def test_both_flag_states_are_echoed_exactly(
    profiles_enabled: bool, search_enabled: bool
) -> None:
    block = build_effective_profile(
        _WORKFLOW,
        _context(
            profile=_balanced(),
            profiles_enabled=profiles_enabled,
            search_enabled=search_enabled,
        ),
    )

    assert block is not None
    assert block.profiles_enabled is profiles_enabled
    assert block.search_enabled is search_enabled


def test_a_resolved_profile_is_echoed_with_its_hashes() -> None:
    block = build_effective_profile(
        _WORKFLOW, _context(profile=_balanced(), profiles_enabled=True)
    )

    assert block is not None
    assert block.profile_id == "balanced"
    assert block.profile_version == "1"
    definition = registry.definition_for("balanced", "1")
    assert definition is not None
    assert block.policy_hash == policy_hash(definition)
    assert block.generation_settings_hash == generation_settings_hash(definition)
    assert block.definition_hash == registry.registry_hash()


# --- What each hash identifies ------------------------------------------------------


def test_the_policy_hash_distinguishes_profiles_and_the_registry_hash_does_not() -> (
    None
):
    # policy_hash answers "which policy ranked this run"; definition_hash answers
    # "which registry is this deployment running", so it is the same for all four.
    blocks = {}
    for profile_id in ProfileId:
        block = build_effective_profile(
            _WORKFLOW,
            _context(
                profile=ProfileResolution(
                    profile_id=profile_id.value, profile_version="1"
                ),
                profiles_enabled=True,
            ),
        )
        assert block is not None
        blocks[profile_id] = block

    policy_hashes = {block.policy_hash for block in blocks.values()}
    definition_hashes = {block.definition_hash for block in blocks.values()}
    assert len(policy_hashes) == len(ProfileId)
    assert len(definition_hashes) == 1


def test_the_policy_hash_changes_when_a_policy_value_changes() -> None:
    # The point of publishing it: two runs with the same hash ranked under the same
    # policy. A single changed weight has to break that equality.
    definition = registry.definition_for("balanced", "1")
    assert definition is not None
    changed_term = definition.terms[0].model_copy(update={"weight": "0.99"})
    changed = definition.model_copy(
        update={"terms": [changed_term, *definition.terms[1:]]}
    )

    assert policy_hash(changed) != policy_hash(definition)


def test_the_generation_settings_hash_tracks_only_generation_settings() -> None:
    definition = registry.definition_for("balanced", "1")
    assert definition is not None
    with_settings = definition.model_copy(
        update={"generation_settings": {"seed_count": "5"}}
    )
    reweighted = definition.model_copy(
        update={
            "terms": [
                definition.terms[0].model_copy(update={"weight": "0.99"}),
                *definition.terms[1:],
            ]
        }
    )

    assert generation_settings_hash(with_settings) != generation_settings_hash(
        definition
    )
    assert generation_settings_hash(reweighted) == generation_settings_hash(definition)


# --- The C2 shape ------------------------------------------------------------------


def test_the_block_matches_the_c2_fixture_shape() -> None:
    with _C2_FIXTURE.open(encoding="utf-8") as handle:
        expected = json.load(handle)["effective_profile"]

    block = build_effective_profile(
        _WORKFLOW,
        _context(profile=_balanced(), profiles_enabled=True, search_enabled=True),
    )
    assert block is not None
    produced = block.model_dump(mode="json")

    assert set(produced) == set(expected)
    # The fixture's hashes are placeholders, so the values that can be compared are
    # the ones it fixes: identity, registry version and flags.
    for field in (
        "profile_id",
        "profile_version",
        "metric_registry_version",
        "profiles_enabled",
        "search_enabled",
    ):
        assert produced[field] == expected[field], field
    assert EffectiveProfile.model_validate(produced) == block


# --- Through the endpoint ------------------------------------------------------------


@pytest.fixture
def profiles_on(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("SURGE_PROFILES_ENABLED", "true")
    get_settings.cache_clear()
    yield TestClient(app, raise_server_exceptions=False)
    get_settings.cache_clear()


def test_a_profile_response_carries_the_echo(profiles_on: TestClient) -> None:
    with _PROJECT.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    payload["profile"] = {"id": "minimum_land_impact", "version": "1"}
    payload["scenario"] = PROFILE_SCENARIO_LABELS[ProfileId.MINIMUM_LAND_IMPACT]

    response = profiles_on.post(
        "/api/v1/optimise",
        content=json.dumps(payload),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200, response.text
    echo = response.json()["effective_profile"]

    assert echo["profile_id"] == "minimum_land_impact"
    assert echo["profile_version"] == "1"
    assert echo["metric_registry_version"] == METRIC_REGISTRY_VERSION
    assert echo["definition_hash"] == registry.registry_hash()
    assert echo["profiles_enabled"] is True
    assert echo["search_enabled"] is False
