param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
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

function Add-Gate {
    param(
        [System.Collections.ArrayList]$Gates,
        [string]$Gate,
        [bool]$Passed,
        [string]$Severity,
        [string]$Evidence,
        [string]$Source = ""
    )

    [void]$Gates.Add([ordered]@{
        gate = $Gate
        passed = $Passed
        severity = $Severity
        evidence = $Evidence
        source = $Source
    })
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

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($DryRunDir)) {
    $DryRunDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_dry_run_*" -JsonName "phase20_bridge_routing_http_client_dry_run.json"
}
if ([string]::IsNullOrWhiteSpace($StubReportDir)) {
    $StubReportDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_stub_*" -JsonName "phase20_bridge_routing_http_client_stub.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($ReleaseCheckpointDir)) {
    $ReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_release_checkpoint_*" -JsonName "phase19_bridge_routing_write_release_checkpoint.json" -Required $false
}

$dryRunPath = Join-Path $DryRunDir "phase20_bridge_routing_http_client_dry_run.json"
$stubPath = if (![string]::IsNullOrWhiteSpace($StubReportDir)) { Join-Path $StubReportDir "phase20_bridge_routing_http_client_stub.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($ReleaseCheckpointDir)) { Join-Path $ReleaseCheckpointDir "phase19_bridge_routing_write_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $dryRunPath)) {
    throw "HTTP client dry-run JSON not found: $dryRunPath"
}

$dryRun = Read-JsonFile $dryRunPath
$stub = if (![string]::IsNullOrWhiteSpace($stubPath) -and (Test-Path -LiteralPath $stubPath)) { Read-JsonFile $stubPath } else { $null }
$release = if (![string]::IsNullOrWhiteSpace($releasePath) -and (Test-Path -LiteralPath $releasePath)) { Read-JsonFile $releasePath } else { $null }

$dryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$stubStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-stub/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$gates = New-Object System.Collections.ArrayList

# Artifact-level safety gates.
Add-Gate $gates "dry_run_artifact_exists" $true "blocker" $dryRunPath "dry_run"
Add-Gate $gates "dry_run_is_dry_run_only" ($dryRun.safety.bridge_routing_http_client_dry_run_only -eq $true) "blocker" "bridge_routing_http_client_dry_run_only=$($dryRun.safety.bridge_routing_http_client_dry_run_only)" "dry_run"
Add-Gate $gates "dry_run_has_no_real_http_client" ($dryRun.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($dryRun.safety.real_bridge_http_client_implemented)" "dry_run"
Add-Gate $gates "dry_run_has_no_network_transport" ($dryRun.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($dryRun.safety.network_transport_implemented)" "dry_run"
Add-Gate $gates "dry_run_has_no_bridge_post_impl" ($dryRun.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_call_implemented=$($dryRun.safety.bridge_post_call_implemented)" "dry_run"
Add-Gate $gates "dry_run_has_no_bridge_post_called" ($dryRun.safety.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($dryRun.safety.bridge_post_called)" "dry_run"
Add-Gate $gates "dry_run_has_no_bridge_mutation" ($dryRun.safety.bridge_mutation_performed -eq $false) "blocker" "bridge_mutation_performed=$($dryRun.safety.bridge_mutation_performed)" "dry_run"
Add-Gate $gates "dry_run_has_no_platform_mutation" ($dryRun.safety.platform_db_mutation_performed -eq $false) "blocker" "platform_db_mutation_performed=$($dryRun.safety.platform_db_mutation_performed)" "dry_run"
Add-Gate $gates "dry_run_has_no_lacrm_call" ($dryRun.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($dryRun.safety.lacrm_call_performed)" "dry_run"
Add-Gate $gates "dry_run_has_no_routing_write_endpoint" ($dryRun.safety.routing_write_endpoint_implemented -eq $false) "blocker" "routing_write_endpoint_implemented=$($dryRun.safety.routing_write_endpoint_implemented)" "dry_run"

foreach ($item in @($dryRun.safety_errors)) {
    Add-Issue $issues "blocker" "source_dry_run_safety_error" "$item" "dry_run"
}

# Simulation-level gates.
$simulation = $dryRun.simulation
$simRequest = $simulation.simulated_request
$simResponse = $simulation.simulated_response

Add-Gate $gates "simulation_is_blocked" ($simulation.blocked -eq $true) "blocker" "blocked=$($simulation.blocked)" "simulation"
Add-Gate $gates "simulation_would_not_call_bridge" ($simulation.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($simulation.would_call_bridge)" "simulation"
Add-Gate $gates "simulation_would_not_mutate_bridge" ($simulation.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($simulation.would_mutate_bridge)" "simulation"
Add-Gate $gates "simulation_would_not_mutate_platform" ($simulation.would_mutate_platform -eq $false) "blocker" "would_mutate_platform=$($simulation.would_mutate_platform)" "simulation"
Add-Gate $gates "simulation_would_not_call_lacrm" ($simulation.would_call_lacrm -eq $false) "blocker" "would_call_lacrm=$($simulation.would_call_lacrm)" "simulation"

Add-Gate $gates "simulated_request_uses_no_network_transport" ($simRequest.transport -eq "dry_run_no_network") "blocker" "transport=$($simRequest.transport)" "simulation"
Add-Gate $gates "simulated_response_would_not_send" ($simResponse.would_send -eq $false) "blocker" "would_send=$($simResponse.would_send)" "simulation"
Add-Gate $gates "simulated_response_would_not_call_bridge" ($simResponse.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($simResponse.would_call_bridge)" "simulation"
Add-Gate $gates "simulated_response_would_not_mutate_bridge" ($simResponse.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($simResponse.would_mutate_bridge)" "simulation"
Add-Gate $gates "simulated_response_status_code_zero" ([int]$simResponse.status_code -eq 0) "blocker" "status_code=$($simResponse.status_code)" "simulation"

$expectedEndpoint = "/api/routing-rules"
$expectedMethod = "POST"
Add-Gate $gates "simulated_request_target_endpoint_shape" ((Normalize-String $simRequest.target_bridge_endpoint) -eq $expectedEndpoint) "blocker" "target_bridge_endpoint=$($simRequest.target_bridge_endpoint)" "simulation"
Add-Gate $gates "simulated_request_method_shape" ((Normalize-String $simRequest.http_method).ToUpperInvariant() -eq $expectedMethod) "blocker" "http_method=$($simRequest.http_method)" "simulation"

$payloadTemplate = $simRequest.payload_template
$headersTemplate = $simRequest.headers_template
foreach ($field in @("phone", "mode", "owner_type", "label", "default_contact_ids", "notes")) {
    Add-Gate $gates "simulated_payload_has_$field" (Test-HasProperty $payloadTemplate $field) "blocker" "payload field $field" "simulation"
}
foreach ($field in @("Authorization", "Idempotency-Key", "Content-Type")) {
    Add-Gate $gates "simulated_headers_have_$field" (Test-HasProperty $headersTemplate $field) "blocker" "header field $field" "simulation"
}

# Optional upstream artifact checks.
if ($stub -ne $null) {
    Add-Gate $gates "stub_artifact_present" $true "review" $stubPath "stub"
    Add-Gate $gates "stub_has_no_real_http_client" ($stub.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($stub.safety.real_bridge_http_client_implemented)" "stub"
    Add-Gate $gates "stub_has_no_bridge_post" ($stub.safety.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($stub.safety.bridge_post_called)" "stub"
} else {
    Add-Gate $gates "stub_artifact_present" $false "review" "Phase 20 Step 1 stub report not found." "stub"
}

if ($release -ne $null) {
    Add-Gate $gates "release_checkpoint_present" $true "review" $releasePath "release_checkpoint"
    Add-Gate $gates "release_checkpoint_has_no_http_client" ($release.safety.bridge_http_client_implemented -eq $false) "blocker" "bridge_http_client_implemented=$($release.safety.bridge_http_client_implemented)" "release_checkpoint"
    Add-Gate $gates "release_checkpoint_has_no_bridge_post" ($release.safety.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($release.safety.bridge_post_called)" "release_checkpoint"
} else {
    Add-Gate $gates "release_checkpoint_present" $false "review" "Phase 19 Step 50 release checkpoint not found." "release_checkpoint"
}

# Runtime checks. Unreachable runtime is review-level because the validation artifact remains useful offline.
if ($dryRunStatus.ok) {
    Add-Gate $gates "runtime_dry_run_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status" "runtime"
    Add-Gate $gates "runtime_dry_run_no_network_transport" ($dryRunStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($dryRunStatus.value.network_transport_implemented)" "runtime"
    Add-Gate $gates "runtime_dry_run_no_post" ($dryRunStatus.value.bridge_post_call_implemented -eq $false -and $dryRunStatus.value.bridge_post_called -eq $false) "blocker" "bridge_post_call_implemented=$($dryRunStatus.value.bridge_post_call_implemented); bridge_post_called=$($dryRunStatus.value.bridge_post_called)" "runtime"
} else {
    Add-Gate $gates "runtime_dry_run_status_readable" $false "review" $dryRunStatus.error "runtime"
}

if ($stubStatus.ok) {
    Add-Gate $gates "runtime_stub_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-http-client-stub/status" "runtime"
    Add-Gate $gates "runtime_stub_no_real_http_client" ($stubStatus.value.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($stubStatus.value.real_bridge_http_client_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_stub_status_readable" $false "review" $stubStatus.error "runtime"
}

if ($executorStatus.ok) {
    Add-Gate $gates "runtime_executor_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-write-executor/status" "runtime"
    Add-Gate $gates "runtime_executor_no_execution_endpoint" ($executorStatus.value.execution_endpoint_available -eq $false) "blocker" "execution_endpoint_available=$($executorStatus.value.execution_endpoint_available)" "runtime"
} else {
    Add-Gate $gates "runtime_executor_status_readable" $false "review" $executorStatus.error "runtime"
}

Add-Gate $gates "runtime_bridge_health_readable" $bridgeHealth.ok "review" $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "runtime"

# Convert failed gates into issues.
foreach ($gate in @($gates)) {
    if ($gate.passed -ne $true) {
        Add-Issue $issues $gate.severity $gate.gate $gate.evidence $gate.source
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$validationStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "valid_dry_run_transport"
} elseif ($blockerCount -eq 0) {
    "valid_with_review_items"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_http_client_dry_run_validation_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 3"
    purpose = "Bridge routing HTTP client dry-run transport validation"
    source_dry_run_report = $dryRunPath
    source_stub_report = $stubPath
    source_release_checkpoint = $releasePath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_http_client_dry_run_validation_only = $true
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
    validation = [ordered]@{
        status = $validationStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        gate_count = @($gates).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_add_real_bridge_http_client_now = $false
        reason = if ($blockerCount -eq 0) {
            "Dry-run transport is structurally valid for review. Phase 20 Step 3 still implements no real bridge HTTP client."
        } else {
            "Dry-run transport validation found blockers. Resolve blockers before any future network transport design."
        }
    }
    gates = @($gates)
    issues = @($issues)
    simulated_request = $simRequest
    simulated_response = $simResponse
    runtime_status = [ordered]@{
        dry_run_status_ok = $dryRunStatus.ok
        dry_run_status = if ($dryRunStatus.ok) { $dryRunStatus.value } else { $null }
        stub_status_ok = $stubStatus.ok
        stub_status = if ($stubStatus.ok) { $stubStatus.value } else { $null }
        executor_status_ok = $executorStatus.ok
        executor_status = if ($executorStatus.ok) { $executorStatus.value } else { $null }
        bridge_health_ok = $bridgeHealth.ok
        bridge_health = if ($bridgeHealth.ok) { $bridgeHealth.value } else { $null }
        bridge_health_error = $bridgeHealth.error
    }
    counts = [ordered]@{
        gates = @($gates).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this validation before adding any real network transport.",
        "Do not call bridge POST endpoints from Phase 20 Step 3.",
        "Future network transport must stay disabled by default and preserve dry-run behavior.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_dry_run_validation.json"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_dry_run_validation_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_dry_run_validation_issues.csv"
$requestCsvPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_dry_run_validation_request.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_dry_run_validation.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

@(
    [ordered]@{
        request_id = $simRequest.request_id
        target_bridge_base_url = $simRequest.target_bridge_base_url
        target_bridge_endpoint = $simRequest.target_bridge_endpoint
        http_method = $simRequest.http_method
        payload_hash = $simRequest.payload_hash
        transport = $simRequest.transport
        simulated_status_code = $simResponse.status_code
        would_send = $simResponse.would_send
        would_call_bridge = $simResponse.would_call_bridge
        would_mutate_bridge = $simResponse.would_mutate_bridge
    }
) | Export-Csv -LiteralPath $requestCsvPath -NoTypeInformation -Encoding UTF8

$gateText = (@($gates) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.gate): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing HTTP Client Dry-run Validation

Generated: $($report.generated_at)

Source dry-run transport report:

``````
$dryRunPath
``````

## Safety

- Bridge routing HTTP client dry-run validation only: true
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

## Validation

- Status: $validationStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Gates: $(@($gates).Count)
- Can execute bridge write now: false
- Can add network transport now: false
- Can add real bridge HTTP client now: false

## Gates

$gateText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_http_client_dry_run_validation=$OutputDir | status=$validationStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_http_client_dry_run_validation=$OutputDir | status=$validationStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "HTTP client dry-run validation files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
