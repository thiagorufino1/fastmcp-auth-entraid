from fastmcp.tools.base import Tool
from mcp.types import ToolAnnotations

from ..auth import require_roles


def _divisao(a: int, b: int) -> dict:
    """Divide the first number by the second and return the result."""
    if b == 0:
        raise ValueError("divisor must be different from zero")
    return {"a": a, "b": b, "resultado": a / b}


divisao: Tool = Tool.from_function(
    _divisao,
    name="divisao",
    title="Divisão",
    description="Divide the first number by the second and return the operands plus the result.",
    annotations=ToolAnnotations(
        title="Divisão",
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
            "resultado": {"type": "number"},
        },
        "required": ["a", "b", "resultado"],
        "additionalProperties": False,
    },
    auth=require_roles("mcp-trc-read", "mcp-trc-admin"),
)
