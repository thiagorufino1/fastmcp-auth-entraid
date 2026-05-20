from fastmcp.tools.base import Tool
from mcp.types import ToolAnnotations

from ..auth import require_roles


def _soma(a: int, b: int) -> dict:
    """Add two numbers and return a structured result."""
    return {"a": a, "b": b, "resultado": a + b}


soma: Tool = Tool.from_function(
    _soma,
    name="soma",
    title="Soma",
    description="Add two numbers and return the operands plus the result.",
    annotations=ToolAnnotations(
        title="Soma",
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
