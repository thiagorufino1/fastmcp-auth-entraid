from __future__ import annotations

from fastmcp.tools.base import Tool

from app.tools import divisao, multiplicacao, register_tools, soma, subtracao


class _FakeMcp:
    def __init__(self) -> None:
        self.added: list[Tool] = []

    def add_tool(self, tool: Tool) -> None:
        self.added.append(tool)


class TestToolRegistration:
    def test_exports_expected_tools(self):
        assert isinstance(soma, Tool)
        assert isinstance(subtracao, Tool)
        assert isinstance(multiplicacao, Tool)
        assert isinstance(divisao, Tool)

    def test_register_tools_is_explicit(self):
        mcp = _FakeMcp()
        register_tools(mcp)
        assert [tool.name for tool in mcp.added] == [
            "soma",
            "subtracao",
            "multiplicacao",
            "divisao",
        ]

    def test_register_tools_only_adds_known_tools(self):
        mcp = _FakeMcp()
        register_tools(mcp)
        assert {tool.name for tool in mcp.added} == {
            "soma",
            "subtracao",
            "multiplicacao",
            "divisao",
        }
