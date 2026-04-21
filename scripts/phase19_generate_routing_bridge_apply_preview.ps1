param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Try-GetJson {
    param([string]$Url)
    try {
        return @{ ok = $true; value = Invoke-RestMethod $Url -TimeoutSec 20; error = "" }
    } catch {
        return @{ ok = $false; value = $null; error = $_.Exception.Message }
    }
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$status = Try-GetJson "$PlatformApi/front-desk/routing/bridge-apply-preview/status"
$preview = Try-GetJson "$PlatformApi/front-desk/routing/bridge-apply-preview?limit=500&include_blocked=true"

if (!$status.ok) {
    throw "Could not read routing bridge apply preview status: $($status.error)"
}
if (!$preview.ok) {
    throw "Could not read routing bridge apply preview rows: $($preview.error)"
}

$safetyErrors = @()
if ($status.value.read_only -ne $true) { $safetyErrors += "preview API is not reporting read_only=true" }
if ($status.value.preview_only -ne $true) { $safetyErrors += "preview API is not reporting preview_only=true" }
if ($status.value.bridge_apply_enabled -ne $false) { $safetyErrors += "bridge_apply_enabled is not false" }
if ($status.value.bridge_apply_armed -ne $false) { $safetyErrors += "bridge_apply_armed is not false" }
if ($status.value.bridge_post_called -ne $false) { $safetyErrors += "bridge_post_called is not false" }
if ($status.value.bridge_write_endpoint_implemented -ne $false) { $safetyErrors += "bridge_write_endpoint_implemented is not false" }
if ($status.value.platform_db_mutation_performed -ne $false) { $safetyErrors += "platform_db_mutation_performed is not false" }
if ($status.value.lacrm_call_performed -ne $false) { $safetyErrors += "lacrm_call_performed is not false" }

if ($preview.value.bridge_post_called -ne $false) { $safetyErrors += "preview response says bridge_post_called is not false" }
if ($preview.value.platform_db_mutation_performed -ne $false) { $safetyErrors += "preview response says platform_db_mutation_performed is not false" }
if ($preview.value.lacrm_call_performed -ne $false) { $safetyErrors += "preview response says lacrm_call_performed is not false" }

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_routing_bridge_apply_preview_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$rows = @()
if ($preview.value.preview_rows) { $rows = @($preview.value.preview_rows) }

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 35"
    purpose = "Dry-run bridge apply preview for routing preference drafts"
    platform_api = $PlatformApi
    safety = [ordered]@{
        bridge_apply_preview_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        bridge_write_endpoint_implemented = $false
    }
    status = $status.value
    preview = $preview.value
    safety_errors = $safetyErrors
    counts = [ordered]@{
        total_drafts = $status.value.total_drafts
        previewable_drafts = $status.value.previewable_drafts
        preview_rows = @($rows).Count
        safety_error_count = $safetyErrors.Count
    }
}

$jsonPath = Join-Path $OutputDir "phase19_routing_bridge_apply_preview.json"
$csvPath = Join-Path $OutputDir "phase19_routing_bridge_apply_preview.csv"
$mdPath = Join-Path $OutputDir "phase19_routing_bridge_apply_preview.md"

$report | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$rows |
    Select-Object draft_id, draft_key, preference_key, phone, mode, owner_type, status, risk_level, operator_decision, previewable, target_bridge_endpoint, http_method, idempotency_key |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }

$actionText = ""
if ($preview.value.action_counts) {
    $actionText = (($preview.value.action_counts.PSObject.Properties | Sort-Object Name) | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
}

$md = @"
# Phase 19 Routing Bridge Apply Preview

Generated: $($report.generated_at)

## Safety

- Bridge apply preview only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Bridge write endpoint implemented: false

## Safety errors

$safetyText

## Counts

- Total drafts: $($report.counts.total_drafts)
- Previewable drafts: $($report.counts.previewable_drafts)
- Preview rows: $($report.counts.preview_rows)

## Action counts

$actionText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($safetyErrors.Count -eq 0) {
    Write-Host "PASS | routing_bridge_apply_preview=$OutputDir | rows=$($rows.Count) | preview_only=True"
} else {
    Write-Host "CHECK | routing_bridge_apply_preview=$OutputDir | safety_errors=$($safetyErrors.Count)"
}

Write-Host ""
Write-Host "Bridge apply preview files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
