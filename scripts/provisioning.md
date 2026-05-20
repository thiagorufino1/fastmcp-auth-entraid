# provisioning.md

Versioned, idempotent PowerShell automation for the Microsoft Entra ID
resources required by the FastMCP server. Replaces the ad-hoc `az`/`az rest`
snippets in the root `README.md` with a single re-runnable provisioning script
plus a teardown counterpart.

## What gets created

`Provision-McpEntra.ps1` provisions, in order:

1. **App Registration**: display name configurable, `signInAudience=AzureADMyOrg`
2. **Identifier URI**: `api://<client-id>`
3. **Token version**: `requestedAccessTokenVersion: 2` (rejects v1.0 tokens)
4. **OAuth scope**: `access_as_user` (delegated, user consent)
5. **App Roles**: `mcp-trc-read` and `mcp-trc-admin` (allowed: `User`, `Application`)
6. **Service Principal**: enables sign-ins for the App Registration
7. **Client Secret**: optional, only for `AUTH_MODE=oauth`
8. **Admin Consent**: `AllPrincipals` grant for `access_as_user`
9. **Security Groups**: `mcp-trc-read`, `mcp-trc-admin`
10. **App Role Assignments**: group -> role bindings

Every step is idempotent: re-running detects existing resources and skips
creation. App Roles are merged into the existing `appRoles` collection rather
than replaced.

## Requirements

- **Azure CLI** (`az`) authenticated against the target tenant
- **PowerShell** 7+ recommended (5.1 works for the calls used here)
- **Permissions** of the running user:
  - `Application Administrator` (minimum) - to create App Registration, SP, App Roles
  - `Group Administrator` or `Groups Administrator` - to create security groups
  - `Privileged Role Administrator` or `Global Administrator` - only for the
    `AllPrincipals` admin consent step. Use `-SkipAdminConsent` if delegating
    this to a separate process.

## Quick start

```powershell
az login --tenant <TENANT_ID>

# Default names: mcp-lab / mcp-trc-read / mcp-trc-admin
./scripts/Provision-McpEntra.ps1 -TenantId <TENANT_ID>

# Capture the .env block to a file (treat as sensitive if secret was issued)
./scripts/Provision-McpEntra.ps1 -TenantId <TENANT_ID> -OutEnvFile .env

# JWT mode only (no client secret)
./scripts/Provision-McpEntra.ps1 -TenantId <TENANT_ID> -SkipClientSecret

# Skip admin consent (apply manually in portal afterwards)
./scripts/Provision-McpEntra.ps1 -TenantId <TENANT_ID> -SkipAdminConsent

# Custom names per environment
./scripts/Provision-McpEntra.ps1 -TenantId <TENANT_ID> `
    -DisplayName    "mcp-lab-stg" `
    -ReadGroupName  "mcp-trc-read-stg" `
    -AdminGroupName "mcp-trc-admin-stg" `
    -OutEnvFile     .env.stg
```

The script ends by printing or writing a `.env`-compatible block:

```env
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
MCP_BASE_URL=http://localhost:8000
AUTH_MODE=jwt
AZURE_CLIENT_SECRET=...   # only if not -SkipClientSecret
```

## Adding users to groups

The script creates empty security groups. Add members manually or with:

```powershell
$USER_OID = az ad user show --id user@example.com --query id -o tsv
az ad group member add --group <group-object-id> --member-id $USER_OID
```

Removing a user takes effect on the **next token issued** (default 1 hour),
not on existing tokens. For immediate revocation, configure
[Continuous Access Evaluation](https://learn.microsoft.com/entra/identity/conditional-access/concept-continuous-access-evaluation).

## Teardown

```powershell
./scripts/Remove-McpEntra.ps1 -TenantId <TENANT_ID>
```

Confirms interactively (type `delete`) unless `-Force` is passed. Removing the
App Registration cascades the Service Principal, secrets, and any App Role
assignments tied to it. Security groups are removed separately.

## Layout

```
scripts/
|-- provisioning.md
|-- Provision-McpEntra.ps1   # orchestrator
|-- Remove-McpEntra.ps1      # teardown
`-- modules/
    `-- McpEntra.psm1        # reusable, idempotent functions
```

`McpEntra.psm1` is the unit of reuse: each helper is named `Verb-McpNoun`,
uses `Set-StrictMode -Version Latest`, and treats missing resources as the
trigger to create rather than fail.

## Operational notes

- **Client secrets rotate on every run.** `New-McpClientSecret` calls
  `az ad app credential reset`, which generates a fresh secret and invalidates
  previous ones with the same display name. Capture the output immediately or
  use `-SkipClientSecret`.
- **Secrets stay out of stdout.** The provisioning script no longer prints
  `AZURE_CLIENT_SECRET` to the terminal. Use `-OutEnvFile` to capture the
  generated `.env` block.
- **Secrets in shell history.** Treat the output file as sensitive. Protect it
  the same way you would treat `.env`.
- **Production should use Key Vault.** This script issues the secret directly.
  For non-dev environments, store the secret in Azure Key Vault and reference
  it from Azure Container Apps via Managed Identity instead of `.env`.
- **No state file.** Each run inspects the tenant rather than relying on local
  state. Manual portal changes that match the same names will be detected as
  already-present and left alone.
- **No drift detection.** Unlike Terraform, manual edits in the portal that
  diverge from the expected configuration (e.g., a removed App Role) are not
  reconciled automatically. Re-running the script will only add missing items.

## Limitations

- **Tenant restrictions.** Many corporate tenants block programmatic App
  Registration creation. Coordinate with IAM team if `az ad app create` fails.
- **Admin consent is non-delegable.** The `AllPrincipals` grant requires
  `Privileged Role Administrator` or `Global Administrator`. Service principals
  used in CI/CD typically cannot perform this step.
- **PowerShell only.** No Bash/CLI port is provided. The root `README.md` still
  documents the manual `az`/`az rest` flow for environments without PowerShell.
