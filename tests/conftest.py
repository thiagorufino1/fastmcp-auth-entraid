from __future__ import annotations

import pytest

from app.config import load_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    load_settings.cache_clear()
    yield
    load_settings.cache_clear()


@pytest.fixture
def azure_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    env = {
        "AZURE_TENANT_ID": "00000000-0000-0000-0000-000000000001",
        "AZURE_CLIENT_ID": "00000000-0000-0000-0000-000000000002",
        "AZURE_CLIENT_SECRET": "test-secret",
        "MCP_BASE_URL": "http://localhost:8000",
        "AUTH_MODE": "jwt",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return env


@pytest.fixture
def oauth_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    env = {
        "AZURE_TENANT_ID": "00000000-0000-0000-0000-000000000001",
        "AZURE_CLIENT_ID": "00000000-0000-0000-0000-000000000002",
        "AZURE_CLIENT_SECRET": "test-secret",
        "MCP_BASE_URL": "http://localhost:8000",
        "AUTH_MODE": "oauth",
        "FASTMCP_JWT_SIGNING_KEY": "0123456789abcdef0123456789abcdef",
        "MCP_OAUTH_STORAGE_DIR": "C:/tmp/fastmcp-oauth",
        "MCP_OAUTH_STORAGE_ENCRYPTION_KEY": "_RdrBTlITrfR1U-z06trb46JkNIvk2lkGEDdcsdIO_A=",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return env
