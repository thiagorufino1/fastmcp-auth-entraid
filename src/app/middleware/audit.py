from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

_logger = structlog.get_logger("app.middleware.audit")


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


class AuditMiddleware(Middleware):
    """Emit structured audit events for tool invocations and client lifecycle.

    Never logs tool arguments or return values to avoid PII leakage.
    """

    async def on_initialize(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        client_id = str(uuid.uuid4())
        identity = _audited_identity()
        with structlog.contextvars.bound_contextvars(client_session=client_id):
            _logger.info(
                "mcp.client.connected",
                **identity,
                roles=_roles_from_token(),
            )
            return await call_next(context)

    async def on_call_tool(self, context: MiddlewareContext, call_next: CallNext) -> Any:
        tool_name = getattr(getattr(context, "message", None), "name", "<unknown>")
        identity = _audited_identity()
        roles = _roles_from_token()
        start = time.perf_counter()

        log = _logger.bind(tool=tool_name, roles=roles, **identity)
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
