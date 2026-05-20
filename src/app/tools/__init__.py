from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

from fastmcp.tools.base import Tool

if TYPE_CHECKING:
    from fastmcp import FastMCP


def discover_tools() -> list[Tool]:
    """Find every Tool instance defined in submodules of this package.

    Scans non-underscore modules under app.tools, imports each one, and
    collects module-level attributes that are Tool instances. Adding a new
    tool only requires dropping a file in this directory; no edits to this
    init module are needed.
    """
    tools: list[Tool] = []
    for module_info in pkgutil.iter_modules(__path__):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{module_info.name}")
        for attr in vars(module).values():
            if isinstance(attr, Tool):
                tools.append(attr)
    return tools


def register_tools(mcp: FastMCP) -> None:
    """Register every discovered tool on the FastMCP server."""
    for tool in discover_tools():
        mcp.add_tool(tool)
