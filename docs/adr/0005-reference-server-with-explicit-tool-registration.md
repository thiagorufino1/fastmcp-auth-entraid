# ADR-0005: Keep the server as a reference implementation with explicit tool registration

## Status

Accepted

## Context

This repository is intended to be a reference for creating other MCP
servers in corporate environments.

That goal creates a few constraints:

1. The code should stay small enough to understand quickly.
2. The runtime surface should remain predictable and easy to audit.
3. New tools should not appear implicitly just because a file exists in a
   directory.
4. Future projects should be able to copy the structure without inheriting
   accidental complexity.

Implicit discovery is convenient for prototypes, but it weakens
governance. A tool can be added, renamed, or removed without a deliberate
registration change, and that makes security review and impact analysis
harder.

## Decision

Keep this repository intentionally small and use explicit tool
registration in production.

- Tools are defined as separate modules under `src/app/tools/`.
- `src/app/tools/__init__.py` is the single registration point.
- `register_tools(mcp)` adds an allowlisted set of tools explicitly.
- No automatic directory scanning is used at runtime.
- Reference tools remain small, simple, and easy to copy into new
  projects.

## Consequences

Positive:

- The exposed tool set is predictable and reviewable.
- Security review becomes simpler because the registration surface is
  explicit.
- New reference projects can follow the same pattern without hidden
  conventions.
- Tool inventory in tests can assert the exact expected set.

Negative:

- Adding a new tool requires touching the central registration module.
- The developer experience is slightly less convenient than auto-discovery.
- Small prototype changes require one extra edit in the registration file.

## Notes

This ADR does not prohibit auto-discovery in every possible context. It
only establishes that production deployments and the reference project
itself should use explicit registration.
