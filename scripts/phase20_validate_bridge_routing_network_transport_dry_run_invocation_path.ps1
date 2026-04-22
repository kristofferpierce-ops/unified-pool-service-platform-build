param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
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

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($DryRunInvocationPathDir)) {
    $DryRunInvocationPathDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path.json"
}
if ([string]::IsNullOrWhiteSpace($InterfaceScaffoldReleaseCheckpointDir)) {
    $InterfaceScaffoldReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($InterfaceScaffoldOperatorSignoffDir)) {
    $InterfaceScaffoldOperatorSignoffDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff_*" -JsonName "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff.json" -Required $false
}

$invocationPath = Join-Path $DryRunInvocationPathDir "phase20_bridge_routing_network_transport_dry_run_invocation_path.json"
$releasePath = if (![string]::IsNullOrWhiteSpace($InterfaceScaffoldReleaseCheckpointDir)) { Join-Path $InterfaceScaffoldReleaseCheckpointDir "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint.json" } else { "" }
$signoffPath = if (![string]::IsNullOrWhiteSpace($InterfaceScaffoldOperatorSignoffDir)) { Join-Path $InterfaceScaffoldOperatorSignoffDir "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff.json" } else { "" }

if (!(Test-Path -LiteralPath $invocationPath)) {
    throw "Dry-run invocation path JSON not found: $invocationPath"
}

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
$gates = New-Object System.Collections.ArrayList

# Artifact-level safety gates.
Add-Gate $gates "dry_run_invocation_path_artifact_exists" $true "blocker" $invocationPath "dry_run_invocation_path"
Add-Gate $gates "invocation_path_is_invocation_only" ($invocation.safety.bridge_routing_network_transport_dry_run_invocation_path_only -eq $true) "blocker" "bridge_routing_network_transport_dry_run_invocation_path_only=$($invocation.safety.bridge_routing_network_transport_dry_run_invocation_path_only)" "dry_run_invocation_path"
Add-Gate $gates "invocation_path_has_no_real_http_client" ($invocation.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($invocation.safety.real_bridge_http_client_implemented)" "dry_run_invocation_path"
Add-Gate $gates "invocation_path_has_no_network_transport" ($invocation.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($invocation.safety.network_transport_implemented)" "dry_run_invocation_path"
Add-Gate $gates "invocation_path_has_no_network_transport_enabled" ($invocation.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($invocation.safety.network_transport_enabled)" "dry_run_invocation_path"
Add-Gate $gates "invocation_path_has_no_network_transport_armed" ($invocation.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($invocation.safety.network_transport_armed)" "dry_run_invocation_path"
Add-Gate $gates "invocation_path_has_no_socket_opened" ($invocation.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($invocation.safety.network_socket_opened)" "dry_run_invocation_path"
Add-Gate $gates "invocation_path_has_no_bridge_post_impl" ($invocation.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_call_implemented=$($invocation.safety.bridge_post_call_implemented)" "dry_run_invocation_path"
Add-Gate $gates "invocation_path_has_no_bridge_post_called" ($invocation.safety.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($invocation.safety.bridge_post_called)" "dry_run_invocation_path"
Add-Gate $gates "invocation_path_has_no_bridge_mutation" ($invocation.safety.bridge_mutation_performed -eq $false) "blocker" "bridge_mutation_performed=$($invocation.safety.bridge_mutation_performed)" "dry_run_invocation_path"
Add-Gate $gates "invocation_path_has_no_platform_mutation" ($invocation.safety.platform_db_mutation_performed -eq $false) "blocker" "platform_db_mutation_performed=$($invocation.safety.platform_db_mutation_performed)" "dry_run_invocation_path"
Add-Gate $gates "invocation_path_has_no_lacrm_call" ($invocation.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($invocation.safety.lacrm_call_performed)" "dry_run_invocation_path"
Add-Gate $gates "invocation_path_has_no_routing_write_endpoint" ($invocation.safety.routing_write_endpoint_implemented -eq $false) "blocker" "routing_write_endpoint_implemented=$($invocation.safety.routing_write_endpoint_implemented)" "dry_run_invocation_path"

foreach ($item in @($invocation.safety_errors)) {
    Add-Issue $issues "blocker" "source_invocation_path_safety_error" "$item" "dry_run_invocation_path"
}

# Preview-level gates.
$preview = $invocation.preview
$contract = $preview.invocation_path_contract
$sampleRequest = $preview.sample_request
$sampleResult = $preview.sample_result
$simulatedInvocation = $preview.simulated_invocation

Add-Gate $gates "preview_is_blocked" ($preview.blocked -eq $true) "blocker" "blocked=$($preview.blocked)" "preview"
Add-Gate $gates "preview_is_preview_only" ($preview.preview_only -eq $true) "blocker" "preview_only=$($preview.preview_only)" "preview"
Add-Gate $gates "preview_is_dry_run" ($preview.dry_run -eq $true) "blocker" "dry_run=$($preview.dry_run)" "preview"
Add-Gate $gates "preview_is_dry_run_invocation_path_only" ($preview.dry_run_invocation_path_only -eq $true) "blocker" "dry_run_invocation_path_only=$($preview.dry_run_invocation_path_only)" "preview"
Add-Gate $gates "preview_would_not_add_network_transport" ($preview.would_add_network_transport -eq $false) "blocker" "would_add_network_transport=$($preview.would_add_network_transport)" "preview"
Add-Gate $gates "preview_would_not_enable_network_transport" ($preview.would_enable_network_transport -eq $false) "blocker" "would_enable_network_transport=$($preview.would_enable_network_transport)" "preview"
Add-Gate $gates "preview_would_not_arm_network_transport" ($preview.would_arm_network_transport -eq $false) "blocker" "would_arm_network_transport=$($preview.would_arm_network_transport)" "preview"
Add-Gate $gates "preview_would_not_open_socket" ($preview.would_open_socket -eq $false) "blocker" "would_open_socket=$($preview.would_open_socket)" "preview"
Add-Gate $gates "preview_would_not_send_http_request" ($preview.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($preview.would_send_http_request)" "preview"
Add-Gate $gates "preview_would_not_call_bridge" ($preview.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($preview.would_call_bridge)" "preview"
Add-Gate $gates "preview_would_not_mutate_bridge" ($preview.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($preview.would_mutate_bridge)" "preview"
Add-Gate $gates "preview_would_not_mutate_platform" ($preview.would_mutate_platform -eq $false) "blocker" "would_mutate_platform=$($preview.would_mutate_platform)" "preview"
Add-Gate $gates "preview_would_not_call_lacrm" ($preview.would_call_lacrm -eq $false) "blocker" "would_call_lacrm=$($preview.would_call_lacrm)" "preview"

# Invocation contract gates.
Add-Gate $gates "contract_name_present" ((Normalize-String $contract.invocation_path_name) -eq "BridgeRoutingNetworkTransportDryRunInvocationPath") "blocker" "invocation_path_name=$($contract.invocation_path_name)" "contract"
Add-Gate $gates "contract_kind_dry_run_invocation_only" ((Normalize-String $contract.implementation_kind) -eq "dry_run_invocation_path_only") "blocker" "implementation_kind=$($contract.implementation_kind)" "contract"
Add-Gate $gates "contract_source_interface_present" ((Normalize-String $contract.source_interface) -eq "BridgeRoutingTransportAdapterInterface") "blocker" "source_interface=$($contract.source_interface)" "contract"
Add-Gate $gates "contract_transport_mode_no_network" ((Normalize-String $contract.transport_mode) -eq "dry_run_no_network") "blocker" "transport_mode=$($contract.transport_mode)" "contract"
Add-Gate $gates "contract_execution_behavior_no_network" ((Normalize-String $contract.execution_behavior) -eq "returns_simulated_result_no_network") "blocker" "execution_behavior=$($contract.execution_behavior)" "contract"
Add-Gate $gates "contract_live_behavior_not_available" ((Normalize-String $contract.execute_live_behavior) -eq "not_available") "blocker" "execute_live_behavior=$($contract.execute_live_behavior)" "contract"
Add-Gate $gates "contract_no_network_transport" ($contract.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($contract.network_transport_implemented)" "contract"
Add-Gate $gates "contract_no_network_enabled" ($contract.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($contract.network_transport_enabled)" "contract"
Add-Gate $gates "contract_no_network_armed" ($contract.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($contract.network_transport_armed)" "contract"
Add-Gate $gates "contract_no_socket_opened" ($contract.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($contract.network_socket_opened)" "contract"
Add-Gate $gates "contract_would_not_open_socket" ($contract.would_open_socket -eq $false) "blocker" "would_open_socket=$($contract.would_open_socket)" "contract"
Add-Gate $gates "contract_would_not_send_http_request" ($contract.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($contract.would_send_http_request)" "contract"
Add-Gate $gates "contract_would_not_call_bridge" ($contract.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($contract.would_call_bridge)" "contract"
Add-Gate $gates "contract_would_not_mutate_bridge" ($contract.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($contract.would_mutate_bridge)" "contract"
Add-Gate $gates "contract_would_not_mutate_platform" ($contract.would_mutate_platform -eq $false) "blocker" "would_mutate_platform=$($contract.would_mutate_platform)" "contract"
Add-Gate $gates "contract_would_not_call_lacrm" ($contract.would_call_lacrm -eq $false) "blocker" "would_call_lacrm=$($contract.would_call_lacrm)" "contract"
Add-Gate $gates "contract_has_hash" (![string]::IsNullOrWhiteSpace((Normalize-String $preview.invocation_path_contract_hash))) "blocker" "invocation_path_contract_hash=$($preview.invocation_path_contract_hash)" "contract"

foreach ($field in @("phone", "mode", "owner_type", "label", "default_contact_ids", "notes", "idempotency_key")) {
    Add-Gate $gates "request_shape_has_$field" (@($contract.request_shape) -contains $field) "blocker" "request field $field" "contract"
}

foreach ($field in @("ok", "status_code", "transport_mode", "invocation_kind", "would_open_socket", "would_send_http_request", "would_call_bridge", "would_mutate_bridge", "would_mutate_platform", "would_call_lacrm", "message")) {
    Add-Gate $gates "result_shape_has_$field" (@($contract.result_shape) -contains $field) "blocker" "result field $field" "contract"
}

foreach ($gateName in @("audit_prerequisite_gate", "rollback_snapshot_gate", "environment_gate_design", "operator_confirmation_gate", "response_capture_design", "future_cutover_packet_prerequisite")) {
    Add-Gate $gates "required_future_gate_$gateName" (@($contract.required_future_gates) -contains $gateName) "blocker" "future gate $gateName" "contract"
}

# Sample and simulated result gates.
Add-Gate $gates "sample_request_mode_dry_run" ((Normalize-String $sampleRequest.mode) -eq "dry_run") "blocker" "mode=$($sampleRequest.mode)" "sample"
Add-Gate $gates "sample_request_has_idempotency_key" (![string]::IsNullOrWhiteSpace((Normalize-String $sampleRequest.idempotency_key))) "blocker" "idempotency_key=$($sampleRequest.idempotency_key)" "sample"
Add-Gate $gates "sample_result_not_ok" ($sampleResult.ok -eq $false) "blocker" "ok=$($sampleResult.ok)" "sample"
Add-Gate $gates "sample_result_status_code_zero" ([int]$sampleResult.status_code -eq 0) "blocker" "status_code=$($sampleResult.status_code)" "sample"
Add-Gate $gates "sample_result_mode_no_network" ((Normalize-String $sampleResult.transport_mode) -eq "dry_run_no_network") "blocker" "transport_mode=$($sampleResult.transport_mode)" "sample"
Add-Gate $gates "sample_result_invocation_kind" ((Normalize-String $sampleResult.invocation_kind) -eq "dry_run_invocation_path_only") "blocker" "invocation_kind=$($sampleResult.invocation_kind)" "sample"
Add-Gate $gates "sample_result_would_not_open_socket" ($sampleResult.would_open_socket -eq $false) "blocker" "would_open_socket=$($sampleResult.would_open_socket)" "sample"
Add-Gate $gates "sample_result_would_not_send_http_request" ($sampleResult.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($sampleResult.would_send_http_request)" "sample"
Add-Gate $gates "sample_result_would_not_call_bridge" ($sampleResult.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($sampleResult.would_call_bridge)" "sample"
Add-Gate $gates "sample_result_would_not_mutate_bridge" ($sampleResult.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($sampleResult.would_mutate_bridge)" "sample"
Add-Gate $gates "sample_result_would_not_mutate_platform" ($sampleResult.would_mutate_platform -eq $false) "blocker" "would_mutate_platform=$($sampleResult.would_mutate_platform)" "sample"
Add-Gate $gates "sample_result_would_not_call_lacrm" ($sampleResult.would_call_lacrm -eq $false) "blocker" "would_call_lacrm=$($sampleResult.would_call_lacrm)" "sample"

Add-Gate $gates "simulated_invocation_status_code_zero" ([int]$simulatedInvocation.status_code -eq 0) "blocker" "status_code=$($simulatedInvocation.status_code)" "simulated_invocation"
Add-Gate $gates "simulated_invocation_not_ok" ($simulatedInvocation.ok -eq $false) "blocker" "ok=$($simulatedInvocation.ok)" "simulated_invocation"
Add-Gate $gates "simulated_invocation_no_network_mode" ((Normalize-String $simulatedInvocation.transport_mode) -eq "dry_run_no_network") "blocker" "transport_mode=$($simulatedInvocation.transport_mode)" "simulated_invocation"
Add-Gate $gates "simulated_invocation_would_not_open_socket" ($simulatedInvocation.would_open_socket -eq $false) "blocker" "would_open_socket=$($simulatedInvocation.would_open_socket)" "simulated_invocation"
Add-Gate $gates "simulated_invocation_would_not_send_http_request" ($simulatedInvocation.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($simulatedInvocation.would_send_http_request)" "simulated_invocation"
Add-Gate $gates "simulated_invocation_would_not_call_bridge" ($simulatedInvocation.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($simulatedInvocation.would_call_bridge)" "simulated_invocation"
Add-Gate $gates "simulated_invocation_would_not_mutate_bridge" ($simulatedInvocation.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($simulatedInvocation.would_mutate_bridge)" "simulated_invocation"
Add-Gate $gates "simulated_invocation_would_not_mutate_platform" ($simulatedInvocation.would_mutate_platform -eq $false) "blocker" "would_mutate_platform=$($simulatedInvocation.would_mutate_platform)" "simulated_invocation"

# Optional upstream artifacts.
if ($release -ne $null) {
    Add-Gate $gates "interface_release_checkpoint_present" $true "review" $releasePath "interface_release_checkpoint"
    Add-Gate $gates "interface_release_has_no_network_transport" ($release.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($release.safety.network_transport_implemented)" "interface_release_checkpoint"
    Add-Gate $gates "interface_release_has_no_socket" ($release.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($release.safety.network_socket_opened)" "interface_release_checkpoint"
    Add-Gate $gates "interface_release_has_no_bridge_post" ($release.safety.bridge_post_called -eq $false -and $release.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($release.safety.bridge_post_called); bridge_post_call_implemented=$($release.safety.bridge_post_call_implemented)" "interface_release_checkpoint"
    Add-Gate $gates "interface_release_blocks_execution" ($release.release_checkpoint.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($release.release_checkpoint.can_execute_bridge_write_now)" "interface_release_checkpoint"
    Add-Gate $gates "interface_release_blocks_bridge_post" ($release.release_checkpoint.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($release.release_checkpoint.can_add_bridge_post_now)" "interface_release_checkpoint"
} else {
    Add-Gate $gates "interface_release_checkpoint_present" $false "review" "Phase 20 Step 18 interface scaffold release checkpoint not found." "interface_release_checkpoint"
}

if ($signoff -ne $null) {
    Add-Gate $gates "interface_operator_signoff_present" $true "review" $signoffPath "interface_operator_signoff"
    Add-Gate $gates "interface_signoff_has_no_network_transport" ($signoff.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($signoff.safety.network_transport_implemented)" "interface_operator_signoff"
    Add-Gate $gates "interface_signoff_has_no_socket" ($signoff.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($signoff.safety.network_socket_opened)" "interface_operator_signoff"
    Add-Gate $gates "interface_signoff_blocks_bridge_post" ($signoff.signoff.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($signoff.signoff.can_add_bridge_post_now)" "interface_operator_signoff"
    Add-Gate $gates "interface_signoff_not_bridge_post_approved" ($signoff.signoff.approved_to_add_bridge_post -ne $true) "blocker" "approved_to_add_bridge_post=$($signoff.signoff.approved_to_add_bridge_post)" "interface_operator_signoff"
} else {
    Add-Gate $gates "interface_operator_signoff_present" $false "review" "Phase 20 Step 17 operator signoff not found." "interface_operator_signoff"
}

# Runtime checks. Unreachable runtime is review-level because artifact validation remains useful offline.
if ($invocationStatus.ok) {
    Add-Gate $gates "runtime_invocation_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status" "runtime"
    Add-Gate $gates "runtime_invocation_no_network_transport" ($invocationStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($invocationStatus.value.network_transport_implemented)" "runtime"
    Add-Gate $gates "runtime_invocation_no_socket" ($invocationStatus.value.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($invocationStatus.value.network_socket_opened)" "runtime"
    Add-Gate $gates "runtime_invocation_no_bridge_post" ($invocationStatus.value.bridge_post_called -eq $false -and $invocationStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($invocationStatus.value.bridge_post_called); bridge_post_call_implemented=$($invocationStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_invocation_status_readable" $false "review" $invocationStatus.error "runtime"
}

if ($scaffoldStatus.ok) {
    Add-Gate $gates "runtime_scaffold_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status" "runtime"
    Add-Gate $gates "runtime_scaffold_no_network_transport" ($scaffoldStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($scaffoldStatus.value.network_transport_implemented)" "runtime"
    Add-Gate $gates "runtime_scaffold_no_socket" ($scaffoldStatus.value.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($scaffoldStatus.value.network_socket_opened)" "runtime"
} else {
    Add-Gate $gates "runtime_scaffold_status_readable" $false "review" $scaffoldStatus.error "runtime"
}

if ($adapterStatus.ok) {
    Add-Gate $gates "runtime_adapter_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status" "runtime"
    Add-Gate $gates "runtime_adapter_no_network_transport" ($adapterStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($adapterStatus.value.network_transport_implemented)" "runtime"
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
    "valid_dry_run_invocation_path"
} elseif ($blockerCount -eq 0) {
    "valid_with_review_items"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 20"
    purpose = "Bridge routing network transport dry-run invocation path validation"
    source_dry_run_invocation_path = $invocationPath
    source_interface_scaffold_release_checkpoint = $releasePath
    source_interface_scaffold_operator_signoff = $signoffPath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_dry_run_invocation_path_validation_only = $true
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
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        can_add_bridge_post_now = $false
        reason = if ($blockerCount -eq 0) {
            "Dry-run invocation path is structurally valid for review. Phase 20 Step 20 still implements no real network transport."
        } else {
            "Dry-run invocation path validation found blockers. Resolve blockers before any future real transport design."
        }
    }
    gates = @($gates)
    issues = @($issues)
    invocation_path_contract = $contract
    sample_request = $sampleRequest
    sample_result = $sampleResult
    simulated_invocation = $simulatedInvocation
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
        gates = @($gates).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
        request_fields = @($contract.request_shape).Count
        result_fields = @($contract.result_shape).Count
    }
    next_recommended_actions = @(
        "Review this validation before adding any future transport adapter.",
        "Do not call bridge POST endpoints from Phase 20 Step 20.",
        "Do not add requests/httpx bridge calls or open sockets in this step.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation.json"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation_issues.csv"
$contractCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation_contract.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

@(
    [ordered]@{
        invocation_path_name = $contract.invocation_path_name
        implementation_kind = $contract.implementation_kind
        source_interface = $contract.source_interface
        transport_mode = $contract.transport_mode
        execution_behavior = $contract.execution_behavior
        execute_live_behavior = $contract.execute_live_behavior
        network_transport_implemented = $contract.network_transport_implemented
        network_socket_opened = $contract.network_socket_opened
        would_open_socket = $contract.would_open_socket
        would_send_http_request = $contract.would_send_http_request
        would_call_bridge = $contract.would_call_bridge
        bridge_post_called = $false
        contract_hash = $preview.invocation_path_contract_hash
    }
) | Export-Csv -LiteralPath $contractCsvPath -NoTypeInformation -Encoding UTF8

$gateText = (@($gates) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.gate): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Dry-run Invocation Path Validation

Generated: $($report.generated_at)

Source dry-run invocation path report:

``````
$invocationPath
``````

## Safety

- Bridge routing network transport dry-run invocation path validation only: true
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
- Can enable network transport now: false
- Can arm network transport now: false
- Can open network socket now: false
- Can add real bridge HTTP client now: false
- Can add bridge POST now: false

## Gates

$gateText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_dry_run_invocation_path_validation=$OutputDir | status=$validationStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_dry_run_invocation_path_validation=$OutputDir | status=$validationStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Dry-run invocation path validation files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
