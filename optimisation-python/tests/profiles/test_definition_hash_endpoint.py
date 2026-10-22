"""WP3-6a: the definition-hash endpoint, the Python half of the C7 handshake.

Exit evidence: the endpoint returns the C6 hash, and the test vector reproduces.
"""

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.contracts import CONTRACT_PACK_VERSION
from app.contracts.metric_registry_version import METRIC_REGISTRY_VERSION
from app.contracts.profiles import ProfileDefinitionSet, definition_set_hash
from app.core.config import get_settings
from app.main import app
from app.optimisation.profiles import registry

_HASH_VECTOR = (
    Path(__file__).resolve().parents[3] / "contracts" / "profiles" / "hash-vector"
)
_ENDPOINT = "/api/v1/profiles/definition-hash"


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def test_the_endpoint_answers_with_exactly_the_c7_keys(client: TestClient) -> None:
    response = client.get(_ENDPOINT)

    assert response.status_code == 200, response.text
    assert set(response.json()) == {
        "definition_hash",
        "metric_registry_version",
        "contract_pack_version",
    }


def test_it_returns_the_registrys_own_hash(client: TestClient) -> None:
    body = client.get(_ENDPOINT).json()

    assert body["definition_hash"] == registry.registry_hash()
    assert body["metric_registry_version"] == METRIC_REGISTRY_VERSION
    assert body["contract_pack_version"] == CONTRACT_PACK_VERSION


def test_the_published_hash_is_the_c6_algorithm_over_the_registry(
    client: TestClient,
) -> None:
    # Recomputed independently of ``registry_hash`` so the endpoint cannot drift
    # onto some other digest while still looking self-consistent.
    recomputed = definition_set_hash(registry.PLACEHOLDER_DEFINITIONS)

    assert client.get(_ENDPOINT).json()["definition_hash"] == recomputed


def test_the_c6_test_vector_reproduces_under_the_same_algorithm() -> None:
    # What Java must reproduce. If the endpoint's algorithm and the published
    # vector ever diverge, the handshake would fail for the wrong reason.
    with (_HASH_VECTOR / "definitions.json").open(encoding="utf-8") as handle:
        vector = ProfileDefinitionSet.model_validate(json.load(handle))
    expected = (_HASH_VECTOR / "expected.sha256").read_text(encoding="utf-8").strip()

    assert definition_set_hash(vector) == expected


def test_the_hash_is_stable_across_calls(client: TestClient) -> None:
    first = client.get(_ENDPOINT).json()["definition_hash"]
    second = client.get(_ENDPOINT).json()["definition_hash"]

    assert first == second


@pytest.mark.parametrize("profiles_enabled", ["true", "false"])
def test_the_handshake_is_not_gated_on_the_profiles_flag(
    monkeypatch: pytest.MonkeyPatch, profiles_enabled: str
) -> None:
    # C7 puts the "when profiles are enabled" condition on Java's side. A
    # deployment with profiles off still has definitions, and Java must be able to
    # detect a mismatch before anyone turns the flag on.
    monkeypatch.setenv("SURGE_PROFILES_ENABLED", profiles_enabled)
    get_settings.cache_clear()
    client = TestClient(app, raise_server_exceptions=False)

    response = client.get(_ENDPOINT)

    assert response.status_code == 200
    assert response.json()["definition_hash"] == registry.registry_hash()


def test_the_endpoint_and_the_response_block_publish_one_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The handshake value and the per-response echo (WP3-7a) must be the same
    # number, or an operator comparing them would chase a difference that is not
    # there.
    monkeypatch.setenv("SURGE_PROFILES_ENABLED", "true")
    get_settings.cache_clear()
    client = TestClient(app, raise_server_exceptions=False)

    from app.contracts.profiles import PROFILE_SCENARIO_LABELS, ProfileId

    project = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "corpus"
        / "SYN-4-SPREAD-30.json"
    )
    with project.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    payload["profile"] = {"id": "balanced", "version": "1"}
    payload["scenario"] = PROFILE_SCENARIO_LABELS[ProfileId.BALANCED]

    optimise = client.post(
        "/api/v1/optimise",
        content=json.dumps(payload),
        headers={"content-type": "application/json"},
    )
    assert optimise.status_code == 200, optimise.text

    handshake = client.get(_ENDPOINT).json()["definition_hash"]
    echoed = optimise.json()["effective_profile"]["definition_hash"]
    assert handshake == echoed
