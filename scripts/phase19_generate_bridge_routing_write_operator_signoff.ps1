param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$PreflightMatrixDir = "",
    [string]$CutoverPacketDir = "",
    [string]$ReadinessDir = "",
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

function Add-SignoffItem {
    param(
        [System.Collections.ArrayList]$Items,
        [string]$Category,
        [string]$Item,
        [bool]$Passed,
        [string]$Evidence = "",
        [string]$Required = "yes",
        [string]$OperatorNote = ""
    )

    [void]$Items.Add([ordered]@{
        category = $Category
        item = $Item
        passed = $Passed
        evidence = $Evidence
        required = $Required
        operator_note = $OperatorNote
    })
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($PreflightMatrixDir)) {
    $PreflightMatrixDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_preflight_matrix_*" -JsonName "phase19_bridge_routing_write_preflight_matrix.json"
}
if ([string]::IsNullOrWhiteSpace($CutoverPacketDir)) {
    $CutoverPacketDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_cutover_packet_*" -JsonName "phase19_bridge_routing_write_cutover_packet.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($ReadinessDir)) {
    $ReadinessDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_readiness_*" -JsonName "phase19_bridge_routing_write_readiness.json" -Required $false
}

$preflightPath = Join-Path $PreflightMatrixDir "phase19_bridge_routing_write_preflight_matrix.json"
$cutoverPath = if (![string]::IsNullOrWhiteSpace($CutoverPacketDir)) { Join-Path $CutoverPacketDir "phase19_bridge_routing_write_cutover_packet.json" } else { "" }
$readinessPath = if (![string]::IsNullOrWhiteSpace($ReadinessDir)) { Join-Path $ReadinessDir "phase19_bridge_routing_write_readiness.json" } else { "" }

if (!(Test-Path -LiteralPath $preflightPath)) { throw "Preflight matrix JSON not found: $preflightPath" }

$preflight = Read-JsonFile $preflightPath
$cutover = if (![string]::IsNullOrWhiteSpace($cutoverPath) -and (Test-Path -LiteralPath $cutoverPath)) { Read-JsonFile $cutoverPath } else { $null }
$readiness = if (![string]::IsNullOrWhiteSpace($readinessPath) -and (Test-Path -LiteralPath $readinessPath)) { Read-JsonFile $readinessPath } else { $null }

$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bundleStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status"
$auditStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-audit/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$signoffItems = New-Object System.Collections.ArrayList

# Preflight gates.
Add-SignoffItem $signoffItems "artifact" "Preflight matrix exists" $true $preflightPath
Add-SignoffItem $signoffItems "safety" "Preflight matrix is no-post" ($preflight.safety.bridge_post_called -eq $false) "bridge_post_called=$($preflight.safety.bridge_post_called)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix is bridge GET only" ($preflight.safety.bridge_get_only -eq $true) "bridge_get_only=$($preflight.safety.bridge_get_only)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no platform DB mutation" ($preflight.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($preflight.safety.platform_db_mutation_performed)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no bridge HTTP client" ($preflight.safety.bridge_http_client_implemented -eq $false) "bridge_http_client_implemented=$($preflight.safety.bridge_http_client_implemented)"
Add-SignoffItem $signoffItems "gate" "Preflight says bridge write cannot execute now" ($preflight.preflight.can_execute_bridge_write_now -eq $false) "can_execute_bridge_write_now=$($preflight.preflight.can_execute_bridge_write_now)"
Add-SignoffItem $signoffItems "gate" "Preflight says bridge HTTP client cannot be added now" ($preflight.preflight.can_add_bridge_http_client_now -eq $false) "can_add_bridge_http_client_now=$($preflight.preflight.can_add_bridge_http_client_now)"
Add-SignoffItem $signoffItems "gate" "Preflight has zero hard blockers" ([int]$preflight.preflight.blocker_count -eq 0) "blocker_count=$($preflight.preflight.blocker_count)"
Add-SignoffItem $signoffItems "gate" "Preflight has zero review items" ([int]$preflight.preflight.review_count -eq 0) "review_count=$($preflight.preflight.review_count)" "recommended"

foreach ($issue in @($preflight.issues)) {
    $severity = if ($issue.severity) { [string]$issue.severity } else { "review" }
    Add-Issue $issues $severity "preflight_$($issue.code)" "$($issue.message)" "preflight"
}

if ($cutover -ne $null) {
    Add-SignoffItem $signoffItems "artifact" "Cutover packet exists" $true $cutoverPath
    Add-SignoffItem $signoffItems "safety" "Cutover packet has no bridge POST" ($cutover.safety.bridge_post_called -eq $false) "bridge_post_called=$($cutover.safety.bridge_post_called)"
    Add-SignoffItem $signoffItems "gate" "Cutover packet says bridge write cannot execute now" ($cutover.cutover_packet.can_execute_bridge_write_now -eq $false) "can_execute_bridge_write_now=$($cutover.cutover_packet.can_execute_bridge_write_now)"
    Add-SignoffItem $signoffItems "operator" "Cutover operator signoff is future-design only" ($cutover.operator_signoff.approved_for_future_design_only -eq $true) "approved_for_future_design_only=$($cutover.operator_signoff.approved_for_future_design_only)" "recommended" "Operator can update packet manually if desired."
    Add-SignoffItem $signoffItems "operator" "Cutover is not approved for live bridge write" ($cutover.operator_signoff.approved_for_live_bridge_write -ne $true) "approved_for_live_bridge_write=$($cutover.operator_signoff.approved_for_live_bridge_write)"
} else {
    Add-SignoffItem $signoffItems "artifact" "Cutover packet exists" $false "Cutover packet artifact not found." "recommended"
    Add-Issue $issues "review" "cutover_packet_missing" "Cutover packet artifact was not found." "cutover"
}

if ($readiness -ne $null) {
    Add-SignoffItem $signoffItems "artifact" "Readiness report exists" $true $readinessPath
    Add-SignoffItem $signoffItems "safety" "Readiness report has no bridge POST" ($readiness.safety.bridge_post_called -eq $false) "bridge_post_called=$($readiness.safety.bridge_post_called)"
    Add-SignoffItem $signoffItems "gate" "Readiness report says bridge write cannot execute now" ($readiness.readiness.can_execute_bridge_write_now -eq $false) "can_execute_bridge_write_now=$($readiness.readiness.can_execute_bridge_write_now)"
} else {
    Add-SignoffItem $signoffItems "artifact" "Readiness report exists" $false "Readiness artifact not found." "recommended"
    Add-Issue $issues "review" "readiness_missing" "Readiness artifact was not found." "readiness"
}

# Runtime checks are review-level if unreachable; this signoff dossier stays file-based and no-write.
if ($executorStatus.ok) {
    Add-SignoffItem $signoffItems "runtime" "Executor status readable" $true "$PlatformApi/front-desk/routing/bridge-write-executor/status" "recommended"
    Add-SignoffItem $signoffItems "runtime" "Executor has no execution endpoint" ($executorStatus.value.execution_endpoint_available -eq $false) "execution_endpoint_available=$($executorStatus.value.execution_endpoint_available)"
    Add-SignoffItem $signoffItems "runtime" "Executor has no bridge POST implementation" ($executorStatus.value.bridge_post_call_implemented -eq $false) "bridge_post_call_implemented=$($executorStatus.value.bridge_post_call_implemented)"
} else {
    Add-SignoffItem $signoffItems "runtime" "Executor status readable" $false $executorStatus.error "recommended"
    Add-Issue $issues "review" "executor_status_unreadable" "Could not read executor status: $($executorStatus.error)" "runtime"
}

if ($bundleStatus.ok) {
    Add-SignoffItem $signoffItems "runtime" "Dry-run bundle status readable" $true "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status" "recommended"
    Add-SignoffItem $signoffItems "runtime" "Dry-run bundle has no HTTP client" ($bundleStatus.value.bridge_http_client_implemented -eq $false) "bridge_http_client_implemented=$($bundleStatus.value.bridge_http_client_implemented)"
    Add-SignoffItem $signoffItems "runtime" "Dry-run bundle has no bridge POST call" ($bundleStatus.value.bridge_post_call_implemented -eq $false) "bridge_post_call_implemented=$($bundleStatus.value.bridge_post_call_implemented)"
} else {
    Add-SignoffItem $signoffItems "runtime" "Dry-run bundle status readable" $false $bundleStatus.error "recommended"
    Add-Issue $issues "review" "bundle_status_unreadable" "Could not read dry-run bundle status: $($bundleStatus.error)" "runtime"
}

if ($auditStatus.ok) {
    Add-SignoffItem $signoffItems "runtime" "Audit status readable" $true "$PlatformApi/front-desk/routing/bridge-write-audit/status" "recommended"
    Add-SignoffItem $signoffItems "runtime" "Audit reports bridge POST disabled" ($auditStatus.value.bridge_post_enabled -eq $false) "bridge_post_enabled=$($auditStatus.value.bridge_post_enabled)"
} else {
    Add-SignoffItem $signoffItems "runtime" "Audit status readable" $false $auditStatus.error "recommended"
    Add-Issue $issues "review" "audit_status_unreadable" "Could not read audit status: $($auditStatus.error)" "runtime"
}

Add-SignoffItem $signoffItems "runtime" "Bridge health readable" $bridgeHealth.ok $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "recommended"

# Convert failed required signoff items into issues too.
foreach ($item in @($signoffItems)) {
    if ($item.passed -ne $true -and $item.required -eq "yes") {
        Add-Issue $issues "blocker" ("signoff_" + ($item.item -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $item.evidence $item.category
    } elseif ($item.passed -ne $true -and $item.required -eq "recommended") {
        Add-Issue $issues "review" ("signoff_" + ($item.item -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $item.evidence $item.category
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$signoffStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "ready_for_operator_signoff_review"
} elseif ($blockerCount -eq 0) {
    "operator_review_required"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_operator_signoff_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$operatorAttestation = [ordered]@{
    operator_name = ""
    reviewed_at = ""
    approved_for_future_design_only = $false
    approved_for_live_bridge_write = $false
    required_statement = "I reviewed the no-POST preflight matrix and understand this packet does not authorize live bridge routing writes."
    notes = ""
}

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 49"
    purpose = "Bridge routing write operator signoff dossier"
    source_preflight_matrix = $preflightPath
    source_cutover_packet = $cutoverPath
    source_readiness = $readinessPath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_write_operator_signoff_only = $true
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
    signoff = [ordered]@{
        status = $signoffStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        checklist_items = @($signoffItems).Count
        can_execute_bridge_write_now = $false
        can_add_bridge_http_client_now = $false
        operator_signoff_required = $true
        approved_for_live_bridge_write = $false
        reason = if ($blockerCount -eq 0) {
            "Operator signoff dossier can be reviewed. Step 49 still implements no bridge write and authorizes no execution."
        } else {
            "Operator signoff dossier has blockers. Resolve blockers before any future bridge HTTP client design."
        }
    }
    operator_attestation = $operatorAttestation
    checklist = @($signoffItems)
    issues = @($issues)
    platform_status = [ordered]@{
        executor_status_ok = $executorStatus.ok
        executor_status = if ($executorStatus.ok) { $executorStatus.value } else { $null }
        bundle_status_ok = $bundleStatus.ok
        bundle_status = if ($bundleStatus.ok) { $bundleStatus.value } else { $null }
        audit_status_ok = $auditStatus.ok
        audit_status = if ($auditStatus.ok) { $auditStatus.value } else { $null }
    }
    bridge_status = [ordered]@{
        health_ok = $bridgeHealth.ok
        health = if ($bridgeHealth.ok) { $bridgeHealth.value } else { $null }
        error = $bridgeHealth.error
    }
    counts = [ordered]@{
        checklist_items = @($signoffItems).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Resolve signoff blockers before designing any bridge HTTP client.",
        "If only review items remain, operator can review and decide whether future design can continue.",
        "Do not call bridge POST endpoints from Step 49.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_operator_signoff.json"
$checklistCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_operator_signoff_checklist.csv"
$issuesCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_operator_signoff_issues.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_operator_signoff.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$signoffItems | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$checklistText = (@($signoffItems) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Bridge Routing Write Operator Signoff

Generated: $($report.generated_at)

Source preflight matrix:

``````
$preflightPath
``````

## Safety

- Bridge routing write operator signoff only: true
- Bridge GET only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Bridge HTTP client implemented: false
- Bridge POST call implemented: false
- Routing write endpoint implemented: false
- Live write enabled: false

## Signoff

- Status: $signoffStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Can execute bridge write now: false
- Can add bridge HTTP client now: false
- Approved for live bridge write: false

## Checklist

$checklistText

## Issues

$issueText

## Operator attestation

- Operator name:
- Reviewed at:
- Approved for future design only: false
- Approved for live bridge write: false
- Required statement: I reviewed the no-POST preflight matrix and understand this packet does not authorize live bridge routing writes.
- Notes:
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_write_operator_signoff=$OutputDir | status=$signoffStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_write_operator_signoff=$OutputDir | status=$signoffStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Operator signoff files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
