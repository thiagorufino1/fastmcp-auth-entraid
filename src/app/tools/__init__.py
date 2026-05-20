from __future__ import annotations

from fastmcp import FastMCP

from .divisao import divisao
from .multiplicacao import multiplicacao
from .soma import soma
from .subtracao import subtracao

__all__ = ["divisao", "multiplicacao", "register_tools", "soma", "subtracao"]


def register_tools(mcp: FastMCP) -> None:
    """Register the explicit production tool set."""
    mcp.add_tool(soma)
    mcp.add_tool(subtracao)
    mcp.add_tool(multiplicacao)
    mcp.add_tool(divisao)
