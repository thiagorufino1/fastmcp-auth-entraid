# ADR-0004: Use PowerShell scripts (not Terraform) for Entra provisioning

## Status

Accepted

## Context

The Microsoft Entra ID resources required by this project (App
Registration, OAuth scope, App Roles, Service Principal, client secret,
admin consent, security groups, role assignments) were originally
documented as ad-hoc `az`/`az rest` snippets in `README.md`. This
introduces:

- No version control of the desired-state configuration
- No idempotency: re-running fails on already-created resources
- No drift detection
- No multi-environment story (dev, staging, prod must be copy-pasted)

Alternatives considered:

- **Terraform with `azuread` provider**: first-class support for App
  Registrations, App Roles, security groups, and assignments. State file
  + drift detection. But requires backend state (Azure Storage), more
  tooling on the developer machine, and authentication choices (service
  principal vs federated workload identity).
- **Bicep**: native to Azure, but **does not support Microsoft Graph
  resources** directly (App Registration, App Roles, groups). Would
  require `deploymentScripts` wrappers around `az`, which is a worse
  experience than plain PowerShell.
- **PowerShell scripts**: zero new dependencies (operators already need
  `az`), idempotent if written defensively, easy to audit step-by-step,
  no state to manage. No drift detection.

## Decision

Implement Entra provisioning as a PowerShell module + orchestrator script
under `scripts/`:

- `scripts/modules/McpEntra.psm1`: reusable, idempotent helpers
  (`New-McpAppRegistration`, `Set-McpTokenVersion2`, `Set-McpAppRoles`,
  `New-McpSecurityGroup`, etc.). Each helper checks before creating.
- `scripts/Provision-McpEntra.ps1`: orchestrator with parameters for
  display name, group names, output env file, and switches to skip
  client secret or admin consent.
- `scripts/Remove-McpEntra.ps1`: teardown using
  `SupportsShouldProcess` and `ConfirmImpact = High`.

If, in the future, infrastructure provisioning expands to Azure Container
Apps, Azure Container Registry, Key Vault, and Log Analytics, that work
should be done in Terraform (`azurerm` provider) and live in a separate
`infra/` directory. PowerShell stays scoped to Entra only.

## Consequences

Positive:

- Replaces error-prone README snippets with versioned, re-runnable code.
- No new tooling required beyond `az` (which operators already have).
- Idempotent: re-running detects existing resources and skips creation.
- Multi-environment story via parameters (`-DisplayName mcp-lab-stg` etc.)
- Each script step is auditable line-by-line.

Negative:

- **No drift detection**: a manual edit in the Azure Portal that diverges
  from the script will not be reconciled automatically. Re-running the
  script only adds missing items.
- Imperative rather than declarative; refactoring is harder than in
  Terraform.
- PowerShell-only; no Bash port. Environments without PowerShell must
  fall back to the manual README flow.
- Admin consent (`AllPrincipals`) requires Global Administrator or
  Privileged Role Administrator, which a CI/CD service principal
  typically lacks. `-SkipAdminConsent` is provided for those cases.
