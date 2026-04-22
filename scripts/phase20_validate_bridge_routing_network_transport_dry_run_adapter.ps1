param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$DryRunAdapterDir = "",
    [string]$GuardReportDir = "",
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

if ([string]::IsNullOrWhiteSpace($DryRunAdapterDir)) {
    $DryRunAdapterDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_adapter_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_adapter.json"
}
if ([string]::IsNullOrWhiteSpace($GuardReportDir)) {
    $GuardReportDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_guard_*" -JsonName "phase20_bridge_routing_network_transport_guard.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($ReleaseCheckpointDir)) {
    $ReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_release_checkpoint_*" -JsonName "phase20_bridge_routing_http_client_release_checkpoint.json" -Required $false
}

$adapterPath = Join-Path $DryRunAdapterDir "phase20_bridge_routing_network_transport_dry_run_adapter.json"
$guardPath = if (![string]::IsNullOrWhiteSpace($GuardReportDir)) { Join-Path $GuardReportDir "phase20_bridge_routing_network_transport_guard.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($ReleaseCheckpointDir)) { Join-Path $ReleaseCheckpointDir "phase20_bridge_routing_http_client_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $adapterPath)) {
    throw "Network transport dry-run adapter JSON not found: $adapterPath"
}

$adapter = Read-JsonFile $adapterPath
$guard = if (![string]::IsNullOrWhiteSpace($guardPath) -and (Test-Path -LiteralPath $guardPath)) { Read-JsonFile $guardPath } else { $null }
$release = if (![string]::IsNullOrWhiteSpace($releasePath) -and (Test-Path -LiteralPath $releasePath)) { Read-JsonFile $releasePath } else { $null }

$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$gates = New-Object System.Collections.ArrayList

# Artifact-level safety gates.
Add-Gate $gates "dry_run_adapter_artifact_exists" $true "blocker" $adapterPath "adapter"
Add-Gate $gates "adapter_is_adapter_only" ($adapter.safety.bridge_routing_network_transport_dry_run_adapter_only -eq $true) "blocker" "bridge_routing_network_transport_dry_run_adapter_only=$($adapter.safety.bridge_routing_network_transport_dry_run_adapter_only)" "adapter"
Add-Gate $gates "adapter_has_no_real_http_client" ($adapter.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($adapter.safety.real_bridge_http_client_implemented)" "adapter"
Add-Gate $gates "adapter_has_no_network_transport" ($adapter.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($adapter.safety.network_transport_implemented)" "adapter"
Add-Gate $gates "adapter_has_no_network_transport_enabled" ($adapter.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($adapter.safety.network_transport_enabled)" "adapter"
Add-Gate $gates "adapter_has_no_network_transport_armed" ($adapter.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($adapter.safety.network_transport_armed)" "adapter"
Add-Gate $gates "adapter_has_no_socket_opened" ($adapter.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($adapter.safety.network_socket_opened)" "adapter"
Add-Gate $gates "adapter_has_no_bridge_post_impl" ($adapter.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_call_implemented=$($adapter.safety.bridge_post_call_implemented)" "adapter"
Add-Gate $gates "adapter_has_no_bridge_post_called" ($adapter.safety.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($adapter.safety.bridge_post_called)" "adapter"
Add-Gate $gates "adapter_has_no_bridge_mutation" ($adapter.safety.bridge_mutation_performed -eq $false) "blocker" "bridge_mutation_performed=$($adapter.safety.bridge_mutation_performed)" "adapter"
Add-Gate $gates "adapter_has_no_platform_mutation" ($adapter.safety.platform_db_mutation_performed -eq $false) "blocker" "platform_db_mutation_performed=$($adapter.safety.platform_db_mutation_performed)" "adapter"
Add-Gate $gates "adapter_has_no_lacrm_call" ($adapter.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($adapter.safety.lacrm_call_performed)" "adapter"
Add-Gate $gates "adapter_has_no_routing_write_endpoint" ($adapter.safety.routing_write_endpoint_implemented -eq $false) "blocker" "routing_write_endpoint_implemented=$($adapter.safety.routing_write_endpoint_implemented)" "adapter"

foreach ($item in @($adapter.safety_errors)) {
    Add-Issue $issues "blocker" "source_adapter_safety_error" "$item" "adapter"
}

# Simulation-level gates.
$simulation = $adapter.simulation
$contract = $simulation.adapter_dry_run_contract
$result = $simulation.simulated_adapter_result

Add-Gate $gates "simulation_is_blocked" ($simulation.blocked -eq $true) "blocker" "blocked=$($simulation.blocked)" "simulation"
Add-Gate $gates "simulation_would_not_add_network_transport" ($simulation.would_add_network_transport -eq $false) "blocker" "would_add_network_transport=$($simulation.would_add_network_transport)" "simulation"
Add-Gate $gates "simulation_would_not_open_socket" ($simulation.would_open_socket -eq $false) "blocker" "would_open_socket=$($simulation.would_open_socket)" "simulation"
Add-Gate $gates "simulation_would_not_send_http_request" ($simulation.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($simulation.would_send_http_request)" "simulation"
Add-Gate $gates "simulation_would_not_call_bridge" ($simulation.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($simulation.would_call_bridge)" "simulation"
Add-Gate $gates "simulation_would_not_mutate_bridge" ($simulation.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($simulation.would_mutate_bridge)" "simulation"
Add-Gate $gates "simulation_would_not_mutate_platform" ($simulation.would_mutate_platform -eq $false) "blocker" "would_mutate_platform=$($simulation.would_mutate_platform)" "simulation"
Add-Gate $gates "simulation_would_not_call_lacrm" ($simulation.would_call_lacrm -eq $false) "blocker" "would_call_lacrm=$($simulation.would_call_lacrm)" "simulation"

Add-Gate $gates "contract_kind_is_dry_run_adapter_harness" ($contract.implementation_kind -eq "dry_run_adapter_harness") "blocker" "implementation_kind=$($contract.implementation_kind)" "contract"
Add-Gate $gates "contract_transport_mode_no_network" ($contract.transport_mode -eq "dry_run_no_network") "blocker" "transport_mode=$($contract.transport_mode)" "contract"
Add-Gate $gates "contract_network_socket_not_opened" ($contract.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($contract.network_socket_opened)" "contract"
Add-Gate $gates "contract_would_not_open_socket" ($contract.would_open_socket -eq $false) "blocker" "would_open_socket=$($contract.would_open_socket)" "contract"
Add-Gate $gates "contract_would_not_send_http_request" ($contract.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($contract.would_send_http_request)" "contract"
Add-Gate $gates "contract_would_not_call_bridge" ($contract.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($contract.would_call_bridge)" "contract"
Add-Gate $gates "contract_would_not_mutate_bridge" ($contract.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($contract.would_mutate_bridge)" "contract"

Add-Gate $gates "adapter_result_status_code_zero" ([int]$result.status_code -eq 0) "blocker" "status_code=$($result.status_code)" "result"
Add-Gate $gates "adapter_result_not_ok" ($result.ok -eq $false) "blocker" "ok=$($result.ok)" "result"
Add-Gate $gates "adapter_result_no_network_mode" ($result.transport_mode -eq "dry_run_no_network") "blocker" "transport_mode=$($result.transport_mode)" "result"
Add-Gate $gates "adapter_result_would_not_open_socket" ($result.would_open_socket -eq $false) "blocker" "would_open_socket=$($result.would_open_socket)" "result"
Add-Gate $gates "adapter_result_would_not_send_http_request" ($result.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($result.would_send_http_request)" "result"
Add-Gate $gates "adapter_result_would_not_call_bridge" ($result.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($result.would_call_bridge)" "result"
Add-Gate $gates "adapter_result_would_not_mutate_bridge" ($result.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($result.would_mutate_bridge)" "result"

$requestShape = $contract.request_shape
Add-Gate $gates "request_shape_method_is_post" ((Normalize-String $requestShape.method).ToUpperInvariant() -eq "POST") "blocker" "method=$($requestShape.method)" "request_shape"
Add-Gate $gates "request_shape_endpoint_is_routing_rules" ((Normalize-String $requestShape.endpoint) -eq "/api/routing-rules") "blocker" "endpoint=$($requestShape.endpoint)" "request_shape"
Add-Gate $gates "request_shape_has_base_url_env" ((Normalize-String $requestShape.base_url_env) -eq "PLATFORM_BRIDGE_BASE_URL") "blocker" "base_url_env=$($requestShape.base_url_env)" "request_shape"
Add-Gate $gates "request_shape_has_admin_token_env" ((Normalize-String $requestShape.admin_token_env) -eq "PLATFORM_BRIDGE_ADMIN_TOKEN") "blocker" "admin_token_env=$($requestShape.admin_token_env)" "request_shape"
Add-Gate $gates "request_shape_has_idempotency_header" ((Normalize-String $requestShape.idempotency_header) -eq "Idempotency-Key") "blocker" "idempotency_header=$($requestShape.idempotency_header)" "request_shape"

foreach ($field in @("phone", "mode", "owner_type", "label", "default_contact_ids", "notes")) {
    Add-Gate $gates "payload_template_has_$field" (Test-HasProperty $requestShape.payload_template $field) "blocker" "payload field $field" "request_shape"
}

$requiredGates = $contract.required_gates
foreach ($field in @("pre_audit_row", "rollback_snapshot", "operator_confirmation", "response_recording", "lacrm_forbidden")) {
    Add-Gate $gates "required_gate_$field" ($requiredGates.$field -eq $true) "blocker" "$field=$($requiredGates.$field)" "required_gates"
}

# Optional upstream artifacts.
if ($guard -ne $null) {
    Add-Gate $gates "guard_artifact_present" $true "review" $guardPath "guard"
    Add-Gate $gates "guard_has_no_network_transport" ($guard.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($guard.safety.network_transport_implemented)" "guard"
    Add-Gate $gates "guard_has_no_bridge_post" ($guard.safety.bridge_post_called -eq $false -and $guard.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($guard.safety.bridge_post_called); bridge_post_call_implemented=$($guard.safety.bridge_post_call_implemented)" "guard"
    Add-Gate $gates "guard_would_not_add_network_transport" ($guard.preview.would_add_network_transport -eq $false) "blocker" "would_add_network_transport=$($guard.preview.would_add_network_transport)" "guard"
} else {
    Add-Gate $gates "guard_artifact_present" $false "review" "Phase 20 Step 7 guard report not found." "guard"
}

if ($release -ne $null) {
    Add-Gate $gates "release_checkpoint_present" $true "review" $releasePath "release_checkpoint"
    Add-Gate $gates "release_checkpoint_has_no_network_transport" ($release.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($release.safety.network_transport_implemented)" "release_checkpoint"
    Add-Gate $gates "release_checkpoint_has_no_bridge_post" ($release.safety.bridge_post_called -eq $false -and $release.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($release.safety.bridge_post_called); bridge_post_call_implemented=$($release.safety.bridge_post_call_implemented)" "release_checkpoint"
} else {
    Add-Gate $gates "release_checkpoint_present" $false "review" "Phase 20 Step 6 release checkpoint not found." "release_checkpoint"
}

# Runtime checks. Unreachable runtime is review-level because the report remains file-reviewable.
if ($adapterStatus.ok) {
    Add-Gate $gates "runtime_adapter_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status" "runtime"
    Add-Gate $gates "runtime_adapter_no_network_transport" ($adapterStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($adapterStatus.value.network_transport_implemented)" "runtime"
    Add-Gate $gates "runtime_adapter_no_socket" ($adapterStatus.value.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($adapterStatus.value.network_socket_opened)" "runtime"
    Add-Gate $gates "runtime_adapter_no_bridge_post" ($adapterStatus.value.bridge_post_called -eq $false -and $adapterStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($adapterStatus.value.bridge_post_called); bridge_post_call_implemented=$($adapterStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_adapter_status_readable" $false "review" $adapterStatus.error "runtime"
}

if ($guardStatus.ok) {
    Add-Gate $gates "runtime_guard_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status" "runtime"
    Add-Gate $gates "runtime_guard_no_network_transport" ($guardStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($guardStatus.value.network_transport_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_guard_status_readable" $false "review" $guardStatus.error "runtime"
}

if ($httpDryRunStatus.ok) {
    Add-Gate $gates "runtime_http_dry_run_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status" "runtime"
    Add-Gate $gates "runtime_http_dry_run_no_network_transport" ($httpDryRunStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($httpDryRunStatus.value.network_transport_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_http_dry_run_status_readable" $false "review" $httpDryRunStatus.error "runtime"
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
    "valid_dry_run_adapter"
} elseif ($blockerCount -eq 0) {
    "valid_with_review_items"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_dry_run_adapter_validation_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 9"
    purpose = "Bridge routing network transport dry-run adapter validation"
    source_dry_run_adapter = $adapterPath
    source_guard_report = $guardPath
    source_release_checkpoint = $releasePath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_dry_run_adapter_validation_only = $true
        bridge_get_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        real_bridge_http_client_implemented = $false
        network_transport_implemented = $false
        network_transport_enabled = $false
        network_transport_armed = $false
        network_socket_opened = $false
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
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        reason = if ($blockerCount -eq 0) {
            "Dry-run network transport adapter is structurally valid for review. Phase 20 Step 9 still implements no real network transport."
        } else {
            "Dry-run network transport adapter validation found blockers. Resolve blockers before any future real transport design."
        }
    }
    gates = @($gates)
    issues = @($issues)
    adapter_contract = $contract
    simulated_adapter_result = $result
    runtime_status = [ordered]@{
        adapter_status_ok = $adapterStatus.ok
        adapter_status = if ($adapterStatus.ok) { $adapterStatus.value } else { $null }
        guard_status_ok = $guardStatus.ok
        guard_status = if ($guardStatus.ok) { $guardStatus.value } else { $null }
        http_dry_run_status_ok = $httpDryRunStatus.ok
        http_dry_run_status = if ($httpDryRunStatus.ok) { $httpDryRunStatus.value } else { $null }
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
        "Do not call bridge POST endpoints from Phase 20 Step 9.",
        "Future transport work must stay disabled by default and preserve dry-run behavior.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_adapter_validation.json"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_adapter_validation_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_adapter_validation_issues.csv"
$contractCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_adapter_validation_contract.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_adapter_validation.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

@(
    [ordered]@{
        adapter_name = $contract.adapter_name
        implementation_kind = $contract.implementation_kind
        transport_mode = $contract.transport_mode
        network_socket_opened = $contract.network_socket_opened
        would_open_socket = $contract.would_open_socket
        would_send_http_request = $contract.would_send_http_request
        would_call_bridge = $contract.would_call_bridge
        would_mutate_bridge = $contract.would_mutate_bridge
        adapter_contract_hash = $result.adapter_contract_hash
        status_code = $result.status_code
        ok = $result.ok
    }
) | Export-Csv -LiteralPath $contractCsvPath -NoTypeInformation -Encoding UTF8

$gateText = (@($gates) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.gate): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Dry-run Adapter Validation

Generated: $($report.generated_at)

Source dry-run adapter report:

``````
$adapterPath
``````

## Safety

- Bridge routing network transport dry-run adapter validation only: true
- Bridge GET only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Real bridge HTTP client implemented: false
- Network transport implemented: false
- Network transport enabled: false
- Network transport armed: false
- Network socket opened: false
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
- Can open network socket now: false
- Can add real bridge HTTP client now: false

## Gates

$gateText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_dry_run_adapter_validation=$OutputDir | status=$validationStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_dry_run_adapter_validation=$OutputDir | status=$validationStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Network transport dry-run adapter validation files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
