"""WP3-1: invalid inputs map to stable codes, and nothing falls back to Balanced.

Driven through the endpoint, so what is asserted is the response a client actually
receives: HTTP status plus the C3 ``{"code", "message"}`` detail, not an internal
exception type.
"""

import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.contracts.codes import ContractErrorCode
from app.contracts.request import MAX_V1_REQUEST_BYTES
from app.core.config import get_settings
from app.main import app

_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "constraint_demo_project_v2.json"
)


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _request() -> dict[str, Any]:
    with _FIXTURE.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    payload.setdefault("scenario", "Balanced")
    return payload


def _mutated(mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    payload = _request()
    mutate(payload)
    return payload


def _post(client: TestClient, payload: dict[str, Any] | str) -> tuple[int, Any]:
    body = payload if isinstance(payload, str) else json.dumps(payload)
    response = client.post(
        "/api/v1/optimise", content=body, headers={"content-type": "application/json"}
    )
    return response.status_code, response.json().get("detail")


def _assert_code(
    detail: Any, code: ContractErrorCode, *, contains: str | None = None
) -> None:
    assert isinstance(detail, dict), detail
    assert detail["code"] == code.value, detail
    assert detail["message"], "a stable code still needs a usable message"
    if contains is not None:
        assert contains in detail["message"], detail["message"]


# --- The request that must keep working -------------------------------------------


def test_a_valid_v0_request_is_unaffected(client: TestClient) -> None:
    status, _ = _post(client, _request())
    assert status == 200


# --- Unknown profile, version and scenario -----------------------------------------


def test_an_unknown_profile_is_named_as_such(client: TestClient) -> None:
    status, detail = _post(
        client,
        _mutated(lambda p: p.__setitem__("profile", {"id": "nope", "version": "1"})),
    )
    assert status == 422
    _assert_code(detail, ContractErrorCode.UNKNOWN_PROFILE, contains="nope")


def test_an_unknown_version_is_distinguished_from_an_unknown_profile(
    client: TestClient,
) -> None:
    status, detail = _post(
        client,
        _mutated(
            lambda p: p.__setitem__("profile", {"id": "balanced", "version": "9"})
        ),
    )
    assert status == 422
    _assert_code(detail, ContractErrorCode.UNKNOWN_PROFILE_VERSION, contains="9")


def test_a_scenario_label_that_contradicts_the_profile_is_rejected(
    client: TestClient,
) -> None:
    # The C6 label and the profile must agree; silently preferring one would make
    # the response describe a policy the client did not ask for.
    def mutate(payload: dict[str, Any]) -> None:
        payload["profile"] = {"id": "minimum_land_impact", "version": "1"}
        payload["scenario"] = "Balanced"

    status, detail = _post(client, _mutated(mutate))
    assert status == 422
    _assert_code(
        detail, ContractErrorCode.PROFILE_SCENARIO_MISMATCH, contains="Minimum Land"
    )


def test_no_invalid_profile_ever_falls_back_to_balanced(client: TestClient) -> None:
    # The heart of WP3-1: every rejection is a rejection. An invalid profile must
    # never be quietly optimised as Balanced, so none of these may return 200.
    rejections = {
        ContractErrorCode.UNKNOWN_PROFILE.value,
        ContractErrorCode.UNKNOWN_PROFILE_VERSION.value,
        ContractErrorCode.PROFILE_SCENARIO_MISMATCH.value,
    }
    for profile in (
        {"id": "nope", "version": "1"},
        {"id": "balanced", "version": "9"},
        {"id": "BALANCED", "version": "1"},
        {"id": "Balanced", "version": "1"},
    ):
        status, detail = _post(
            client, _mutated(lambda p, v=profile: p.__setitem__("profile", v))
        )
        assert status == 422, (profile, status)
        assert isinstance(detail, dict), (profile, detail)
        assert detail["code"] in rejections, (profile, detail)


def test_a_valid_profile_is_refused_until_selection_drives_the_recommendation(
    client: TestClient,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["profile"] = {"id": "balanced", "version": "1"}
        payload["scenario"] = "Balanced"

    status, detail = _post(client, _mutated(mutate))
    assert status == 422
    _assert_code(detail, ContractErrorCode.PROFILE_NOT_SUPPORTED)


# --- Non-finite and out-of-range ----------------------------------------------------


def test_a_non_finite_coordinate_is_a_stable_code_not_a_free_text_error(
    client: TestClient,
) -> None:
    payload = _request()
    original = payload["wtg_geojson"]["features"][0]["geometry"]["coordinates"][0]
    body = json.dumps(payload).replace(str(original), "NaN", 1)

    status, detail = _post(client, body)
    assert status == 422
    _assert_code(detail, ContractErrorCode.NON_FINITE_VALUE, contains="wtg_geojson")


def test_a_non_finite_value_anywhere_in_the_payload_is_caught(
    client: TestClient,
) -> None:
    # Not only coordinates: any float the request carries must be finite.
    payload = _request()
    body = json.dumps(payload).replace('"capacity_mw": 5.0', '"capacity_mw": 1e999', 1)

    status, detail = _post(client, body)
    assert status == 422
    _assert_code(detail, ContractErrorCode.NON_FINITE_VALUE)


def test_an_out_of_range_longitude_is_a_stable_code(client: TestClient) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["wtg_geojson"]["features"][0]["geometry"]["coordinates"][0] = 500.0

    status, detail = _post(client, _mutated(mutate))
    assert status == 422
    _assert_code(detail, ContractErrorCode.VALUE_OUT_OF_RANGE, contains="longitude")


def test_an_out_of_range_latitude_is_a_stable_code(client: TestClient) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["wtg_geojson"]["features"][0]["geometry"]["coordinates"][1] = 91.0

    status, detail = _post(client, _mutated(mutate))
    assert status == 422
    _assert_code(detail, ContractErrorCode.VALUE_OUT_OF_RANGE, contains="latitude")


def test_out_of_range_coordinates_are_found_at_any_geometry_depth(
    client: TestClient,
) -> None:
    # A polygon ring is nested three deep; the check must not stop at points.
    def mutate(payload: dict[str, Any]) -> None:
        payload["avoidance_geojson"]["features"][0]["geometry"]["coordinates"][0][2][
            0
        ] = -500.0

    status, detail = _post(client, _mutated(mutate))
    assert status == 422
    _assert_code(
        detail, ContractErrorCode.VALUE_OUT_OF_RANGE, contains="avoidance_geojson"
    )


def test_a_negative_buffer_is_out_of_range(client: TestClient) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["avoidance_geojson"]["features"][0]["properties"]["buffer_m"] = -5.0

    status, detail = _post(client, _mutated(mutate))
    assert status == 422
    _assert_code(detail, ContractErrorCode.VALUE_OUT_OF_RANGE, contains="buffer_m")


# --- Typed identity: the gap WP2-4 deferred to WP3-1 --------------------------------


def test_an_unknown_feature_type_is_rejected_rather_than_ignored(
    client: TestClient,
) -> None:
    # Before WP3-1 this was accepted with a 200 and the identity silently dropped.
    def mutate(payload: dict[str, Any]) -> None:
        payload["avoidance_geojson"]["features"][0]["properties"]["feature_type"] = (
            "bogus"
        )

    status, detail = _post(client, _mutated(mutate))
    assert status == 422
    _assert_code(detail, ContractErrorCode.INVALID_TYPED_IDENTITY, contains="bogus")


def test_an_alias_the_parser_accepts_is_not_rejected(client: TestClient) -> None:
    # Validation and parsing share one alias table, so they cannot disagree about
    # which values are usable.
    def mutate(payload: dict[str, Any]) -> None:
        payload["avoidance_geojson"]["features"][0]["properties"]["feature_type"] = (
            "Reserve Forest"
        )

    status, _ = _post(client, _mutated(mutate))
    assert status == 200


def test_an_empty_source_id_is_rejected(client: TestClient) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["avoidance_geojson"]["features"][0]["properties"]["source_id"] = "   "

    status, detail = _post(client, _mutated(mutate))
    assert status == 422
    _assert_code(detail, ContractErrorCode.INVALID_TYPED_IDENTITY, contains="source_id")


def test_absent_typed_identity_stays_v0(client: TestClient) -> None:
    # Absent means V0: the properties simply are not there in the fixture.
    payload = _request()
    properties = payload["avoidance_geojson"]["features"][0]["properties"]
    assert "feature_type" not in properties and "source_id" not in properties

    status, _ = _post(client, payload)
    assert status == 200


# --- Oversized payload ---------------------------------------------------------------


def test_a_payload_over_the_limit_when_serialised_is_refused_with_413(
    client: TestClient,
) -> None:
    payload = _request()
    # Refused by ``RequestSizeLimitMiddleware`` on the raw body, before the
    # canonical-form check in ``_check_size`` is ever reached. What matters to a
    # client is unchanged: 413 with the C1 code, whichever layer answers.
    # One turbine carrying an oversized property: padding with extra features would
    # trip the 500-turbine limit long before the size limit.
    padding = "x" * (MAX_V1_REQUEST_BYTES + 1024)
    payload["wtg_geojson"]["features"][0]["properties"]["note"] = padding

    status, detail = _post(client, payload)
    assert status == 413
    _assert_code(detail, ContractErrorCode.PAYLOAD_TOO_LARGE)


# --- Precedence --------------------------------------------------------------------


def test_payload_defects_are_reported_before_profile_defects(
    client: TestClient,
) -> None:
    # A fixed order means a request with several defects always gets the same
    # answer, so a client can fix them one at a time.
    def mutate(payload: dict[str, Any]) -> None:
        payload["profile"] = {"id": "nope", "version": "1"}
        payload["wtg_geojson"]["features"][0]["geometry"]["coordinates"][0] = 500.0

    status, detail = _post(client, _mutated(mutate))
    assert status == 422
    _assert_code(detail, ContractErrorCode.VALUE_OUT_OF_RANGE)


def test_an_unknown_profile_is_reported_before_a_scenario_mismatch(
    client: TestClient,
) -> None:
    def mutate(payload: dict[str, Any]) -> None:
        payload["profile"] = {"id": "nope", "version": "1"}
        payload["scenario"] = "Minimum Cost"

    status, detail = _post(client, _mutated(mutate))
    assert status == 422
    _assert_code(detail, ContractErrorCode.UNKNOWN_PROFILE)
