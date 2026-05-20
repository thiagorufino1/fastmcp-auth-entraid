from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.auth.verifier import RoleEnforcedJWTVerifier


@dataclass
class _FakeAccessToken:
    claims: dict[str, Any]


@pytest.fixture
def make_verifier(monkeypatch):
    def _factory(parent_return: _FakeAccessToken | None):
        async def _fake_super_verify(self, token: str):
            return parent_return

        monkeypatch.setattr(
            "app.auth.verifier.AzureJWTVerifier.verify_token",
            _fake_super_verify,
        )

        return RoleEnforcedJWTVerifier(
            allowed_roles=frozenset({"mcp-trc-read", "mcp-trc-admin"}),
            client_id="00000000-0000-0000-0000-000000000002",
            tenant_id="00000000-0000-0000-0000-000000000001",
            required_scopes=["access_as_user"],
        )

    return _factory


class TestRoleEnforcedJWTVerifier:
    async def test_returns_none_when_parent_returns_none(self, make_verifier):
        verifier = make_verifier(parent_return=None)
        assert await verifier.verify_token("any-token") is None

    async def test_returns_none_when_roles_claim_missing(self, make_verifier):
        token = _FakeAccessToken(claims={"sub": "alice"})
        verifier = make_verifier(parent_return=token)
        assert await verifier.verify_token("any-token") is None

    async def test_returns_none_when_roles_claim_empty(self, make_verifier):
        token = _FakeAccessToken(claims={"roles": []})
        verifier = make_verifier(parent_return=token)
        assert await verifier.verify_token("any-token") is None

    async def test_returns_none_when_role_not_in_allowed(self, make_verifier):
        token = _FakeAccessToken(claims={"roles": ["unauthorized-role"]})
        verifier = make_verifier(parent_return=token)
        assert await verifier.verify_token("any-token") is None

    async def test_returns_token_when_read_role_present(self, make_verifier):
        token = _FakeAccessToken(claims={"roles": ["mcp-trc-read"]})
        verifier = make_verifier(parent_return=token)
        assert await verifier.verify_token("any-token") is token

    async def test_returns_token_when_admin_role_present(self, make_verifier):
        token = _FakeAccessToken(claims={"roles": ["mcp-trc-admin"]})
        verifier = make_verifier(parent_return=token)
        assert await verifier.verify_token("any-token") is token

    async def test_returns_token_when_mixed_roles(self, make_verifier):
        token = _FakeAccessToken(
            claims={"roles": ["mcp-trc-read", "another-role"]}
        )
        verifier = make_verifier(parent_return=token)
        assert await verifier.verify_token("any-token") is token

    async def test_returns_none_with_empty_allowed_roles(self, monkeypatch):
        async def _fake_super_verify(self, token: str):
            return _FakeAccessToken(claims={"roles": ["mcp-trc-read"]})

        monkeypatch.setattr(
            "app.auth.verifier.AzureJWTVerifier.verify_token",
            _fake_super_verify,
        )
        verifier = RoleEnforcedJWTVerifier(
            allowed_roles=frozenset(),
            client_id="00000000-0000-0000-0000-000000000002",
            tenant_id="00000000-0000-0000-0000-000000000001",
            required_scopes=["access_as_user"],
        )
        assert await verifier.verify_token("any-token") is None
