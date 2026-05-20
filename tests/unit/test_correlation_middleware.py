from __future__ import annotations

import uuid

import pytest
import structlog

from app.middleware.correlation import CorrelationMiddleware, _generate_request_id


@pytest.fixture(autouse=True)
def _clear_ctx():
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


class TestGenerateRequestId:
    def test_always_generates_uuid(self):
        first = _generate_request_id()
        second = _generate_request_id()
        uuid.UUID(first)
        uuid.UUID(second)
        assert first != second

    def test_none_generates_uuid(self):
        result = _generate_request_id()
        uuid.UUID(result)  # raises if invalid

    def test_generates_uuid(self):
        result = _generate_request_id()
        uuid.UUID(result)

    def test_generates_uuid_for_empty_case(self):
        result = _generate_request_id()
        uuid.UUID(result)

    def test_generated_ids_are_unique(self):
        ids = {_generate_request_id() for _ in range(50)}
        assert len(ids) == 50


class TestCorrelationMiddleware:
    def _make_scope(
        self,
        headers: list[tuple[bytes, bytes]] | None = None,
        client: tuple[str, int] | None = None,
    ) -> dict:
        return {
            "type": "http",
            "headers": headers or [],
            "method": "POST",
            "path": "/mcp",
            "client": client,
        }

    def _make_send_capture(self) -> tuple[list, object]:
        sent: list = []

        async def _send(msg):
            sent.append(msg)

        return sent, _send

    async def test_injects_request_id_header_in_response(self):
        messages, send = self._make_send_capture()
        scope = self._make_scope()

        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = CorrelationMiddleware(app)
        await mw(scope, None, send)

        start = next(m for m in messages if m["type"] == "http.response.start")
        header_keys = [k for k, _ in start["headers"]]
        assert b"x-request-id" in header_keys

    async def test_ignores_valid_request_id_from_incoming_header(self):
        fixed_id = str(uuid.uuid4())
        messages, send = self._make_send_capture()
        scope = self._make_scope(headers=[(b"x-request-id", fixed_id.encode())])

        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = CorrelationMiddleware(app)
        await mw(scope, None, send)

        start = next(m for m in messages if m["type"] == "http.response.start")
        id_in_response = dict(start["headers"]).get(b"x-request-id")
        assert id_in_response != fixed_id.encode()
        uuid.UUID(id_in_response.decode())

    async def test_replaces_invalid_request_id(self):
        messages, send = self._make_send_capture()
        scope = self._make_scope(headers=[(b"x-request-id", b"bad-value")])

        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = CorrelationMiddleware(app)
        await mw(scope, None, send)

        start = next(m for m in messages if m["type"] == "http.response.start")
        id_in_response = dict(start["headers"]).get(b"x-request-id", b"").decode()
        assert id_in_response != "bad-value"
        uuid.UUID(id_in_response)

    async def test_ignores_incoming_request_id_even_when_valid(self):
        incoming_id = str(uuid.uuid4())
        messages, send = self._make_send_capture()
        scope = self._make_scope(headers=[(b"x-request-id", incoming_id.encode())])

        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = CorrelationMiddleware(app)
        await mw(scope, None, send)

        start = next(m for m in messages if m["type"] == "http.response.start")
        id_in_response = dict(start["headers"]).get(b"x-request-id", b"").decode()
        assert id_in_response != incoming_id
        uuid.UUID(id_in_response)

    async def test_binds_request_id_in_structlog_during_request(self):
        captured: list[str] = []
        scope = self._make_scope()
        _sent, send = self._make_send_capture()

        async def app(scope, receive, send):
            ctx = structlog.contextvars.get_contextvars()
            captured.append(ctx.get("request_id", ""))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = CorrelationMiddleware(app)
        await mw(scope, None, send)

        assert len(captured) == 1
        uuid.UUID(captured[0])

    async def test_clears_contextvars_after_request(self):
        scope = self._make_scope()
        _sent, send = self._make_send_capture()

        async def app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = CorrelationMiddleware(app)
        await mw(scope, None, send)

        ctx = structlog.contextvars.get_contextvars()
        assert "request_id" not in ctx
        assert "client_ip" not in ctx

    async def test_uses_scope_client_ip_by_default(self):
        captured: list = []
        scope = self._make_scope(client=("192.0.2.10", 1234))
        _sent, send = self._make_send_capture()

        async def app(scope, receive, send):
            captured.append(structlog.contextvars.get_contextvars().get("client_ip"))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = CorrelationMiddleware(app)
        await mw(scope, None, send)

        assert captured[0] == "192.0.2.10"

    async def test_extracts_client_ip_from_forwarded_for_when_trusted(self):
        captured: list = []
        scope = self._make_scope(
            headers=[(b"x-forwarded-for", b"10.0.0.1, 172.16.0.1")],
            client=("192.0.2.10", 1234),
        )
        _sent, send = self._make_send_capture()

        async def app(scope, receive, send):
            captured.append(structlog.contextvars.get_contextvars().get("client_ip"))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = CorrelationMiddleware(app, trust_proxy_headers=True)
        await mw(scope, None, send)

        assert captured[0] == "10.0.0.1"

    async def test_non_http_scope_passes_through(self):
        called: list[bool] = []

        async def app(scope, receive, send):
            called.append(True)

        mw = CorrelationMiddleware(app)
        await mw({"type": "websocket"}, None, None)
        assert called == [True]
