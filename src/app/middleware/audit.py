from __future__ import annotations

import time
from typing import Any

import structlog
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

from ..logging_config import get_logger

_logger = get_logger("app.middleware.audit")


def _claims_from_token() -> dict[str, Any]:
    try:
        token = get_access_token()
    except Exception:
        return {}
    if token is None:
        return {}
    claims = getattr(token, "claims", {}) or {}
    return claims


def _audited_identity() -> dict[str, str | None]:
    claims = _claims_from_token()
    return {
        "subject": claims.get("sub") or claims.get("oid"),
        "upn": claims.get("upn") or claims.get("preferred_username"),
        "oid": claims.get("oid"),
        "tid": claims.get("tid"),
    }


def _roles_from_token() -> list[str]:
    claims = _claims_from_token()
    roles = claims.get("roles", [])
    return list(roles) if isinstance(roles, (list, tuple)) else []


def _client_session_from_context(context: MiddlewareContext) -> str | None:
    fastmcp_context = getattr(context, "fastmcp_context", None)
    session_id = (
        getattr(fastmcp_context, "session_id", None) if fastmcp_context else None
    )
    return str(session_id) if session_id is not None else None


class AuditMiddleware(Middleware):
    """Emit structured audit events for tool invocations and client lifecycle.

    Never logs tool arguments or return values to avoid PII leakage.
    """

    async def on_initialize(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        identity = _audited_identity()
        client_session = _client_session_from_context(context)
        bound = {"client_session": client_session} if client_session else {}
        with structlog.contextvars.bound_contextvars(**bound):
            _logger.info(
                "mcp.client.connected",
                **identity,
                client_session=client_session,
                roles=_roles_from_token(),
            )
            return await call_next(context)

    async def on_call_tool(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        tool_name = getattr(getattr(context, "message", None), "name", "<unknown>")
        identity = _audited_identity()
        roles = _roles_from_token()
        client_session = _client_session_from_context(context)
        start = time.perf_counter()

        log = _logger.bind(
            tool=tool_name,
            roles=roles,
            client_session=client_session,
            **identity,
        )
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
