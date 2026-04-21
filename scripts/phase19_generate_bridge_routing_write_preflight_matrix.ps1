param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$ValidationDir = "",
    [string]$DryRunBundleDir = "",
    [string]$RollbackSnapshotDir = "",
    [string]$AuditPlanDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestArtifactDir {
    param(
        [string]$FolderFilter,
        [string]$JsonName,
        [bool]$Required = $true
    )

    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter $FolderFilter -ErrorAction SilentlyContinue |
        Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName $JsonName)
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        if ($Required) {
            throw "No $FolderFilter folder containing $JsonName found in $BackupDir."
        }
        return ""
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

function Gate-Row {
    param(
        [string]$Gate,
        [bool]$Passed,
        [string]$Severity,
        [string]$Evidence,
        [string]$Source,
        [string]$FutureAction = ""
    )

    return [ordered]@{
        gate = $Gate
        passed = $Passed
        severity = $Severity
        evidence = $Evidence
        source = $Source
        future_action = $FutureAction
    }
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

if ([string]::IsNullOrWhiteSpace($ValidationDir)) {
    $ValidationDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_dry_run_validation_*" -JsonName "phase19_bridge_routing_write_dry_run_validation.json"
}

if ([string]::IsNullOrWhiteSpace($DryRunBundleDir)) {
    $DryRunBundleDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_dry_run_bundle_*" -JsonName "phase19_bridge_routing_write_dry_run_bundle.json"
}

if ([string]::IsNullOrWhiteSpace($RollbackSnapshotDir)) {
    $RollbackSnapshotDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_rollback_snapshot_*" -JsonName "phase19_bridge_routing_rollback_snapshot.json" -Required $false
}

if ([string]::IsNullOrWhiteSpace($AuditPlanDir)) {
    $AuditPlanDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_audit_plan_*" -JsonName "phase19_bridge_routing_write_audit_plan.json" -Required $false
}

$validationPath = Join-Path $ValidationDir "phase19_bridge_routing_write_dry_run_validation.json"
$bundlePath = Join-Path $DryRunBundleDir "phase19_bridge_routing_write_dry_run_bundle.json"
$rollbackPath = if (![string]::IsNullOrWhiteSpace($RollbackSnapshotDir)) { Join-Path $RollbackSnapshotDir "phase19_bridge_routing_rollback_snapshot.json" } else { "" }
$auditPlanPath = if (![string]::IsNullOrWhiteSpace($AuditPlanDir)) { Join-Path $AuditPlanDir "phase19_bridge_routing_write_audit_plan.json" } else { "" }

if (!(Test-Path -LiteralPath $validationPath)) { throw "Dry-run validation JSON not found: $validationPath" }
if (!(Test-Path -LiteralPath $bundlePath)) { throw "Dry-run bundle JSON not found: $bundlePath" }

$validation = Read-JsonFile $validationPath
$bundle = Read-JsonFile $bundlePath
$rollback = if (![string]::IsNullOrWhiteSpace($rollbackPath) -and (Test-Path -LiteralPath $rollbackPath)) { Read-JsonFile $rollbackPath } else { $null }
$auditPlan = if (![string]::IsNullOrWhiteSpace($auditPlanPath) -and (Test-Path -LiteralPath $auditPlanPath)) { Read-JsonFile $auditPlanPath } else { $null }

$bundleStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$auditStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-audit/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList

$globalGates = @()
$globalGates += Gate-Row "dry_run_validation_exists" $true "blocker" $validationPath "validation"
$globalGates += Gate-Row "dry_run_bundle_exists" $true "blocker" $bundlePath "bundle"
$globalGates += Gate-Row "validation_is_no_post" ($validation.safety.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($validation.safety.bridge_post_called)" "validation"
$globalGates += Gate-Row "validation_is_no_mutation" ($validation.safety.platform_db_mutation_performed -eq $false -and $validation.safety.bridge_mutation_performed -eq $false) "blocker" "platform_db_mutation=$($validation.safety.platform_db_mutation_performed); bridge_mutation=$($validation.safety.bridge_mutation_performed)" "validation"
$globalGates += Gate-Row "validation_bridge_get_only" ($validation.safety.bridge_get_only -eq $true) "blocker" "bridge_get_only=$($validation.safety.bridge_get_only)" "validation"
$globalGates += Gate-Row "bundle_is_no_post" ($bundle.safety.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($bundle.safety.bridge_post_called)" "bundle"
$globalGates += Gate-Row "bundle_has_no_http_client" ($bundle.safety.bridge_http_client_implemented -eq $false) "blocker" "bridge_http_client_implemented=$($bundle.safety.bridge_http_client_implemented)" "bundle"
$globalGates += Gate-Row "bundle_is_dry_run_only" ($bundle.safety.bridge_routing_write_dry_run_bundle_only -eq $true) "blocker" "bridge_routing_write_dry_run_bundle_only=$($bundle.safety.bridge_routing_write_dry_run_bundle_only)" "bundle"
$globalGates += Gate-Row "validation_allows_no_execution" ($validation.validation.can_execute_bridge_write_now -eq $false -and $validation.validation.can_add_bridge_http_client_now -eq $false) "blocker" "can_execute=$($validation.validation.can_execute_bridge_write_now); can_add_client=$($validation.validation.can_add_bridge_http_client_now)" "validation"

if ($rollback -ne $null) {
    $globalGates += Gate-Row "rollback_snapshot_present" $true "review" $rollbackPath "rollback"
    $globalGates += Gate-Row "rollback_snapshot_get_only" ($rollback.safety.bridge_get_only -eq $true) "blocker" "bridge_get_only=$($rollback.safety.bridge_get_only)" "rollback"
    $globalGates += Gate-Row "rollback_no_bridge_post" ($rollback.safety.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($rollback.safety.bridge_post_called)" "rollback"
} else {
    $globalGates += Gate-Row "rollback_snapshot_present" $false "review" "Rollback snapshot artifact not found." "rollback" "Generate Step 41 rollback snapshot before any future live design."
}

if ($auditPlan -ne $null) {
    $globalGates += Gate-Row "audit_plan_present" $true "review" $auditPlanPath "audit_plan"
    $globalGates += Gate-Row "audit_plan_no_bridge_post" ($auditPlan.safety.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($auditPlan.safety.bridge_post_called)" "audit_plan"
} else {
    $globalGates += Gate-Row "audit_plan_present" $false "review" "Audit plan artifact not found." "audit_plan" "Generate Step 39 audit plan before any future live design."
}

if ($bundleStatus.ok) {
    $globalGates += Gate-Row "platform_bundle_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status" "platform"
    $globalGates += Gate-Row "platform_bundle_no_http_client" ($bundleStatus.value.bridge_http_client_implemented -eq $false) "blocker" "bridge_http_client_implemented=$($bundleStatus.value.bridge_http_client_implemented)" "platform"
    $globalGates += Gate-Row "platform_bundle_no_post" ($bundleStatus.value.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($bundleStatus.value.bridge_post_called)" "platform"
} else {
    $globalGates += Gate-Row "platform_bundle_status_readable" $false "review" $bundleStatus.error "platform"
}

if ($executorStatus.ok) {
    $globalGates += Gate-Row "platform_executor_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-write-executor/status" "platform"
    $globalGates += Gate-Row "platform_executor_no_execution_endpoint" ($executorStatus.value.execution_endpoint_available -eq $false) "blocker" "execution_endpoint_available=$($executorStatus.value.execution_endpoint_available)" "platform"
    $globalGates += Gate-Row "platform_executor_no_post_impl" ($executorStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_call_implemented=$($executorStatus.value.bridge_post_call_implemented)" "platform"
} else {
    $globalGates += Gate-Row "platform_executor_status_readable" $false "review" $executorStatus.error "platform"
}

if ($auditStatus.ok) {
    $globalGates += Gate-Row "platform_audit_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-write-audit/status" "platform"
    $globalGates += Gate-Row "platform_audit_bridge_post_disabled" ($auditStatus.value.bridge_post_enabled -eq $false) "blocker" "bridge_post_enabled=$($auditStatus.value.bridge_post_enabled)" "platform"
} else {
    $globalGates += Gate-Row "platform_audit_status_readable" $false "review" $auditStatus.error "platform"
}

$globalGates += Gate-Row "bridge_health_readable" $bridgeHealth.ok "review" $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "bridge"

foreach ($gate in $globalGates) {
    if ($gate.passed -ne $true) {
        Add-Issue $issues $gate.severity $gate.gate $gate.evidence $gate.source
    }
}

$bundleRows = @()
if ($bundle.bundle -and $bundle.bundle.bundle_rows) {
    $bundleRows = @($bundle.bundle.bundle_rows)
}

$validationRows = @()
if ($validation.row_reports) {
    $validationRows = @($validation.row_reports)
}

$validationByHash = @{}
foreach ($row in $validationRows) {
    $hash = Normalize-String $row.payload_hash
    if (![string]::IsNullOrWhiteSpace($hash) -and !$validationByHash.ContainsKey($hash)) {
        $validationByHash[$hash] = $row
    }
}

$rollbackByPhone = @{}
if ($rollback -ne $null -and $rollback.rollback_rows) {
    foreach ($row in @($rollback.rollback_rows)) {
        $phone = Normalize-Phone (Normalize-String $row.phone)
        if (![string]::IsNullOrWhiteSpace($phone) -and !$rollbackByPhone.ContainsKey($phone)) {
            $rollbackByPhone[$phone] = $row
        }
    }
}

$preflightRows = @()
$rowIndex = 0

foreach ($bundleRow in $bundleRows) {
    $payloadHash = Normalize-String $bundleRow.payload_hash
    $payload = $bundleRow.payload_template
    $phone = Normalize-Phone (Normalize-String $payload.phone)

    $validationMatch = if ($validationByHash.ContainsKey($payloadHash)) { $validationByHash[$payloadHash] } else { $null }
    $rollbackMatch = if (![string]::IsNullOrWhiteSpace($phone) -and $rollbackByPhone.ContainsKey($phone)) { $rollbackByPhone[$phone] } else { $null }

    $rowGates = @()
    $rowGates += Gate-Row "row_has_validation_match" ($validationMatch -ne $null) "blocker" "payload_hash=$payloadHash" "validation"
    $rowGates += Gate-Row "row_validation_valid_template" ($validationMatch -ne $null -and $validationMatch.row_status -eq "valid_dry_run_template") "blocker" $(if ($validationMatch) { "row_status=$($validationMatch.row_status)" } else { "no validation match" }) "validation"
    $rowGates += Gate-Row "row_not_ready_for_live_execution" ($bundleRow.ready_for_live_execution -eq $false) "blocker" "ready_for_live_execution=$($bundleRow.ready_for_live_execution)" "bundle"
    $rowGates += Gate-Row "row_would_not_call_bridge" ($bundleRow.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($bundleRow.would_call_bridge)" "bundle"
    $rowGates += Gate-Row "row_would_not_mutate_platform" ($bundleRow.would_mutate_platform -eq $false) "blocker" "would_mutate_platform=$($bundleRow.would_mutate_platform)" "bundle"
    $rowGates += Gate-Row "row_would_not_call_lacrm" ($bundleRow.would_call_lacrm -eq $false) "blocker" "would_call_lacrm=$($bundleRow.would_call_lacrm)" "bundle"
    $rowGates += Gate-Row "row_has_idempotency_key_template" (![string]::IsNullOrWhiteSpace((Normalize-String $bundleRow.idempotency_key_template))) "blocker" "idempotency_key_template=$($bundleRow.idempotency_key_template)" "bundle"
    $rowGates += Gate-Row "row_has_rollback_snapshot" ($rollbackMatch -ne $null -and $rollbackMatch.rollback_snapshot_status -eq "rollback_snapshot_available") "review" $(if ($rollbackMatch) { "rollback_snapshot_status=$($rollbackMatch.rollback_snapshot_status)" } else { "no rollback match for phone=$phone" }) "rollback"

    $rowFailures = @($rowGates | Where-Object { $_.passed -ne $true })
    foreach ($gate in $rowFailures) {
        Add-Issue $issues $gate.severity "row_$rowIndex`_$($gate.gate)" $gate.evidence $gate.source
    }

    $rowStatus = if (@($rowFailures | Where-Object { $_.severity -eq "blocker" }).Count -gt 0) {
        "blocked"
    } elseif (@($rowFailures).Count -gt 0) {
        "review_required"
    } else {
        "preflight_valid_for_future_design_review"
    }

    $preflightRows += [ordered]@{
        row_index = $rowIndex
        payload_hash = $payloadHash
        phone = $phone
        target_bridge_endpoint = Normalize-String $bundleRow.target_bridge_endpoint
        http_method = Normalize-String $bundleRow.http_method
        row_status = $rowStatus
        gate_count = @($rowGates).Count
        failed_gate_count = @($rowFailures).Count
        blocker_count = @($rowFailures | Where-Object { $_.severity -eq "blocker" }).Count
        review_count = @($rowFailures | Where-Object { $_.severity -eq "review" }).Count
        validation_status = if ($validationMatch) { Normalize-String $validationMatch.row_status } else { "" }
        rollback_status = if ($rollbackMatch) { Normalize-String $rollbackMatch.rollback_snapshot_status } else { "" }
        would_call_bridge = [bool]$bundleRow.would_call_bridge
        would_mutate_platform = [bool]$bundleRow.would_mutate_platform
        would_call_lacrm = [bool]$bundleRow.would_call_lacrm
        ready_for_live_execution = [bool]$bundleRow.ready_for_live_execution
        gates = $rowGates
    }

    $rowIndex += 1
}

if ($preflightRows.Count -eq 0) {
    Add-Issue $issues "blocker" "preflight_rows_missing" "No preflight rows were generated from the dry-run bundle." "bundle"
}

$statusCounts = @{}
foreach ($row in $preflightRows) {
    if (!$statusCounts.ContainsKey($row.row_status)) { $statusCounts[$row.row_status] = 0 }
    $statusCounts[$row.row_status] += 1
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$preflightStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "preflight_valid_for_future_design_review"
} elseif ($blockerCount -eq 0) {
    "preflight_valid_with_review_items"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_preflight_matrix_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 48"
    purpose = "Bridge routing write no-POST preflight matrix"
    source_dry_run_validation = $validationPath
    source_dry_run_bundle = $bundlePath
    source_rollback_snapshot = $rollbackPath
    source_audit_plan = $auditPlanPath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_write_preflight_matrix_only = $true
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
    preflight = [ordered]@{
        status = $preflightStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        row_count = @($preflightRows).Count
        can_execute_bridge_write_now = $false
        can_add_bridge_http_client_now = $false
        can_design_future_guarded_http_client = ($blockerCount -eq 0)
        reason = if ($blockerCount -eq 0) {
            "Preflight matrix has no hard blockers. This is only for future design review; Step 48 still implements no bridge write."
        } else {
            "Preflight matrix found blockers. Resolve blockers before any future bridge HTTP client design."
        }
    }
    global_gates = $globalGates
    preflight_rows = $preflightRows
    issues = @($issues)
    platform_status = [ordered]@{
        bundle_status_ok = $bundleStatus.ok
        bundle_status = if ($bundleStatus.ok) { $bundleStatus.value } else { $null }
        executor_status_ok = $executorStatus.ok
        executor_status = if ($executorStatus.ok) { $executorStatus.value } else { $null }
        audit_status_ok = $auditStatus.ok
        audit_status = if ($auditStatus.ok) { $auditStatus.value } else { $null }
    }
    bridge_status = [ordered]@{
        health_ok = $bridgeHealth.ok
        health = if ($bridgeHealth.ok) { $bridgeHealth.value } else { $null }
    }
    counts = [ordered]@{
        global_gates = @($globalGates).Count
        preflight_rows = @($preflightRows).Count
        blockers = $blockerCount
        reviews = $reviewCount
        status_counts = $statusCounts
    }
    next_recommended_actions = @(
        "Resolve preflight blockers before designing any bridge HTTP client.",
        "If only review items remain, review and accept them before future design.",
        "Do not call bridge POST endpoints from Step 48.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_preflight_matrix.json"
$rowsCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_preflight_matrix_rows.csv"
$issuesCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_preflight_matrix_issues.csv"
$gatesCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_preflight_matrix_global_gates.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_preflight_matrix.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$preflightRows |
    Select-Object row_index, payload_hash, phone, target_bridge_endpoint, http_method, row_status, gate_count, failed_gate_count, blocker_count, review_count, validation_status, rollback_status, would_call_bridge, would_mutate_platform, would_call_lacrm, ready_for_live_execution |
    Export-Csv -LiteralPath $rowsCsvPath -NoTypeInformation -Encoding UTF8

$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8
$globalGates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8

$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }
$statusText = if ($statusCounts.Count -gt 0) { ($statusCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Bridge Routing Write Preflight Matrix

Generated: $($report.generated_at)

Source dry-run validation:

``````
$validationPath
``````

Source dry-run bundle:

``````
$bundlePath
``````

## Safety

- Bridge routing write preflight matrix only: true
- Bridge GET only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Bridge HTTP client implemented: false
- Bridge POST call implemented: false
- Routing write endpoint implemented: false
- Live write enabled: false

## Preflight

- Status: $preflightStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Rows: $($preflightRows.Count)
- Can execute bridge write now: false
- Can add bridge HTTP client now: false

## Row status counts

$statusText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_write_preflight_matrix=$OutputDir | status=$preflightStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_write_preflight_matrix=$OutputDir | status=$preflightStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Preflight matrix files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
