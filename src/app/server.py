from collections.abc import Sequence
from typing import Any

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.types import ASGIApp

from .auth import build_auth_provider
from .config import load_settings
from .middleware import AuditMiddleware, CorrelationMiddleware
from .tools import register_tools


def create_mcp() -> FastMCP:
    settings = load_settings()
    mcp = FastMCP("mcp-lab", auth=build_auth_provider(settings))
    mcp.add_middleware(AuditMiddleware())
    register_tools(mcp)
    return mcp


def create_http_app(extra_middleware: Sequence[Middleware] | None = None) -> ASGIApp:
    """Return the ASGI app with Starlette middleware wired in.

    CorrelationMiddleware is always included first so every downstream
    component (audit logs, tool call events) inherits request_id.
    Pass extra_middleware to inject additional layers (e.g. in tests).
    """
    mcp = create_mcp()
    middleware: list[Any] = [Middleware(CorrelationMiddleware)]
    if extra_middleware:
        middleware.extend(extra_middleware)
    return mcp.http_app(middleware=middleware)
