from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

_logger = structlog.get_logger("app.middleware.audit")


def _subject_from_token() -> str | None:
    try:
        token = get_access_token()
    except Exception:
        return None
    if token is None:
        return None
    claims = getattr(token, "claims", {}) or {}
    return claims.get("sub") or claims.get("oid")


def _roles_from_token() -> list[str]:
    try:
        token = get_access_token()
    except Exception:
        return []
    if token is None:
        return []
    claims = getattr(token, "claims", {}) or {}
    roles = claims.get("roles", [])
    return list(roles) if isinstance(roles, (list, tuple)) else []


class AuditMiddleware(Middleware):
    """Emit structured audit events for tool invocations and client lifecycle.

    Never logs tool arguments or return values to avoid PII leakage.
    """

    async def on_initialize(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        client_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(client_session=client_id)
        _logger.info(
            "mcp.client.connected",
            subject=_subject_from_token(),
            roles=_roles_from_token(),
        )
        try:
            return await call_next(context)
        finally:
            pass

    async def on_call_tool(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        tool_name = getattr(getattr(context, "message", None), "name", "<unknown>")
        subject = _subject_from_token()
        roles = _roles_from_token()
        start = time.perf_counter()

        log = _logger.bind(tool=tool_name, subject=subject, roles=roles)
        log.info("mcp.tool.call.start")

        try:
            result = await call_next(context)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            log.warning(
                "mcp.tool.call.error",
                error_type=type(exc).__name__,
                duration_ms=round(elapsed_ms, 2),
            )
            raise
        else:
            elapsed_ms = (time.perf_counter() - start) * 1000
            log.info(
                "mcp.tool.call.success",
                duration_ms=round(elapsed_ms, 2),
            )
            return result
