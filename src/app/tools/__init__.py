from __future__ import annotations

from fastmcp import FastMCP

from .health import health_check
from .soma import soma

__all__ = ["health_check", "register_tools", "soma"]


def register_tools(mcp: FastMCP) -> None:
    """Register the explicit production tool set."""
    mcp.add_tool(soma)
    mcp.add_tool(health_check)
