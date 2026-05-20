from __future__ import annotations

import uuid

import pytest
import structlog

from app.middleware.correlation import CorrelationMiddleware, _parse_or_generate


@pytest.fixture(autouse=True)
def _clear_ctx():
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


class TestParseOrGenerate:
    def test_valid_uuid_reused(self):
        val = str(uuid.uuid4())
        assert _parse_or_generate(val) == val

    def test_none_generates_uuid(self):
        result = _parse_or_generate(None)
        uuid.UUID(result)  # raises if invalid

    def test_invalid_string_generates_new_uuid(self):
        result = _parse_or_generate("not-a-uuid")
        uuid.UUID(result)
        assert result != "not-a-uuid"

    def test_empty_string_generates_uuid(self):
        result = _parse_or_generate("")
        uuid.UUID(result)

    def test_generated_ids_are_unique(self):
        ids = {_parse_or_generate(None) for _ in range(50)}
        assert len(ids) == 50


class TestCorrelationMiddleware:
    def _make_scope(self, headers: list[tuple[bytes, bytes]] | None = None) -> dict:
        return {
            "type": "http",
            "headers": headers or [],
            "method": "POST",
            "path": "/mcp",
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

    async def test_reuses_valid_request_id_from_incoming_header(self):
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
        assert id_in_response == fixed_id.encode()

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

    async def test_extracts_client_ip_from_forwarded_for(self):
        captured: list = []
        scope = self._make_scope(headers=[(b"x-forwarded-for", b"10.0.0.1, 172.16.0.1")])
        _sent, send = self._make_send_capture()

        async def app(scope, receive, send):
            captured.append(structlog.contextvars.get_contextvars().get("client_ip"))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        mw = CorrelationMiddleware(app)
        await mw(scope, None, send)

        assert captured[0] == "10.0.0.1"

    async def test_non_http_scope_passes_through(self):
        called: list[bool] = []

        async def app(scope, receive, send):
            called.append(True)

        mw = CorrelationMiddleware(app)
        await mw({"type": "websocket"}, None, None)
        assert called == [True]
