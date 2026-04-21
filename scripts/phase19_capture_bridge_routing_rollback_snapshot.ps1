param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$AuditWriterRunDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestAuditWriterRunDir {
    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter "phase19_bridge_routing_write_audit_writer_run_*" -ErrorAction SilentlyContinue |
        Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName "phase19_bridge_routing_write_audit_writer_run.json")
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No phase19_bridge_routing_write_audit_writer_run_* folder containing phase19_bridge_routing_write_audit_writer_run.json found in $BackupDir. Run Step 40 option 5 first."
    }

    return $latest.FullName
}

function Try-GetJson {
    param([string]$Url)
    try {
        return @{ ok = $true; value = Invoke-RestMethod $Url -TimeoutSec 30; error = "" }
    } catch {
        return @{ ok = $false; value = $null; error = $_.Exception.Message }
    }
}

function Normalize-String {
    param($Value)
    if ($null -eq $Value) { return "" }
    return ([string]$Value).Trim()
}

function Normalize-Phone {
    param([string]$Phone)
    if ([string]::IsNullOrWhiteSpace($Phone)) { return "" }
    return ($Phone -replace "[^\d+]", "").Trim()
}

function Normalize-Mode {
    param([string]$Mode)
    if ([string]::IsNullOrWhiteSpace($Mode)) { return "manual" }
    $m = $Mode.Trim().ToLowerInvariant()
    if ($m -in @("auto", "automatic", "auto_attach")) { return "auto" }
    if ($m -in @("manual", "manual_review", "review")) { return "manual" }
    return $m
}

function Normalize-OwnerType {
    param([string]$OwnerType)
    if ([string]::IsNullOrWhiteSpace($OwnerType)) { return "unknown" }
    return $OwnerType.Trim().ToLowerInvariant()
}

function Routing-Key {
    param($Rule)
    $phone = Normalize-Phone ([string]$Rule.phone)
    $mode = Normalize-Mode ([string]$Rule.mode)
    $owner = Normalize-OwnerType ([string]$Rule.owner_type)
    return "$phone|$mode|$owner"
}

function Extract-Array {
    param($Value, [string[]]$CandidateKeys)

    if ($null -eq $Value) { return @() }

    if ($Value -is [System.Array]) {
        return @($Value)
    }

    foreach ($key in $CandidateKeys) {
        if ($Value.$key -is [System.Array]) {
            return @($Value.$key)
        }
    }

    return @()
}

function Extract-BridgeRoutingRules {
    param($RoutingRulesResponse, $ActiveBatchesResponse)

    $rules = @()

    if ($RoutingRulesResponse.ok) {
        $rules = Extract-Array $RoutingRulesResponse.value @("routing_rules", "rules", "items", "results", "data")
    }

    if ($rules.Count -gt 0) {
        return @($rules)
    }

    # Fallback: active SMS batches include a routing_rule object per phone.
    if ($ActiveBatchesResponse.ok) {
        $batches = Extract-Array $ActiveBatchesResponse.value @("batches", "items", "results", "data")
        $fallbackRules = @()
        foreach ($batch in $batches) {
            if ($batch.routing_rule) {
                $fallbackRules += $batch.routing_rule
            }
        }
        return @($fallbackRules)
    }

    return @()
}

function Load-AuditWriterRun {
    param([string]$RunDir)

    $path = Join-Path $RunDir "phase19_bridge_routing_write_audit_writer_run.json"
    if (!(Test-Path -LiteralPath $path)) {
        throw "Audit writer run JSON not found: $path"
    }

    return @{
        path = $path
        data = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    }
}

if ([string]::IsNullOrWhiteSpace($AuditWriterRunDir)) {
    $AuditWriterRunDir = Get-LatestAuditWriterRunDir
}

$runInfo = Load-AuditWriterRun $AuditWriterRunDir
$runPath = $runInfo.path
$run = $runInfo.data

$bridgeHealth = Try-GetJson "$BridgeUrl/health"
$bridgeRoutingRules = Try-GetJson "$BridgeUrl/api/routing-rules"
$bridgeActiveBatches = Try-GetJson "$BridgeUrl/api/sms/batches?view=active"
$auditStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-audit/status"
$auditRowsResponse = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-audit?limit=500&offset=0"

$rules = Extract-BridgeRoutingRules $bridgeRoutingRules $bridgeActiveBatches

$ruleByPhone = @{}
$ruleByKey = @{}

foreach ($rule in $rules) {
    $phone = Normalize-Phone ([string]$rule.phone)
    $key = Routing-Key $rule

    if (![string]::IsNullOrWhiteSpace($phone) -and !$ruleByPhone.ContainsKey($phone)) {
        $ruleByPhone[$phone] = $rule
    }
    if (![string]::IsNullOrWhiteSpace($key) -and $key -ne "||" -and !$ruleByKey.ContainsKey($key)) {
        $ruleByKey[$key] = $rule
    }
}

$safetyErrors = @()
if (!$bridgeHealth.ok) { $safetyErrors += "bridge health endpoint could not be read" }
if ($bridgeRoutingRules.ok -ne $true -and $bridgeActiveBatches.ok -ne $true) { $safetyErrors += "could not read bridge routing rules or active batch fallback" }
if (!$auditStatus.ok) { $safetyErrors += "could not read platform audit status" }
if (!$auditRowsResponse.ok) { $safetyErrors += "could not read platform audit rows" }

if ($auditStatus.ok) {
    if ($auditStatus.value.read_only -ne $true) { $safetyErrors += "audit API is not reporting read_only=true" }
    if ($auditStatus.value.audit_write_endpoint_implemented -ne $false) { $safetyErrors += "audit_write_endpoint_implemented is not false" }
    if ($auditStatus.value.rollback_write_endpoint_implemented -ne $false) { $safetyErrors += "rollback_write_endpoint_implemented is not false" }
    if ($auditStatus.value.bridge_post_enabled -ne $false) { $safetyErrors += "bridge_post_enabled is not false" }
    if ([int]$auditStatus.value.bridge_post_called_rows -ne 0) { $safetyErrors += "audit table contains bridge_post_called rows" }
}

$writeRows = @()
if ($run.write_rows) { $writeRows = @($run.write_rows) }

$auditRows = @()
if ($auditRowsResponse.ok -and $auditRowsResponse.value.audit_rows) { $auditRows = @($auditRowsResponse.value.audit_rows) }

$auditByKey = @{}
foreach ($audit in $auditRows) {
    $auditKey = Normalize-String $audit.audit_key
    if (![string]::IsNullOrWhiteSpace($auditKey) -and !$auditByKey.ContainsKey($auditKey)) {
        $auditByKey[$auditKey] = $audit
    }
}

$rollbackRows = @()
foreach ($row in $writeRows) {
    $auditKey = Normalize-String $row.audit_key
    $payload = $row.payload_preview
    if ($payload -eq $null -and $row.PSObject.Properties.Name -contains "payload_preview") {
        $payload = $row.payload_preview
    }

    $phone = ""
    $mode = "manual"
    $owner = "unknown"
    if ($payload) {
        $phone = Normalize-Phone ([string]$payload.phone)
        $mode = Normalize-Mode ([string]$payload.mode)
        $owner = Normalize-OwnerType ([string]$payload.owner_type)
    }

    $lookupKey = "$phone|$mode|$owner"
    $currentRule = $null
    $matchSource = "none"

    if ($ruleByKey.ContainsKey($lookupKey)) {
        $currentRule = $ruleByKey[$lookupKey]
        $matchSource = "routing_key"
    } elseif ($ruleByPhone.ContainsKey($phone)) {
        $currentRule = $ruleByPhone[$phone]
        $matchSource = "phone"
    }

    $existingAudit = $null
    if ($auditByKey.ContainsKey($auditKey)) {
        $existingAudit = $auditByKey[$auditKey]
    }

    $rollbackPayload = [ordered]@{
        phone = $phone
        restore_mode = if ($currentRule) { Normalize-Mode ([string]$currentRule.mode) } else { "" }
        restore_owner_type = if ($currentRule) { Normalize-OwnerType ([string]$currentRule.owner_type) } else { "" }
        restore_label = if ($currentRule) { Normalize-String $currentRule.label } else { "" }
        restore_default_contact_ids = if ($currentRule -and $currentRule.default_contact_ids) { @($currentRule.default_contact_ids) } else { @() }
        restore_notes = if ($currentRule) { Normalize-String $currentRule.notes } else { "" }
        restore_source = "bridge_get_snapshot_only"
    }

    $status = "rollback_snapshot_not_available"
    $reason = "no current bridge rule found for audit plan row"
    if ($currentRule) {
        $status = "rollback_snapshot_available"
        $reason = "current bridge routing rule captured from GET-only snapshot"
    }
    if ([string]::IsNullOrWhiteSpace($auditKey)) {
        $status = "rollback_snapshot_blocked"
        $reason = "audit key missing"
    }

    $rollbackRows += [ordered]@{
        audit_key = $auditKey
        existing_audit_id = if ($existingAudit) { $existingAudit.id } else { $null }
        phone = $phone
        mode = $mode
        owner_type = $owner
        lookup_key = $lookupKey
        bridge_rule_match_source = $matchSource
        rollback_snapshot_status = $status
        reason = $reason
        current_bridge_rule = $currentRule
        rollback_payload_preview = $rollbackPayload
        bridge_get_only = $true
        bridge_post_called = $false
        platform_db_mutation_performed = $false
    }
}

$statusCounts = @{}
foreach ($row in $rollbackRows) {
    if (!$statusCounts.ContainsKey($row.rollback_snapshot_status)) { $statusCounts[$row.rollback_snapshot_status] = 0 }
    $statusCounts[$row.rollback_snapshot_status] += 1
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_rollback_snapshot_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 41"
    purpose = "Read-only bridge routing rollback snapshot from current bridge routing rules"
    source_audit_writer_run = $runPath
    bridge_url = $BridgeUrl
    platform_api = $PlatformApi
    safety = [ordered]@{
        bridge_routing_rollback_snapshot_only = $true
        bridge_get_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        rollback_write_endpoint_implemented = $false
        routing_write_endpoint_implemented = $false
    }
    bridge_read_status = [ordered]@{
        health_ok = $bridgeHealth.ok
        routing_rules_get_ok = $bridgeRoutingRules.ok
        active_batches_get_ok = $bridgeActiveBatches.ok
        routing_rule_count = @($rules).Count
    }
    audit_status = if ($auditStatus.ok) { $auditStatus.value } else { $null }
    safety_errors = $safetyErrors
    counts = [ordered]@{
        audit_writer_rows = @($writeRows).Count
        existing_audit_rows = @($auditRows).Count
        bridge_routing_rules_seen = @($rules).Count
        rollback_rows = @($rollbackRows).Count
        safety_error_count = $safetyErrors.Count
        status_counts = $statusCounts
    }
    rollback_rows = $rollbackRows
    next_recommended_actions = @(
        "Review rollback_snapshot_available rows before any future bridge write implementation.",
        "Rows without rollback snapshots must not advance to bridge write implementation.",
        "Add rollback capture to future audit writer before any live bridge POST.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_rollback_snapshot.json"
$csvPath = Join-Path $OutputDir "phase19_bridge_routing_rollback_snapshot.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_rollback_snapshot.md"

$report | ConvertTo-Json -Depth 80 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$rollbackRows |
    Select-Object audit_key, existing_audit_id, phone, mode, owner_type, lookup_key, bridge_rule_match_source, rollback_snapshot_status, reason, bridge_get_only, bridge_post_called, platform_db_mutation_performed |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }
$statusText = if ($statusCounts.Count -gt 0) { ($statusCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Bridge Routing Rollback Snapshot

Generated: $($report.generated_at)

Source audit writer run:

``````
$runPath
``````

## Safety

- Bridge routing rollback snapshot only: true
- Bridge GET only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Rollback write endpoint implemented: false
- Routing write endpoint implemented: false

## Safety errors

$safetyText

## Counts

- Audit writer rows: $($report.counts.audit_writer_rows)
- Existing audit rows: $($report.counts.existing_audit_rows)
- Bridge routing rules seen: $($report.counts.bridge_routing_rules_seen)
- Rollback rows: $($report.counts.rollback_rows)

## Rollback snapshot status counts

$statusText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($safetyErrors.Count -eq 0) {
    Write-Host "PASS | bridge_routing_rollback_snapshot=$OutputDir | rows=$($rollbackRows.Count) | bridge_get_only=True"
} else {
    Write-Host "CHECK | bridge_routing_rollback_snapshot=$OutputDir | safety_errors=$($safetyErrors.Count) | bridge_post_called=False"
}

Write-Host ""
Write-Host "Rollback snapshot files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
