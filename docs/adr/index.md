# Architecture Decision Records

Lightweight log of architectural decisions for this project, following the
[Michael Nygard ADR template](https://github.com/joelparkerhenderson/architecture-decision-record/blob/main/locales/en/templates/decision-record-template-by-michael-nygard/index.md).

Each file is numbered and immutable once accepted. To revise a decision,
create a new ADR that supersedes the old one and update the **Status** of
the original to `Superseded by ADR-XXXX`.

## Index

| ID | Title | Status |
|----|-------|--------|
| [0001](0001-dual-auth-modes-jwt-and-oauth-proxy.md) | Dual authentication modes (JWT verifier and OAuth proxy) | Accepted |
| [0002](0002-app-roles-over-oauth-scopes.md) | Use App Roles instead of OAuth scopes for authorization | Accepted |
| [0003](0003-structlog-for-observability.md) | Use structlog with JSON output for observability | Accepted |
| [0004](0004-powershell-for-entra-provisioning.md) | Use PowerShell scripts (not Terraform) for Entra provisioning | Accepted |
| [0005](0005-reference-server-with-explicit-tool-registration.md) | Keep the server as a reference implementation with explicit tool registration | Accepted |

## Template

```markdown
# ADR-NNNN: <decision title>

## Status

Proposed | Accepted | Superseded by ADR-XXXX

## Context

What problem is being solved? What forces are at play (technical, social,
political, project)?

## Decision

What we decided to do, in active voice.

## Consequences

What becomes easier or harder. List both positive and negative outcomes.
```
