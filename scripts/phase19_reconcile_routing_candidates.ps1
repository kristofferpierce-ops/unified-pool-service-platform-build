param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$RoutingSnapshotPath = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestRoutingSnapshot {
    $latest = Get-ChildItem -LiteralPath $BackupDir -File -Filter "phase19_routing_rules_snapshot_*.json" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No phase19_routing_rules_snapshot_*.json found in $BackupDir. Run Step 22 option 4 first."
    }

    return $latest.FullName
}

function Try-GetJson {
    param([string]$Url)
    try {
        return @{ ok = $true; value = Invoke-RestMethod $Url -TimeoutSec 20; error = "" }
    } catch {
        return @{ ok = $false; value = $null; error = $_.Exception.Message }
    }
}

function Normalize-String {
    param($Value)
    if ($null -eq $Value) { return "" }
    return ([string]$Value).Trim()
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

function Normalize-Phone {
    param([string]$Phone)
    if ([string]::IsNullOrWhiteSpace($Phone)) { return "" }
    return ($Phone -replace "[^\d+]", "").Trim()
}

function Bridge-Key {
    param($Rule)
    $phone = Normalize-Phone ([string]$Rule.phone)
    $mode = Normalize-Mode ([string]$Rule.mode)
    $owner = Normalize-OwnerType ([string]$Rule.owner_type)
    return "$phone|$mode|$owner"
}

function Candidate-Key {
    param($Candidate)
    $candidateKey = Normalize-String $Candidate.preference_key
    if (![string]::IsNullOrWhiteSpace($candidateKey)) {
        return $candidateKey
    }
    $phone = Normalize-Phone ([string]$Candidate.phone)
    $mode = Normalize-Mode ([string]$Candidate.proposed_mode)
    $owner = Normalize-OwnerType ([string]$Candidate.proposed_owner_type)
    return "$phone|$mode|$owner"
}

if ([string]::IsNullOrWhiteSpace($RoutingSnapshotPath)) {
    $RoutingSnapshotPath = Get-LatestRoutingSnapshot
}

if (!(Test-Path -LiteralPath $RoutingSnapshotPath)) {
    throw "Routing snapshot not found: $RoutingSnapshotPath"
}

$snapshot = Get-Content -LiteralPath $RoutingSnapshotPath -Raw | ConvertFrom-Json
$rules = @()
if ($snapshot.routing_rules -and $snapshot.routing_rules.rules_preview) {
    $rules = @($snapshot.routing_rules.rules_preview)
}

$status = Try-GetJson "$PlatformApi/front-desk/routing/candidates/status"
$candidates = Try-GetJson "$PlatformApi/front-desk/routing/candidates?limit=500&offset=0"
$workbench = Try-GetJson "$PlatformApi/front-desk/routing/candidate-workbench/status"

if (!$status.ok) {
    throw "Could not read routing candidate status from platform: $($status.error)"
}
if (!$candidates.ok) {
    throw "Could not read routing candidates from platform: $($candidates.error)"
}

$safetyErrors = @()
if ($status.value.read_only -ne $true) { $safetyErrors += "candidate API is not read_only=true" }
if ($status.value.candidate_import_enabled -ne $false) { $safetyErrors += "candidate_import_enabled is not false" }
if ($status.value.routing_write_endpoint_implemented -ne $false) { $safetyErrors += "routing_write_endpoint_implemented is not false" }
if ($status.value.bridge_post_enabled -ne $false) { $safetyErrors += "bridge_post_enabled is not false" }
if ($status.value.lacrm_call_enabled -ne $false) { $safetyErrors += "lacrm_call_enabled is not false" }

if ($workbench.ok) {
    if ($workbench.value.read_only -ne $true) { $safetyErrors += "workbench API is not read_only=true" }
    if ($workbench.value.review_write_endpoint_implemented -ne $false) { $safetyErrors += "review_write_endpoint_implemented is not false" }
    if ($workbench.value.bridge_post_enabled -ne $false) { $safetyErrors += "workbench bridge_post_enabled is not false" }
    if ($workbench.value.lacrm_call_enabled -ne $false) { $safetyErrors += "workbench lacrm_call_enabled is not false" }
}

$candidateRows = @()
if ($candidates.value.candidates) { $candidateRows = @($candidates.value.candidates) }

$bridgeByKey = @{}
foreach ($rule in $rules) {
    $key = Bridge-Key $rule
    if ([string]::IsNullOrWhiteSpace($key) -or $key -eq "||") { continue }
    if (!$bridgeByKey.ContainsKey($key)) {
        $bridgeByKey[$key] = @()
    }
    $bridgeByKey[$key] += $rule
}

$candidateByKey = @{}
foreach ($candidate in $candidateRows) {
    $key = Candidate-Key $candidate
    if ([string]::IsNullOrWhiteSpace($key) -or $key -eq "||") { continue }
    if (!$candidateByKey.ContainsKey($key)) {
        $candidateByKey[$key] = @()
    }
    $candidateByKey[$key] += $candidate
}

$rows = @()

foreach ($key in $bridgeByKey.Keys) {
    $bridgeRules = @($bridgeByKey[$key])
    $candidateMatches = if ($candidateByKey.ContainsKey($key)) { @($candidateByKey[$key]) } else { @() }

    if ($candidateMatches.Count -eq 0) {
        $rule = $bridgeRules[0]
        $rows += [ordered]@{
            preference_key = $key
            phone = Normalize-Phone ([string]$rule.phone)
            bridge_mode = Normalize-Mode ([string]$rule.mode)
            bridge_owner_type = Normalize-OwnerType ([string]$rule.owner_type)
            candidate_count = 0
            bridge_rule_count = $bridgeRules.Count
            reconciliation_status = "bridge_rule_missing_platform_candidate"
            severity = "review"
            reason = "Bridge routing rule exists in snapshot but no platform candidate exists for the same key."
        }
    } elseif ($candidateMatches.Count -gt 1) {
        $rule = $bridgeRules[0]
        $rows += [ordered]@{
            preference_key = $key
            phone = Normalize-Phone ([string]$rule.phone)
            bridge_mode = Normalize-Mode ([string]$rule.mode)
            bridge_owner_type = Normalize-OwnerType ([string]$rule.owner_type)
            candidate_count = $candidateMatches.Count
            bridge_rule_count = $bridgeRules.Count
            reconciliation_status = "duplicate_platform_candidates_for_bridge_rule"
            severity = "error"
            reason = "More than one platform candidate matches the same bridge routing key."
        }
    } else {
        $rule = $bridgeRules[0]
        $candidate = $candidateMatches[0]
        $rows += [ordered]@{
            preference_key = $key
            phone = Normalize-Phone ([string]$rule.phone)
            bridge_mode = Normalize-Mode ([string]$rule.mode)
            bridge_owner_type = Normalize-OwnerType ([string]$rule.owner_type)
            candidate_count = 1
            bridge_rule_count = $bridgeRules.Count
            reconciliation_status = "matched"
            severity = "ok"
            reason = "Bridge routing key has exactly one matching platform candidate."
            candidate_id = $candidate.id
            candidate_write_status = $candidate.write_status
            candidate_operator_decision = $candidate.operator_decision
        }
    }
}

foreach ($key in $candidateByKey.Keys) {
    if ($bridgeByKey.ContainsKey($key)) { continue }

    foreach ($candidate in @($candidateByKey[$key])) {
        $rows += [ordered]@{
            preference_key = $key
            phone = Normalize-Phone ([string]$candidate.phone)
            bridge_mode = ""
            bridge_owner_type = ""
            candidate_count = 1
            bridge_rule_count = 0
            reconciliation_status = "platform_candidate_missing_bridge_rule"
            severity = "review"
            reason = "Platform candidate exists but the latest bridge routing snapshot does not include the same key."
            candidate_id = $candidate.id
            candidate_write_status = $candidate.write_status
            candidate_operator_decision = $candidate.operator_decision
        }
    }
}

$statusCounts = @{}
$severityCounts = @{}
foreach ($row in $rows) {
    if (!$statusCounts.ContainsKey($row.reconciliation_status)) { $statusCounts[$row.reconciliation_status] = 0 }
    if (!$severityCounts.ContainsKey($row.severity)) { $severityCounts[$row.severity] = 0 }
    $statusCounts[$row.reconciliation_status] += 1
    $severityCounts[$row.severity] += 1
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_routing_candidate_reconciliation_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 33"
    purpose = "Read-only reconciliation between bridge routing snapshot and platform routing candidates"
    source_routing_snapshot = $RoutingSnapshotPath
    platform_api = $PlatformApi
    safety = [ordered]@{
        reconciliation_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        candidate_review_write_enabled = $false
        routing_write_endpoint_implemented = $false
    }
    candidate_api_status = $status.value
    workbench_status = if ($workbench.ok) { $workbench.value } else { $null }
    safety_errors = $safetyErrors
    counts = [ordered]@{
        bridge_unique_keys = $bridgeByKey.Count
        platform_candidate_keys = $candidateByKey.Count
        platform_candidate_rows = @($candidateRows).Count
        reconciliation_rows = @($rows).Count
        status_counts = $statusCounts
        severity_counts = $severityCounts
        safety_error_count = $safetyErrors.Count
    }
    reconciliation_rows = $rows
    next_recommended_actions = @(
        "Review bridge_rule_missing_platform_candidate rows before relying on platform candidates.",
        "Resolve duplicate platform candidates before any future review/write workflow.",
        "If platform candidates are empty, run a gated Step 31 import only when intentionally enabled.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_routing_candidate_reconciliation.json"
$csvPath = Join-Path $OutputDir "phase19_routing_candidate_reconciliation.csv"
$mdPath = Join-Path $OutputDir "phase19_routing_candidate_reconciliation.md"

$report | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$rows |
    Select-Object preference_key, phone, bridge_mode, bridge_owner_type, candidate_count, bridge_rule_count, reconciliation_status, severity, reason, candidate_id, candidate_write_status, candidate_operator_decision |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$statusText = ($statusCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
$severityText = ($severityCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Routing Candidate Reconciliation

Generated: $($report.generated_at)

Source routing snapshot:

``````
$RoutingSnapshotPath
``````

## Safety

- Reconciliation only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Candidate review write enabled: false
- Routing write endpoint implemented: false

## Safety errors

$safetyText

## Counts

- Bridge unique keys: $($report.counts.bridge_unique_keys)
- Platform candidate keys: $($report.counts.platform_candidate_keys)
- Platform candidate rows: $($report.counts.platform_candidate_rows)
- Reconciliation rows: $($report.counts.reconciliation_rows)

### Reconciliation status counts

$statusText

### Severity counts

$severityText

## Next recommended actions

$($report.next_recommended_actions | ForEach-Object { "- $_" } | Out-String)
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($safetyErrors.Count -eq 0) {
    Write-Host "PASS | routing_candidate_reconciliation=$OutputDir | rows=$($rows.Count) | reconciliation_only=True"
} else {
    Write-Host "CHECK | routing_candidate_reconciliation=$OutputDir | rows=$($rows.Count) | safety_errors=$($safetyErrors.Count)"
}

Write-Host ""
Write-Host "Reconciliation files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
