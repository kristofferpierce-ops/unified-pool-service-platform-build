param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeApplyPreviewDir = "",
    [string]$OutputDir = "",
    [string]$ConfirmationPhrase = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestPreviewDir {
    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter "phase19_routing_bridge_apply_preview_*" -ErrorAction SilentlyContinue |
        Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName "phase19_routing_bridge_apply_preview.json")
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No phase19_routing_bridge_apply_preview_* folder containing phase19_routing_bridge_apply_preview.json found in $BackupDir. Run Step 35 option 5 first."
    }

    return $latest.FullName
}

function Invoke-PlatformJson {
    param(
        [string]$Url,
        [string]$Method = "GET",
        [object]$Body = $null
    )

    if ($Method -eq "POST") {
        return Invoke-RestMethod $Url -Method Post -Body ($Body | ConvertTo-Json -Depth 40) -ContentType "application/json" -TimeoutSec 60
    }

    return Invoke-RestMethod $Url -TimeoutSec 30
}

if ([string]::IsNullOrWhiteSpace($BridgeApplyPreviewDir)) {
    $BridgeApplyPreviewDir = Get-LatestPreviewDir
}

$previewPath = Join-Path $BridgeApplyPreviewDir "phase19_routing_bridge_apply_preview.json"
if (!(Test-Path -LiteralPath $previewPath)) {
    throw "Bridge apply preview JSON not found: $previewPath"
}

$previewReport = Get-Content -LiteralPath $previewPath -Raw | ConvertFrom-Json
$status = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-write-rehearsal/status"

$previewRows = @()
if ($previewReport.preview -and $previewReport.preview.preview_rows) {
    $previewRows = @($previewReport.preview.preview_rows)
}

$rehearsals = @()
foreach ($row in ($previewRows | Select-Object -First 100)) {
    $body = @{
        preview_row = $row
        confirmation_phrase = $ConfirmationPhrase
    }
    $rehearsals += Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-write-rehearsal/rehearse" -Method "POST" -Body $body
}

$safetyErrors = @()
if ($status.rehearsal_only -ne $true) { $safetyErrors += "status does not report rehearsal_only=true" }
if ($status.bridge_post_call_implemented -ne $false) { $safetyErrors += "bridge_post_call_implemented is not false" }
if ($status.bridge_post_called -ne $false) { $safetyErrors += "bridge_post_called is not false" }
if ($status.platform_db_mutation_performed -ne $false) { $safetyErrors += "platform_db_mutation_performed is not false" }
if ($status.bridge_mutation_performed -ne $false) { $safetyErrors += "bridge_mutation_performed is not false" }
if ($status.lacrm_call_performed -ne $false) { $safetyErrors += "lacrm_call_performed is not false" }
if ($status.routing_write_endpoint_implemented -ne $false) { $safetyErrors += "routing_write_endpoint_implemented is not false" }

foreach ($r in $rehearsals) {
    if ($r.would_call_bridge -ne $false) { $safetyErrors += "a rehearsal row says would_call_bridge is not false" }
    if ($r.safety.bridge_post_called -ne $false) { $safetyErrors += "a rehearsal row says bridge_post_called is not false" }
    if ($r.safety.platform_db_mutation_performed -ne $false) { $safetyErrors += "a rehearsal row says platform_db_mutation_performed is not false" }
    if ($r.blocked -ne $true) { $safetyErrors += "a rehearsal row is not blocked" }
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_rehearsal_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$blockerCounts = @{}
foreach ($r in $rehearsals) {
    foreach ($blocker in @($r.blockers)) {
        if (!$blockerCounts.ContainsKey($blocker)) { $blockerCounts[$blocker] = 0 }
        $blockerCounts[$blocker] += 1
    }
}

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 37"
    purpose = "Guarded bridge routing write rehearsal blocked by default"
    source_bridge_apply_preview = $previewPath
    platform_api = $PlatformApi
    safety = [ordered]@{
        bridge_routing_write_rehearsal_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        bridge_post_call_implemented = $false
        routing_write_endpoint_implemented = $false
    }
    status = $status
    rehearsals = $rehearsals
    safety_errors = $safetyErrors
    counts = [ordered]@{
        preview_rows_seen = @($previewRows).Count
        rehearsals_run = @($rehearsals).Count
        safety_error_count = $safetyErrors.Count
        blocker_counts = $blockerCounts
    }
    next_recommended_actions = @(
        "Review blockers before any future bridge write implementation.",
        "Keep Bridge POST implementation absent until contract and rollback requirements are accepted.",
        "Add explicit audit and rollback capture before any future live bridge routing write.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_rehearsal.json"
$csvPath = Join-Path $OutputDir "phase19_bridge_routing_write_rehearsal.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_rehearsal.md"

$report | ConvertTo-Json -Depth 50 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$rehearsals |
    Select-Object rehearsal_version, target_bridge_endpoint, http_method, idempotency_key, previewable, blocked, blocker_count, would_call_bridge, would_mutate_platform |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }
$blockerText = if ($blockerCounts.Count -gt 0) { ($blockerCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Bridge Routing Write Rehearsal

Generated: $($report.generated_at)

Source bridge apply preview:

``````
$previewPath
``````

## Safety

- Bridge routing write rehearsal only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Bridge POST call implemented: false
- Routing write endpoint implemented: false

## Safety errors

$safetyText

## Counts

- Preview rows seen: $($report.counts.preview_rows_seen)
- Rehearsals run: $($report.counts.rehearsals_run)

## Blocker counts

$blockerText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($safetyErrors.Count -eq 0) {
    Write-Host "PASS | bridge_routing_write_rehearsal=$OutputDir | rehearsals=$($rehearsals.Count) | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_write_rehearsal=$OutputDir | safety_errors=$($safetyErrors.Count)"
}

Write-Host ""
Write-Host "Rehearsal files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
