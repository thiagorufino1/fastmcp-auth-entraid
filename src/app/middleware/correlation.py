from __future__ import annotations

import uuid

import structlog
from starlette.types import ASGIApp, Receive, Scope, Send

_logger = structlog.get_logger("app.middleware.correlation")

_REQUEST_ID_HEADER = "x-request-id"
_FORWARDED_FOR_HEADER = "x-forwarded-for"


def _generate_request_id() -> str:
    return str(uuid.uuid4())


def _extract_client_ip(
    headers: dict[bytes, bytes],
    *,
    trust_forwarded_for: bool,
    scope: Scope,
) -> str | None:
    if trust_forwarded_for:
        forwarded = headers.get(_FORWARDED_FOR_HEADER.encode())
        if forwarded:
            return forwarded.decode(errors="replace").split(",")[0].strip()

    client = scope.get("client")
    if isinstance(client, tuple) and client:
        host = client[0]
        if isinstance(host, str) and host.strip():
            return host.strip()
    return None


class CorrelationMiddleware:
    """Starlette ASGI middleware that tags every HTTP request with a
    correlation ID and propagates it via structlog context variables.

    - Generates a fresh ``request_id`` server-side for every request.
    - Binds ``request_id`` and ``client_ip`` into structlog's contextvars
      so every log line emitted during the request carries them.
    - Appends ``X-Request-ID`` to the response headers.
    - Clears the contextvars after the response is fully sent.
    """

    def __init__(self, app: ASGIApp, *, trust_proxy_headers: bool = False) -> None:
        self.app = app
        self._trust_proxy_headers = trust_proxy_headers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        request_id = _generate_request_id()
        client_ip = _extract_client_ip(
            headers,
            trust_forwarded_for=self._trust_proxy_headers,
            scope=scope,
        )

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
