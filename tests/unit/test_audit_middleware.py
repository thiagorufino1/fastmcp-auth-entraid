from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
import structlog
from structlog.testing import capture_logs

from app.middleware.audit import AuditMiddleware


@dataclass
class _FakeMessage:
    name: str


@dataclass
class _FakeContext:
    message: Any = None
    timestamp: str = "2026-05-19T12:00:00Z"


@dataclass
class _FakeToken:
    claims: dict[str, Any] = field(default_factory=dict)


@pytest.fixture
def _reset_structlog():
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


@pytest.fixture
def patch_token(monkeypatch):
    def _set(token):
        monkeypatch.setattr("app.middleware.audit.get_access_token", lambda: token)

    return _set


class TestAuditMiddleware:
    async def test_on_call_tool_success_logs_start_and_success(self, _reset_structlog, patch_token):
        patch_token(_FakeToken(claims={"sub": "user-1", "roles": ["mcp-trc-read"]}))
        middleware = AuditMiddleware()
        ctx = _FakeContext(message=_FakeMessage(name="soma"))

        async def _next(_ctx):
            return "ok"

        with capture_logs() as events:
            result = await middleware.on_call_tool(ctx, _next)

        assert result == "ok"
        event_names = [e["event"] for e in events]
        assert "mcp.tool.call.start" in event_names
        assert "mcp.tool.call.success" in event_names
        success = next(e for e in events if e["event"] == "mcp.tool.call.success")
        assert success["tool"] == "soma"
        assert success["subject"] == "user-1"
        assert success["roles"] == ["mcp-trc-read"]
        assert "duration_ms" in success

    async def test_on_call_tool_error_logs_error_event(self, _reset_structlog, patch_token):
        patch_token(_FakeToken(claims={"sub": "user-2", "roles": ["mcp-trc-admin"]}))
        middleware = AuditMiddleware()
        ctx = _FakeContext(message=_FakeMessage(name="health_check"))

        async def _next(_ctx):
            raise RuntimeError("boom")

        with capture_logs() as events, pytest.raises(RuntimeError):
            await middleware.on_call_tool(ctx, _next)

        error = next(e for e in events if e["event"] == "mcp.tool.call.error")
        assert error["tool"] == "health_check"
        assert error["error_type"] == "RuntimeError"
        assert error["subject"] == "user-2"

    async def test_handles_missing_token_gracefully(self, _reset_structlog, patch_token):
        patch_token(None)
        middleware = AuditMiddleware()
        ctx = _FakeContext(message=_FakeMessage(name="soma"))

        async def _next(_ctx):
            return "ok"

        with capture_logs() as events:
            await middleware.on_call_tool(ctx, _next)

        success = next(e for e in events if e["event"] == "mcp.tool.call.success")
        assert success["subject"] is None
        assert success["roles"] == []

    async def test_prefers_oid_when_sub_missing(self, _reset_structlog, patch_token):
        patch_token(_FakeToken(claims={"oid": "object-id-9"}))
        middleware = AuditMiddleware()
        ctx = _FakeContext(message=_FakeMessage(name="soma"))

        async def _next(_ctx):
            return None

        with capture_logs() as events:
            await middleware.on_call_tool(ctx, _next)

        success = next(e for e in events if e["event"] == "mcp.tool.call.success")
        assert success["subject"] == "object-id-9"

    async def test_on_initialize_emits_connected_event(self, _reset_structlog, patch_token):
        patch_token(_FakeToken(claims={"sub": "user-3", "roles": ["mcp-trc-read"]}))
        middleware = AuditMiddleware()
        ctx = _FakeContext()

        async def _next(_ctx):
            return "initialized"

        with capture_logs() as events:
            result = await middleware.on_initialize(ctx, _next)

        assert result == "initialized"
        connected = next(e for e in events if e["event"] == "mcp.client.connected")
        assert connected["subject"] == "user-3"
        assert connected["roles"] == ["mcp-trc-read"]

    async def test_does_not_log_tool_arguments_or_return_value(self, _reset_structlog, patch_token):
        patch_token(_FakeToken(claims={"sub": "user-4", "roles": ["mcp-trc-read"]}))
        middleware = AuditMiddleware()
        ctx = _FakeContext(message=_FakeMessage(name="soma"))
        secret_args = {"password": "should-never-leak"}
        ctx.arguments = secret_args

        async def _next(_ctx):
            return {"secret_result": "should-never-leak"}

        with capture_logs() as events:
            await middleware.on_call_tool(ctx, _next)

        rendered = str(events)
        assert "should-never-leak" not in rendered
        assert "password" not in rendered
