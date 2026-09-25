"""The two request guards in ``app/main.py``, driven through the endpoint.

Both run outside any endpoint, so neither is reachable from
``tests/profiles/test_request_validation.py``, which exercises the checks that do
run inside ``resolve_profile``. What is asserted here is the response a client
receives: the HTTP status and the C3 ``{"code", "message"}`` detail.
"""

import copy
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.contracts.codes import ContractErrorCode
from app.contracts.request import MAX_V1_REQUEST_BYTES
from app.main import app

_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "constraint_demo_project_v2.json"
)

_JSON = {"content-type": "application/json"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _request() -> dict[str, Any]:
    with _FIXTURE.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    payload.setdefault("scenario", "Balanced")
    return payload


def _post(client: TestClient, body: bytes | str) -> tuple[int, Any]:
    response = client.post("/api/v1/optimise", content=body, headers=_JSON)
    return response.status_code, response.json().get("detail")


def _assert_code(detail: Any, code: ContractErrorCode) -> None:
    assert isinstance(detail, dict), detail
    assert detail["code"] == code.value, detail
    assert detail["message"], "a stable code still needs a usable message"


# --- Non-finite literals that pydantic rejects before the endpoint runs -------------


@pytest.mark.parametrize("literal", ["Infinity", "-Infinity", "NaN"])
def test_a_non_finite_value_failing_its_field_constraint_is_422_not_500(
    client: TestClient, literal: str
) -> None:
    """The reported defect. ``json.loads`` accepts these non-standard literals, so
    the value reaches pydantic, fails ``operating_factor``'s ``le=1.0`` and never
    reaches ``validate_request``. FastAPI's default handler then echoed the input
    into the response body, which could not be serialised — a 500 any client could
    trigger.
    """
    body = json.dumps(_request()).replace(
        '"operating_factor": 1.0', f'"operating_factor": {literal}', 1
    )

    status, detail = _post(client, body)

    assert status == 422
    _assert_code(detail, ContractErrorCode.NON_FINITE_VALUE)
    assert "operating_factor" in detail["message"], detail


def test_the_rejection_never_echoes_the_offending_input(client: TestClient) -> None:
    # Echoing the input is what made this a 500, and a response that cannot be
    # serialised is a 500 however the code is chosen. The detail carries the field
    # path and a reason, never the value.
    body = json.dumps(_request()).replace(
        '"operating_factor": 1.0', '"operating_factor": Infinity', 1
    )

    response = client.post("/api/v1/optimise", content=body, headers=_JSON)

    assert response.status_code == 422
    assert set(response.json()["detail"]) == {"code", "message"}
    assert "Infinity" not in response.text
    json.loads(response.text)  # strict: no bare Infinity or NaN anywhere in the body


def test_a_non_finite_value_that_passes_pydantic_still_reports_the_same_code(
    client: TestClient,
) -> None:
    # A coordinate has no declared bound, so it reaches ``validate_request``. The
    # two layers must not disagree about what a non-finite value is called.
    payload = _request()
    original = payload["wtg_geojson"]["features"][0]["geometry"]["coordinates"][0]
    body = json.dumps(payload).replace(str(original), "NaN", 1)

    status, detail = _post(client, body)

    assert status == 422
    _assert_code(detail, ContractErrorCode.NON_FINITE_VALUE)


# --- Everything else pydantic rejects -----------------------------------------------


def test_a_field_that_breaks_its_constraint_gets_a_stable_code(
    client: TestClient,
) -> None:
    payload = _request()
    payload["operating_point_config"]["operating_factor"] = 5.0

    status, detail = _post(client, json.dumps(payload))

    assert status == 422
    _assert_code(detail, ContractErrorCode.VALUE_OUT_OF_RANGE)
    assert "operating_factor" in detail["message"], detail


def test_a_missing_required_field_gets_a_stable_code(client: TestClient) -> None:
    payload = _request()
    del payload["request_id"]

    status, detail = _post(client, json.dumps(payload))

    assert status == 422
    _assert_code(detail, ContractErrorCode.VALUE_OUT_OF_RANGE)
    assert "request_id" in detail["message"], detail


def test_a_malformed_body_is_named_as_bad_json_not_as_a_field(
    client: TestClient,
) -> None:
    # Pydantic reports a character offset here, not a field path, so the message
    # must not present that number as if it were a field name.
    status, detail = _post(client, "{not json")

    assert status == 422
    _assert_code(detail, ContractErrorCode.VALUE_OUT_OF_RANGE)
    assert "valid JSON" in detail["message"], detail


def test_the_field_path_reads_the_same_as_the_one_validation_py_produces(
    client: TestClient,
) -> None:
    # ``body`` is dropped from the front so a client sees one vocabulary either
    # side of the seam: ``operating_point_config.operating_factor``, not
    # ``body.operating_point_config.operating_factor``.
    payload = _request()
    payload["operating_point_config"]["operating_factor"] = 5.0

    _, detail = _post(client, json.dumps(payload))

    assert detail["message"].startswith("operating_point_config.operating_factor"), (
        detail
    )


# --- The raw-body size limit ---------------------------------------------------------


def _oversized_body() -> bytes:
    payload = _request()
    # One turbine carrying an oversized property: padding with extra features would
    # trip the 500-turbine limit long before the size limit.
    payload["wtg_geojson"]["features"][0]["properties"]["note"] = "x" * (
        MAX_V1_REQUEST_BYTES + 1024
    )
    body = json.dumps(payload).encode("utf-8")
    assert len(body) > MAX_V1_REQUEST_BYTES
    return body


def test_a_raw_body_over_the_limit_is_refused_with_413(client: TestClient) -> None:
    status, detail = _post(client, _oversized_body())

    assert status == 413
    _assert_code(detail, ContractErrorCode.PAYLOAD_TOO_LARGE)


def test_an_oversized_body_is_refused_before_anything_parses_it(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The point of the middleware. Before it, the body was parsed in full and the
    only size available afterwards was the re-serialised payload, which is smaller:
    a body over the limit could be parsed and then accepted.
    """
    from app.api.v1.endpoints import optimise as endpoint

    def fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("the endpoint must not run for an oversized body")

    monkeypatch.setattr(endpoint, "resolve_profile", fail)

    status, _ = _post(client, _oversized_body())

    assert status == 413


def test_a_raw_body_over_the_limit_whose_canonical_form_is_under_it_is_refused(
    client: TestClient,
) -> None:
    """Closes the hole ``validate_request`` could not reach.

    This body is over the limit while its re-serialised form is under it, so the
    canonical-form check in ``_check_size`` passes it. It used to be accepted and
    rejected later for an unrelated reason; the raw limit now refuses it.
    """
    payload = _request()
    template = copy.deepcopy(payload["wtg_geojson"]["features"][0])
    features = payload["wtg_geojson"]["features"]
    while len(json.dumps(payload).encode("utf-8")) <= MAX_V1_REQUEST_BYTES:
        for _ in range(2000):
            clone = copy.deepcopy(template)
            clone["properties"]["turbine_id"] = f"T{len(features):07d}"
            features.append(clone)

    body = json.dumps(payload).encode("utf-8")
    assert len(body) > MAX_V1_REQUEST_BYTES

    status, detail = _post(client, body)

    assert status == 413
    _assert_code(detail, ContractErrorCode.PAYLOAD_TOO_LARGE)


def test_a_chunked_body_is_counted_as_it_arrives(client: TestClient) -> None:
    # No Content-Length to trust, so the middleware counts the stream instead.
    def stream() -> Iterator[bytes]:
        for _ in range(MAX_V1_REQUEST_BYTES // (1024 * 1024) + 2):
            yield b"x" * 1024 * 1024

    response = client.post("/api/v1/optimise", content=stream(), headers=_JSON)

    assert response.status_code == 413
    _assert_code(response.json()["detail"], ContractErrorCode.PAYLOAD_TOO_LARGE)


def test_a_chunked_body_under_the_limit_is_replayed_intact(
    client: TestClient,
) -> None:
    # The middleware buffers a chunked body to count it, so it also has to hand
    # every byte on: a request split across chunks must still optimise.
    body = json.dumps(_request()).encode("utf-8")

    def stream() -> Iterator[bytes]:
        half = len(body) // 2
        yield body[:half]
        yield body[half:]

    response = client.post("/api/v1/optimise", content=stream(), headers=_JSON)

    assert response.status_code == 200


def test_a_request_under_the_limit_is_unaffected(client: TestClient) -> None:
    status, _ = _post(client, json.dumps(_request()))
    assert status == 200


def test_a_bodyless_request_passes_the_limit_untouched(client: TestClient) -> None:
    # No Content-Length and no chunked framing means no body to size; the
    # middleware must not wait on a receive that never comes.
    assert client.get("/api/v1/health").status_code == 200
