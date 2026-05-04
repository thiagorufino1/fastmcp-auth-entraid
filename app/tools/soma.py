from fastmcp.tools.base import Tool

from ..auth import require_roles


def _soma(a: int, b: int) -> dict:
    """Soma dois números. Requer role mcp-trc-read ou mcp-trc-admin."""
    return {"a": a, "b": b, "resultado": a + b}


soma: Tool = Tool.from_function(
    _soma,
    name="soma",
    auth=require_roles("mcp-trc-read", "mcp-trc-admin"),
)
