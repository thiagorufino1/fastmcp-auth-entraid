# ADR-0002: Use App Roles instead of OAuth scopes for authorization

## Status

Accepted

## Context

Microsoft Entra ID supports two authorization primitives:

- **OAuth delegated scopes** (`scp` claim): the application defines
  scopes; the user (or admin) consents at sign-in time.
- **App Roles** (`roles` claim): the administrator assigns roles, either
  directly to users or to security groups; users cannot self-grant.

For an enterprise audit and RBAC story, the difference matters:

| Concern | OAuth scopes | App Roles |
|---------|--------------|-----------|
| Who decides access | User consents | Admin assigns |
| Revocation surface | User revokes consent | Admin removes group membership |
| Group-based delegation | No (scope is per-user-per-app) | Yes (assignable to groups) |
| Central audit | Partial | Full, via Entra audit log |

## Decision

Use App Roles (`mcp-trc-read`, `mcp-trc-admin`) as the authorization
primitive. Wire each tool with `auth=require_roles(...)` in FastMCP so that
`tools/list` is filtered per-token and `tools/call` is enforced again at
invocation. Assign roles to security groups (not directly to users), so
that access management is a group-membership change with no application
deployment.

Keep one OAuth scope, `access_as_user`, as the minimum required for
clients to obtain a token; it carries no authorization weight on its own.

## Consequences

Positive:

- Access changes are a group-membership edit; no code, no deploy.
- The audit trail in Entra ID is unified and central.
- LLM never sees tools the user cannot invoke (eliminates a class of
  prompt-injection attempts to call unauthorized tools).
- Self-assignment is impossible: roles require admin action.

Negative:

- Initial setup requires admin privileges (App Role creation, group
  creation, role assignment). Not a per-developer task.
- Role changes propagate **on the next token issued** (default 1 hour).
  For immediate revocation, Continuous Access Evaluation must be
  configured separately.
- Adding a new role still requires updating the App Registration manifest
  (now automated via `scripts/Provision-McpEntra.ps1`, but still a step).
