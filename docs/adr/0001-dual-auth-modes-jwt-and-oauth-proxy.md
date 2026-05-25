# ADR-0001: Dual authentication modes (JWT verifier and OAuth proxy)

## Status

Accepted

## Context

The server must support two distinct client populations:

1. **Programmatic clients** (custom portals, Azure App Service with
   On-Behalf-Of, Azure Container Apps with Managed Identity, automation
   scripts) that already hold an Entra ID JWT and pass it as a Bearer
   header.
2. **Interactive MCP clients** (Claude Desktop, Cursor, VS Code MCP
   extensions) that expect the server itself to drive an OAuth 2.0
   browser-based login flow.

FastMCP exposes two compatible primitives: `RemoteAuthProvider` +
`AzureJWTVerifier` for case 1, and `AzureProvider` (OAuth Proxy pattern)
for case 2. They cannot coexist within a single server instance.

## Decision

Expose both modes behind a single `AUTH_MODE` environment variable
(`jwt` | `oauth`, default `jwt`). The factory `create_mcp()` selects the
appropriate provider via `build_auth_provider(settings)`. Authorization
(App Roles, per-tool `auth=` checks) is identical between modes.

## Consequences

Positive:

- Same code base, deployment image, and authorization model serves both
  client populations.
- Operators switch modes by changing one env var and restarting; no code
  fork.
- Tests cover both branches via a single factory.

Negative:

- A given **instance** can only serve one population. Multi-tenant
  scenarios require two deployments (or a routing layer).
- `AZURE_CLIENT_SECRET` is mandatory in `oauth` mode and irrelevant in
  `jwt` mode; the secret-handling story differs across environments.
- `oauth` mode also requires persistent client storage and a stable JWT
  signing key for production use.
- Documentation must explain both flows, doubling the surface area.
