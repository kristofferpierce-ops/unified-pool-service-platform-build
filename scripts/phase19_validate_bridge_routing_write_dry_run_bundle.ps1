param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$DryRunBundleDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestArtifactDir {
    param(
        [string]$FolderFilter,
        [string]$JsonName
    )

    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter $FolderFilter -ErrorAction SilentlyContinue |
        Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName $JsonName)
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No $FolderFilter folder containing $JsonName found in $BackupDir."
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

function Read-JsonFile {
    param([string]$Path)
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Add-Issue {
    param(
        [System.Collections.ArrayList]$Issues,
        [string]$Severity,
        [string]$Code,
        [string]$Message,
        [string]$Source = ""
    )

    [void]$Issues.Add([ordered]@{
        severity = $Severity
        code = $Code
        source = $Source
        message = $Message
    })
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

function Normalize-String {
    param($Value)
    if ($null -eq $Value) { return "" }
    return ([string]$Value).Trim()
}

if ([string]::IsNullOrWhiteSpace($DryRunBundleDir)) {
    $DryRunBundleDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_dry_run_bundle_*" -JsonName "phase19_bridge_routing_write_dry_run_bundle.json"
}

$bundlePath = Join-Path $DryRunBundleDir "phase19_bridge_routing_write_dry_run_bundle.json"
if (!(Test-Path -LiteralPath $bundlePath)) {
    throw "Dry-run bundle JSON not found: $bundlePath"
}

$bundleReport = Read-JsonFile $bundlePath

$bundleStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"
$bridgeRoutingRules = Try-GetJson "$BridgeUrl/api/routing-rules"
$bridgeActiveBatches = Try-GetJson "$BridgeUrl/api/sms/batches?view=active"

$issues = New-Object System.Collections.ArrayList

# Top-level artifact safety checks.
if ($bundleReport.safety.bridge_routing_write_dry_run_bundle_only -ne $true) {
    Add-Issue $issues "blocker" "bundle_not_dry_run_bundle_only" "Bundle report is not marked bridge_routing_write_dry_run_bundle_only=true." "bundle"
}
if ($bundleReport.safety.bridge_http_client_implemented -ne $false) {
    Add-Issue $issues "blocker" "bridge_http_client_implemented" "Bundle report says bridge_http_client_implemented is not false." "bundle"
}
if ($bundleReport.safety.bridge_post_call_implemented -ne $false) {
    Add-Issue $issues "blocker" "bridge_post_call_implemented" "Bundle report says bridge_post_call_implemented is not false." "bundle"
}
if ($bundleReport.safety.bridge_post_called -ne $false) {
    Add-Issue $issues "blocker" "bridge_post_called" "Bundle report says bridge_post_called is not false." "bundle"
}
if ($bundleReport.safety.bridge_mutation_performed -ne $false) {
    Add-Issue $issues "blocker" "bridge_mutation_performed" "Bundle report says bridge_mutation_performed is not false." "bundle"
}
if ($bundleReport.safety.platform_db_mutation_performed -ne $false) {
    Add-Issue $issues "blocker" "platform_db_mutation_performed" "Bundle report says platform_db_mutation_performed is not false." "bundle"
}
if ($bundleReport.safety.lacrm_call_performed -ne $false) {
    Add-Issue $issues "blocker" "lacrm_call_performed" "Bundle report says lacrm_call_performed is not false." "bundle"
}

foreach ($item in @($bundleReport.safety_errors)) {
    Add-Issue $issues "blocker" "source_bundle_safety_error" "$item" "bundle"
}

# Runtime status checks are review-level when unreachable because the bundle itself remains offline-reviewable.
if (!$bundleStatus.ok) {
    Add-Issue $issues "review" "bundle_status_unreadable" "Could not read dry-run bundle status: $($bundleStatus.error)" "platform"
} else {
    if ($bundleStatus.value.dry_run_bundle_only -ne $true) {
        Add-Issue $issues "blocker" "platform_bundle_not_dry_run_only" "Platform bundle status is not dry_run_bundle_only=true." "platform"
    }
    if ($bundleStatus.value.bridge_http_client_implemented -ne $false) {
        Add-Issue $issues "blocker" "platform_bundle_http_client_implemented" "Platform bundle status says bridge_http_client_implemented is not false." "platform"
    }
    if ($bundleStatus.value.bridge_post_called -ne $false) {
        Add-Issue $issues "blocker" "platform_bundle_post_called" "Platform bundle status says bridge_post_called is not false." "platform"
    }
}

if (!$executorStatus.ok) {
    Add-Issue $issues "review" "executor_status_unreadable" "Could not read bridge write executor status: $($executorStatus.error)" "platform"
} else {
    if ($executorStatus.value.execution_endpoint_available -ne $false) {
        Add-Issue $issues "blocker" "executor_execution_endpoint_available" "Executor status says execution_endpoint_available is not false." "platform"
    }
    if ($executorStatus.value.bridge_post_call_implemented -ne $false) {
        Add-Issue $issues "blocker" "executor_post_call_implemented" "Executor status says bridge_post_call_implemented is not false." "platform"
    }
}

if (!$bridgeHealth.ok) {
    Add-Issue $issues "review" "bridge_health_unreadable" "Could not read bridge health: $($bridgeHealth.error)" "bridge"
}

$rules = @()
if ($bridgeRoutingRules.ok) {
    $rules = Extract-Array $bridgeRoutingRules.value @("routing_rules", "rules", "items", "results", "data")
} elseif ($bridgeActiveBatches.ok) {
    $batches = Extract-Array $bridgeActiveBatches.value @("batches", "items", "results", "data")
    foreach ($batch in $batches) {
        if ($batch.routing_rule) { $rules += $batch.routing_rule }
    }
} else {
    Add-Issue $issues "review" "bridge_routing_state_unreadable" "Could not read bridge routing rules or active SMS batch fallback." "bridge"
}

$bundleRows = @()
if ($bundleReport.bundle -and $bundleReport.bundle.bundle_rows) {
    $bundleRows = @($bundleReport.bundle.bundle_rows)
}

if ($bundleRows.Count -eq 0) {
    Add-Issue $issues "blocker" "bundle_rows_missing" "Dry-run bundle contains zero bundle rows." "bundle"
}

$rowReports = @()
$rowIndex = 0

foreach ($row in $bundleRows) {
    $rowIssues = New-Object System.Collections.ArrayList
    $target = Normalize-String $row.target_bridge_endpoint
    $method = (Normalize-String $row.http_method).ToUpperInvariant()

    if ($row.bundle_row_type -ne "request_template_only") {
        Add-Issue $rowIssues "blocker" "row_not_request_template_only" "Bundle row is not request_template_only." "row"
    }
    if ($target -ne "/api/routing-rules") {
        Add-Issue $rowIssues "blocker" "row_unexpected_target_endpoint" "Target endpoint is not /api/routing-rules." "row"
    }
    if ($method -ne "POST") {
        Add-Issue $rowIssues "blocker" "row_unexpected_http_method" "HTTP method is not POST." "row"
    }
    if ($row.would_call_bridge -ne $false) {
        Add-Issue $rowIssues "blocker" "row_would_call_bridge" "Bundle row says would_call_bridge is not false." "row"
    }
    if ($row.would_mutate_platform -ne $false) {
        Add-Issue $rowIssues "blocker" "row_would_mutate_platform" "Bundle row says would_mutate_platform is not false." "row"
    }
    if ($row.would_call_lacrm -ne $false) {
        Add-Issue $rowIssues "blocker" "row_would_call_lacrm" "Bundle row says would_call_lacrm is not false." "row"
    }
    if ($row.ready_for_live_execution -ne $false) {
        Add-Issue $rowIssues "blocker" "row_ready_for_live_execution" "Bundle row says ready_for_live_execution is not false." "row"
    }

    $payload = $row.payload_template
    $requiredPayloadFields = @("phone", "mode", "owner_type", "label", "default_contact_ids", "notes")
    foreach ($field in $requiredPayloadFields) {
        if ($payload -eq $null -or ($payload.PSObject.Properties.Name -notcontains $field)) {
            Add-Issue $rowIssues "blocker" "row_payload_missing_$field" "Payload template is missing field: $field." "row"
        }
    }

    $headers = $row.headers_template
    if ($headers -eq $null -or ($headers.PSObject.Properties.Name -notcontains "Idempotency-Key")) {
        Add-Issue $rowIssues "blocker" "row_missing_idempotency_key_template" "Headers template is missing Idempotency-Key." "row"
    }

    $rowReports += [ordered]@{
        row_index = $rowIndex
        target_bridge_endpoint = $target
        http_method = $method
        payload_hash = Normalize-String $row.payload_hash
        row_status = if (@($rowIssues).Count -eq 0) { "valid_dry_run_template" } else { "invalid_dry_run_template" }
        issue_count = @($rowIssues).Count
        issues = @($rowIssues)
        would_call_bridge = [bool]$row.would_call_bridge
        would_mutate_platform = [bool]$row.would_mutate_platform
        would_call_lacrm = [bool]$row.would_call_lacrm
        ready_for_live_execution = [bool]$row.ready_for_live_execution
    }

    foreach ($issue in @($rowIssues)) {
        Add-Issue $issues $issue.severity $issue.code $issue.message "row_$rowIndex"
    }

    $rowIndex += 1
}

$statusCounts = @{}
foreach ($rowReport in $rowReports) {
    if (!$statusCounts.ContainsKey($rowReport.row_status)) { $statusCounts[$rowReport.row_status] = 0 }
    $statusCounts[$rowReport.row_status] += 1
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$validationStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "valid_dry_run_bundle"
} elseif ($blockerCount -eq 0) {
    "valid_with_review_items"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_dry_run_validation_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 47"
    purpose = "Bridge routing write dry-run bundle validation"
    source_dry_run_bundle = $bundlePath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_write_dry_run_validation_only = $true
        bridge_get_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        bridge_http_client_implemented = $false
        bridge_post_call_implemented = $false
        routing_write_endpoint_implemented = $false
        live_write_enabled = $false
    }
    validation = [ordered]@{
        status = $validationStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        bundle_rows = @($bundleRows).Count
        can_execute_bridge_write_now = $false
        can_add_bridge_http_client_now = $false
        reason = if ($blockerCount -eq 0) {
            "Dry-run bundle is structurally valid for review. Step 47 still implements no bridge write."
        } else {
            "Dry-run bundle validation found blockers. Resolve blockers before any future bridge HTTP client work."
        }
    }
    platform_status = [ordered]@{
        bundle_status_ok = $bundleStatus.ok
        bundle_status = if ($bundleStatus.ok) { $bundleStatus.value } else { $null }
        executor_status_ok = $executorStatus.ok
        executor_status = if ($executorStatus.ok) { $executorStatus.value } else { $null }
    }
    bridge_status = [ordered]@{
        health_ok = $bridgeHealth.ok
        health = if ($bridgeHealth.ok) { $bridgeHealth.value } else { $null }
        routing_rules_get_ok = $bridgeRoutingRules.ok
        active_batches_get_ok = $bridgeActiveBatches.ok
        routing_rules_seen = @($rules).Count
    }
    issues = @($issues)
    row_reports = $rowReports
    counts = [ordered]@{
        bundle_rows = @($bundleRows).Count
        row_reports = @($rowReports).Count
        blockers = $blockerCount
        reviews = $reviewCount
        routing_rules_seen = @($rules).Count
        status_counts = $statusCounts
    }
    next_recommended_actions = @(
        "Review validation blockers before adding any bridge HTTP client.",
        "If only review items remain, resolve or accept them before future design.",
        "Do not call bridge POST endpoints from Step 47.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_dry_run_validation.json"
$rowsCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_dry_run_validation_rows.csv"
$issuesCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_dry_run_validation_issues.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_dry_run_validation.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$rowReports |
    Select-Object row_index, target_bridge_endpoint, http_method, payload_hash, row_status, issue_count, would_call_bridge, would_mutate_platform, would_call_lacrm, ready_for_live_execution |
    Export-Csv -LiteralPath $rowsCsvPath -NoTypeInformation -Encoding UTF8

$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }
$statusText = if ($statusCounts.Count -gt 0) { ($statusCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Bridge Routing Write Dry-run Bundle Validation

Generated: $($report.generated_at)

Source dry-run bundle:

``````
$bundlePath
``````

## Safety

- Bridge routing write dry-run validation only: true
- Bridge GET only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Bridge HTTP client implemented: false
- Bridge POST call implemented: false
- Routing write endpoint implemented: false
- Live write enabled: false

## Validation

- Status: $validationStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Can execute bridge write now: false
- Can add bridge HTTP client now: false

## Row status counts

$statusText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_write_dry_run_validation=$OutputDir | status=$validationStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_write_dry_run_validation=$OutputDir | status=$validationStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Dry-run validation files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
