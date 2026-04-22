param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$DryRunInvocationValidationDir = "",
    [string]$DryRunInvocationPathDir = "",
    [string]$InterfaceScaffoldReleaseCheckpointDir = "",
    [string]$InterfaceScaffoldOperatorSignoffDir = "",
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

if ([string]::IsNullOrWhiteSpace($DryRunInvocationValidationDir)) {
    $DryRunInvocationValidationDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation.json"
}
if ([string]::IsNullOrWhiteSpace($DryRunInvocationPathDir)) {
    $DryRunInvocationPathDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path.json"
}
if ([string]::IsNullOrWhiteSpace($InterfaceScaffoldReleaseCheckpointDir)) {
    $InterfaceScaffoldReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($InterfaceScaffoldOperatorSignoffDir)) {
    $InterfaceScaffoldOperatorSignoffDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff_*" -JsonName "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff.json" -Required $false
}

$validationPath = Join-Path $DryRunInvocationValidationDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation.json"
$invocationPath = Join-Path $DryRunInvocationPathDir "phase20_bridge_routing_network_transport_dry_run_invocation_path.json"
$releasePath = if (![string]::IsNullOrWhiteSpace($InterfaceScaffoldReleaseCheckpointDir)) { Join-Path $InterfaceScaffoldReleaseCheckpointDir "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint.json" } else { "" }
$signoffPath = if (![string]::IsNullOrWhiteSpace($InterfaceScaffoldOperatorSignoffDir)) { Join-Path $InterfaceScaffoldOperatorSignoffDir "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff.json" } else { "" }

if (!(Test-Path -LiteralPath $validationPath)) { throw "Dry-run invocation path validation JSON not found: $validationPath" }
if (!(Test-Path -LiteralPath $invocationPath)) { throw "Dry-run invocation path JSON not found: $invocationPath" }

$validation = Read-JsonFile $validationPath
$invocation = Read-JsonFile $invocationPath
$release = if (![string]::IsNullOrWhiteSpace($releasePath) -and (Test-Path -LiteralPath $releasePath)) { Read-JsonFile $releasePath } else { $null }
$signoff = if (![string]::IsNullOrWhiteSpace($signoffPath) -and (Test-Path -LiteralPath $signoffPath)) { Read-JsonFile $signoffPath } else { $null }

$invocationStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$globalGates = @()

# Global gates from Phase 20 Step 20 validation.
$globalGates += Gate-Row "dry_run_invocation_validation_exists" $true "blocker" $validationPath "dry_run_invocation_validation"
$globalGates += Gate-Row "dry_run_invocation_path_exists" $true "blocker" $invocationPath "dry_run_invocation_path"
$globalGates += Gate-Row "validation_is_validation_only" ($validation.safety.bridge_routing_network_transport_dry_run_invocation_path_validation_only -eq $true) "blocker" "bridge_routing_network_transport_dry_run_invocation_path_validation_only=$($validation.safety.bridge_routing_network_transport_dry_run_invocation_path_validation_only)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_bridge_get_only" ($validation.safety.bridge_get_only -eq $true) "blocker" "bridge_get_only=$($validation.safety.bridge_get_only)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_no_network_transport" ($validation.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($validation.safety.network_transport_implemented)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_no_network_enabled" ($validation.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($validation.safety.network_transport_enabled)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_no_network_armed" ($validation.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($validation.safety.network_transport_armed)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_no_socket" ($validation.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($validation.safety.network_socket_opened)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_no_real_http_client" ($validation.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($validation.safety.real_bridge_http_client_implemented)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_no_bridge_post" ($validation.safety.bridge_post_called -eq $false -and $validation.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($validation.safety.bridge_post_called); bridge_post_call_implemented=$($validation.safety.bridge_post_call_implemented)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_no_mutation" ($validation.safety.platform_db_mutation_performed -eq $false -and $validation.safety.bridge_mutation_performed -eq $false) "blocker" "platform_db_mutation=$($validation.safety.platform_db_mutation_performed); bridge_mutation=$($validation.safety.bridge_mutation_performed)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_no_lacrm" ($validation.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($validation.safety.lacrm_call_performed)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_blocks_execution" ($validation.validation.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($validation.validation.can_execute_bridge_write_now)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_blocks_network_transport" ($validation.validation.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($validation.validation.can_add_network_transport_now)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_blocks_enable_network" ($validation.validation.can_enable_network_transport_now -eq $false) "blocker" "can_enable_network_transport_now=$($validation.validation.can_enable_network_transport_now)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_blocks_arm_network" ($validation.validation.can_arm_network_transport_now -eq $false) "blocker" "can_arm_network_transport_now=$($validation.validation.can_arm_network_transport_now)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_blocks_socket" ($validation.validation.can_open_network_socket_now -eq $false) "blocker" "can_open_network_socket_now=$($validation.validation.can_open_network_socket_now)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_blocks_real_http_client" ($validation.validation.can_add_real_bridge_http_client_now -eq $false) "blocker" "can_add_real_bridge_http_client_now=$($validation.validation.can_add_real_bridge_http_client_now)" "dry_run_invocation_validation"
$globalGates += Gate-Row "validation_blocks_bridge_post" ($validation.validation.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($validation.validation.can_add_bridge_post_now)" "dry_run_invocation_validation"

# Global gates from Phase 20 Step 19 dry-run invocation path artifact.
$globalGates += Gate-Row "invocation_path_is_dry_run_only" ($invocation.safety.bridge_routing_network_transport_dry_run_invocation_path_only -eq $true) "blocker" "bridge_routing_network_transport_dry_run_invocation_path_only=$($invocation.safety.bridge_routing_network_transport_dry_run_invocation_path_only)" "dry_run_invocation_path"
$globalGates += Gate-Row "invocation_path_no_network_transport" ($invocation.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($invocation.safety.network_transport_implemented)" "dry_run_invocation_path"
$globalGates += Gate-Row "invocation_path_no_network_enabled" ($invocation.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($invocation.safety.network_transport_enabled)" "dry_run_invocation_path"
$globalGates += Gate-Row "invocation_path_no_network_armed" ($invocation.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($invocation.safety.network_transport_armed)" "dry_run_invocation_path"
$globalGates += Gate-Row "invocation_path_no_socket_opened" ($invocation.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($invocation.safety.network_socket_opened)" "dry_run_invocation_path"
$globalGates += Gate-Row "invocation_path_no_bridge_post" ($invocation.safety.bridge_post_called -eq $false -and $invocation.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($invocation.safety.bridge_post_called); bridge_post_call_implemented=$($invocation.safety.bridge_post_call_implemented)" "dry_run_invocation_path"
$globalGates += Gate-Row "invocation_preview_blocks_network" ($invocation.preview.would_add_network_transport -eq $false) "blocker" "would_add_network_transport=$($invocation.preview.would_add_network_transport)" "dry_run_invocation_path"
$globalGates += Gate-Row "invocation_preview_blocks_socket" ($invocation.preview.would_open_socket -eq $false) "blocker" "would_open_socket=$($invocation.preview.would_open_socket)" "dry_run_invocation_path"
$globalGates += Gate-Row "invocation_preview_blocks_send" ($invocation.preview.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($invocation.preview.would_send_http_request)" "dry_run_invocation_path"
$globalGates += Gate-Row "invocation_preview_blocks_bridge_call" ($invocation.preview.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($invocation.preview.would_call_bridge)" "dry_run_invocation_path"
$globalGates += Gate-Row "invocation_preview_blocks_bridge_mutation" ($invocation.preview.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($invocation.preview.would_mutate_bridge)" "dry_run_invocation_path"
$globalGates += Gate-Row "invocation_preview_blocks_platform_mutation" ($invocation.preview.would_mutate_platform -eq $false) "blocker" "would_mutate_platform=$($invocation.preview.would_mutate_platform)" "dry_run_invocation_path"
$globalGates += Gate-Row "invocation_preview_blocks_lacrm" ($invocation.preview.would_call_lacrm -eq $false) "blocker" "would_call_lacrm=$($invocation.preview.would_call_lacrm)" "dry_run_invocation_path"

# Optional upstream evidence.
if ($release -ne $null) {
    $globalGates += Gate-Row "interface_release_checkpoint_present" $true "review" $releasePath "interface_release_checkpoint"
    $globalGates += Gate-Row "interface_release_no_network_transport" ($release.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($release.safety.network_transport_implemented)" "interface_release_checkpoint"
    $globalGates += Gate-Row "interface_release_no_socket" ($release.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($release.safety.network_socket_opened)" "interface_release_checkpoint"
    $globalGates += Gate-Row "interface_release_no_bridge_post" ($release.safety.bridge_post_called -eq $false -and $release.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($release.safety.bridge_post_called); bridge_post_call_implemented=$($release.safety.bridge_post_call_implemented)" "interface_release_checkpoint"
    $globalGates += Gate-Row "interface_release_blocks_execution" ($release.release_checkpoint.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($release.release_checkpoint.can_execute_bridge_write_now)" "interface_release_checkpoint"
    $globalGates += Gate-Row "interface_release_blocks_bridge_post" ($release.release_checkpoint.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($release.release_checkpoint.can_add_bridge_post_now)" "interface_release_checkpoint"
} else {
    $globalGates += Gate-Row "interface_release_checkpoint_present" $false "review" "Phase 20 Step 18 release checkpoint not found." "interface_release_checkpoint" "Generate Step 18 release checkpoint before real transport design."
}

if ($signoff -ne $null) {
    $globalGates += Gate-Row "interface_operator_signoff_present" $true "review" $signoffPath "interface_operator_signoff"
    $globalGates += Gate-Row "interface_signoff_no_network_transport" ($signoff.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($signoff.safety.network_transport_implemented)" "interface_operator_signoff"
    $globalGates += Gate-Row "interface_signoff_no_socket" ($signoff.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($signoff.safety.network_socket_opened)" "interface_operator_signoff"
    $globalGates += Gate-Row "interface_signoff_blocks_bridge_post" ($signoff.signoff.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($signoff.signoff.can_add_bridge_post_now)" "interface_operator_signoff"
} else {
    $globalGates += Gate-Row "interface_operator_signoff_present" $false "review" "Phase 20 Step 17 operator signoff not found." "interface_operator_signoff" "Generate Step 17 signoff before real transport design."
}

# Runtime gates. Unreachable runtime is review-level, safety contradictions are blockers.
if ($invocationStatus.ok) {
    $globalGates += Gate-Row "runtime_invocation_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status" "runtime"
    $globalGates += Gate-Row "runtime_invocation_no_network_transport" ($invocationStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($invocationStatus.value.network_transport_implemented)" "runtime"
    $globalGates += Gate-Row "runtime_invocation_no_socket" ($invocationStatus.value.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($invocationStatus.value.network_socket_opened)" "runtime"
    $globalGates += Gate-Row "runtime_invocation_no_bridge_post" ($invocationStatus.value.bridge_post_called -eq $false -and $invocationStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($invocationStatus.value.bridge_post_called); bridge_post_call_implemented=$($invocationStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    $globalGates += Gate-Row "runtime_invocation_status_readable" $false "review" $invocationStatus.error "runtime"
}

if ($scaffoldStatus.ok) {
    $globalGates += Gate-Row "runtime_scaffold_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status" "runtime"
    $globalGates += Gate-Row "runtime_scaffold_no_network_transport" ($scaffoldStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($scaffoldStatus.value.network_transport_implemented)" "runtime"
    $globalGates += Gate-Row "runtime_scaffold_no_socket" ($scaffoldStatus.value.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($scaffoldStatus.value.network_socket_opened)" "runtime"
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

# Invocation row matrix.
$contract = $invocation.preview.invocation_path_contract
$sampleRequest = $invocation.preview.sample_request
$sampleResult = $invocation.preview.sample_result
$simulatedInvocation = $invocation.preview.simulated_invocation

$invocationRows = @()
$rowGates = @()

$rowGates += Gate-Row "row_invocation_path_name_present" ((Normalize-String $contract.invocation_path_name) -eq "BridgeRoutingNetworkTransportDryRunInvocationPath") "blocker" "invocation_path_name=$($contract.invocation_path_name)" "invocation_row"
$rowGates += Gate-Row "row_kind_dry_run_invocation_only" ((Normalize-String $contract.implementation_kind) -eq "dry_run_invocation_path_only") "blocker" "implementation_kind=$($contract.implementation_kind)" "invocation_row"
$rowGates += Gate-Row "row_source_interface_present" ((Normalize-String $contract.source_interface) -eq "BridgeRoutingTransportAdapterInterface") "blocker" "source_interface=$($contract.source_interface)" "invocation_row"
$rowGates += Gate-Row "row_transport_mode_no_network" ((Normalize-String $contract.transport_mode) -eq "dry_run_no_network") "blocker" "transport_mode=$($contract.transport_mode)" "invocation_row"
$rowGates += Gate-Row "row_execution_behavior_no_network" ((Normalize-String $contract.execution_behavior) -eq "returns_simulated_result_no_network") "blocker" "execution_behavior=$($contract.execution_behavior)" "invocation_row"
$rowGates += Gate-Row "row_live_behavior_not_available" ((Normalize-String $contract.execute_live_behavior) -eq "not_available") "blocker" "execute_live_behavior=$($contract.execute_live_behavior)" "invocation_row"
$rowGates += Gate-Row "row_no_network_transport" ($contract.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($contract.network_transport_implemented)" "invocation_row"
$rowGates += Gate-Row "row_no_network_enabled" ($contract.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($contract.network_transport_enabled)" "invocation_row"
$rowGates += Gate-Row "row_no_network_armed" ($contract.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($contract.network_transport_armed)" "invocation_row"
$rowGates += Gate-Row "row_no_socket_opened" ($contract.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($contract.network_socket_opened)" "invocation_row"
$rowGates += Gate-Row "row_would_not_open_socket" ($contract.would_open_socket -eq $false) "blocker" "would_open_socket=$($contract.would_open_socket)" "invocation_row"
$rowGates += Gate-Row "row_would_not_send_http_request" ($contract.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($contract.would_send_http_request)" "invocation_row"
$rowGates += Gate-Row "row_would_not_call_bridge" ($contract.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($contract.would_call_bridge)" "invocation_row"
$rowGates += Gate-Row "row_would_not_mutate_bridge" ($contract.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($contract.would_mutate_bridge)" "invocation_row"
$rowGates += Gate-Row "row_would_not_mutate_platform" ($contract.would_mutate_platform -eq $false) "blocker" "would_mutate_platform=$($contract.would_mutate_platform)" "invocation_row"
$rowGates += Gate-Row "row_would_not_call_lacrm" ($contract.would_call_lacrm -eq $false) "blocker" "would_call_lacrm=$($contract.would_call_lacrm)" "invocation_row"
$rowGates += Gate-Row "row_has_contract_hash" (![string]::IsNullOrWhiteSpace((Normalize-String $invocation.preview.invocation_path_contract_hash))) "blocker" "invocation_path_contract_hash=$($invocation.preview.invocation_path_contract_hash)" "invocation_row"

foreach ($field in @("phone", "mode", "owner_type", "label", "default_contact_ids", "notes", "idempotency_key")) {
    $rowGates += Gate-Row "row_request_field_$field" (@($contract.request_shape) -contains $field) "blocker" "request field $field" "invocation_row"
}

foreach ($field in @("ok", "status_code", "transport_mode", "invocation_kind", "would_open_socket", "would_send_http_request", "would_call_bridge", "would_mutate_bridge", "would_mutate_platform", "would_call_lacrm", "message")) {
    $rowGates += Gate-Row "row_result_field_$field" (@($contract.result_shape) -contains $field) "blocker" "result field $field" "invocation_row"
}

foreach ($futureGate in @("audit_prerequisite_gate", "rollback_snapshot_gate", "environment_gate_design", "operator_confirmation_gate", "response_capture_design", "future_cutover_packet_prerequisite")) {
    $rowGates += Gate-Row "row_required_future_gate_$futureGate" (@($contract.required_future_gates) -contains $futureGate) "blocker" "future gate $futureGate" "invocation_row"
}

$rowGates += Gate-Row "row_sample_request_dry_run" ((Normalize-String $sampleRequest.mode) -eq "dry_run") "blocker" "mode=$($sampleRequest.mode)" "invocation_row"
$rowGates += Gate-Row "row_sample_request_idempotency_key_present" (![string]::IsNullOrWhiteSpace((Normalize-String $sampleRequest.idempotency_key))) "blocker" "idempotency_key=$($sampleRequest.idempotency_key)" "invocation_row"
$rowGates += Gate-Row "row_sample_result_not_ok" ($sampleResult.ok -eq $false) "blocker" "ok=$($sampleResult.ok)" "invocation_row"
$rowGates += Gate-Row "row_sample_result_status_code_zero" ([int]$sampleResult.status_code -eq 0) "blocker" "status_code=$($sampleResult.status_code)" "invocation_row"
$rowGates += Gate-Row "row_sample_result_no_network_mode" ((Normalize-String $sampleResult.transport_mode) -eq "dry_run_no_network") "blocker" "transport_mode=$($sampleResult.transport_mode)" "invocation_row"
$rowGates += Gate-Row "row_sample_result_invocation_kind" ((Normalize-String $sampleResult.invocation_kind) -eq "dry_run_invocation_path_only") "blocker" "invocation_kind=$($sampleResult.invocation_kind)" "invocation_row"
$rowGates += Gate-Row "row_sample_result_would_not_open_socket" ($sampleResult.would_open_socket -eq $false) "blocker" "would_open_socket=$($sampleResult.would_open_socket)" "invocation_row"
$rowGates += Gate-Row "row_sample_result_would_not_send_http_request" ($sampleResult.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($sampleResult.would_send_http_request)" "invocation_row"
$rowGates += Gate-Row "row_sample_result_would_not_call_bridge" ($sampleResult.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($sampleResult.would_call_bridge)" "invocation_row"
$rowGates += Gate-Row "row_sample_result_would_not_mutate_bridge" ($sampleResult.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($sampleResult.would_mutate_bridge)" "invocation_row"
$rowGates += Gate-Row "row_sample_result_would_not_mutate_platform" ($sampleResult.would_mutate_platform -eq $false) "blocker" "would_mutate_platform=$($sampleResult.would_mutate_platform)" "invocation_row"
$rowGates += Gate-Row "row_sample_result_would_not_call_lacrm" ($sampleResult.would_call_lacrm -eq $false) "blocker" "would_call_lacrm=$($sampleResult.would_call_lacrm)" "invocation_row"

$rowGates += Gate-Row "row_simulated_invocation_not_ok" ($simulatedInvocation.ok -eq $false) "blocker" "ok=$($simulatedInvocation.ok)" "invocation_row"
$rowGates += Gate-Row "row_simulated_invocation_status_zero" ([int]$simulatedInvocation.status_code -eq 0) "blocker" "status_code=$($simulatedInvocation.status_code)" "invocation_row"
$rowGates += Gate-Row "row_simulated_invocation_no_network_mode" ((Normalize-String $simulatedInvocation.transport_mode) -eq "dry_run_no_network") "blocker" "transport_mode=$($simulatedInvocation.transport_mode)" "invocation_row"
$rowGates += Gate-Row "row_simulated_invocation_would_not_open_socket" ($simulatedInvocation.would_open_socket -eq $false) "blocker" "would_open_socket=$($simulatedInvocation.would_open_socket)" "invocation_row"
$rowGates += Gate-Row "row_simulated_invocation_would_not_send_http_request" ($simulatedInvocation.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($simulatedInvocation.would_send_http_request)" "invocation_row"
$rowGates += Gate-Row "row_simulated_invocation_would_not_call_bridge" ($simulatedInvocation.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($simulatedInvocation.would_call_bridge)" "invocation_row"
$rowGates += Gate-Row "row_simulated_invocation_would_not_mutate_bridge" ($simulatedInvocation.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($simulatedInvocation.would_mutate_bridge)" "invocation_row"
$rowGates += Gate-Row "row_simulated_invocation_would_not_mutate_platform" ($simulatedInvocation.would_mutate_platform -eq $false) "blocker" "would_mutate_platform=$($simulatedInvocation.would_mutate_platform)" "invocation_row"

$rowFailures = @($rowGates | Where-Object { $_.passed -ne $true })
foreach ($gate in $rowFailures) {
    Add-Issue $issues $gate.severity "invocation_row_$($gate.gate)" $gate.evidence $gate.source
}

$rowStatus = if (@($rowFailures | Where-Object { $_.severity -eq "blocker" }).Count -gt 0) {
    "blocked"
} elseif (@($rowFailures).Count -gt 0) {
    "review_required"
} else {
    "preflight_valid_for_future_dry_run_adapter_design"
}

$invocationRows += [ordered]@{
    row_index = 0
    invocation_path_name = Normalize-String $contract.invocation_path_name
    implementation_kind = Normalize-String $contract.implementation_kind
    source_interface = Normalize-String $contract.source_interface
    transport_mode = Normalize-String $contract.transport_mode
    invocation_path_contract_hash = Normalize-String $invocation.preview.invocation_path_contract_hash
    row_status = $rowStatus
    gate_count = @($rowGates).Count
    failed_gate_count = @($rowFailures).Count
    blocker_count = @($rowFailures | Where-Object { $_.severity -eq "blocker" }).Count
    review_count = @($rowFailures | Where-Object { $_.severity -eq "review" }).Count
    request_field_count = @($contract.request_shape).Count
    result_field_count = @($contract.result_shape).Count
    network_transport_implemented = [bool]$contract.network_transport_implemented
    network_socket_opened = [bool]$contract.network_socket_opened
    bridge_post_call_implemented = $false
    would_open_socket = [bool]$contract.would_open_socket
    would_send_http_request = [bool]$contract.would_send_http_request
    would_call_bridge = [bool]$contract.would_call_bridge
    would_mutate_bridge = [bool]$contract.would_mutate_bridge
    would_mutate_platform = [bool]$contract.would_mutate_platform
    would_call_lacrm = [bool]$contract.would_call_lacrm
    execution_behavior = Normalize-String $contract.execution_behavior
    execute_live_behavior = Normalize-String $contract.execute_live_behavior
    gates = $rowGates
}

$statusCounts = @{}
foreach ($row in $invocationRows) {
    if (!$statusCounts.ContainsKey($row.row_status)) { $statusCounts[$row.row_status] = 0 }
    $statusCounts[$row.row_status] += 1
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$preflightStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "preflight_valid_for_future_dry_run_adapter_design"
} elseif ($blockerCount -eq 0) {
    "preflight_valid_with_review_items"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 21"
    purpose = "Bridge routing network transport dry-run invocation path preflight matrix"
    source_dry_run_invocation_validation = $validationPath
    source_dry_run_invocation_path = $invocationPath
    source_interface_scaffold_release_checkpoint = $releasePath
    source_interface_scaffold_operator_signoff = $signoffPath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_only = $true
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
        invocation_row_count = @($invocationRows).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        can_add_bridge_post_now = $false
        reason = if ($blockerCount -eq 0) {
            "Dry-run invocation path preflight has no hard blockers. Phase 20 Step 21 still implements no real transport and opens no socket."
        } else {
            "Dry-run invocation path preflight found blockers. Resolve blockers before any future network transport design."
        }
    }
    global_gates = $globalGates
    invocation_rows = $invocationRows
    issues = @($issues)
    runtime_status = [ordered]@{
        invocation_status_ok = $invocationStatus.ok
        invocation_status = if ($invocationStatus.ok) { $invocationStatus.value } else { $null }
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
        invocation_rows = @($invocationRows).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
        status_counts = $statusCounts
    }
    next_recommended_actions = @(
        "Review this preflight matrix before adding any real invocation-backed transport adapter.",
        "Do not call bridge POST endpoints from Phase 20 Step 21.",
        "Future network transport must remain disabled by default and preserve dry-run behavior.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix.json"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_global_gates.csv"
$rowsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_rows.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$globalGates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$invocationRows |
    Select-Object row_index, invocation_path_name, implementation_kind, source_interface, transport_mode, invocation_path_contract_hash, row_status, gate_count, failed_gate_count, blocker_count, review_count, request_field_count, result_field_count, network_transport_implemented, network_socket_opened, bridge_post_call_implemented, would_open_socket, would_send_http_request, would_call_bridge, would_mutate_bridge, would_mutate_platform, would_call_lacrm, execution_behavior, execute_live_behavior |
    Export-Csv -LiteralPath $rowsCsvPath -NoTypeInformation -Encoding UTF8

$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }
$statusText = if ($statusCounts.Count -gt 0) { ($statusCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Dry-run Invocation Path Preflight Matrix

Generated: $($report.generated_at)

Source dry-run invocation path validation:

``````
$validationPath
``````

Source dry-run invocation path report:

``````
$invocationPath
``````

## Safety

- Bridge routing network transport dry-run invocation path preflight matrix only: true
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
- Invocation rows: $($invocationRows.Count)
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
    Write-Host "PASS | bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix=$OutputDir | status=$preflightStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix=$OutputDir | status=$preflightStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Network transport dry-run invocation path preflight matrix files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
