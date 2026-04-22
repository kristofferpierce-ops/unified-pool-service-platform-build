param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$PreflightMatrixDir = "",
    [string]$DryRunValidationDir = "",
    [string]$DryRunDir = "",
    [string]$StubReportDir = "",
    [string]$ReleaseCheckpointDir = "",
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
    $PreflightMatrixDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_preflight_matrix_*" -JsonName "phase20_bridge_routing_http_client_preflight_matrix.json"
}
if ([string]::IsNullOrWhiteSpace($DryRunValidationDir)) {
    $DryRunValidationDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_dry_run_validation_*" -JsonName "phase20_bridge_routing_http_client_dry_run_validation.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($DryRunDir)) {
    $DryRunDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_dry_run_*" -JsonName "phase20_bridge_routing_http_client_dry_run.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($StubReportDir)) {
    $StubReportDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_stub_*" -JsonName "phase20_bridge_routing_http_client_stub.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($ReleaseCheckpointDir)) {
    $ReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_release_checkpoint_*" -JsonName "phase19_bridge_routing_write_release_checkpoint.json" -Required $false
}

$preflightPath = Join-Path $PreflightMatrixDir "phase20_bridge_routing_http_client_preflight_matrix.json"
$validationPath = if (![string]::IsNullOrWhiteSpace($DryRunValidationDir)) { Join-Path $DryRunValidationDir "phase20_bridge_routing_http_client_dry_run_validation.json" } else { "" }
$dryRunPath = if (![string]::IsNullOrWhiteSpace($DryRunDir)) { Join-Path $DryRunDir "phase20_bridge_routing_http_client_dry_run.json" } else { "" }
$stubPath = if (![string]::IsNullOrWhiteSpace($StubReportDir)) { Join-Path $StubReportDir "phase20_bridge_routing_http_client_stub.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($ReleaseCheckpointDir)) { Join-Path $ReleaseCheckpointDir "phase19_bridge_routing_write_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $preflightPath)) {
    throw "HTTP client preflight matrix JSON not found: $preflightPath"
}

$preflight = Read-JsonFile $preflightPath
$validation = if (![string]::IsNullOrWhiteSpace($validationPath) -and (Test-Path -LiteralPath $validationPath)) { Read-JsonFile $validationPath } else { $null }
$dryRun = if (![string]::IsNullOrWhiteSpace($dryRunPath) -and (Test-Path -LiteralPath $dryRunPath)) { Read-JsonFile $dryRunPath } else { $null }
$stub = if (![string]::IsNullOrWhiteSpace($stubPath) -and (Test-Path -LiteralPath $stubPath)) { Read-JsonFile $stubPath } else { $null }
$release = if (![string]::IsNullOrWhiteSpace($releasePath) -and (Test-Path -LiteralPath $releasePath)) { Read-JsonFile $releasePath } else { $null }

$dryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$stubStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-stub/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bundleStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$signoffItems = New-Object System.Collections.ArrayList

Add-SignoffItem $signoffItems "artifact" "HTTP client preflight matrix exists" $true $preflightPath
Add-SignoffItem $signoffItems "safety" "Preflight matrix is preflight-matrix-only" ($preflight.safety.bridge_routing_http_client_preflight_matrix_only -eq $true) "bridge_routing_http_client_preflight_matrix_only=$($preflight.safety.bridge_routing_http_client_preflight_matrix_only)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix is bridge GET only" ($preflight.safety.bridge_get_only -eq $true) "bridge_get_only=$($preflight.safety.bridge_get_only)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no platform DB mutation" ($preflight.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($preflight.safety.platform_db_mutation_performed)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no bridge mutation" ($preflight.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($preflight.safety.bridge_mutation_performed)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no bridge POST" ($preflight.safety.bridge_post_called -eq $false -and $preflight.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($preflight.safety.bridge_post_called); bridge_post_call_implemented=$($preflight.safety.bridge_post_call_implemented)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no real HTTP client" ($preflight.safety.real_bridge_http_client_implemented -eq $false) "real_bridge_http_client_implemented=$($preflight.safety.real_bridge_http_client_implemented)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no network transport" ($preflight.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($preflight.safety.network_transport_implemented)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no LACRM call" ($preflight.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($preflight.safety.lacrm_call_performed)"

Add-SignoffItem $signoffItems "gate" "Preflight says bridge write cannot execute now" ($preflight.preflight.can_execute_bridge_write_now -eq $false) "can_execute_bridge_write_now=$($preflight.preflight.can_execute_bridge_write_now)"
Add-SignoffItem $signoffItems "gate" "Preflight says network transport cannot be added now" ($preflight.preflight.can_add_network_transport_now -eq $false) "can_add_network_transport_now=$($preflight.preflight.can_add_network_transport_now)"
Add-SignoffItem $signoffItems "gate" "Preflight says real bridge HTTP client cannot be added now" ($preflight.preflight.can_add_real_bridge_http_client_now -eq $false) "can_add_real_bridge_http_client_now=$($preflight.preflight.can_add_real_bridge_http_client_now)"
Add-SignoffItem $signoffItems "gate" "Preflight has zero hard blockers" ([int]$preflight.preflight.blocker_count -eq 0) "blocker_count=$($preflight.preflight.blocker_count)"
Add-SignoffItem $signoffItems "gate" "Preflight has zero review items" ([int]$preflight.preflight.review_count -eq 0) "review_count=$($preflight.preflight.review_count)" "recommended"

foreach ($issue in @($preflight.issues)) {
    $severity = if ($issue.severity) { [string]$issue.severity } else { "review" }
    Add-Issue $issues $severity "preflight_$($issue.code)" "$($issue.message)" "preflight"
}

if ($validation -ne $null) {
    Add-SignoffItem $signoffItems "artifact" "Dry-run validation report exists" $true $validationPath
    Add-SignoffItem $signoffItems "safety" "Dry-run validation has no network transport" ($validation.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($validation.safety.network_transport_implemented)"
    Add-SignoffItem $signoffItems "safety" "Dry-run validation has no bridge POST" ($validation.safety.bridge_post_called -eq $false -and $validation.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($validation.safety.bridge_post_called); bridge_post_call_implemented=$($validation.safety.bridge_post_call_implemented)"
    Add-SignoffItem $signoffItems "gate" "Dry-run validation says bridge write cannot execute now" ($validation.validation.can_execute_bridge_write_now -eq $false) "can_execute_bridge_write_now=$($validation.validation.can_execute_bridge_write_now)"
} else {
    Add-SignoffItem $signoffItems "artifact" "Dry-run validation report exists" $false "Phase 20 Step 3 validation artifact not found." "recommended"
    Add-Issue $issues "review" "dry_run_validation_missing" "Phase 20 Step 3 validation artifact was not found." "dry_run_validation"
}

if ($dryRun -ne $null) {
    Add-SignoffItem $signoffItems "artifact" "Dry-run transport report exists" $true $dryRunPath
    Add-SignoffItem $signoffItems "safety" "Dry-run transport report has no network transport" ($dryRun.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($dryRun.safety.network_transport_implemented)"
    Add-SignoffItem $signoffItems "safety" "Dry-run simulated response would not send" ($dryRun.simulation.simulated_response.would_send -eq $false) "would_send=$($dryRun.simulation.simulated_response.would_send)"
} else {
    Add-SignoffItem $signoffItems "artifact" "Dry-run transport report exists" $false "Phase 20 Step 2 dry-run artifact not found." "recommended"
    Add-Issue $issues "review" "dry_run_transport_missing" "Phase 20 Step 2 dry-run artifact was not found." "dry_run"
}

if ($stub -ne $null) {
    Add-SignoffItem $signoffItems "artifact" "HTTP client stub report exists" $true $stubPath
    Add-SignoffItem $signoffItems "safety" "Stub report has no real HTTP client" ($stub.safety.real_bridge_http_client_implemented -eq $false) "real_bridge_http_client_implemented=$($stub.safety.real_bridge_http_client_implemented)"
    Add-SignoffItem $signoffItems "safety" "Stub report has no bridge POST" ($stub.safety.bridge_post_called -eq $false) "bridge_post_called=$($stub.safety.bridge_post_called)"
} else {
    Add-SignoffItem $signoffItems "artifact" "HTTP client stub report exists" $false "Phase 20 Step 1 stub artifact not found." "recommended"
    Add-Issue $issues "review" "http_client_stub_missing" "Phase 20 Step 1 stub artifact was not found." "stub"
}

if ($release -ne $null) {
    Add-SignoffItem $signoffItems "artifact" "Phase 19 no-POST release checkpoint exists" $true $releasePath
    Add-SignoffItem $signoffItems "safety" "Release checkpoint has no bridge HTTP client" ($release.safety.bridge_http_client_implemented -eq $false) "bridge_http_client_implemented=$($release.safety.bridge_http_client_implemented)"
    Add-SignoffItem $signoffItems "safety" "Release checkpoint has no bridge POST" ($release.safety.bridge_post_called -eq $false) "bridge_post_called=$($release.safety.bridge_post_called)"
} else {
    Add-SignoffItem $signoffItems "artifact" "Phase 19 no-POST release checkpoint exists" $false "Phase 19 Step 50 release checkpoint artifact not found." "recommended"
    Add-Issue $issues "review" "release_checkpoint_missing" "Phase 19 Step 50 release checkpoint artifact was not found." "release_checkpoint"
}

# Runtime checks are review-level when unreachable, but safety contradictions are required.
if ($dryRunStatus.ok) {
    Add-SignoffItem $signoffItems "runtime" "Dry-run status readable" $true "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status" "recommended"
    Add-SignoffItem $signoffItems "runtime" "Runtime dry-run has no network transport" ($dryRunStatus.value.network_transport_implemented -eq $false) "network_transport_implemented=$($dryRunStatus.value.network_transport_implemented)"
    Add-SignoffItem $signoffItems "runtime" "Runtime dry-run has no bridge POST" ($dryRunStatus.value.bridge_post_called -eq $false -and $dryRunStatus.value.bridge_post_call_implemented -eq $false) "bridge_post_called=$($dryRunStatus.value.bridge_post_called); bridge_post_call_implemented=$($dryRunStatus.value.bridge_post_call_implemented)"
} else {
    Add-SignoffItem $signoffItems "runtime" "Dry-run status readable" $false $dryRunStatus.error "recommended"
    Add-Issue $issues "review" "dry_run_status_unreadable" "Could not read dry-run status: $($dryRunStatus.error)" "runtime"
}

if ($stubStatus.ok) {
    Add-SignoffItem $signoffItems "runtime" "Stub status readable" $true "$PlatformApi/front-desk/routing/bridge-http-client-stub/status" "recommended"
    Add-SignoffItem $signoffItems "runtime" "Runtime stub has no real HTTP client" ($stubStatus.value.real_bridge_http_client_implemented -eq $false) "real_bridge_http_client_implemented=$($stubStatus.value.real_bridge_http_client_implemented)"
} else {
    Add-SignoffItem $signoffItems "runtime" "Stub status readable" $false $stubStatus.error "recommended"
    Add-Issue $issues "review" "stub_status_unreadable" "Could not read stub status: $($stubStatus.error)" "runtime"
}

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
    Add-SignoffItem $signoffItems "runtime" "Dry-run bundle has no bridge POST" ($bundleStatus.value.bridge_post_called -eq $false -and $bundleStatus.value.bridge_post_call_implemented -eq $false) "bridge_post_called=$($bundleStatus.value.bridge_post_called); bridge_post_call_implemented=$($bundleStatus.value.bridge_post_call_implemented)"
} else {
    Add-SignoffItem $signoffItems "runtime" "Dry-run bundle status readable" $false $bundleStatus.error "recommended"
    Add-Issue $issues "review" "bundle_status_unreadable" "Could not read bundle status: $($bundleStatus.error)" "runtime"
}

Add-SignoffItem $signoffItems "runtime" "Bridge health readable" $bridgeHealth.ok $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "recommended"

# Convert failed signoff items into issues.
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
    "ready_for_operator_transport_design_review"
} elseif ($blockerCount -eq 0) {
    "operator_review_required"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_http_client_operator_signoff_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$operatorAttestation = [ordered]@{
    operator_name = ""
    reviewed_at = ""
    approved_for_future_transport_design_only = $false
    approved_for_live_bridge_write = $false
    approved_for_real_network_transport = $false
    required_statement = "I reviewed the no-network HTTP client preflight matrix and understand this packet does not authorize live bridge routing writes or real bridge network transport."
    notes = ""
}

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 5"
    purpose = "Bridge routing HTTP client operator signoff dossier"
    source_preflight_matrix = $preflightPath
    source_dry_run_validation = $validationPath
    source_dry_run_report = $dryRunPath
    source_stub_report = $stubPath
    source_release_checkpoint = $releasePath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_http_client_operator_signoff_only = $true
        bridge_get_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        real_bridge_http_client_implemented = $false
        network_transport_implemented = $false
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
        can_add_network_transport_now = $false
        can_add_real_bridge_http_client_now = $false
        operator_signoff_required = $true
        approved_for_live_bridge_write = $false
        approved_for_real_network_transport = $false
        reason = if ($blockerCount -eq 0) {
            "HTTP client operator signoff dossier can be reviewed. Phase 20 Step 5 still implements no real transport and authorizes no execution."
        } else {
            "HTTP client operator signoff dossier has blockers. Resolve blockers before any future network transport design."
        }
    }
    operator_attestation = $operatorAttestation
    checklist = @($signoffItems)
    issues = @($issues)
    runtime_status = [ordered]@{
        dry_run_status_ok = $dryRunStatus.ok
        dry_run_status = if ($dryRunStatus.ok) { $dryRunStatus.value } else { $null }
        stub_status_ok = $stubStatus.ok
        stub_status = if ($stubStatus.ok) { $stubStatus.value } else { $null }
        executor_status_ok = $executorStatus.ok
        executor_status = if ($executorStatus.ok) { $executorStatus.value } else { $null }
        bundle_status_ok = $bundleStatus.ok
        bundle_status = if ($bundleStatus.ok) { $bundleStatus.value } else { $null }
        bridge_health_ok = $bridgeHealth.ok
        bridge_health = if ($bridgeHealth.ok) { $bridgeHealth.value } else { $null }
        bridge_health_error = $bridgeHealth.error
    }
    counts = [ordered]@{
        checklist_items = @($signoffItems).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Resolve signoff blockers before designing any real bridge network transport.",
        "If only review items remain, operator can review and decide whether future design can continue.",
        "Do not call bridge POST endpoints from Phase 20 Step 5.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_operator_signoff.json"
$checklistCsvPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_operator_signoff_checklist.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_operator_signoff_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_operator_signoff.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$signoffItems | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$checklistText = (@($signoffItems) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing HTTP Client Operator Signoff

Generated: $($report.generated_at)

Source preflight matrix:

``````
$preflightPath
``````

## Safety

- Bridge routing HTTP client operator signoff only: true
- Bridge GET only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Real bridge HTTP client implemented: false
- Network transport implemented: false
- Bridge POST call implemented: false
- Routing write endpoint implemented: false
- Live write enabled: false

## Signoff

- Status: $signoffStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Can execute bridge write now: false
- Can add network transport now: false
- Can add real bridge HTTP client now: false
- Approved for live bridge write: false
- Approved for real network transport: false

## Checklist

$checklistText

## Issues

$issueText

## Operator attestation

- Operator name:
- Reviewed at:
- Approved for future transport design only: false
- Approved for live bridge write: false
- Approved for real network transport: false
- Required statement: I reviewed the no-network HTTP client preflight matrix and understand this packet does not authorize live bridge routing writes or real bridge network transport.
- Notes:
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_http_client_operator_signoff=$OutputDir | status=$signoffStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_http_client_operator_signoff=$OutputDir | status=$signoffStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "HTTP client operator signoff files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
