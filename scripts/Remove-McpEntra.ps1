<#
.SYNOPSIS
    Removes Entra resources provisioned by Provision-McpEntra.ps1:
    App Registration (cascades Service Principal + secrets + assignments)
    and the security groups.

.PARAMETER TenantId
    Azure AD tenant GUID. Required.

.PARAMETER DisplayName
    Display name of the App Registration. Default: mcp-lab.

.PARAMETER ReadGroupName
    Display name of the read group. Default: mcp-trc-read.

.PARAMETER AdminGroupName
    Display name of the admin group. Default: mcp-trc-admin.

.PARAMETER Force
    Skip interactive confirmation.

.EXAMPLE
    ./scripts/Remove-McpEntra.ps1 -TenantId 00000000-0000-0000-0000-000000000000
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory)][string]$TenantId,
    [string]$DisplayName = 'mcp-lab',
    [string]$ReadGroupName = 'mcp-trc-read',
    [string]$AdminGroupName = 'mcp-trc-admin',
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot 'modules/McpEntra.psm1') -Force

$current = & az account show --query "tenantId" -o tsv 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "az CLI not authenticated. Run: az login --tenant $TenantId"
}
if ($current -ne $TenantId) {
    throw "az is on tenant $current, expected $TenantId."
}

Write-Host ""
Write-Warning "About to delete in tenant ${TenantId}:"
Write-Warning "  - App Registration '$DisplayName' (cascades SP, secrets, role assignments)"
Write-Warning "  - Security group  '$ReadGroupName'"
Write-Warning "  - Security group  '$AdminGroupName'"
Write-Host ""

if (-not $Force) {
    $answer = Read-Host "Type 'delete' to proceed"
    if ($answer -ne 'delete') {
        Write-Host "Aborted." -ForegroundColor Yellow
        return
    }
}

if ($PSCmdlet.ShouldProcess($DisplayName, 'Remove App Registration')) {
    Remove-McpAppRegistration -DisplayName $DisplayName
}
if ($PSCmdlet.ShouldProcess($ReadGroupName, 'Remove Security Group')) {
    Remove-McpSecurityGroup -DisplayName $ReadGroupName
}
if ($PSCmdlet.ShouldProcess($AdminGroupName, 'Remove Security Group')) {
    Remove-McpSecurityGroup -DisplayName $AdminGroupName
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
