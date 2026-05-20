from fastmcp.tools.base import Tool
from mcp.types import ToolAnnotations

from ..auth import require_roles


def _health_check() -> dict:
    """Return a basic health payload for operational checks."""
    return {"status": "ok", "message": "MCP rodando com sucesso"}


health_check: Tool = Tool.from_function(
    _health_check,
    name="health_check",
    title="Health Check",
    description="Return a simple health payload for administrative checks.",
    annotations=ToolAnnotations(
        title="Health Check",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    output_schema={
        "type": "object",
        "properties": {
            "status": {"type": "string"},
            "message": {"type": "string"},
        },
        "required": ["status", "message"],
        "additionalProperties": False,
    },
    auth=require_roles("mcp-trc-admin"),
)
