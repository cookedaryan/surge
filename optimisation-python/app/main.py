"""Application assembly, plus the two request guards that no router can apply.

Both sit here because both run outside the endpoint. The C1 size limit has to
refuse a body before anything reads it, and by the time pydantic has rejected a
declared request field the endpoint function never runs at all. Everything that
does reach an endpoint is validated in ``app/optimisation/profiles/validation.py``
against the same C3 codes; these two guards close the ends that module documents
as out of its reach.
"""

import json
import math
from collections.abc import Iterable
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.v1.router import api_router as api_v1_router
from app.api.v2.router import api_router as api_v2_router
from app.contracts.codes import ContractErrorCode
from app.contracts.errors import ContractError
from app.contracts.request import MAX_V1_REQUEST_BYTES
from app.core.config import settings

# Errors pydantic raises against the body are reported with paths that read like
# the ones validation.py produces, so a client sees one vocabulary either side of
# the seam. Other sources keep their prefix, because "header" or "query" is the
# useful half of the message.
_BODY_LOCATION = "body"


class RequestSizeLimitMiddleware:
    """Refuse an over-sized raw body with 413 before anything parses it (C1).

    This is the raw-body half of the C1 limit. ``validation.py`` can only measure
    the re-serialised payload, which is smaller than the body it came from, so a
    body over the limit used to be parsed in full and then accepted. Here the
    declared ``Content-Length`` is checked before a single byte is read, and a
    chunked body is counted as it arrives and abandoned as soon as it goes over.

    Scoped to the V1 prefix: ``MAX_V1_REQUEST_BYTES`` is the V1 request limit that
    contract C1 publishes, and V2 declares no limit of its own.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_bytes: int,
        path_prefix: str,
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.path_prefix = path_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope.get("path", "").startswith(
            self.path_prefix
        ):
            await self.app(scope, receive, send)
            return

        # Chunked framing is checked first because it wins over Content-Length
        # when a request carries both, and trusting the length there is how a
        # size check gets walked past.
        if _is_chunked(scope):
            await self._call_counting_body(scope, receive, send)
            return

        declared = _declared_content_length(scope)
        if declared is None:
            # Neither a length nor chunked framing means there is no body to size.
            await self.app(scope, receive, send)
            return

        if declared > self.max_bytes:
            await self._refuse(
                send,
                f"Request body is {declared} bytes; the limit is {self.max_bytes}.",
            )
            return

        # The server never delivers more than it announced, so counting again
        # would only duplicate the check and buffer the body for nothing.
        await self.app(scope, receive, send)

    async def _call_counting_body(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """Buffer a chunked body up to the limit, then replay it to the app.

        Buffering costs nothing the request was not already going to spend: the
        endpoint reads the whole body to parse it. What it buys is the stop, which
        happens at the limit rather than at whatever the client decides to send.
        """
        buffered: list[Message] = []
        size = 0
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                buffered.append(message)
                break
            size += len(message.get("body", b""))
            if size > self.max_bytes:
                # The rest of the body is never read, so the exact size is
                # unknown and deliberately not reported as if it were.
                await self._refuse(
                    send,
                    f"Request body exceeds the limit of {self.max_bytes} bytes.",
                )
                return
            buffered.append(message)
            more_body = bool(message.get("more_body", False))

        replay = iter(buffered)

        async def receive_buffered() -> Message:
            try:
                return next(replay)
            except StopIteration:
                return await receive()

        await self.app(scope, receive_buffered, send)

    async def _refuse(self, send: Send, message: str) -> None:
        error = ContractError(
            ContractErrorCode.PAYLOAD_TOO_LARGE,
            message,
            http_status=413,
        )
        body = json.dumps({"detail": error.detail()}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": error.http_status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("latin-1")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


def _header(scope: Scope, name: bytes) -> bytes | None:
    headers: Iterable[tuple[bytes, bytes]] = scope.get("headers") or ()
    for key, value in headers:
        if key.lower() == name:
            return value
    return None


def _declared_content_length(scope: Scope) -> int | None:
    raw = _header(scope, b"content-length")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        # Malformed framing is the server's to reject; do not guess a size.
        return None


def _is_chunked(scope: Scope) -> bool:
    raw = _header(scope, b"transfer-encoding")
    return raw is not None and b"chunked" in raw.lower()


def _location(loc: tuple[Any, ...]) -> str:
    parts = loc[1:] if loc and loc[0] == _BODY_LOCATION else loc
    return ".".join(str(part) for part in parts)


def _is_non_finite(value: object) -> bool:
    return isinstance(value, float) and not math.isfinite(value)


def contract_validation_detail(errors: list[Any]) -> dict[str, str]:
    """Map pydantic's report of a rejected request onto one stable C3 detail.

    Only the field path and pydantic's own message are used. The offending input
    is never read into the response: echoing it is what made this a 500, because
    ``Infinity`` and ``NaN`` survive ``json.loads`` but cannot be serialised back
    out again.

    A non-finite value is named as such wherever pydantic rejected one, which
    matches the order ``validation.py`` checks in, so a request reports the same
    defect whichever side of the seam catches it. Anything else is a value the
    field does not accept, which is ``VALUE_OUT_OF_RANGE``.
    """
    chosen = next(
        (error for error in errors if _is_non_finite(error.get("input"))), None
    )
    if chosen is not None:
        location = _location(tuple(chosen.get("loc", ())))
        message = (
            f"{location} must be a finite number."
            if location
            else "Request contains a value that is not a finite number."
        )
        return ContractError(ContractErrorCode.NON_FINITE_VALUE, message).detail()

    if not errors:
        return ContractError(
            ContractErrorCode.VALUE_OUT_OF_RANGE,
            "Request was rejected by its schema.",
        ).detail()

    first = errors[0]
    return ContractError(
        ContractErrorCode.VALUE_OUT_OF_RANGE, _message(first)
    ).detail()


def _message(error: dict[str, Any]) -> str:
    if error.get("type") == "json_invalid":
        # ``loc`` here is a character offset, not a field path, so naming it would
        # read like a field. The parser's own reason is the useful part.
        reason = (error.get("ctx") or {}).get("error")
        if reason:
            return f"Request body is not valid JSON: {reason}."
        return "Request body is not valid JSON."
    location = _location(tuple(error.get("loc", ())))
    reason = str(error.get("msg") or "is not an accepted value")
    return f"{location}: {reason}" if location else reason


async def handle_request_validation_error(
    _request: Request, exc: Exception
) -> JSONResponse:
    """Return the C3 ``{"code", "message"}`` shape instead of echoing the input."""
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    return JSONResponse(
        status_code=422,
        content={"detail": contract_validation_detail(list(errors))},
    )


def create_application() -> FastAPI:
    docs_enabled = settings.environment != "production"

    application = FastAPI(
        title=settings.project_name,
        version=settings.version,
        openapi_url=(
            f"{settings.api_v1_prefix}/openapi.json" if docs_enabled else None
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
    )

    application.add_middleware(
        RequestSizeLimitMiddleware,
        max_bytes=MAX_V1_REQUEST_BYTES,
        path_prefix=settings.api_v1_prefix,
    )

    application.add_exception_handler(
        RequestValidationError,
        handle_request_validation_error,
    )

    application.include_router(
        api_v1_router,
        prefix=settings.api_v1_prefix,
    )

    application.include_router(
        api_v2_router,
        prefix=settings.api_v2_prefix,
    )

    return application


app = create_application()
