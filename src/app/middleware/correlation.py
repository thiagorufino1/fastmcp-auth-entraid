from __future__ import annotations

import uuid

import structlog
from starlette.types import ASGIApp, Receive, Scope, Send

_logger = structlog.get_logger("app.middleware.correlation")

_REQUEST_ID_HEADER = "x-request-id"
_FORWARDED_FOR_HEADER = "x-forwarded-for"


def _parse_or_generate(value: str | None) -> str:
    if value:
        try:
            return str(uuid.UUID(value))
        except ValueError:
            pass
    return str(uuid.uuid4())


def _extract_client_ip(headers: dict[bytes, bytes]) -> str | None:
    forwarded = headers.get(_FORWARDED_FOR_HEADER.encode())
    if forwarded:
        return forwarded.decode(errors="replace").split(",")[0].strip()
    return None


class CorrelationMiddleware:
    """Starlette ASGI middleware that tags every HTTP request with a
    correlation ID and propagates it via structlog context variables.

    - Reads ``X-Request-ID`` from the incoming request headers.
    - If the value is a valid UUID it is reused; otherwise a new UUID v4
      is generated (preventing header injection with arbitrary strings).
    - Binds ``request_id`` and ``client_ip`` into structlog's contextvars
      so every log line emitted during the request carries them.
    - Appends ``X-Request-ID`` to the response headers.
    - Clears the contextvars after the response is fully sent.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        raw_id = headers.get(_REQUEST_ID_HEADER.encode())
        request_id = _parse_or_generate(raw_id.decode(errors="replace") if raw_id else None)
        client_ip = _extract_client_ip(headers)

        structlog.contextvars.bind_contextvars(request_id=request_id, client_ip=client_ip)

        async def send_with_header(message: dict) -> None:
            if message.get("type") == "http.response.start":
                existing: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                existing.append((_REQUEST_ID_HEADER.encode(), request_id.encode()))
                message = {**message, "headers": existing}
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)  # type: ignore[arg-type]
        finally:
            structlog.contextvars.unbind_contextvars("request_id", "client_ip")
