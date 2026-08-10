[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9_-]+\.md$')]
    [string]$TasteFile,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Entry
)

$ErrorActionPreference = 'Stop'
$tasteRoot = [System.IO.Path]::GetFullPath((Join-Path $env:USERPROFILE '.photo-grade\tastes')).TrimEnd('\')
New-Item -ItemType Directory -Path $tasteRoot -Force | Out-Null
$target = [System.IO.Path]::GetFullPath((Join-Path $tasteRoot $TasteFile))
if (-not $target.StartsWith($tasteRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'Taste file escaped the configured taste directory.'
}

$cleanEntry = ($Entry -replace '[\r\n]+', ' ').Trim()
if ([string]::IsNullOrWhiteSpace($cleanEntry)) {
    throw 'Taste entry is empty.'
}

if (-not (Test-Path -LiteralPath $target)) {
    Set-Content -LiteralPath $target -Value "# Confirmed taste`r`n" -Encoding UTF8
}
$existing = Get-Content -LiteralPath $target -Raw
if ($existing -match [regex]::Escape($cleanEntry)) {
    Write-Output "Already present: $target"
    exit 0
}

$datedLine = "- $([DateTime]::Now.ToString('yyyy-MM-dd')): $cleanEntry"
Add-Content -LiteralPath $target -Value $datedLine -Encoding UTF8
Write-Output "Appended confirmed taste: $target"
