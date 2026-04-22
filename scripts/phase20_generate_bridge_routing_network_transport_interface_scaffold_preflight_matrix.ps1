param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$ScaffoldValidationDir = "",
    [string]$InterfaceScaffoldDir = "",
    [string]$ImplementationPlanDir = "",
    [string]$NetworkReleaseCheckpointDir = "",
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

if ([string]::IsNullOrWhiteSpace($ScaffoldValidationDir)) {
    $ScaffoldValidationDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_interface_scaffold_validation_*" -JsonName "phase20_bridge_routing_network_transport_interface_scaffold_validation.json"
}
if ([string]::IsNullOrWhiteSpace($InterfaceScaffoldDir)) {
    $InterfaceScaffoldDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_interface_scaffold_*" -JsonName "phase20_bridge_routing_network_transport_interface_scaffold.json"
}
if ([string]::IsNullOrWhiteSpace($ImplementationPlanDir)) {
    $ImplementationPlanDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_implementation_plan_*" -JsonName "phase20_bridge_routing_network_transport_implementation_plan.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($NetworkReleaseCheckpointDir)) {
    $NetworkReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_release_checkpoint.json" -Required $false
}

$validationPath = Join-Path $ScaffoldValidationDir "phase20_bridge_routing_network_transport_interface_scaffold_validation.json"
$scaffoldPath = Join-Path $InterfaceScaffoldDir "phase20_bridge_routing_network_transport_interface_scaffold.json"
$planPath = if (![string]::IsNullOrWhiteSpace($ImplementationPlanDir)) { Join-Path $ImplementationPlanDir "phase20_bridge_routing_network_transport_implementation_plan.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($NetworkReleaseCheckpointDir)) { Join-Path $NetworkReleaseCheckpointDir "phase20_bridge_routing_network_transport_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $validationPath)) { throw "Interface scaffold validation JSON not found: $validationPath" }
if (!(Test-Path -LiteralPath $scaffoldPath)) { throw "Interface scaffold JSON not found: $scaffoldPath" }

$validation = Read-JsonFile $validationPath
$scaffold = Read-JsonFile $scaffoldPath
$plan = if (![string]::IsNullOrWhiteSpace($planPath) -and (Test-Path -LiteralPath $planPath)) { Read-JsonFile $planPath } else { $null }
$release = if (![string]::IsNullOrWhiteSpace($releasePath) -and (Test-Path -LiteralPath $releasePath)) { Read-JsonFile $releasePath } else { $null }

$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$globalGates = @()

# Global gates from Phase 20 Step 15 validation.
$globalGates += Gate-Row "scaffold_validation_exists" $true "blocker" $validationPath "scaffold_validation"
$globalGates += Gate-Row "interface_scaffold_exists" $true "blocker" $scaffoldPath "interface_scaffold"
$globalGates += Gate-Row "validation_is_validation_only" ($validation.safety.bridge_routing_network_transport_interface_scaffold_validation_only -eq $true) "blocker" "bridge_routing_network_transport_interface_scaffold_validation_only=$($validation.safety.bridge_routing_network_transport_interface_scaffold_validation_only)" "scaffold_validation"
$globalGates += Gate-Row "validation_bridge_get_only" ($validation.safety.bridge_get_only -eq $true) "blocker" "bridge_get_only=$($validation.safety.bridge_get_only)" "scaffold_validation"
$globalGates += Gate-Row "validation_no_network_transport" ($validation.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($validation.safety.network_transport_implemented)" "scaffold_validation"
$globalGates += Gate-Row "validation_no_network_enabled" ($validation.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($validation.safety.network_transport_enabled)" "scaffold_validation"
$globalGates += Gate-Row "validation_no_network_armed" ($validation.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($validation.safety.network_transport_armed)" "scaffold_validation"
$globalGates += Gate-Row "validation_no_socket" ($validation.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($validation.safety.network_socket_opened)" "scaffold_validation"
$globalGates += Gate-Row "validation_no_real_http_client" ($validation.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($validation.safety.real_bridge_http_client_implemented)" "scaffold_validation"
$globalGates += Gate-Row "validation_no_bridge_post" ($validation.safety.bridge_post_called -eq $false -and $validation.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($validation.safety.bridge_post_called); bridge_post_call_implemented=$($validation.safety.bridge_post_call_implemented)" "scaffold_validation"
$globalGates += Gate-Row "validation_no_mutation" ($validation.safety.platform_db_mutation_performed -eq $false -and $validation.safety.bridge_mutation_performed -eq $false) "blocker" "platform_db_mutation=$($validation.safety.platform_db_mutation_performed); bridge_mutation=$($validation.safety.bridge_mutation_performed)" "scaffold_validation"
$globalGates += Gate-Row "validation_no_lacrm" ($validation.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($validation.safety.lacrm_call_performed)" "scaffold_validation"
$globalGates += Gate-Row "validation_blocks_execution" ($validation.validation.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($validation.validation.can_execute_bridge_write_now)" "scaffold_validation"
$globalGates += Gate-Row "validation_blocks_network_transport" ($validation.validation.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($validation.validation.can_add_network_transport_now)" "scaffold_validation"
$globalGates += Gate-Row "validation_blocks_enable_network" ($validation.validation.can_enable_network_transport_now -eq $false) "blocker" "can_enable_network_transport_now=$($validation.validation.can_enable_network_transport_now)" "scaffold_validation"
$globalGates += Gate-Row "validation_blocks_arm_network" ($validation.validation.can_arm_network_transport_now -eq $false) "blocker" "can_arm_network_transport_now=$($validation.validation.can_arm_network_transport_now)" "scaffold_validation"
$globalGates += Gate-Row "validation_blocks_socket" ($validation.validation.can_open_network_socket_now -eq $false) "blocker" "can_open_network_socket_now=$($validation.validation.can_open_network_socket_now)" "scaffold_validation"
$globalGates += Gate-Row "validation_blocks_real_http_client" ($validation.validation.can_add_real_bridge_http_client_now -eq $false) "blocker" "can_add_real_bridge_http_client_now=$($validation.validation.can_add_real_bridge_http_client_now)" "scaffold_validation"
$globalGates += Gate-Row "validation_blocks_bridge_post" ($validation.validation.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($validation.validation.can_add_bridge_post_now)" "scaffold_validation"

# Global gates from Phase 20 Step 14 scaffold artifact.
$globalGates += Gate-Row "scaffold_is_scaffold_only" ($scaffold.safety.bridge_routing_network_transport_interface_scaffold_only -eq $true) "blocker" "bridge_routing_network_transport_interface_scaffold_only=$($scaffold.safety.bridge_routing_network_transport_interface_scaffold_only)" "interface_scaffold"
$globalGates += Gate-Row "scaffold_no_network_transport" ($scaffold.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($scaffold.safety.network_transport_implemented)" "interface_scaffold"
$globalGates += Gate-Row "scaffold_no_network_enabled" ($scaffold.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($scaffold.safety.network_transport_enabled)" "interface_scaffold"
$globalGates += Gate-Row "scaffold_no_network_armed" ($scaffold.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($scaffold.safety.network_transport_armed)" "interface_scaffold"
$globalGates += Gate-Row "scaffold_no_socket_opened" ($scaffold.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($scaffold.safety.network_socket_opened)" "interface_scaffold"
$globalGates += Gate-Row "scaffold_no_bridge_post" ($scaffold.safety.bridge_post_called -eq $false -and $scaffold.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($scaffold.safety.bridge_post_called); bridge_post_call_implemented=$($scaffold.safety.bridge_post_call_implemented)" "interface_scaffold"
$globalGates += Gate-Row "scaffold_preview_blocks_network" ($scaffold.preview.would_add_network_transport -eq $false) "blocker" "would_add_network_transport=$($scaffold.preview.would_add_network_transport)" "interface_scaffold"
$globalGates += Gate-Row "scaffold_preview_blocks_socket" ($scaffold.preview.would_open_socket -eq $false) "blocker" "would_open_socket=$($scaffold.preview.would_open_socket)" "interface_scaffold"
$globalGates += Gate-Row "scaffold_preview_blocks_send" ($scaffold.preview.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($scaffold.preview.would_send_http_request)" "interface_scaffold"
$globalGates += Gate-Row "scaffold_preview_blocks_bridge_call" ($scaffold.preview.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($scaffold.preview.would_call_bridge)" "interface_scaffold"

# Optional upstream evidence.
if ($plan -ne $null) {
    $globalGates += Gate-Row "implementation_plan_present" $true "review" $planPath "implementation_plan"
    $globalGates += Gate-Row "implementation_plan_no_network_transport" ($plan.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($plan.safety.network_transport_implemented)" "implementation_plan"
    $globalGates += Gate-Row "implementation_plan_no_socket" ($plan.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($plan.safety.network_socket_opened)" "implementation_plan"
    $globalGates += Gate-Row "implementation_plan_blocks_bridge_post" ($plan.implementation_plan.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($plan.implementation_plan.can_add_bridge_post_now)" "implementation_plan"
} else {
    $globalGates += Gate-Row "implementation_plan_present" $false "review" "Phase 20 Step 13 implementation plan not found." "implementation_plan" "Generate Step 13 plan before real transport design."
}

if ($release -ne $null) {
    $globalGates += Gate-Row "network_release_checkpoint_present" $true "review" $releasePath "network_release_checkpoint"
    $globalGates += Gate-Row "network_release_no_network_transport" ($release.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($release.safety.network_transport_implemented)" "network_release_checkpoint"
    $globalGates += Gate-Row "network_release_no_socket" ($release.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($release.safety.network_socket_opened)" "network_release_checkpoint"
    $globalGates += Gate-Row "network_release_no_bridge_post" ($release.safety.bridge_post_called -eq $false -and $release.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($release.safety.bridge_post_called); bridge_post_call_implemented=$($release.safety.bridge_post_call_implemented)" "network_release_checkpoint"
} else {
    $globalGates += Gate-Row "network_release_checkpoint_present" $false "review" "Phase 20 Step 12 release checkpoint not found." "network_release_checkpoint" "Generate Step 12 release checkpoint before real transport design."
}

# Runtime gates. Unreachable runtime is review-level, but safety contradictions are blockers.
if ($scaffoldStatus.ok) {
    $globalGates += Gate-Row "runtime_scaffold_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status" "runtime"
    $globalGates += Gate-Row "runtime_scaffold_no_network_transport" ($scaffoldStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($scaffoldStatus.value.network_transport_implemented)" "runtime"
    $globalGates += Gate-Row "runtime_scaffold_no_socket" ($scaffoldStatus.value.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($scaffoldStatus.value.network_socket_opened)" "runtime"
    $globalGates += Gate-Row "runtime_scaffold_no_bridge_post" ($scaffoldStatus.value.bridge_post_called -eq $false -and $scaffoldStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($scaffoldStatus.value.bridge_post_called); bridge_post_call_implemented=$($scaffoldStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    $globalGates += Gate-Row "runtime_scaffold_status_readable" $false "review" $scaffoldStatus.error "runtime"
}

if ($adapterStatus.ok) {
    $globalGates += Gate-Row "runtime_adapter_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status" "runtime"
    $globalGates += Gate-Row "runtime_adapter_no_network_transport" ($adapterStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($adapterStatus.value.network_transport_implemented)" "runtime"
    $globalGates += Gate-Row "runtime_adapter_no_socket" ($adapterStatus.value.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($adapterStatus.value.network_socket_opened)" "runtime"
} else {
    $globalGates += Gate-Row "runtime_adapter_status_readable" $false "review" $adapterStatus.error "runtime"
}

if ($guardStatus.ok) {
    $globalGates += Gate-Row "runtime_guard_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status" "runtime"
    $globalGates += Gate-Row "runtime_guard_no_network_transport" ($guardStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($guardStatus.value.network_transport_implemented)" "runtime"
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

$globalGates += Gate-Row "runtime_bridge_health_readable" $bridgeHealth.ok "review" $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "runtime"

foreach ($gate in $globalGates) {
    Add-GateIssueIfFailed $issues $gate
}

# Interface scaffold row matrix.
$interface = $scaffold.preview.interface_scaffold
$sampleRequest = $scaffold.preview.sample_request
$sampleResult = $scaffold.preview.sample_result

$interfaceRows = @()
$rowGates = @()

$rowGates += Gate-Row "row_interface_module_present" ((Normalize-String $interface.module) -eq "app.services.routing_bridge_network_transport_interface_scaffold") "blocker" "module=$($interface.module)" "interface_row"
$rowGates += Gate-Row "row_adapter_name_present" ((Normalize-String $interface.adapter_name) -eq "BridgeRoutingTransportAdapterInterface") "blocker" "adapter_name=$($interface.adapter_name)" "interface_row"
$rowGates += Gate-Row "row_kind_scaffold_only" ((Normalize-String $interface.implementation_kind) -eq "interface_scaffold_only") "blocker" "implementation_kind=$($interface.implementation_kind)" "interface_row"
$rowGates += Gate-Row "row_execute_raises" ((Normalize-String $interface.execute_method_behavior) -eq "raises_runtime_error_no_transport") "blocker" "execute_method_behavior=$($interface.execute_method_behavior)" "interface_row"
$rowGates += Gate-Row "row_simulate_no_network" ((Normalize-String $interface.simulate_method_behavior) -eq "shape_only_no_network") "blocker" "simulate_method_behavior=$($interface.simulate_method_behavior)" "interface_row"
$rowGates += Gate-Row "row_no_network_transport" ($interface.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($interface.network_transport_implemented)" "interface_row"
$rowGates += Gate-Row "row_no_socket_opened" ($interface.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($interface.network_socket_opened)" "interface_row"
$rowGates += Gate-Row "row_no_bridge_post_impl" ($interface.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_call_implemented=$($interface.bridge_post_call_implemented)" "interface_row"
$rowGates += Gate-Row "row_has_scaffold_hash" (![string]::IsNullOrWhiteSpace((Normalize-String $scaffold.preview.interface_scaffold_hash))) "blocker" "interface_scaffold_hash=$($scaffold.preview.interface_scaffold_hash)" "interface_row"

foreach ($className in @("BridgeRoutingTransportRequest", "BridgeRoutingTransportResult", "BridgeRoutingTransportAdapterInterface")) {
    $rowGates += Gate-Row "row_has_class_$className" (@($interface.classes) -contains $className) "blocker" "class=$className" "interface_row"
}

foreach ($field in @("phone", "mode", "owner_type", "label", "default_contact_ids", "notes", "idempotency_key")) {
    $rowGates += Gate-Row "row_request_field_$field" (@($interface.request_fields) -contains $field) "blocker" "request field $field" "interface_row"
}

foreach ($field in @("ok", "status_code", "transport_mode", "would_open_socket", "would_send_http_request", "would_call_bridge", "would_mutate_bridge", "message")) {
    $rowGates += Gate-Row "row_result_field_$field" (@($interface.result_fields) -contains $field) "blocker" "result field $field" "interface_row"
}

foreach ($futureGate in @("audit_prerequisite_gate", "rollback_snapshot_gate", "environment_gate_design", "operator_confirmation_gate", "response_capture_design", "future_cutover_packet_prerequisite")) {
    $rowGates += Gate-Row "row_required_future_gate_$futureGate" (@($interface.required_future_gates) -contains $futureGate) "blocker" "future gate $futureGate" "interface_row"
}

$rowGates += Gate-Row "row_sample_request_dry_run" ((Normalize-String $sampleRequest.mode) -eq "dry_run") "blocker" "mode=$($sampleRequest.mode)" "interface_row"
$rowGates += Gate-Row "row_sample_request_idempotency_key_present" (![string]::IsNullOrWhiteSpace((Normalize-String $sampleRequest.idempotency_key))) "blocker" "idempotency_key=$($sampleRequest.idempotency_key)" "interface_row"
$rowGates += Gate-Row "row_sample_result_not_ok" ($sampleResult.ok -eq $false) "blocker" "ok=$($sampleResult.ok)" "interface_row"
$rowGates += Gate-Row "row_sample_result_status_code_zero" ([int]$sampleResult.status_code -eq 0) "blocker" "status_code=$($sampleResult.status_code)" "interface_row"
$rowGates += Gate-Row "row_sample_result_no_network_mode" ((Normalize-String $sampleResult.transport_mode) -eq "dry_run_no_network") "blocker" "transport_mode=$($sampleResult.transport_mode)" "interface_row"
$rowGates += Gate-Row "row_sample_result_would_not_open_socket" ($sampleResult.would_open_socket -eq $false) "blocker" "would_open_socket=$($sampleResult.would_open_socket)" "interface_row"
$rowGates += Gate-Row "row_sample_result_would_not_send_http_request" ($sampleResult.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($sampleResult.would_send_http_request)" "interface_row"
$rowGates += Gate-Row "row_sample_result_would_not_call_bridge" ($sampleResult.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($sampleResult.would_call_bridge)" "interface_row"
$rowGates += Gate-Row "row_sample_result_would_not_mutate_bridge" ($sampleResult.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($sampleResult.would_mutate_bridge)" "interface_row"

$rowFailures = @($rowGates | Where-Object { $_.passed -ne $true })
foreach ($gate in $rowFailures) {
    Add-Issue $issues $gate.severity "interface_row_$($gate.gate)" $gate.evidence $gate.source
}

$rowStatus = if (@($rowFailures | Where-Object { $_.severity -eq "blocker" }).Count -gt 0) {
    "blocked"
} elseif (@($rowFailures).Count -gt 0) {
    "review_required"
} else {
    "preflight_valid_for_future_interface_adapter_design"
}

$interfaceRows += [ordered]@{
    row_index = 0
    adapter_name = Normalize-String $interface.adapter_name
    implementation_kind = Normalize-String $interface.implementation_kind
    module = Normalize-String $interface.module
    interface_scaffold_hash = Normalize-String $scaffold.preview.interface_scaffold_hash
    row_status = $rowStatus
    gate_count = @($rowGates).Count
    failed_gate_count = @($rowFailures).Count
    blocker_count = @($rowFailures | Where-Object { $_.severity -eq "blocker" }).Count
    review_count = @($rowFailures | Where-Object { $_.severity -eq "review" }).Count
    class_count = @($interface.classes).Count
    request_field_count = @($interface.request_fields).Count
    result_field_count = @($interface.result_fields).Count
    network_transport_implemented = [bool]$interface.network_transport_implemented
    network_socket_opened = [bool]$interface.network_socket_opened
    bridge_post_call_implemented = [bool]$interface.bridge_post_call_implemented
    execute_method_behavior = Normalize-String $interface.execute_method_behavior
    simulate_method_behavior = Normalize-String $interface.simulate_method_behavior
    gates = $rowGates
}

$statusCounts = @{}
foreach ($row in $interfaceRows) {
    if (!$statusCounts.ContainsKey($row.row_status)) { $statusCounts[$row.row_status] = 0 }
    $statusCounts[$row.row_status] += 1
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$preflightStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "preflight_valid_for_future_interface_adapter_design"
} elseif ($blockerCount -eq 0) {
    "preflight_valid_with_review_items"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_interface_scaffold_preflight_matrix_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 16"
    purpose = "Bridge routing network transport interface scaffold preflight matrix"
    source_scaffold_validation = $validationPath
    source_interface_scaffold = $scaffoldPath
    source_implementation_plan = $planPath
    source_network_release_checkpoint = $releasePath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_interface_scaffold_preflight_matrix_only = $true
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
        interface_row_count = @($interfaceRows).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        can_add_bridge_post_now = $false
        reason = if ($blockerCount -eq 0) {
            "Interface scaffold preflight has no hard blockers. Phase 20 Step 16 still implements no real transport and opens no socket."
        } else {
            "Interface scaffold preflight found blockers. Resolve blockers before any future network transport design."
        }
    }
    global_gates = $globalGates
    interface_rows = $interfaceRows
    issues = @($issues)
    runtime_status = [ordered]@{
        scaffold_status_ok = $scaffoldStatus.ok
        scaffold_status = if ($scaffoldStatus.ok) { $scaffoldStatus.value } else { $null }
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
        global_gates = @($globalGates).Count
        interface_rows = @($interfaceRows).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
        status_counts = $statusCounts
    }
    next_recommended_actions = @(
        "Review this preflight matrix before adding any real interface-backed transport adapter.",
        "Do not call bridge POST endpoints from Phase 20 Step 16.",
        "Future network transport must remain disabled by default and preserve dry-run behavior.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_preflight_matrix.json"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_preflight_matrix_global_gates.csv"
$rowsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_preflight_matrix_rows.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_preflight_matrix_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_preflight_matrix.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$globalGates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$interfaceRows |
    Select-Object row_index, adapter_name, implementation_kind, module, interface_scaffold_hash, row_status, gate_count, failed_gate_count, blocker_count, review_count, class_count, request_field_count, result_field_count, network_transport_implemented, network_socket_opened, bridge_post_call_implemented, execute_method_behavior, simulate_method_behavior |
    Export-Csv -LiteralPath $rowsCsvPath -NoTypeInformation -Encoding UTF8

$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }
$statusText = if ($statusCounts.Count -gt 0) { ($statusCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Interface Scaffold Preflight Matrix

Generated: $($report.generated_at)

Source interface scaffold validation:

``````
$validationPath
``````

Source interface scaffold report:

``````
$scaffoldPath
``````

## Safety

- Bridge routing network transport interface scaffold preflight matrix only: true
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
- Interface rows: $($interfaceRows.Count)
- Can execute bridge write now: false
- Can add network transport now: false
- Can enable network transport now: false
- Can arm network transport now: false
- Can open network socket now: false
- Can add real bridge HTTP client now: false
- Can add bridge POST now: false

## Row status counts

$statusText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_interface_scaffold_preflight_matrix=$OutputDir | status=$preflightStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_interface_scaffold_preflight_matrix=$OutputDir | status=$preflightStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Network transport interface scaffold preflight matrix files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
