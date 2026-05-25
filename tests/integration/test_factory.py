from __future__ import annotations

import pytest
from fastmcp import FastMCP
from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.azure import AzureProvider

from app.server import create_mcp


class TestCreateMcp:
    def test_returns_fastmcp_instance(self, azure_env):
        mcp = create_mcp()
        assert isinstance(mcp, FastMCP)

    def test_server_name_is_mcp_lab(self, azure_env):
        mcp = create_mcp()
        assert mcp.name == "mcp-lab"

    def test_default_mode_uses_remote_auth_provider(self, azure_env):
        mcp = create_mcp()
        assert isinstance(mcp.auth, RemoteAuthProvider)

    def test_oauth_mode_uses_azure_provider(self, oauth_env):
        mcp = create_mcp()
        assert isinstance(mcp.auth, AzureProvider)

    def test_oauth_mode_without_secret_raises(self, azure_env, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "oauth")
        monkeypatch.delenv("AZURE_CLIENT_SECRET", raising=False)
        with pytest.raises(ValueError, match="AZURE_CLIENT_SECRET"):
            create_mcp()

    async def test_expected_tools_registered(self, azure_env):
        mcp = create_mcp()
        tools = await mcp._list_tools()
        assert {t.name for t in tools} == {"soma", "subtracao", "multiplicacao", "divisao"}

    def test_audit_middleware_registered(self, azure_env):
        from app.middleware import AuditMiddleware

        mcp = create_mcp()
        middlewares = getattr(mcp, "_middleware", None) or getattr(mcp, "middleware", [])
        assert any(isinstance(m, AuditMiddleware) for m in middlewares)
