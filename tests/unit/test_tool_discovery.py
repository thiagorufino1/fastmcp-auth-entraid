from __future__ import annotations

from fastmcp.tools.base import Tool

from app.tools import health_check, register_tools, soma


class _FakeMcp:
    def __init__(self) -> None:
        self.added: list[Tool] = []

    def add_tool(self, tool: Tool) -> None:
        self.added.append(tool)


class TestToolRegistration:
    def test_soma_is_tool(self):
        assert isinstance(soma, Tool)
        assert soma.name == "soma"

    def test_health_check_is_tool(self):
        assert isinstance(health_check, Tool)
        assert health_check.name == "health_check"

    def test_register_tools_adds_both(self):
        mcp = _FakeMcp()
        register_tools(mcp)
        assert {t.name for t in mcp.added} == {"soma", "health_check"}

    def test_register_tools_no_extras(self):
        mcp = _FakeMcp()
        register_tools(mcp)
        assert len(mcp.added) == 2
