[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Workspace
)

$ErrorActionPreference = 'Stop'
$workspacePath = [System.IO.Path]::GetFullPath($Workspace).TrimEnd('\')
if (-not (Test-Path -LiteralPath $workspacePath -PathType Container)) {
    throw "Workspace does not exist: $workspacePath"
}

$stateRoot = [System.IO.Path]::GetFullPath((Join-Path $workspacePath '.photo-grade'))
$currentPath = [System.IO.Path]::GetFullPath((Join-Path $stateRoot 'current'))
if (-not $currentPath.StartsWith($stateRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Resolved session path escaped the workspace state directory.'
}

$manifestPath = Join-Path $currentPath 'manifest.json'
if (Test-Path -LiteralPath $manifestPath) {
    $existing = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $protectedStates = @('pilot_applied', 'pilot_approved', 'batch_applied')
    if ($protectedStates -contains [string]$existing.status) {
        throw "The current session is '$($existing.status)' and may require rollback. Complete or roll it back before starting another task."
    }
}

if (Test-Path -LiteralPath $currentPath) {
    Remove-Item -LiteralPath $currentPath -Recurse -Force
}
New-Item -ItemType Directory -Path (Join-Path $currentPath 'before') -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $currentPath 'after') -Force | Out-Null

$manifest = [ordered]@{
    schema_version = 1
    status = 'planned'
    created_at = [DateTime]::UtcNow.ToString('o')
    updated_at = [DateTime]::UtcNow.ToString('o')
    selected_count = 0
    photos = @()
    applied_photo_ids = @()
    errors = @()
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Set-Content -LiteralPath (Join-Path $currentPath 'style-intent.md') -Value "# Style intent`r`n" -Encoding UTF8
Write-Output $currentPath
