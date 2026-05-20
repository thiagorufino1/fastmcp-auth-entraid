from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
import structlog
from structlog.testing import capture_logs

from app.auth.verifier import RoleEnforcedJWTVerifier


@dataclass
class _FakeAccessToken:
    claims: dict[str, Any]


@pytest.fixture
def _reset_structlog():
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


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


class TestVerifierLogging:
    async def test_logs_invalid_when_parent_returns_none(self, _reset_structlog, make_verifier):
        verifier = make_verifier(parent_return=None)
        with capture_logs() as events:
            await verifier.verify_token("x")
        assert any(e["event"] == "auth.token.invalid" for e in events)

    async def test_logs_rejected_with_subject_when_no_role(self, _reset_structlog, make_verifier):
        token = _FakeAccessToken(claims={"sub": "user-x", "roles": ["unauthorized"]})
        verifier = make_verifier(parent_return=token)
        with capture_logs() as events:
            await verifier.verify_token("x")
        rejected = next(e for e in events if e["event"] == "auth.token.rejected")
        assert rejected["subject"] == "user-x"
        assert rejected["reason"] == "no_allowed_role"
        assert rejected["token_roles"] == ["unauthorized"]

    async def test_logs_accepted_with_granted_roles(self, _reset_structlog, make_verifier):
        token = _FakeAccessToken(claims={"sub": "user-y", "roles": ["mcp-trc-admin", "other"]})
        verifier = make_verifier(parent_return=token)
        with capture_logs() as events:
            await verifier.verify_token("x")
        accepted = next(e for e in events if e["event"] == "auth.token.accepted")
        assert accepted["subject"] == "user-y"
        assert accepted["granted_roles"] == ["mcp-trc-admin"]

    async def test_never_logs_raw_token(self, _reset_structlog, make_verifier):
        token = _FakeAccessToken(claims={"sub": "user-z", "roles": ["mcp-trc-read"]})
        verifier = make_verifier(parent_return=token)
        with capture_logs() as events:
            await verifier.verify_token("super-secret-token-value")
        rendered = str(events)
        assert "super-secret-token-value" not in rendered
