from fastmcp.tools.base import Tool
from mcp.types import ToolAnnotations

from ..auth import require_roles


def _subtracao(a: int, b: int) -> dict:
    """Subtract the second number from the first and return the result."""
    return {"a": a, "b": b, "resultado": a - b}


subtracao: Tool = Tool.from_function(
    _subtracao,
    name="subtracao",
    title="Subtração",
    description=(
        "Subtract the second number from the first and return the operands "
        "plus the result."
    ),
    annotations=ToolAnnotations(
        title="Subtração",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    ),
    output_schema={
        "type": "object",
        "properties": {
            "a": {"type": "integer"},
            "b": {"type": "integer"},
            "resultado": {"type": "integer"},
        },
        "required": ["a", "b", "resultado"],
        "additionalProperties": False,
    },
    auth=require_roles("mcp-trc-read", "mcp-trc-admin"),
)
