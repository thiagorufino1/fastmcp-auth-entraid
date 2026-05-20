from fastmcp.tools.base import Tool
from mcp.types import ToolAnnotations

from ..auth import require_roles


def _multiplicacao(a: int, b: int) -> dict:
    """Multiply two numbers and return a structured result."""
    return {"a": a, "b": b, "resultado": a * b}


multiplicacao: Tool = Tool.from_function(
    _multiplicacao,
    name="multiplicacao",
    title="Multiplicação",
    description="Multiply two numbers and return the operands plus the result.",
    annotations=ToolAnnotations(
        title="Multiplicação",
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
