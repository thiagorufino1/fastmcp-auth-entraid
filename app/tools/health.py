from fastmcp.tools.base import Tool

from ..auth import require_roles


def _health_check() -> dict:
    """Verifica se o MCP está funcionando. Requer role mcp-trc-admin."""
    return {"status": "ok", "message": "MCP rodando com sucesso"}


health_check: Tool = Tool.from_function(
    _health_check,
    name="health_check",
    auth=require_roles("mcp-trc-admin"),
)
