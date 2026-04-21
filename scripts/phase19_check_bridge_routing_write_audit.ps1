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

$status = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-audit/status"
$audits = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-audit?limit=100"

if (!$status.ok) {
    throw "Could not read bridge routing write audit status: $($status.error)"
}
if (!$audits.ok) {
    throw "Could not read bridge routing write audit rows: $($audits.error)"
}

$safetyErrors = @()
if ($status.value.read_only -ne $true) { $safetyErrors += "audit API is not reporting read_only=true" }
if ($status.value.audit_write_enabled -ne $false) { $safetyErrors += "audit_write_enabled is not false" }
if ($status.value.audit_write_endpoint_implemented -ne $false) { $safetyErrors += "audit_write_endpoint_implemented is not false" }
if ($status.value.rollback_write_enabled -ne $false) { $safetyErrors += "rollback_write_enabled is not false" }
if ($status.value.rollback_write_endpoint_implemented -ne $false) { $safetyErrors += "rollback_write_endpoint_implemented is not false" }
if ($status.value.bridge_post_enabled -ne $false) { $safetyErrors += "bridge_post_enabled is not false" }
if ($status.value.bridge_write_endpoint_implemented -ne $false) { $safetyErrors += "bridge_write_endpoint_implemented is not false" }
if ($status.value.lacrm_call_enabled -ne $false) { $safetyErrors += "lacrm_call_enabled is not false" }
if ([int]$status.value.bridge_post_called_rows -ne 0) { $safetyErrors += "audit table contains rows with bridge_post_called=true" }
if ([int]$status.value.bridge_mutation_rows -ne 0) { $safetyErrors += "audit table contains rows with bridge_mutation_performed=true" }

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_audit_check_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 38"
    purpose = "Read-only bridge routing write audit/rollback ledger check"
    platform_api = $PlatformApi
    safety = [ordered]@{
        bridge_routing_write_audit_check_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        audit_write_endpoint_implemented = $false
        rollback_write_endpoint_implemented = $false
        routing_write_endpoint_implemented = $false
    }
    status = $status.value
    audits = $audits.value
    safety_errors = $safetyErrors
    counts = [ordered]@{
        total_audit_rows = $status.value.total_audit_rows
        list_count = @($audits.value.audit_rows).Count
        safety_error_count = $safetyErrors.Count
    }
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_audit_check.json"
$csvPath = Join-Path $OutputDir "phase19_bridge_routing_write_audit_rows.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_audit_check.md"

$report | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

@($audits.value.audit_rows) |
    Select-Object id, audit_key, rehearsal_idempotency_key, draft_id, draft_key, preference_key, phone, mode, owner_type, status, bridge_endpoint, bridge_method, bridge_post_called, bridge_mutation_performed |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Bridge Routing Write Audit Check

Generated: $($report.generated_at)

## Safety

- Bridge routing write audit check only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Audit write endpoint implemented: false
- Rollback write endpoint implemented: false
- Routing write endpoint implemented: false

## Safety errors

$safetyText

## Counts

- Total audit rows: $($report.counts.total_audit_rows)
- List count: $($report.counts.list_count)
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($safetyErrors.Count -eq 0) {
    Write-Host "PASS | bridge_routing_write_audit_check=$OutputDir | audit_rows=$($report.counts.total_audit_rows) | read_only=True"
} else {
    Write-Host "CHECK | bridge_routing_write_audit_check=$OutputDir | safety_errors=$($safetyErrors.Count)"
}

Write-Host ""
Write-Host "Audit check files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
