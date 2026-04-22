param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$AdapterValidationDir = "",
    [string]$DryRunAdapterDir = "",
    [string]$GuardReportDir = "",
    [string]$HttpClientReleaseCheckpointDir = "",
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

if ([string]::IsNullOrWhiteSpace($AdapterValidationDir)) {
    $AdapterValidationDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_adapter_validation_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_adapter_validation.json"
}
if ([string]::IsNullOrWhiteSpace($DryRunAdapterDir)) {
    $DryRunAdapterDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_adapter_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_adapter.json"
}
if ([string]::IsNullOrWhiteSpace($GuardReportDir)) {
    $GuardReportDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_guard_*" -JsonName "phase20_bridge_routing_network_transport_guard.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($HttpClientReleaseCheckpointDir)) {
    $HttpClientReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_release_checkpoint_*" -JsonName "phase20_bridge_routing_http_client_release_checkpoint.json" -Required $false
}

$validationPath = Join-Path $AdapterValidationDir "phase20_bridge_routing_network_transport_dry_run_adapter_validation.json"
$adapterPath = Join-Path $DryRunAdapterDir "phase20_bridge_routing_network_transport_dry_run_adapter.json"
$guardPath = if (![string]::IsNullOrWhiteSpace($GuardReportDir)) { Join-Path $GuardReportDir "phase20_bridge_routing_network_transport_guard.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($HttpClientReleaseCheckpointDir)) { Join-Path $HttpClientReleaseCheckpointDir "phase20_bridge_routing_http_client_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $validationPath)) { throw "Dry-run adapter validation JSON not found: $validationPath" }
if (!(Test-Path -LiteralPath $adapterPath)) { throw "Dry-run adapter JSON not found: $adapterPath" }

$validation = Read-JsonFile $validationPath
$adapter = Read-JsonFile $adapterPath
$guard = if (![string]::IsNullOrWhiteSpace($guardPath) -and (Test-Path -LiteralPath $guardPath)) { Read-JsonFile $guardPath } else { $null }
$release = if (![string]::IsNullOrWhiteSpace($releasePath) -and (Test-Path -LiteralPath $releasePath)) { Read-JsonFile $releasePath } else { $null }

$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bundleStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$globalGates = @()

# Global gates from Phase 20 Step 9 validation.
$globalGates += Gate-Row "adapter_validation_exists" $true "blocker" $validationPath "adapter_validation"
$globalGates += Gate-Row "dry_run_adapter_exists" $true "blocker" $adapterPath "adapter"
$globalGates += Gate-Row "validation_is_validation_only" ($validation.safety.bridge_routing_network_transport_dry_run_adapter_validation_only -eq $true) "blocker" "bridge_routing_network_transport_dry_run_adapter_validation_only=$($validation.safety.bridge_routing_network_transport_dry_run_adapter_validation_only)" "adapter_validation"
$globalGates += Gate-Row "validation_bridge_get_only" ($validation.safety.bridge_get_only -eq $true) "blocker" "bridge_get_only=$($validation.safety.bridge_get_only)" "adapter_validation"
$globalGates += Gate-Row "validation_no_network_transport" ($validation.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($validation.safety.network_transport_implemented)" "adapter_validation"
$globalGates += Gate-Row "validation_no_network_enabled" ($validation.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($validation.safety.network_transport_enabled)" "adapter_validation"
$globalGates += Gate-Row "validation_no_network_armed" ($validation.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($validation.safety.network_transport_armed)" "adapter_validation"
$globalGates += Gate-Row "validation_no_socket" ($validation.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($validation.safety.network_socket_opened)" "adapter_validation"
$globalGates += Gate-Row "validation_no_real_http_client" ($validation.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($validation.safety.real_bridge_http_client_implemented)" "adapter_validation"
$globalGates += Gate-Row "validation_no_bridge_post" ($validation.safety.bridge_post_called -eq $false -and $validation.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($validation.safety.bridge_post_called); bridge_post_call_implemented=$($validation.safety.bridge_post_call_implemented)" "adapter_validation"
$globalGates += Gate-Row "validation_no_mutation" ($validation.safety.platform_db_mutation_performed -eq $false -and $validation.safety.bridge_mutation_performed -eq $false) "blocker" "platform_db_mutation=$($validation.safety.platform_db_mutation_performed); bridge_mutation=$($validation.safety.bridge_mutation_performed)" "adapter_validation"
$globalGates += Gate-Row "validation_no_lacrm" ($validation.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($validation.safety.lacrm_call_performed)" "adapter_validation"
$globalGates += Gate-Row "validation_blocks_execution" ($validation.validation.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($validation.validation.can_execute_bridge_write_now)" "adapter_validation"
$globalGates += Gate-Row "validation_blocks_network_transport" ($validation.validation.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($validation.validation.can_add_network_transport_now)" "adapter_validation"
$globalGates += Gate-Row "validation_blocks_socket" ($validation.validation.can_open_network_socket_now -eq $false) "blocker" "can_open_network_socket_now=$($validation.validation.can_open_network_socket_now)" "adapter_validation"
$globalGates += Gate-Row "validation_blocks_real_http_client" ($validation.validation.can_add_real_bridge_http_client_now -eq $false) "blocker" "can_add_real_bridge_http_client_now=$($validation.validation.can_add_real_bridge_http_client_now)" "adapter_validation"

# Global gates from Phase 20 Step 8 adapter artifact.
$globalGates += Gate-Row "adapter_is_adapter_only" ($adapter.safety.bridge_routing_network_transport_dry_run_adapter_only -eq $true) "blocker" "bridge_routing_network_transport_dry_run_adapter_only=$($adapter.safety.bridge_routing_network_transport_dry_run_adapter_only)" "adapter"
$globalGates += Gate-Row "adapter_no_network_transport" ($adapter.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($adapter.safety.network_transport_implemented)" "adapter"
$globalGates += Gate-Row "adapter_no_network_enabled" ($adapter.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($adapter.safety.network_transport_enabled)" "adapter"
$globalGates += Gate-Row "adapter_no_network_armed" ($adapter.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($adapter.safety.network_transport_armed)" "adapter"
$globalGates += Gate-Row "adapter_no_socket_opened" ($adapter.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($adapter.safety.network_socket_opened)" "adapter"
$globalGates += Gate-Row "adapter_no_bridge_post" ($adapter.safety.bridge_post_called -eq $false -and $adapter.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($adapter.safety.bridge_post_called); bridge_post_call_implemented=$($adapter.safety.bridge_post_call_implemented)" "adapter"
$globalGates += Gate-Row "adapter_simulation_no_socket" ($adapter.simulation.simulated_adapter_result.would_open_socket -eq $false) "blocker" "would_open_socket=$($adapter.simulation.simulated_adapter_result.would_open_socket)" "adapter"
$globalGates += Gate-Row "adapter_simulation_no_send" ($adapter.simulation.simulated_adapter_result.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($adapter.simulation.simulated_adapter_result.would_send_http_request)" "adapter"
$globalGates += Gate-Row "adapter_simulation_no_bridge_call" ($adapter.simulation.simulated_adapter_result.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($adapter.simulation.simulated_adapter_result.would_call_bridge)" "adapter"

# Optional upstream evidence.
if ($guard -ne $null) {
    $globalGates += Gate-Row "guard_report_present" $true "review" $guardPath "guard"
    $globalGates += Gate-Row "guard_no_network_transport" ($guard.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($guard.safety.network_transport_implemented)" "guard"
    $globalGates += Gate-Row "guard_no_bridge_post" ($guard.safety.bridge_post_called -eq $false -and $guard.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($guard.safety.bridge_post_called); bridge_post_call_implemented=$($guard.safety.bridge_post_call_implemented)" "guard"
    $globalGates += Gate-Row "guard_would_not_add_network_transport" ($guard.preview.would_add_network_transport -eq $false) "blocker" "would_add_network_transport=$($guard.preview.would_add_network_transport)" "guard"
} else {
    $globalGates += Gate-Row "guard_report_present" $false "review" "Phase 20 Step 7 guard report not found." "guard" "Generate Step 7 guard before real transport design."
}

if ($release -ne $null) {
    $globalGates += Gate-Row "http_client_release_checkpoint_present" $true "review" $releasePath "http_client_release_checkpoint"
    $globalGates += Gate-Row "http_client_release_no_network_transport" ($release.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($release.safety.network_transport_implemented)" "http_client_release_checkpoint"
    $globalGates += Gate-Row "http_client_release_no_bridge_post" ($release.safety.bridge_post_called -eq $false -and $release.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($release.safety.bridge_post_called); bridge_post_call_implemented=$($release.safety.bridge_post_call_implemented)" "http_client_release_checkpoint"
    $globalGates += Gate-Row "http_client_release_blocks_execution" ($release.release_checkpoint.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($release.release_checkpoint.can_execute_bridge_write_now)" "http_client_release_checkpoint"
} else {
    $globalGates += Gate-Row "http_client_release_checkpoint_present" $false "review" "Phase 20 Step 6 release checkpoint not found." "http_client_release_checkpoint" "Generate Step 6 release checkpoint before real transport design."
}

# Runtime gates. Unreachable runtime is review-level, but any safety contradiction is blocker.
if ($adapterStatus.ok) {
    $globalGates += Gate-Row "runtime_adapter_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status" "runtime"
    $globalGates += Gate-Row "runtime_adapter_no_network_transport" ($adapterStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($adapterStatus.value.network_transport_implemented)" "runtime"
    $globalGates += Gate-Row "runtime_adapter_no_socket" ($adapterStatus.value.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($adapterStatus.value.network_socket_opened)" "runtime"
    $globalGates += Gate-Row "runtime_adapter_no_bridge_post" ($adapterStatus.value.bridge_post_called -eq $false -and $adapterStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($adapterStatus.value.bridge_post_called); bridge_post_call_implemented=$($adapterStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    $globalGates += Gate-Row "runtime_adapter_status_readable" $false "review" $adapterStatus.error "runtime"
}

if ($guardStatus.ok) {
    $globalGates += Gate-Row "runtime_guard_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status" "runtime"
    $globalGates += Gate-Row "runtime_guard_no_network_transport" ($guardStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($guardStatus.value.network_transport_implemented)" "runtime"
    $globalGates += Gate-Row "runtime_guard_no_bridge_post" ($guardStatus.value.bridge_post_called -eq $false -and $guardStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($guardStatus.value.bridge_post_called); bridge_post_call_implemented=$($guardStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    $globalGates += Gate-Row "runtime_guard_status_readable" $false "review" $guardStatus.error "runtime"
}

if ($httpDryRunStatus.ok) {
    $globalGates += Gate-Row "runtime_http_dry_run_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status" "runtime"
    $globalGates += Gate-Row "runtime_http_dry_run_no_network_transport" ($httpDryRunStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($httpDryRunStatus.value.network_transport_implemented)" "runtime"
} else {
    $globalGates += Gate-Row "runtime_http_dry_run_status_readable" $false "review" $httpDryRunStatus.error "runtime"
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

# Transport preflight row matrix from the adapter contract/result.
$contract = $adapter.simulation.adapter_dry_run_contract
$result = $adapter.simulation.simulated_adapter_result
$requestShape = $contract.request_shape
$requiredGates = $contract.required_gates

$transportRows = @()
$rowGates = @()

$rowGates += Gate-Row "row_contract_kind_is_dry_run_adapter_harness" ($contract.implementation_kind -eq "dry_run_adapter_harness") "blocker" "implementation_kind=$($contract.implementation_kind)" "transport_row"
$rowGates += Gate-Row "row_transport_mode_no_network" ($contract.transport_mode -eq "dry_run_no_network") "blocker" "transport_mode=$($contract.transport_mode)" "transport_row"
$rowGates += Gate-Row "row_network_socket_not_opened" ($contract.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($contract.network_socket_opened)" "transport_row"
$rowGates += Gate-Row "row_would_not_open_socket" ($contract.would_open_socket -eq $false) "blocker" "would_open_socket=$($contract.would_open_socket)" "transport_row"
$rowGates += Gate-Row "row_would_not_send_http_request" ($contract.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($contract.would_send_http_request)" "transport_row"
$rowGates += Gate-Row "row_would_not_call_bridge" ($contract.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($contract.would_call_bridge)" "transport_row"
$rowGates += Gate-Row "row_would_not_mutate_bridge" ($contract.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($contract.would_mutate_bridge)" "transport_row"
$rowGates += Gate-Row "row_result_status_code_zero" ([int]$result.status_code -eq 0) "blocker" "status_code=$($result.status_code)" "transport_row"
$rowGates += Gate-Row "row_result_not_ok" ($result.ok -eq $false) "blocker" "ok=$($result.ok)" "transport_row"
$rowGates += Gate-Row "row_result_has_contract_hash" (![string]::IsNullOrWhiteSpace((Normalize-String $result.adapter_contract_hash))) "blocker" "adapter_contract_hash=$($result.adapter_contract_hash)" "transport_row"
$rowGates += Gate-Row "row_request_method_post" ((Normalize-String $requestShape.method).ToUpperInvariant() -eq "POST") "blocker" "method=$($requestShape.method)" "transport_row"
$rowGates += Gate-Row "row_request_endpoint_routing_rules" ((Normalize-String $requestShape.endpoint) -eq "/api/routing-rules") "blocker" "endpoint=$($requestShape.endpoint)" "transport_row"
$rowGates += Gate-Row "row_request_base_url_env" ((Normalize-String $requestShape.base_url_env) -eq "PLATFORM_BRIDGE_BASE_URL") "blocker" "base_url_env=$($requestShape.base_url_env)" "transport_row"
$rowGates += Gate-Row "row_request_admin_token_env" ((Normalize-String $requestShape.admin_token_env) -eq "PLATFORM_BRIDGE_ADMIN_TOKEN") "blocker" "admin_token_env=$($requestShape.admin_token_env)" "transport_row"
$rowGates += Gate-Row "row_request_idempotency_header" ((Normalize-String $requestShape.idempotency_header) -eq "Idempotency-Key") "blocker" "idempotency_header=$($requestShape.idempotency_header)" "transport_row"

foreach ($field in @("phone", "mode", "owner_type", "label", "default_contact_ids", "notes")) {
    $rowGates += Gate-Row "row_payload_template_has_$field" (Test-HasProperty $requestShape.payload_template $field) "blocker" "payload field $field" "transport_row"
}

foreach ($field in @("pre_audit_row", "rollback_snapshot", "operator_confirmation", "response_recording", "lacrm_forbidden")) {
    $rowGates += Gate-Row "row_required_gate_$field" ($requiredGates.$field -eq $true) "blocker" "$field=$($requiredGates.$field)" "transport_row"
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
    "preflight_valid_for_future_network_transport_design"
}

$transportRows += [ordered]@{
    row_index = 0
    adapter_name = Normalize-String $contract.adapter_name
    implementation_kind = Normalize-String $contract.implementation_kind
    transport_mode = Normalize-String $contract.transport_mode
    request_method = Normalize-String $requestShape.method
    request_endpoint = Normalize-String $requestShape.endpoint
    adapter_contract_hash = Normalize-String $result.adapter_contract_hash
    row_status = $rowStatus
    gate_count = @($rowGates).Count
    failed_gate_count = @($rowFailures).Count
    blocker_count = @($rowFailures | Where-Object { $_.severity -eq "blocker" }).Count
    review_count = @($rowFailures | Where-Object { $_.severity -eq "review" }).Count
    network_socket_opened = [bool]$contract.network_socket_opened
    would_open_socket = [bool]$contract.would_open_socket
    would_send_http_request = [bool]$contract.would_send_http_request
    would_call_bridge = [bool]$contract.would_call_bridge
    would_mutate_bridge = [bool]$contract.would_mutate_bridge
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
    "preflight_valid_for_future_network_transport_design"
} elseif ($blockerCount -eq 0) {
    "preflight_valid_with_review_items"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_preflight_matrix_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 10"
    purpose = "Bridge routing network transport no-socket preflight matrix"
    source_adapter_validation = $validationPath
    source_dry_run_adapter = $adapterPath
    source_guard_report = $guardPath
    source_http_client_release_checkpoint = $releasePath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_preflight_matrix_only = $true
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
    preflight = [ordered]@{
        status = $preflightStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        global_gate_count = @($globalGates).Count
        transport_row_count = @($transportRows).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        reason = if ($blockerCount -eq 0) {
            "Network transport dry-run adapter preflight has no hard blockers. Phase 20 Step 10 still implements no real transport and opens no socket."
        } else {
            "Network transport dry-run adapter preflight found blockers. Resolve blockers before any future network transport design."
        }
    }
    global_gates = $globalGates
    transport_rows = $transportRows
    issues = @($issues)
    runtime_status = [ordered]@{
        adapter_status_ok = $adapterStatus.ok
        adapter_status = if ($adapterStatus.ok) { $adapterStatus.value } else { $null }
        guard_status_ok = $guardStatus.ok
        guard_status = if ($guardStatus.ok) { $guardStatus.value } else { $null }
        http_dry_run_status_ok = $httpDryRunStatus.ok
        http_dry_run_status = if ($httpDryRunStatus.ok) { $httpDryRunStatus.value } else { $null }
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
        "Do not call bridge POST endpoints from Phase 20 Step 10.",
        "Future network transport must remain disabled by default and preserve dry-run behavior.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_preflight_matrix.json"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_preflight_matrix_global_gates.csv"
$rowsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_preflight_matrix_rows.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_preflight_matrix_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_preflight_matrix.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$globalGates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$transportRows |
    Select-Object row_index, adapter_name, implementation_kind, transport_mode, request_method, request_endpoint, adapter_contract_hash, row_status, gate_count, failed_gate_count, blocker_count, review_count, network_socket_opened, would_open_socket, would_send_http_request, would_call_bridge, would_mutate_bridge |
    Export-Csv -LiteralPath $rowsCsvPath -NoTypeInformation -Encoding UTF8

$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }
$statusText = if ($statusCounts.Count -gt 0) { ($statusCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Preflight Matrix

Generated: $($report.generated_at)

Source dry-run adapter validation:

``````
$validationPath
``````

Source dry-run adapter report:

``````
$adapterPath
``````

## Safety

- Bridge routing network transport preflight matrix only: true
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

## Preflight

- Status: $preflightStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Transport rows: $($transportRows.Count)
- Can execute bridge write now: false
- Can add network transport now: false
- Can enable network transport now: false
- Can arm network transport now: false
- Can open network socket now: false
- Can add real bridge HTTP client now: false

## Row status counts

$statusText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_preflight_matrix=$OutputDir | status=$preflightStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_preflight_matrix=$OutputDir | status=$preflightStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Network transport preflight matrix files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
