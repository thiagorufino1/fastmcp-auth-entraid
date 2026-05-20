from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.auth.checks import require_roles


@dataclass
class _FakeToken:
    claims: dict[str, Any]


@dataclass
class _FakeContext:
    token: _FakeToken | None


class TestRequireRoles:
    def test_returns_false_when_token_is_none(self):
        check = require_roles("mcp-trc-read")
        assert check(_FakeContext(token=None)) is False

    def test_returns_false_when_roles_claim_missing(self):
        check = require_roles("mcp-trc-read")
        ctx = _FakeContext(token=_FakeToken(claims={"sub": "alice"}))
        assert check(ctx) is False

    def test_returns_false_when_roles_claim_empty(self):
        check = require_roles("mcp-trc-read")
        ctx = _FakeContext(token=_FakeToken(claims={"roles": []}))
        assert check(ctx) is False

    def test_returns_true_when_single_role_matches(self):
        check = require_roles("mcp-trc-read")
        ctx = _FakeContext(token=_FakeToken(claims={"roles": ["mcp-trc-read"]}))
        assert check(ctx) is True

    def test_or_semantics_across_required_roles(self):
        check = require_roles("mcp-trc-read", "mcp-trc-admin")
        ctx = _FakeContext(token=_FakeToken(claims={"roles": ["mcp-trc-admin"]}))
        assert check(ctx) is True

    def test_returns_false_when_no_required_role_present(self):
        check = require_roles("mcp-trc-admin")
        ctx = _FakeContext(token=_FakeToken(claims={"roles": ["mcp-trc-read"]}))
        assert check(ctx) is False

    def test_extra_roles_in_token_do_not_break(self):
        check = require_roles("mcp-trc-read")
        ctx = _FakeContext(token=_FakeToken(claims={"roles": ["mcp-trc-read", "other-role"]}))
        assert check(ctx) is True

    def test_no_required_roles_always_false(self):
        check = require_roles()
        ctx = _FakeContext(token=_FakeToken(claims={"roles": ["mcp-trc-read"]}))
        assert check(ctx) is False
