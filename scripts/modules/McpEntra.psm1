Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Info {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "    $Message" -ForegroundColor DarkGray
}

function Write-Ok {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Message)
    Write-Host "    [OK] $Message" -ForegroundColor Green
}

function Invoke-AzJson {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory, ValueFromRemainingArguments)]
        [string[]]$Args
    )
    $output = & az @Args 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "az command failed: $($Args -join ' ')`n$output"
    }
    if (-not $output) { return $null }
    return ($output | Out-String | ConvertFrom-Json)
}

function Get-AppRegistrationByName {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$DisplayName)
    $apps = Invoke-AzJson ad app list --display-name $DisplayName --query "[].{appId:appId, objectId:id, displayName:displayName}" -o json
    if (-not $apps) { return $null }
    return @($apps)[0]
}

function New-McpAppRegistration {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$DisplayName,
        [string]$SignInAudience = 'AzureADMyOrg'
    )
    Write-Step "App Registration: $DisplayName"
    $existing = Get-AppRegistrationByName -DisplayName $DisplayName
    if ($existing) {
        Write-Ok "already exists (appId=$($existing.appId))"
        return $existing
    }
    $created = Invoke-AzJson ad app create --display-name $DisplayName --sign-in-audience $SignInAudience --query "{appId:appId, objectId:id, displayName:displayName}" -o json
    Write-Ok "created (appId=$($created.appId))"
    return $created
}

function Set-McpTokenVersion2 {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$ObjectId)
    Write-Step "Token version v2"
    $bodyFile = New-TemporaryFile
    try {
        '{"api":{"requestedAccessTokenVersion":2}}' | Out-File $bodyFile -Encoding utf8 -NoNewline
        Invoke-AzJson rest --method PATCH `
            --uri "https://graph.microsoft.com/v1.0/applications/$ObjectId" `
            --headers "Content-Type=application/json" `
            --body "@$bodyFile" | Out-Null
        Write-Ok "set to 2"
    }
    finally { Remove-Item $bodyFile -Force -ErrorAction SilentlyContinue }
}

function Set-McpIdentifierUri {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$AppId,
        [Parameter(Mandatory)][string]$Uri
    )
    Write-Step "Identifier URI"
    $current = Invoke-AzJson ad app show --id $AppId --query "identifierUris" -o json
    if ($current -and ($current -contains $Uri)) {
        Write-Ok "already set ($Uri)"
        return
    }
    & az ad app update --id $AppId --identifier-uris $Uri 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to set identifier URI" }
    Write-Ok "set to $Uri"
}

function Set-McpAccessAsUserScope {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$ObjectId)
    Write-Step "OAuth scope: access_as_user"
    $app = Invoke-AzJson rest --method GET --uri "https://graph.microsoft.com/v1.0/applications/$ObjectId" -o json
    $api = @{}
    if ($app.api) {
        foreach ($prop in $app.api.PSObject.Properties) {
            $api[$prop.Name] = $prop.Value
        }
    }

    $currentScopes = @()
    if ($api.ContainsKey('oauth2PermissionScopes') -and $api.oauth2PermissionScopes) {
        $currentScopes = @($api.oauth2PermissionScopes | Where-Object { $_ })
    }

    $existingScopes = @($currentScopes | Where-Object { $_.value -eq 'access_as_user' })
    $scopeId = $null
    if ($existingScopes.Count -gt 0) {
        $scopeId = $existingScopes[0].id
    }
    else {
        $scopeId = [System.Guid]::NewGuid().ToString()
        $api.oauth2PermissionScopes = @(
            @($currentScopes) + @(@{
                adminConsentDescription = 'Acessar mcp-lab como o usuario autenticado'
                adminConsentDisplayName = 'Acessar mcp-lab'
                id                      = $scopeId
                isEnabled               = $true
                type                    = 'User'
                userConsentDescription  = 'Acessar mcp-lab em seu nome'
                userConsentDisplayName  = 'Acessar mcp-lab'
                value                   = 'access_as_user'
            })
        )
    }

    if ($api.requestedAccessTokenVersion -ne 2) {
        $api.requestedAccessTokenVersion = 2
    }

    $body = @{
        api = $api
    } | ConvertTo-Json -Depth 8 -Compress

    $bodyFile = New-TemporaryFile
    try {
        $body | Out-File $bodyFile -Encoding utf8 -NoNewline
        Invoke-AzJson rest --method PATCH `
            --uri "https://graph.microsoft.com/v1.0/applications/$ObjectId" `
            --headers "Content-Type=application/json" `
            --body "@$bodyFile" | Out-Null
        if ($existingScopes.Count -gt 0) {
            Write-Ok "already exists (id=$scopeId)"
        }
        else {
            Write-Ok "created (id=$scopeId)"
        }
        return $scopeId
    }
    finally { Remove-Item $bodyFile -Force -ErrorAction SilentlyContinue }
}

function Set-McpAppRoles {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ObjectId,
        [Parameter(Mandatory)][hashtable]$Roles
    )
    Write-Step "App Roles"
    $app = Invoke-AzJson rest --method GET --uri "https://graph.microsoft.com/v1.0/applications/$ObjectId" -o json
    $existingByValue = @{}
    foreach ($r in $app.appRoles) { $existingByValue[$r.value] = $r }

    $result = @{}
    $needsPatch = $false
    $newAppRoles = @()
    foreach ($r in $app.appRoles) { $newAppRoles += $r }

    foreach ($key in $Roles.Keys) {
        $spec = $Roles[$key]
        if ($existingByValue.ContainsKey($spec.Value)) {
            $existing = $existingByValue[$spec.Value]
            Write-Ok "role '$($spec.Value)' already exists (id=$($existing.id))"
            $result[$spec.Value] = $existing.id
            continue
        }
        $roleId = [System.Guid]::NewGuid().ToString()
        $newAppRoles += @{
            allowedMemberTypes = @('User', 'Application')
            description        = $spec.Description
            displayName        = $spec.DisplayName
            id                 = $roleId
            isEnabled          = $true
            value              = $spec.Value
        }
        $result[$spec.Value] = $roleId
        $needsPatch = $true
        Write-Info "queued role '$($spec.Value)' (id=$roleId)"
    }

    if ($needsPatch) {
        $body = @{ appRoles = $newAppRoles } | ConvertTo-Json -Depth 6 -Compress
        $bodyFile = New-TemporaryFile
        try {
            $body | Out-File $bodyFile -Encoding utf8 -NoNewline
            Invoke-AzJson rest --method PATCH `
                --uri "https://graph.microsoft.com/v1.0/applications/$ObjectId" `
                --headers "Content-Type=application/json" `
                --body "@$bodyFile" | Out-Null
            Write-Ok "patched appRoles"
        }
        finally { Remove-Item $bodyFile -Force -ErrorAction SilentlyContinue }
    }

    return $result
}

function New-McpServicePrincipal {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$AppId)
    Write-Step "Service Principal"
    $existing = Invoke-AzJson ad sp list --filter "appId eq '$AppId'" --query "[0].{id:id, appId:appId}" -o json
    if ($existing) {
        Write-Ok "already exists (id=$($existing.id))"
        return $existing
    }
    $sp = Invoke-AzJson ad sp create --id $AppId --query "{id:id, appId:appId}" -o json
    Write-Ok "created (id=$($sp.id))"
    return $sp
}

function New-McpClientSecret {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$AppId,
        [int]$Years = 1,
        [string]$DisplayName = 'mcp-lab-secret'
    )
    Write-Step "Client Secret (rotates on every run)"
    $secret = Invoke-AzJson ad app credential reset --id $AppId --years $Years --display-name $DisplayName --query "{password:password, endDateTime:endDateTime}" -o json --only-show-errors
    Write-Ok "issued (expires=$($secret.endDateTime))"
    return $secret.password
}

function Grant-McpAdminConsent {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$ServicePrincipalId,
        [Parameter(Mandatory)][string]$ScopeName
    )
    Write-Step "Admin consent (AllPrincipals): $ScopeName"
    $existing = Invoke-AzJson rest --method GET `
        --uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants?`$filter=clientId eq '$ServicePrincipalId' and resourceId eq '$ServicePrincipalId'" `
        -o json
    if ($existing.value -and (@($existing.value | Where-Object { $_.scope -like "*$ScopeName*" }).Count -gt 0)) {
        Write-Ok "already granted"
        return
    }
    $body = @{
        clientId    = $ServicePrincipalId
        consentType = 'AllPrincipals'
        resourceId  = $ServicePrincipalId
        scope       = $ScopeName
    } | ConvertTo-Json -Compress

    $bodyFile = New-TemporaryFile
    try {
        $body | Out-File $bodyFile -Encoding utf8 -NoNewline
        Invoke-AzJson rest --method POST `
            --uri "https://graph.microsoft.com/v1.0/oauth2PermissionGrants" `
            --headers "Content-Type=application/json" `
            --body "@$bodyFile" | Out-Null
        Write-Ok "granted"
    }
    finally { Remove-Item $bodyFile -Force -ErrorAction SilentlyContinue }
}

function New-McpSecurityGroup {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$DisplayName,
        [string]$MailNickname = $null
    )
    Write-Step "Security Group: $DisplayName"
    $existing = Invoke-AzJson rest --method GET `
        --uri "https://graph.microsoft.com/v1.0/groups?`$filter=displayName eq '$DisplayName'" `
        -o json
    if ($existing.value -and @($existing.value).Count -gt 0) {
        $g = @($existing.value)[0]
        Write-Ok "already exists (id=$($g.id))"
        return $g.id
    }

    if (-not $MailNickname) { $MailNickname = $DisplayName }
    $body = @{
        displayName     = $DisplayName
        mailEnabled     = $false
        mailNickname    = $MailNickname
        securityEnabled = $true
    } | ConvertTo-Json -Compress

    $bodyFile = New-TemporaryFile
    try {
        $body | Out-File $bodyFile -Encoding utf8 -NoNewline
        $created = Invoke-AzJson rest --method POST `
            --uri "https://graph.microsoft.com/v1.0/groups" `
            --headers "Content-Type=application/json" `
            --body "@$bodyFile" -o json
        Write-Ok "created (id=$($created.id))"
        return $created.id
    }
    finally { Remove-Item $bodyFile -Force -ErrorAction SilentlyContinue }
}

function Set-McpAppRoleAssignment {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$PrincipalId,
        [Parameter(Mandatory)][string]$ResourceId,
        [Parameter(Mandatory)][string]$AppRoleId,
        [Parameter(Mandatory)][string]$RoleValue
    )
    Write-Step "Assign role '$RoleValue' to principal $PrincipalId"
    $existing = Invoke-AzJson rest --method GET `
        --uri "https://graph.microsoft.com/v1.0/servicePrincipals/$ResourceId/appRoleAssignedTo" `
        -o json
    if ($existing.value -and @($existing.value).Count -gt 0) {
        $match = @($existing.value | Where-Object {
            $_.principalId -eq $PrincipalId -and $_.appRoleId -eq $AppRoleId
        })
        if ($match.Count -gt 0) {
            Write-Ok "already assigned"
            return
        }
    }

    $body = @{
        principalId = $PrincipalId
        resourceId  = $ResourceId
        appRoleId   = $AppRoleId
    } | ConvertTo-Json -Compress

    $bodyFile = New-TemporaryFile
    try {
        $body | Out-File $bodyFile -Encoding utf8 -NoNewline
        Invoke-AzJson rest --method POST `
            --uri "https://graph.microsoft.com/v1.0/groups/$PrincipalId/appRoleAssignments" `
            --headers "Content-Type=application/json" `
            --body "@$bodyFile" | Out-Null
        Write-Ok "assigned"
    }
    finally { Remove-Item $bodyFile -Force -ErrorAction SilentlyContinue }
}

function Remove-McpAppRegistration {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$DisplayName)
    Write-Step "Remove App Registration: $DisplayName"
    $existing = Get-AppRegistrationByName -DisplayName $DisplayName
    if (-not $existing) {
        Write-Ok "not present"
        return
    }
    & az ad app delete --id $existing.appId 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to delete app registration" }
    Write-Ok "deleted (appId=$($existing.appId))"
}

function Remove-McpSecurityGroup {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$DisplayName)
    Write-Step "Remove Security Group: $DisplayName"
    $existing = Invoke-AzJson rest --method GET `
        --uri "https://graph.microsoft.com/v1.0/groups?`$filter=displayName eq '$DisplayName'" `
        -o json
    if (-not $existing.value -or @($existing.value).Count -eq 0) {
        Write-Ok "not present"
        return
    }
    $g = @($existing.value)[0]
    Invoke-AzJson rest --method DELETE --uri "https://graph.microsoft.com/v1.0/groups/$($g.id)" | Out-Null
    Write-Ok "deleted (id=$($g.id))"
}

Export-ModuleMember -Function `
    Write-Step, Write-Info, Write-Ok, `
    Invoke-AzJson, Get-AppRegistrationByName, `
    New-McpAppRegistration, Set-McpTokenVersion2, Set-McpIdentifierUri, `
    Set-McpAccessAsUserScope, Set-McpAppRoles, New-McpServicePrincipal, `
    New-McpClientSecret, Grant-McpAdminConsent, New-McpSecurityGroup, `
    Set-McpAppRoleAssignment, Remove-McpAppRegistration, Remove-McpSecurityGroup
