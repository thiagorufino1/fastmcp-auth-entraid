from fastmcp import FastMCP

from .health import health_check
from .soma import soma


def register_tools(mcp: FastMCP) -> None:
    mcp.add_tool(health_check)
    mcp.add_tool(soma)
