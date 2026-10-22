"""A resolved profile drives the recommendation, not only the explanation.

WP3-3 made profile selection exist and WP2-7 published the explanation, but the
recommendation still came from the V0 scorer. A profile request would then answer
with the V0 winner and a profile-ranked explanation beside it: two answers to the
same question. These tests hold the two together.

Driven through the endpoint with the C5 profiles flag on, because that is the only
state in which a profile resolves at all.
"""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.contracts.profiles import PROFILE_SCENARIO_LABELS, ProfileId
from app.core.config import get_settings
from app.main import app

_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "corpus" / "SYN-4-SPREAD-30.json"
)
# Carries no costing config, so nothing in it has a lifecycle cost.
_FIXTURE_WITHOUT_COSTS = (
    Path(__file__).resolve().parents[1] / "fixtures" / "constraint_demo_project_v2.json"
)


@pytest.fixture
def profiles_on(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("SURGE_PROFILES_ENABLED", "true")
    get_settings.cache_clear()
    yield TestClient(app, raise_server_exceptions=False)
    get_settings.cache_clear()


@pytest.fixture
def profiles_off(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv("SURGE_PROFILES_ENABLED", raising=False)
    get_settings.cache_clear()
    yield TestClient(app, raise_server_exceptions=False)
    get_settings.cache_clear()


def _request(profile_id: ProfileId | None = None) -> dict[str, Any]:
    with _FIXTURE.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    payload.setdefault("scenario", "Balanced")
    if profile_id is not None:
        payload["profile"] = {"id": profile_id.value, "version": "1"}
        payload["scenario"] = PROFILE_SCENARIO_LABELS[profile_id]
    return payload


def _post(client: TestClient, payload: dict[str, Any]) -> tuple[int, Any]:
    response = client.post(
        "/api/v1/optimise",
        content=json.dumps(payload),
        headers={"content-type": "application/json"},
    )
    return response.status_code, response.json()


def _winner(body: Any) -> str | None:
    return body["recommendation"]["recommended_scenario_id"]


def _explanation(body: Any) -> Any:
    return body.get("scoring_explanation")


def test_a_profile_request_now_succeeds(profiles_on: TestClient) -> None:
    status, body = _post(profiles_on, _request(ProfileId.BALANCED))
    assert status == 200, body
    assert _winner(body) is not None


def test_the_flag_still_gates_profiles(profiles_off: TestClient) -> None:
    status, body = _post(profiles_off, _request(ProfileId.BALANCED))
    assert status == 422
    assert body["detail"]["code"] == "PROFILE_NOT_SUPPORTED"


@pytest.mark.parametrize("profile_id", list(ProfileId))
def test_the_recommendation_is_the_explanations_top_ranked_candidate(
    profiles_on: TestClient, profile_id: ProfileId
) -> None:
    # The claim this whole wiring exists to make true, for every profile.
    status, body = _post(profiles_on, _request(profile_id))
    assert status == 200, body

    explanation = _explanation(body)
    assert explanation is not None, "a resolved profile must publish its reasoning"
    assert explanation["profile_id"] == profile_id.value

    ranked_first = [
        item["candidate_id"]
        for item in explanation["candidates"]
        if item.get("rank") == 1
    ]
    assert ranked_first == [_winner(body)]


def test_the_published_ranking_is_a_complete_order(profiles_on: TestClient) -> None:
    # The V1 response does not publish per-candidate evaluations, so the explanation
    # block is the ranking a client sees. Every candidate the profile could order
    # gets a distinct rank, 1..n, with no gaps and no ties left unresolved.
    status, body = _post(profiles_on, _request(ProfileId.MINIMUM_LAND_IMPACT))
    assert status == 200, body

    ranks = sorted(
        item["rank"]
        for item in _explanation(body)["candidates"]
        if item.get("rank") is not None
    )
    assert ranks == list(range(1, len(ranks) + 1))
    assert ranks, "at least one candidate must be rankable on this fixture"


def test_v0_reasons_are_not_published_under_a_profile(
    profiles_on: TestClient,
) -> None:
    # Every code except ONLY_ELIGIBLE_CANDIDATE describes V0 scoring, which is not
    # what ranked this run; the explanation block carries the profile's reasoning.
    status, body = _post(profiles_on, _request(ProfileId.MINIMUM_ENVIRONMENTAL_IMPACT))
    assert status == 200, body

    codes = {reason["code"] for reason in body["recommendation"]["reasons"]}
    assert codes <= {"ONLY_ELIGIBLE_CANDIDATE"}


def test_a_profile_that_can_rank_nobody_recommends_nobody(
    profiles_on: TestClient,
) -> None:
    """The silent fallback this wiring must not have.

    This fixture carries no costing config, so no candidate has a lifecycle cost and
    Minimum Cost cannot order a single one. Answering with the V0 winner would tell
    the client "here is your lowest-cost design" on evidence that does not exist.
    The run fails instead, and the explanation shows the candidate unranked so an
    operator can see why.
    """
    with _FIXTURE_WITHOUT_COSTS.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert "costing_config" not in payload
    payload["profile"] = {"id": ProfileId.MINIMUM_COST.value, "version": "1"}
    payload["scenario"] = PROFILE_SCENARIO_LABELS[ProfileId.MINIMUM_COST]

    status, body = _post(profiles_on, payload)

    assert status == 200, body
    assert body["status"] == "failed"
    assert body["recommendation"].get("recommended_scenario_id") is None
    explanation = _explanation(body)
    assert explanation is not None
    assert all(item.get("rank") is None for item in explanation["candidates"])
    assert all(item.get("total_score") is None for item in explanation["candidates"])


def test_a_v0_request_is_unchanged_while_the_flag_is_on(
    profiles_on: TestClient,
) -> None:
    # Absent profile still means V0: no explanation block, V0 reasons intact.
    status, body = _post(profiles_on, _request())
    assert status == 200, body
    assert _explanation(body) is None


def test_two_profiles_can_choose_differently_on_the_same_project(
    profiles_on: TestClient,
) -> None:
    # Not an assertion that they must differ on this fixture - that is a property of
    # the cohort, and of policy values FRZ-1 has not set. What is asserted is that
    # each profile's recommendation is its own selection's winner, so a difference
    # would be carried through rather than flattened to one answer.
    winners = {}
    for profile_id in (ProfileId.MINIMUM_LAND_IMPACT, ProfileId.MINIMUM_COST):
        status, body = _post(profiles_on, _request(profile_id))
        assert status == 200, body
        explanation = _explanation(body)
        top = [
            item["candidate_id"]
            for item in explanation["candidates"]
            if item.get("rank") == 1
        ]
        assert top == [_winner(body)], profile_id
        winners[profile_id] = _winner(body)

    assert set(winners) == {ProfileId.MINIMUM_LAND_IMPACT, ProfileId.MINIMUM_COST}
