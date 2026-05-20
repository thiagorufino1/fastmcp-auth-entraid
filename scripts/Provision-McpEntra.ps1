<#
.SYNOPSIS
    Idempotently provisions all Microsoft Entra ID resources required by the
    FastMCP server: App Registration, OAuth scope, App Roles, Service Principal,
    client secret, admin consent, security groups, and role assignments.

.DESCRIPTION
    Safe to re-run. Each step checks for existing resources before creating.
    Outputs a .env-compatible block (and optionally writes a file) so the
    application can be configured without manual copy-paste from the portal.

    Requires:
      - Azure CLI (az) authenticated against the target tenant
      - Permissions: Application Administrator OR Global Administrator
                     (for AllPrincipals admin consent step)

.PARAMETER TenantId
    Azure AD tenant GUID. Required.

.PARAMETER DisplayName
    Display name for the App Registration. Default: mcp-lab.

.PARAMETER ReadGroupName
    Display name for the read-only security group. Default: mcp-trc-read.

.PARAMETER AdminGroupName
    Display name for the admin security group. Default: mcp-trc-admin.

.PARAMETER OutEnvFile
    Optional path to write the generated .env block.

.PARAMETER SkipClientSecret
    Skip secret generation. Use for AUTH_MODE=jwt (no secret needed).

.PARAMETER SkipAdminConsent
    Skip the admin consent step (requires Global Admin). Apply consent
    manually in the portal if needed.

.EXAMPLE
    ./scripts/Provision-McpEntra.ps1 -TenantId 00000000-0000-0000-0000-000000000000

.EXAMPLE
    ./scripts/Provision-McpEntra.ps1 -TenantId $env:TENANT_ID `
        -DisplayName "mcp-lab-stg" -OutEnvFile .env.stg -SkipClientSecret
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$TenantId,
    [string]$DisplayName = 'mcp-lab',
    [string]$ReadGroupName = 'mcp-trc-read',
    [string]$AdminGroupName = 'mcp-trc-admin',
    [string]$OutEnvFile,
    [switch]$SkipClientSecret,
    [switch]$SkipAdminConsent
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot 'modules/McpEntra.psm1') -Force

Write-Host ""
Write-Host "Provisioning Entra resources for tenant $TenantId" -ForegroundColor Yellow
Write-Host ""

$current = & az account show --query "{tenantId:tenantId, user:user.name}" -o json 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "az CLI not authenticated. Run: az login --tenant $TenantId"
}
$account = $current | ConvertFrom-Json
if ($account.tenantId -ne $TenantId) {
    throw "az is on tenant $($account.tenantId), expected $TenantId. Run: az login --tenant $TenantId"
}
Write-Info "Authenticated as $($account.user) in tenant $TenantId"
Write-Host ""

$app = New-McpAppRegistration -DisplayName $DisplayName
$clientId = $app.appId
$objectId = $app.objectId

Set-McpIdentifierUri -AppId $clientId -Uri "api://$clientId"
Set-McpTokenVersion2 -ObjectId $objectId
$scopeId = Set-McpAccessAsUserScope -ObjectId $objectId

$roleSpecs = @{
    Read  = @{ Value = 'mcp-trc-read';  DisplayName = 'MCP Read';  Description = 'Acesso de leitura as ferramentas MCP' }
    Admin = @{ Value = 'mcp-trc-admin'; DisplayName = 'MCP Admin'; Description = 'Acesso administrativo as ferramentas MCP' }
}
$roleIds = Set-McpAppRoles -ObjectId $objectId -Roles $roleSpecs

$sp = New-McpServicePrincipal -AppId $clientId
$spId = $sp.id

$clientSecret = $null
if (-not $SkipClientSecret) {
    $clientSecret = New-McpClientSecret -AppId $clientId
}
else {
    Write-Info "Skipping client secret (AUTH_MODE=jwt does not need it)"
}

if (-not $SkipAdminConsent) {
    try {
        Grant-McpAdminConsent -ServicePrincipalId $spId -ScopeName 'access_as_user'
    }
    catch {
        Write-Warning "Admin consent failed. Grant manually via portal or with Global Admin account."
        Write-Warning $_.Exception.Message
    }
}
else {
    Write-Info "Skipping admin consent (apply manually in portal)"
}

$readGroupId = New-McpSecurityGroup -DisplayName $ReadGroupName
$adminGroupId = New-McpSecurityGroup -DisplayName $AdminGroupName

Set-McpAppRoleAssignment -PrincipalId $readGroupId  -ResourceId $spId -AppRoleId $roleIds['mcp-trc-read']  -RoleValue 'mcp-trc-read'
Set-McpAppRoleAssignment -PrincipalId $adminGroupId -ResourceId $spId -AppRoleId $roleIds['mcp-trc-admin'] -RoleValue 'mcp-trc-admin'

Write-Host ""
Write-Host "=== SUMMARY ===" -ForegroundColor Yellow
Write-Host "Tenant:        $TenantId"
Write-Host "Client ID:     $clientId"
Write-Host "App Object ID: $objectId"
Write-Host "SP Object ID:  $spId"
Write-Host "Read Group:    $readGroupId"
Write-Host "Admin Group:   $adminGroupId"
Write-Host ""

$envContent = @"
AZURE_TENANT_ID=$TenantId
AZURE_CLIENT_ID=$clientId
MCP_BASE_URL=http://localhost:8000
AUTH_MODE=jwt
"@

if ($clientSecret) {
    $envContent += "`nAZURE_CLIENT_SECRET=$clientSecret"
}

if ($OutEnvFile) {
    $envContent | Out-File $OutEnvFile -Encoding utf8 -NoNewline
    Write-Ok "Wrote $OutEnvFile"
    if ($clientSecret) {
        Write-Warning "File contains client_secret. Treat as sensitive."
    }
}
else {
    $safeEnvContent = @"
AZURE_TENANT_ID=$TenantId
AZURE_CLIENT_ID=$clientId
MCP_BASE_URL=http://localhost:8000
AUTH_MODE=jwt
"@
    Write-Host "=== .env values ===" -ForegroundColor Yellow
    Write-Host $safeEnvContent
    if ($clientSecret) {
        Write-Host ""
        Write-Warning "AZURE_CLIENT_SECRET was generated but not printed. Use -OutEnvFile to capture it securely."
    }
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "  - Add users to '$ReadGroupName' or '$AdminGroupName' via portal or:"
Write-Host "      az ad group member add --group $readGroupId --member-id <user-object-id>"
Write-Host ""
