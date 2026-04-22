param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
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

function Gate-Row {
    param(
        [string]$Gate,
        [bool]$Passed,
        [string]$Severity,
        [string]$Evidence,
        [string]$Source = "",
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

function Normalize-String {
    param($Value)
    if ($null -eq $Value) { return "" }
    return ([string]$Value).Trim()
}

function Test-HasProperty {
    param($Object, [string]$Name)
    if ($null -eq $Object) { return $false }
    return $Object.PSObject.Properties.Name -contains $Name
}

function Add-GateIssueIfFailed {
    param(
        [System.Collections.ArrayList]$Issues,
        $Gate
    )

    if ($Gate.passed -ne $true) {
        Add-Issue $Issues $Gate.severity $Gate.gate $Gate.evidence $Gate.source
    }
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($DryRunValidationDir)) {
    $DryRunValidationDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_dry_run_validation_*" -JsonName "phase20_bridge_routing_http_client_dry_run_validation.json"
}
if ([string]::IsNullOrWhiteSpace($DryRunDir)) {
    $DryRunDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_dry_run_*" -JsonName "phase20_bridge_routing_http_client_dry_run.json"
}
if ([string]::IsNullOrWhiteSpace($StubReportDir)) {
    $StubReportDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_stub_*" -JsonName "phase20_bridge_routing_http_client_stub.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($ReleaseCheckpointDir)) {
    $ReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_release_checkpoint_*" -JsonName "phase19_bridge_routing_write_release_checkpoint.json" -Required $false
}

$validationPath = Join-Path $DryRunValidationDir "phase20_bridge_routing_http_client_dry_run_validation.json"
$dryRunPath = Join-Path $DryRunDir "phase20_bridge_routing_http_client_dry_run.json"
$stubPath = if (![string]::IsNullOrWhiteSpace($StubReportDir)) { Join-Path $StubReportDir "phase20_bridge_routing_http_client_stub.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($ReleaseCheckpointDir)) { Join-Path $ReleaseCheckpointDir "phase19_bridge_routing_write_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $validationPath)) { throw "Dry-run validation JSON not found: $validationPath" }
if (!(Test-Path -LiteralPath $dryRunPath)) { throw "Dry-run transport JSON not found: $dryRunPath" }

$validation = Read-JsonFile $validationPath
$dryRun = Read-JsonFile $dryRunPath
$stub = if (![string]::IsNullOrWhiteSpace($stubPath) -and (Test-Path -LiteralPath $stubPath)) { Read-JsonFile $stubPath } else { $null }
$release = if (![string]::IsNullOrWhiteSpace($releasePath) -and (Test-Path -LiteralPath $releasePath)) { Read-JsonFile $releasePath } else { $null }

$dryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$stubStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-stub/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bundleStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$globalGates = @()

# Global gates from Phase 20 Step 3 validation.
$globalGates += Gate-Row "dry_run_validation_exists" $true "blocker" $validationPath "dry_run_validation"
$globalGates += Gate-Row "dry_run_report_exists" $true "blocker" $dryRunPath "dry_run"
$globalGates += Gate-Row "validation_is_validation_only" ($validation.safety.bridge_routing_http_client_dry_run_validation_only -eq $true) "blocker" "bridge_routing_http_client_dry_run_validation_only=$($validation.safety.bridge_routing_http_client_dry_run_validation_only)" "dry_run_validation"
$globalGates += Gate-Row "validation_bridge_get_only" ($validation.safety.bridge_get_only -eq $true) "blocker" "bridge_get_only=$($validation.safety.bridge_get_only)" "dry_run_validation"
$globalGates += Gate-Row "validation_no_network_transport" ($validation.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($validation.safety.network_transport_implemented)" "dry_run_validation"
$globalGates += Gate-Row "validation_no_real_http_client" ($validation.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($validation.safety.real_bridge_http_client_implemented)" "dry_run_validation"
$globalGates += Gate-Row "validation_no_bridge_post" ($validation.safety.bridge_post_called -eq $false -and $validation.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($validation.safety.bridge_post_called); bridge_post_call_implemented=$($validation.safety.bridge_post_call_implemented)" "dry_run_validation"
$globalGates += Gate-Row "validation_no_mutation" ($validation.safety.platform_db_mutation_performed -eq $false -and $validation.safety.bridge_mutation_performed -eq $false) "blocker" "platform_db_mutation=$($validation.safety.platform_db_mutation_performed); bridge_mutation=$($validation.safety.bridge_mutation_performed)" "dry_run_validation"
$globalGates += Gate-Row "validation_no_lacrm" ($validation.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($validation.safety.lacrm_call_performed)" "dry_run_validation"
$globalGates += Gate-Row "validation_blocks_execution" ($validation.validation.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($validation.validation.can_execute_bridge_write_now)" "dry_run_validation"
$globalGates += Gate-Row "validation_blocks_network_transport" ($validation.validation.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($validation.validation.can_add_network_transport_now)" "dry_run_validation"
$globalGates += Gate-Row "validation_blocks_real_http_client" ($validation.validation.can_add_real_bridge_http_client_now -eq $false) "blocker" "can_add_real_bridge_http_client_now=$($validation.validation.can_add_real_bridge_http_client_now)" "dry_run_validation"

# Global gates from Phase 20 Step 2 dry-run report.
$globalGates += Gate-Row "dry_run_transport_only" ($dryRun.safety.bridge_routing_http_client_dry_run_only -eq $true) "blocker" "bridge_routing_http_client_dry_run_only=$($dryRun.safety.bridge_routing_http_client_dry_run_only)" "dry_run"
$globalGates += Gate-Row "dry_run_no_network_transport" ($dryRun.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($dryRun.safety.network_transport_implemented)" "dry_run"
$globalGates += Gate-Row "dry_run_no_bridge_post" ($dryRun.safety.bridge_post_called -eq $false -and $dryRun.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($dryRun.safety.bridge_post_called); bridge_post_call_implemented=$($dryRun.safety.bridge_post_call_implemented)" "dry_run"
$globalGates += Gate-Row "dry_run_simulated_response_no_send" ($dryRun.simulation.simulated_response.would_send -eq $false) "blocker" "would_send=$($dryRun.simulation.simulated_response.would_send)" "dry_run"
$globalGates += Gate-Row "dry_run_simulated_transport_no_network" ($dryRun.simulation.simulated_request.transport -eq "dry_run_no_network") "blocker" "transport=$($dryRun.simulation.simulated_request.transport)" "dry_run"

# Optional upstream evidence.
if ($stub -ne $null) {
    $globalGates += Gate-Row "stub_report_present" $true "review" $stubPath "stub"
    $globalGates += Gate-Row "stub_no_real_http_client" ($stub.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($stub.safety.real_bridge_http_client_implemented)" "stub"
    $globalGates += Gate-Row "stub_no_bridge_post" ($stub.safety.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($stub.safety.bridge_post_called)" "stub"
} else {
    $globalGates += Gate-Row "stub_report_present" $false "review" "Phase 20 Step 1 stub report not found." "stub" "Generate Step 1 stub report before real transport design."
}

if ($release -ne $null) {
    $globalGates += Gate-Row "release_checkpoint_present" $true "review" $releasePath "release_checkpoint"
    $globalGates += Gate-Row "release_checkpoint_no_http_client" ($release.safety.bridge_http_client_implemented -eq $false) "blocker" "bridge_http_client_implemented=$($release.safety.bridge_http_client_implemented)" "release_checkpoint"
    $globalGates += Gate-Row "release_checkpoint_no_bridge_post" ($release.safety.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($release.safety.bridge_post_called)" "release_checkpoint"
    $globalGates += Gate-Row "release_checkpoint_blocks_execution" ($release.release_checkpoint.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($release.release_checkpoint.can_execute_bridge_write_now)" "release_checkpoint"
} else {
    $globalGates += Gate-Row "release_checkpoint_present" $false "review" "Phase 19 Step 50 release checkpoint not found." "release_checkpoint" "Generate Step 50 release checkpoint before real transport design."
}

# Runtime gates. Unreachable runtime is review-level, but any safety contradiction is blocker.
if ($dryRunStatus.ok) {
    $globalGates += Gate-Row "runtime_dry_run_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status" "runtime"
    $globalGates += Gate-Row "runtime_dry_run_no_network_transport" ($dryRunStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($dryRunStatus.value.network_transport_implemented)" "runtime"
    $globalGates += Gate-Row "runtime_dry_run_no_bridge_post" ($dryRunStatus.value.bridge_post_called -eq $false -and $dryRunStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($dryRunStatus.value.bridge_post_called); bridge_post_call_implemented=$($dryRunStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    $globalGates += Gate-Row "runtime_dry_run_status_readable" $false "review" $dryRunStatus.error "runtime"
}

if ($stubStatus.ok) {
    $globalGates += Gate-Row "runtime_stub_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-http-client-stub/status" "runtime"
    $globalGates += Gate-Row "runtime_stub_no_real_http_client" ($stubStatus.value.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($stubStatus.value.real_bridge_http_client_implemented)" "runtime"
} else {
    $globalGates += Gate-Row "runtime_stub_status_readable" $false "review" $stubStatus.error "runtime"
}

if ($executorStatus.ok) {
    $globalGates += Gate-Row "runtime_executor_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-write-executor/status" "runtime"
    $globalGates += Gate-Row "runtime_executor_no_execution_endpoint" ($executorStatus.value.execution_endpoint_available -eq $false) "blocker" "execution_endpoint_available=$($executorStatus.value.execution_endpoint_available)" "runtime"
    $globalGates += Gate-Row "runtime_executor_no_bridge_post_impl" ($executorStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_call_implemented=$($executorStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    $globalGates += Gate-Row "runtime_executor_status_readable" $false "review" $executorStatus.error "runtime"
}

if ($bundleStatus.ok) {
    $globalGates += Gate-Row "runtime_bundle_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status" "runtime"
    $globalGates += Gate-Row "runtime_bundle_no_bridge_post" ($bundleStatus.value.bridge_post_called -eq $false -and $bundleStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($bundleStatus.value.bridge_post_called); bridge_post_call_implemented=$($bundleStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    $globalGates += Gate-Row "runtime_bundle_status_readable" $false "review" $bundleStatus.error "runtime"
}

$globalGates += Gate-Row "runtime_bridge_health_readable" $bridgeHealth.ok "review" $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "runtime"

foreach ($gate in $globalGates) {
    Add-GateIssueIfFailed $issues $gate
}

# Transport row matrix from the simulated request/response pair.
$simRequest = $dryRun.simulation.simulated_request
$simResponse = $dryRun.simulation.simulated_response
$transportRows = @()

$rowGates = @()
$rowGates += Gate-Row "row_transport_is_dry_run_no_network" ($simRequest.transport -eq "dry_run_no_network") "blocker" "transport=$($simRequest.transport)" "transport_row"
$rowGates += Gate-Row "row_response_would_not_send" ($simResponse.would_send -eq $false) "blocker" "would_send=$($simResponse.would_send)" "transport_row"
$rowGates += Gate-Row "row_response_would_not_call_bridge" ($simResponse.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($simResponse.would_call_bridge)" "transport_row"
$rowGates += Gate-Row "row_response_would_not_mutate_bridge" ($simResponse.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($simResponse.would_mutate_bridge)" "transport_row"
$rowGates += Gate-Row "row_status_code_zero" ([int]$simResponse.status_code -eq 0) "blocker" "status_code=$($simResponse.status_code)" "transport_row"
$rowGates += Gate-Row "row_endpoint_shape" ((Normalize-String $simRequest.target_bridge_endpoint) -eq "/api/routing-rules") "blocker" "target_bridge_endpoint=$($simRequest.target_bridge_endpoint)" "transport_row"
$rowGates += Gate-Row "row_method_shape" ((Normalize-String $simRequest.http_method).ToUpperInvariant() -eq "POST") "blocker" "http_method=$($simRequest.http_method)" "transport_row"
$rowGates += Gate-Row "row_has_payload_hash" (![string]::IsNullOrWhiteSpace((Normalize-String $simRequest.payload_hash))) "blocker" "payload_hash=$($simRequest.payload_hash)" "transport_row"

foreach ($field in @("phone", "mode", "owner_type", "label", "default_contact_ids", "notes")) {
    $rowGates += Gate-Row "row_payload_has_$field" (Test-HasProperty $simRequest.payload_template $field) "blocker" "payload field $field" "transport_row"
}

foreach ($field in @("Authorization", "Idempotency-Key", "Content-Type")) {
    $rowGates += Gate-Row "row_headers_have_$field" (Test-HasProperty $simRequest.headers_template $field) "blocker" "header field $field" "transport_row"
}

$rowFailures = @($rowGates | Where-Object { $_.passed -ne $true })
foreach ($gate in $rowFailures) {
    Add-Issue $issues $gate.severity "transport_row_$($gate.gate)" $gate.evidence $gate.source
}

$rowStatus = if (@($rowFailures | Where-Object { $_.severity -eq "blocker" }).Count -gt 0) {
    "blocked"
} elseif (@($rowFailures).Count -gt 0) {
    "review_required"
} else {
    "preflight_valid_for_future_transport_design"
}

$transportRows += [ordered]@{
    row_index = 0
    request_id = Normalize-String $simRequest.request_id
    target_bridge_base_url = Normalize-String $simRequest.target_bridge_base_url
    target_bridge_endpoint = Normalize-String $simRequest.target_bridge_endpoint
    http_method = Normalize-String $simRequest.http_method
    payload_hash = Normalize-String $simRequest.payload_hash
    transport = Normalize-String $simRequest.transport
    row_status = $rowStatus
    gate_count = @($rowGates).Count
    failed_gate_count = @($rowFailures).Count
    blocker_count = @($rowFailures | Where-Object { $_.severity -eq "blocker" }).Count
    review_count = @($rowFailures | Where-Object { $_.severity -eq "review" }).Count
    would_send = [bool]$simResponse.would_send
    would_call_bridge = [bool]$simResponse.would_call_bridge
    would_mutate_bridge = [bool]$simResponse.would_mutate_bridge
    gates = $rowGates
}

$statusCounts = @{}
foreach ($row in $transportRows) {
    if (!$statusCounts.ContainsKey($row.row_status)) { $statusCounts[$row.row_status] = 0 }
    $statusCounts[$row.row_status] += 1
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$preflightStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "preflight_valid_for_future_transport_design"
} elseif ($blockerCount -eq 0) {
    "preflight_valid_with_review_items"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_http_client_preflight_matrix_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 4"
    purpose = "Bridge routing HTTP client no-network preflight matrix"
    source_dry_run_validation = $validationPath
    source_dry_run_report = $dryRunPath
    source_stub_report = $stubPath
    source_release_checkpoint = $releasePath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_http_client_preflight_matrix_only = $true
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
    preflight = [ordered]@{
        status = $preflightStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        global_gate_count = @($globalGates).Count
        transport_row_count = @($transportRows).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_add_real_bridge_http_client_now = $false
        reason = if ($blockerCount -eq 0) {
            "HTTP client dry-run transport preflight has no hard blockers. Phase 20 Step 4 still implements no real transport."
        } else {
            "HTTP client dry-run transport preflight found blockers. Resolve blockers before any future network transport design."
        }
    }
    global_gates = $globalGates
    transport_rows = $transportRows
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
        global_gates = @($globalGates).Count
        transport_rows = @($transportRows).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
        status_counts = $statusCounts
    }
    next_recommended_actions = @(
        "Review this preflight matrix before adding any real network transport.",
        "Do not call bridge POST endpoints from Phase 20 Step 4.",
        "Future network transport must remain disabled by default and preserve dry-run behavior.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_preflight_matrix.json"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_preflight_matrix_global_gates.csv"
$rowsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_preflight_matrix_rows.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_preflight_matrix_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_preflight_matrix.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$globalGates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$transportRows |
    Select-Object row_index, request_id, target_bridge_base_url, target_bridge_endpoint, http_method, payload_hash, transport, row_status, gate_count, failed_gate_count, blocker_count, review_count, would_send, would_call_bridge, would_mutate_bridge |
    Export-Csv -LiteralPath $rowsCsvPath -NoTypeInformation -Encoding UTF8

$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }
$statusText = if ($statusCounts.Count -gt 0) { ($statusCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing HTTP Client Preflight Matrix

Generated: $($report.generated_at)

Source dry-run validation:

``````
$validationPath
``````

Source dry-run report:

``````
$dryRunPath
``````

## Safety

- Bridge routing HTTP client preflight matrix only: true
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

## Preflight

- Status: $preflightStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Transport rows: $($transportRows.Count)
- Can execute bridge write now: false
- Can add network transport now: false
- Can add real bridge HTTP client now: false

## Row status counts

$statusText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_http_client_preflight_matrix=$OutputDir | status=$preflightStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_http_client_preflight_matrix=$OutputDir | status=$preflightStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "HTTP client preflight matrix files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
