from __future__ import annotations

import dataclasses

import pytest

from app.config import (
    ALLOWED_ROLES,
    DEFAULT_AUTH_MODE,
    DEFAULT_BASE_URL,
    Settings,
    load_settings,
)


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "AZURE_TENANT_ID",
        "AZURE_CLIENT_ID",
        "AZURE_CLIENT_SECRET",
        "MCP_BASE_URL",
        "AUTH_MODE",
    ):
        monkeypatch.delenv(key, raising=False)


class TestAllowedRoles:
    def test_is_frozenset(self):
        assert isinstance(ALLOWED_ROLES, frozenset)

    def test_contains_expected_roles(self):
        assert frozenset({"mcp-trc-read", "mcp-trc-admin"}) == ALLOWED_ROLES


class TestSettingsDataclass:
    def test_is_frozen(self):
        settings = Settings(tenant_id="t", client_id="c")
        with pytest.raises(dataclasses.FrozenInstanceError):
            settings.tenant_id = "other"

    def test_defaults_applied(self):
        settings = Settings(tenant_id="t", client_id="c")
        assert settings.client_secret == ""
        assert settings.base_url == DEFAULT_BASE_URL
        assert settings.auth_mode == DEFAULT_AUTH_MODE

    def test_uses_slots(self):
        settings = Settings(tenant_id="t", client_id="c")
        assert not hasattr(settings, "__dict__")


class TestLoadSettings:
    def test_returns_settings_with_env(self, azure_env):
        settings = load_settings()
        assert settings.tenant_id == azure_env["AZURE_TENANT_ID"]
        assert settings.client_id == azure_env["AZURE_CLIENT_ID"]
        assert settings.client_secret == azure_env["AZURE_CLIENT_SECRET"]
        assert settings.base_url == azure_env["MCP_BASE_URL"]
        assert settings.auth_mode == "jwt"

    def test_missing_tenant_id_raises(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("AZURE_CLIENT_ID", "client")
        with pytest.raises(ValueError, match="AZURE_TENANT_ID"):
            load_settings()

    def test_missing_client_id_raises(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
        with pytest.raises(ValueError, match="AZURE_CLIENT_ID"):
            load_settings()

    def test_whitespace_only_env_treated_as_missing(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("AZURE_TENANT_ID", "   ")
        monkeypatch.setenv("AZURE_CLIENT_ID", "client")
        with pytest.raises(ValueError, match="AZURE_TENANT_ID"):
            load_settings()

    def test_invalid_auth_mode_raises(self, azure_env, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "invalid")
        with pytest.raises(ValueError, match="AUTH_MODE"):
            load_settings()

    def test_auth_mode_case_insensitive(self, azure_env, monkeypatch):
        monkeypatch.setenv("AUTH_MODE", "OAUTH")
        assert load_settings().auth_mode == "oauth"

    def test_client_secret_optional(self, azure_env, monkeypatch):
        monkeypatch.delenv("AZURE_CLIENT_SECRET", raising=False)
        assert load_settings().client_secret == ""

    def test_default_base_url(self, monkeypatch):
        _clear_env(monkeypatch)
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant")
        monkeypatch.setenv("AZURE_CLIENT_ID", "client")
        assert load_settings().base_url == DEFAULT_BASE_URL

    def test_empty_base_url_falls_back_to_default(self, azure_env, monkeypatch):
        monkeypatch.setenv("MCP_BASE_URL", "   ")
        assert load_settings().base_url == DEFAULT_BASE_URL

    def test_lru_cache_returns_same_instance(self, azure_env):
        assert load_settings() is load_settings()
