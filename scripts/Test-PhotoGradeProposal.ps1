[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Path
)

$ErrorActionPreference = 'Stop'
$proposalPath = [System.IO.Path]::GetFullPath($Path)
if (-not (Test-Path -LiteralPath $proposalPath -PathType Leaf)) {
    throw "Proposal not found: $proposalPath"
}

function Get-PropertyNames($Object) {
    if ($null -eq $Object) { return @() }
    return @($Object.PSObject.Properties.Name)
}

function Get-PropertyValue($Object, [string]$Name) {
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Test-FiniteNumber($Value) {
    if ($Value -isnot [ValueType] -or $Value -is [bool]) { return $false }
    try { $number = [double]$Value } catch { return $false }
    return -not [double]::IsNaN($number) -and -not [double]::IsInfinity($number)
}

$rules = @{
    Exposure2012 = @(-5, 5, 1.25)
    Contrast2012 = @(-100, 100, 50)
    Highlights2012 = @(-100, 100, 60)
    Shadows2012 = @(-100, 100, 60)
    Whites2012 = @(-100, 100, 50)
    Blacks2012 = @(-100, 100, 50)
    Vibrance = @(-100, 100, 35)
    Saturation = @(-100, 100, 30)
    Tint = @(-150, 150, 25)
    ParametricShadows = @(-100, 100, 40)
    ParametricDarks = @(-100, 100, 40)
    ParametricLights = @(-100, 100, 40)
    ParametricHighlights = @(-100, 100, 40)
}
$hslAxes = @('Hue', 'Saturation', 'Luminance')
$hslColors = @('Red', 'Orange', 'Yellow', 'Green', 'Aqua', 'Blue', 'Purple', 'Magenta')
$hslFlatKeys = @()
foreach ($axis in @('HueAdjustment', 'SaturationAdjustment', 'LuminanceAdjustment')) {
    foreach ($color in $hslColors) { $hslFlatKeys += "$axis$color" }
}
$allowed = @($rules.Keys) + @('WhiteBalance', 'Temperature', 'HSL') + $hslFlatKeys
$errors = [System.Collections.Generic.List[string]]::new()

try { $document = Get-Content -LiteralPath $proposalPath -Raw | ConvertFrom-Json } catch { throw "Invalid JSON: $($_.Exception.Message)" }
$photos = @($document.photos)
if ($null -eq $document.photos -or $photos.Count -lt 1) { $errors.Add('photos must contain at least one item.') }
if ($photos.Count -gt 100) { $errors.Add('photos exceeds the 100-photo V1 limit.') }

$seenIds = @{}
foreach ($photo in $photos) {
    $id = [string]$photo.photo_id
    if ([string]::IsNullOrWhiteSpace($id)) { $errors.Add('Every photo requires photo_id.'); continue }
    if ($seenIds.ContainsKey($id)) { $errors.Add("Duplicate photo_id: $id") } else { $seenIds[$id] = $true }
    if ($null -eq $photo.baseline_develop) { $errors.Add("$id is missing baseline_develop."); continue }
    if ($null -eq $photo.proposed_settings) { $errors.Add("$id is missing proposed_settings."); continue }

    foreach ($key in (Get-PropertyNames $photo.proposed_settings)) {
        if ($allowed -notcontains $key) { $errors.Add("$id uses forbidden key '$key'."); continue }
        $baselineNames = Get-PropertyNames $photo.baseline_develop
        if ($baselineNames -notcontains $key) { $errors.Add("$id has no baseline value for '$key'."); continue }
        $newValue = Get-PropertyValue $photo.proposed_settings $key
        $oldValue = Get-PropertyValue $photo.baseline_develop $key

        if ($key -eq 'WhiteBalance') {
            if ($newValue -ne $oldValue -and $newValue -ne 'Custom') { $errors.Add("$id WhiteBalance must stay unchanged or be Custom.") }
            continue
        }
        if ($key -eq 'HSL') {
            foreach ($axis in (Get-PropertyNames $newValue)) {
                if ($hslAxes -notcontains $axis) { $errors.Add("$id HSL uses forbidden axis '$axis'."); continue }
                $newAxis = Get-PropertyValue $newValue $axis
                $oldAxis = Get-PropertyValue $oldValue $axis
                if ($null -eq $oldAxis) { $errors.Add("$id HSL.$axis has no baseline object."); continue }
                foreach ($color in (Get-PropertyNames $newAxis)) {
                    if ($hslColors -notcontains $color) { $errors.Add("$id HSL.$axis uses forbidden color '$color'."); continue }
                    $newChannel = Get-PropertyValue $newAxis $color
                    $oldChannel = Get-PropertyValue $oldAxis $color
                    if ($null -eq $oldChannel) { $errors.Add("$id HSL.$axis.$color has no baseline value."); continue }
                    if (-not (Test-FiniteNumber $newChannel) -or -not (Test-FiniteNumber $oldChannel)) { $errors.Add("$id HSL.$axis.$color must be finite numeric values."); continue }
                    if ([double]$newChannel -lt -100 -or [double]$newChannel -gt 100 -or [math]::Abs([double]$newChannel - [double]$oldChannel) -gt 35) { $errors.Add("$id HSL.$axis.$color exceeds its bound or delta limit.") }
                }
            }
            continue
        }
        if ($hslFlatKeys -contains $key) {
            if (-not (Test-FiniteNumber $newValue) -or -not (Test-FiniteNumber $oldValue)) { $errors.Add("$id '$key' must use finite numeric baseline and proposed values."); continue }
            if ([double]$newValue -lt -100 -or [double]$newValue -gt 100 -or [math]::Abs([double]$newValue - [double]$oldValue) -gt 35) { $errors.Add("$id '$key' exceeds its bound or delta limit.") }
            continue
        }
        if (-not (Test-FiniteNumber $newValue) -or -not (Test-FiniteNumber $oldValue)) { $errors.Add("$id '$key' must use finite numeric baseline and proposed values."); continue }

        if ($key -eq 'Temperature') {
            $rawLike = ([string]$photo.source_type).ToLowerInvariant() -eq 'raw'
            if ([math]::Abs([double]$oldValue) -gt 500) {
                $minimum, $maximum, $delta = 2000, 50000, 2500
            } else {
                $minimum, $maximum, $delta = -100, 100, $(if ($rawLike) { 35 } else { 20 })
            }
        } else {
            $minimum, $maximum, $delta = $rules[$key]
        }
        if ([double]$newValue -lt $minimum -or [double]$newValue -gt $maximum) { $errors.Add("$id '$key' is outside [$minimum, $maximum].") }
        if ([math]::Abs([double]$newValue - [double]$oldValue) -gt $delta) { $errors.Add("$id '$key' changes by more than $delta.") }
    }
}

if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Error $_ }
    throw "Proposal validation failed with $($errors.Count) error(s)."
}
Write-Output "Proposal valid: $($photos.Count) photo(s), strict color contract satisfied."
