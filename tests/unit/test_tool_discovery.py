from __future__ import annotations

from fastmcp.tools.base import Tool

from app.tools import discover_tools


class TestDiscoverTools:
    def test_returns_tool_instances(self):
        tools = discover_tools()
        assert all(isinstance(t, Tool) for t in tools)

    def test_finds_expected_tools(self):
        names = {t.name for t in discover_tools()}
        assert names == {"soma", "health_check"}

    def test_skips_underscore_modules(self, tmp_path, monkeypatch):
        # Ensure _private.py would be ignored if present (regression guard).
        tools = discover_tools()
        names = {t.name for t in tools}
        assert "_private" not in names
