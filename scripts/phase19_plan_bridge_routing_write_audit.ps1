param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$RehearsalDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestRehearsalDir {
    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter "phase19_bridge_routing_write_rehearsal_*" -ErrorAction SilentlyContinue |
        Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName "phase19_bridge_routing_write_rehearsal.json")
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No phase19_bridge_routing_write_rehearsal_* folder containing phase19_bridge_routing_write_rehearsal.json found in $BackupDir. Run Step 37 option 5 first."
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
        return Invoke-RestMethod $Url -Method Post -Body ($Body | ConvertTo-Json -Depth 60) -ContentType "application/json" -TimeoutSec 60
    }

    return Invoke-RestMethod $Url -TimeoutSec 30
}

function Normalize-String {
    param($Value)
    if ($null -eq $Value) { return "" }
    return ([string]$Value).Trim()
}

function Audit-Key-From-Preview {
    param($Preview)
    if ($Preview -and $Preview.audit_preview -and $Preview.audit_preview.audit_key) {
        return Normalize-String $Preview.audit_preview.audit_key
    }
    return ""
}

if ([string]::IsNullOrWhiteSpace($RehearsalDir)) {
    $RehearsalDir = Get-LatestRehearsalDir
}

$rehearsalPath = Join-Path $RehearsalDir "phase19_bridge_routing_write_rehearsal.json"
if (!(Test-Path -LiteralPath $rehearsalPath)) {
    throw "Bridge routing write rehearsal JSON not found: $rehearsalPath"
}

$rehearsalReport = Get-Content -LiteralPath $rehearsalPath -Raw | ConvertFrom-Json
$status = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-write-audit/status"
$existing = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-write-audit?limit=500&offset=0"

$safetyErrors = @()
if ($status.read_only -ne $true) { $safetyErrors += "audit API is not reporting read_only=true" }
if ($status.audit_write_enabled -ne $false) { $safetyErrors += "audit_write_enabled is not false" }
if ($status.audit_write_endpoint_implemented -ne $false) { $safetyErrors += "audit_write_endpoint_implemented is not false" }
if ($status.rollback_write_endpoint_implemented -ne $false) { $safetyErrors += "rollback_write_endpoint_implemented is not false" }
if ($status.bridge_post_enabled -ne $false) { $safetyErrors += "bridge_post_enabled is not false" }
if ($status.bridge_write_endpoint_implemented -ne $false) { $safetyErrors += "bridge_write_endpoint_implemented is not false" }
if ($status.lacrm_call_enabled -ne $false) { $safetyErrors += "lacrm_call_enabled is not false" }
if ([int]$status.bridge_post_called_rows -ne 0) { $safetyErrors += "audit table contains rows with bridge_post_called=true" }
if ([int]$status.bridge_mutation_rows -ne 0) { $safetyErrors += "audit table contains rows with bridge_mutation_performed=true" }

$existingAuditKeys = @{}
foreach ($audit in @($existing.audit_rows)) {
    $key = Normalize-String $audit.audit_key
    if (![string]::IsNullOrWhiteSpace($key)) {
        $existingAuditKeys[$key] = $audit
    }
}

$rehearsals = @()
if ($rehearsalReport.rehearsals) { $rehearsals = @($rehearsalReport.rehearsals) }

$planRows = @()
foreach ($row in $rehearsals) {
    $body = @{ rehearsal_row = $row }
    $preview = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-write-audit/preview-from-rehearsal" -Method "POST" -Body $body
    $auditKey = Audit-Key-From-Preview $preview
    $existingAudit = $null
    if ($existingAuditKeys.ContainsKey($auditKey)) {
        $existingAudit = $existingAuditKeys[$auditKey]
    }

    $planAction = "would_block"
    $reason = "audit preview has issues"
    if ($safetyErrors.Count -gt 0) {
        $planAction = "blocked_by_api_safety_flags"
        $reason = "audit API safety flags are not read-only"
    } elseif ($preview.would_create_future_audit_row -eq $true -and $null -eq $existingAudit) {
        $planAction = "would_create_audit_row"
        $reason = "valid rehearsal audit preview does not exist in audit table"
    } elseif ($preview.would_create_future_audit_row -eq $true -and $null -ne $existingAudit) {
        $planAction = "would_skip_existing_audit_row"
        $reason = "matching audit row already exists"
    }

    $planRows += [ordered]@{
        audit_key = $auditKey
        rehearsal_idempotency_key = if ($preview.audit_preview) { $preview.audit_preview.rehearsal_idempotency_key } else { "" }
        draft_id = if ($preview.audit_preview) { $preview.audit_preview.draft_id } else { $null }
        draft_key = if ($preview.audit_preview) { $preview.audit_preview.draft_key } else { "" }
        preference_key = if ($preview.audit_preview) { $preview.audit_preview.preference_key } else { "" }
        phone = if ($preview.audit_preview) { $preview.audit_preview.phone } else { "" }
        mode = if ($preview.audit_preview) { $preview.audit_preview.mode } else { "" }
        owner_type = if ($preview.audit_preview) { $preview.audit_preview.owner_type } else { "" }
        bridge_endpoint = if ($preview.audit_preview) { $preview.audit_preview.bridge_endpoint } else { "" }
        bridge_method = if ($preview.audit_preview) { $preview.audit_preview.bridge_method } else { "" }
        existing_audit_id = if ($existingAudit) { $existingAudit.id } else { $null }
        plan_action = $planAction
        reason = $reason
        issue_count = @($preview.issues).Count
        issues = @($preview.issues)
        would_create_future_audit_row = [bool]$preview.would_create_future_audit_row
        bridge_post_called = [bool]$preview.bridge_post_called
        platform_db_mutation_performed = [bool]$preview.platform_db_mutation_performed
        preview = $preview
    }
}

$actionCounts = @{}
foreach ($row in $planRows) {
    if (!$actionCounts.ContainsKey($row.plan_action)) { $actionCounts[$row.plan_action] = 0 }
    $actionCounts[$row.plan_action] += 1
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_audit_plan_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 39"
    purpose = "Dry-run audit row plan from bridge routing write rehearsal output"
    source_rehearsal_report = $rehearsalPath
    platform_api = $PlatformApi
    safety = [ordered]@{
        bridge_routing_write_audit_plan_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        audit_write_endpoint_implemented = $false
        rollback_write_endpoint_implemented = $false
        routing_write_endpoint_implemented = $false
    }
    audit_status = $status
    existing_audit_rows = $existing
    safety_errors = $safetyErrors
    counts = [ordered]@{
        rehearsal_rows = @($rehearsals).Count
        existing_audit_rows = @($existing.audit_rows).Count
        plan_rows = @($planRows).Count
        safety_error_count = $safetyErrors.Count
        action_counts = $actionCounts
    }
    plan_rows = $planRows
    next_recommended_actions = @(
        "Review would_create_audit_row rows before enabling any audit writer.",
        "If audit API safety flags fail, fix Step 38 before continuing.",
        "Next step may add a disabled-by-default audit writer that creates platform-local audit rows only.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_audit_plan.json"
$csvPath = Join-Path $OutputDir "phase19_bridge_routing_write_audit_plan.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_audit_plan.md"

$report | ConvertTo-Json -Depth 60 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$planRows |
    Select-Object audit_key, rehearsal_idempotency_key, draft_id, draft_key, preference_key, phone, mode, owner_type, bridge_endpoint, bridge_method, existing_audit_id, plan_action, reason, issue_count, would_create_future_audit_row |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }
$actionText = if ($actionCounts.Count -gt 0) { ($actionCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Bridge Routing Write Audit Plan

Generated: $($report.generated_at)

Source rehearsal report:

``````
$rehearsalPath
``````

## Safety

- Bridge routing write audit plan only: true
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

- Rehearsal rows: $($report.counts.rehearsal_rows)
- Existing audit rows: $($report.counts.existing_audit_rows)
- Plan rows: $($report.counts.plan_rows)

## Plan action counts

$actionText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($safetyErrors.Count -eq 0) {
    Write-Host "PASS | bridge_routing_write_audit_plan=$OutputDir | rows=$($planRows.Count) | audit_plan_only=True"
} else {
    Write-Host "CHECK | bridge_routing_write_audit_plan=$OutputDir | safety_errors=$($safetyErrors.Count)"
}

Write-Host ""
Write-Host "Audit plan files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
