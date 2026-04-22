param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$ResponseCaptureGateDesignDir = "",
    [string]$OperatorConfirmationGateDesignDir = "",
    [string]$EnvironmentGateDesignDir = "",
    [string]$RollbackSnapshotPrerequisiteGateDir = "",
    [string]$AuditPrerequisiteGateDir = "",
    [string]$DryRunInvocationReleaseCheckpointDir = "",
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

function Get-FileSha256 {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
    if (!(Test-Path -LiteralPath $Path)) { return "" }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
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

function Add-Requirement {
    param(
        [System.Collections.ArrayList]$Requirements,
        [string]$Category,
        [string]$FieldName,
        [string]$RequiredValue,
        [string]$FutureLiveRequirement,
        [string]$Reason,
        [bool]$ImplementedNow = $false,
        [bool]$AllowsLiveWriteNow = $false
    )

    [void]$Requirements.Add([ordered]@{
        category = $Category
        field_name = $FieldName
        required_value = $RequiredValue
        future_live_requirement = $FutureLiveRequirement
        reason = $Reason
        implemented_now = $ImplementedNow
        allows_live_write_now = $AllowsLiveWriteNow
    })
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($ResponseCaptureGateDesignDir)) {
    $ResponseCaptureGateDesignDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_response_capture_gate_design_*" -JsonName "phase20_bridge_routing_network_transport_response_capture_gate_design.json"
}
if ([string]::IsNullOrWhiteSpace($OperatorConfirmationGateDesignDir)) {
    $OperatorConfirmationGateDesignDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_*" -JsonName "phase20_bridge_routing_network_transport_operator_confirmation_gate_design.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($EnvironmentGateDesignDir)) {
    $EnvironmentGateDesignDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_environment_gate_design_*" -JsonName "phase20_bridge_routing_network_transport_environment_gate_design.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($RollbackSnapshotPrerequisiteGateDir)) {
    $RollbackSnapshotPrerequisiteGateDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_*" -JsonName "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($AuditPrerequisiteGateDir)) {
    $AuditPrerequisiteGateDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_audit_prerequisite_gate_*" -JsonName "phase20_bridge_routing_network_transport_audit_prerequisite_gate.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($DryRunInvocationReleaseCheckpointDir)) {
    $DryRunInvocationReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json" -Required $false
}

$responsePath = Join-Path $ResponseCaptureGateDesignDir "phase20_bridge_routing_network_transport_response_capture_gate_design.json"
$operatorPath = if (![string]::IsNullOrWhiteSpace($OperatorConfirmationGateDesignDir)) { Join-Path $OperatorConfirmationGateDesignDir "phase20_bridge_routing_network_transport_operator_confirmation_gate_design.json" } else { "" }
$environmentPath = if (![string]::IsNullOrWhiteSpace($EnvironmentGateDesignDir)) { Join-Path $EnvironmentGateDesignDir "phase20_bridge_routing_network_transport_environment_gate_design.json" } else { "" }
$rollbackPath = if (![string]::IsNullOrWhiteSpace($RollbackSnapshotPrerequisiteGateDir)) { Join-Path $RollbackSnapshotPrerequisiteGateDir "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.json" } else { "" }
$auditPath = if (![string]::IsNullOrWhiteSpace($AuditPrerequisiteGateDir)) { Join-Path $AuditPrerequisiteGateDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($DryRunInvocationReleaseCheckpointDir)) { Join-Path $DryRunInvocationReleaseCheckpointDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $responsePath)) {
    throw "Response capture gate design JSON not found: $responsePath"
}

$response = Read-JsonFile $responsePath
$operator = if (![string]::IsNullOrWhiteSpace($operatorPath) -and (Test-Path -LiteralPath $operatorPath)) { Read-JsonFile $operatorPath } else { $null }
$environment = if (![string]::IsNullOrWhiteSpace($environmentPath) -and (Test-Path -LiteralPath $environmentPath)) { Read-JsonFile $environmentPath } else { $null }
$rollback = if (![string]::IsNullOrWhiteSpace($rollbackPath) -and (Test-Path -LiteralPath $rollbackPath)) { Read-JsonFile $rollbackPath } else { $null }
$audit = if (![string]::IsNullOrWhiteSpace($auditPath) -and (Test-Path -LiteralPath $auditPath)) { Read-JsonFile $auditPath } else { $null }
$release = if (![string]::IsNullOrWhiteSpace($releasePath) -and (Test-Path -LiteralPath $releasePath)) { Read-JsonFile $releasePath } else { $null }

$invocationStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$gates = New-Object System.Collections.ArrayList
$requirements = New-Object System.Collections.ArrayList

# Source response capture gate safety.
Add-Gate $gates "response_capture_gate_design_exists" $true "blocker" $responsePath "response_capture_gate_design"
Add-Gate $gates "response_capture_is_design_only" ($response.safety.bridge_routing_network_transport_response_capture_gate_design_only -eq $true) "blocker" "bridge_routing_network_transport_response_capture_gate_design_only=$($response.safety.bridge_routing_network_transport_response_capture_gate_design_only)" "response_capture_gate_design"
Add-Gate $gates "response_capture_bridge_get_only" ($response.safety.bridge_get_only -eq $true) "blocker" "bridge_get_only=$($response.safety.bridge_get_only)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_bridge_response" ($response.safety.bridge_response_captured -eq $false) "blocker" "bridge_response_captured=$($response.safety.bridge_response_captured)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_response_record" ($response.safety.response_capture_record_created -eq $false) "blocker" "response_capture_record_created=$($response.safety.response_capture_record_created)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_operator_approval" ($response.safety.operator_approval_recorded -eq $false) "blocker" "operator_approval_recorded=$($response.safety.operator_approval_recorded)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_confirmation_record" ($response.safety.confirmation_record_created -eq $false) "blocker" "confirmation_record_created=$($response.safety.confirmation_record_created)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_environment_variables_set" ($response.safety.environment_variables_set -eq $false) "blocker" "environment_variables_set=$($response.safety.environment_variables_set)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_rollback_snapshot" ($response.safety.rollback_snapshot_created -eq $false) "blocker" "rollback_snapshot_created=$($response.safety.rollback_snapshot_created)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_rollback_row" ($response.safety.rollback_row_created -eq $false) "blocker" "rollback_row_created=$($response.safety.rollback_row_created)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_audit_row" ($response.safety.audit_row_created -eq $false) "blocker" "audit_row_created=$($response.safety.audit_row_created)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_network_transport" ($response.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($response.safety.network_transport_implemented)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_network_enabled" ($response.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($response.safety.network_transport_enabled)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_network_armed" ($response.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($response.safety.network_transport_armed)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_socket" ($response.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($response.safety.network_socket_opened)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_real_http_client" ($response.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($response.safety.real_bridge_http_client_implemented)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_bridge_post" ($response.safety.bridge_post_called -eq $false -and $response.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($response.safety.bridge_post_called); bridge_post_call_implemented=$($response.safety.bridge_post_call_implemented)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_mutation" ($response.safety.platform_db_mutation_performed -eq $false -and $response.safety.bridge_mutation_performed -eq $false) "blocker" "platform_db_mutation=$($response.safety.platform_db_mutation_performed); bridge_mutation=$($response.safety.bridge_mutation_performed)" "response_capture_gate_design"
Add-Gate $gates "response_capture_no_lacrm" ($response.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($response.safety.lacrm_call_performed)" "response_capture_gate_design"
Add-Gate $gates "response_capture_blocks_execution" ($response.response_capture_gate_design.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($response.response_capture_gate_design.can_execute_bridge_write_now)" "response_capture_gate_design"
Add-Gate $gates "response_capture_blocks_network_transport" ($response.response_capture_gate_design.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($response.response_capture_gate_design.can_add_network_transport_now)" "response_capture_gate_design"
Add-Gate $gates "response_capture_blocks_socket" ($response.response_capture_gate_design.can_open_network_socket_now -eq $false) "blocker" "can_open_network_socket_now=$($response.response_capture_gate_design.can_open_network_socket_now)" "response_capture_gate_design"
Add-Gate $gates "response_capture_blocks_bridge_post" ($response.response_capture_gate_design.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($response.response_capture_gate_design.can_add_bridge_post_now)" "response_capture_gate_design"
Add-Gate $gates "response_capture_blocks_response_capture" ($response.response_capture_gate_design.can_capture_bridge_response_now -eq $false) "blocker" "can_capture_bridge_response_now=$($response.response_capture_gate_design.can_capture_bridge_response_now)" "response_capture_gate_design"
Add-Gate $gates "response_capture_blocks_response_records" ($response.response_capture_gate_design.can_create_response_capture_records_now -eq $false) "blocker" "can_create_response_capture_records_now=$($response.response_capture_gate_design.can_create_response_capture_records_now)" "response_capture_gate_design"
Add-Gate $gates "response_capture_has_no_blockers" ([int]$response.response_capture_gate_design.blocker_count -eq 0) "blocker" "blocker_count=$($response.response_capture_gate_design.blocker_count)" "response_capture_gate_design"

foreach ($issue in @($response.issues)) {
    if ($issue.severity -eq "blocker") {
        Add-Issue $issues "blocker" "response_capture_$($issue.code)" "$($issue.message)" "response_capture_gate_design"
    } elseif ($issue.severity -eq "review") {
        Add-Issue $issues "review" "response_capture_$($issue.code)" "$($issue.message)" "response_capture_gate_design"
    }
}

# Optional upstream evidence.
if ($operator -ne $null) {
    Add-Gate $gates "operator_confirmation_gate_design_present" $true "review" $operatorPath "operator_confirmation_gate_design"
    Add-Gate $gates "operator_confirmation_blocks_approval_records" ($operator.operator_confirmation_gate_design.can_record_operator_approval_now -eq $false) "blocker" "can_record_operator_approval_now=$($operator.operator_confirmation_gate_design.can_record_operator_approval_now)" "operator_confirmation_gate_design"
    Add-Gate $gates "operator_confirmation_blocks_confirmation_records" ($operator.operator_confirmation_gate_design.can_create_confirmation_records_now -eq $false) "blocker" "can_create_confirmation_records_now=$($operator.operator_confirmation_gate_design.can_create_confirmation_records_now)" "operator_confirmation_gate_design"
} else {
    Add-Gate $gates "operator_confirmation_gate_design_present" $false "review" "Phase 20 Step 27 operator confirmation gate design not found." "operator_confirmation_gate_design"
}

if ($environment -ne $null) {
    Add-Gate $gates "environment_gate_design_present" $true "review" $environmentPath "environment_gate_design"
    Add-Gate $gates "environment_gate_blocks_env_setting" ($environment.environment_gate_design.can_set_environment_variables_now -eq $false) "blocker" "can_set_environment_variables_now=$($environment.environment_gate_design.can_set_environment_variables_now)" "environment_gate_design"
} else {
    Add-Gate $gates "environment_gate_design_present" $false "review" "Phase 20 Step 26 environment gate design not found." "environment_gate_design"
}

if ($rollback -ne $null) {
    Add-Gate $gates "rollback_snapshot_prerequisite_gate_present" $true "review" $rollbackPath "rollback_snapshot_prerequisite_gate"
    Add-Gate $gates "rollback_gate_blocks_snapshots" ($rollback.rollback_snapshot_prerequisite_gate.can_create_rollback_snapshots_now -eq $false) "blocker" "can_create_rollback_snapshots_now=$($rollback.rollback_snapshot_prerequisite_gate.can_create_rollback_snapshots_now)" "rollback_snapshot_prerequisite_gate"
} else {
    Add-Gate $gates "rollback_snapshot_prerequisite_gate_present" $false "review" "Phase 20 Step 25 rollback prerequisite gate not found." "rollback_snapshot_prerequisite_gate"
}

if ($audit -ne $null) {
    Add-Gate $gates "audit_prerequisite_gate_present" $true "review" $auditPath "audit_prerequisite_gate"
    Add-Gate $gates "audit_gate_blocks_audit_rows" ($audit.audit_prerequisite_gate.can_create_audit_rows_now -eq $false) "blocker" "can_create_audit_rows_now=$($audit.audit_prerequisite_gate.can_create_audit_rows_now)" "audit_prerequisite_gate"
} else {
    Add-Gate $gates "audit_prerequisite_gate_present" $false "review" "Phase 20 Step 24 audit prerequisite gate not found." "audit_prerequisite_gate"
}

if ($release -ne $null) {
    Add-Gate $gates "dry_run_release_checkpoint_present" $true "review" $releasePath "dry_run_release_checkpoint"
    Add-Gate $gates "dry_run_release_blocks_execution" ($release.release_checkpoint.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($release.release_checkpoint.can_execute_bridge_write_now)" "dry_run_release_checkpoint"
} else {
    Add-Gate $gates "dry_run_release_checkpoint_present" $false "review" "Phase 20 Step 23 dry-run release checkpoint not found." "dry_run_release_checkpoint"
}

# Runtime checks. Unreachable runtime is review-level; contradictions are blockers.
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
    Add-Gate $gates "runtime_executor_no_bridge_post_impl" ($executorStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_call_implemented=$($executorStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_executor_status_readable" $false "review" $executorStatus.error "runtime"
}

Add-Gate $gates "runtime_bridge_health_readable" $bridgeHealth.ok "review" $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "runtime"

# Future cutover packet prerequisite gate design requirements only. Step 29 does not create a cutover packet.
Add-Requirement $requirements "identity" "cutover_packet_id" "required" "stable id for every future cutover packet" "Allows the final future packet to be referenced by audit, rollback, response, and operator confirmation evidence."
Add-Requirement $requirements "identity" "cutover_packet_version" "required" "schema version must be explicit" "Makes future packet structure reviewable."
Add-Requirement $requirements "identity" "transport_execution_id" "required" "must match future transport execution id" "Prevents cutover evidence from being disconnected from execution evidence."
Add-Requirement $requirements "source" "source_artifact_hashes" "required" "must include Step 23 through Step 29 evidence hashes" "Binds future cutover approval to reviewed artifacts."
Add-Requirement $requirements "source" "dry_run_release_checkpoint_hash" "required" "must match the reviewed dry-run invocation release checkpoint" "Prevents cutover from skipping the dry-run evidence chain."
Add-Requirement $requirements "gate" "audit_prerequisite_gate_status" "required clean or reviewed" "must be recorded before future live approval" "Ensures audit prerequisites are visible."
Add-Requirement $requirements "gate" "rollback_snapshot_prerequisite_gate_status" "required clean or reviewed" "must be recorded before future live approval" "Ensures rollback prerequisites are visible."
Add-Requirement $requirements "gate" "environment_gate_status" "required clean or reviewed" "must be recorded before future live approval" "Ensures environment requirements are visible."
Add-Requirement $requirements "gate" "operator_confirmation_gate_status" "required clean or reviewed" "must be recorded before future live approval" "Ensures operator confirmation requirements are visible."
Add-Requirement $requirements "gate" "response_capture_gate_status" "required clean or reviewed" "must be recorded before future live approval" "Ensures response capture requirements are visible."
Add-Requirement $requirements "operator" "cutover_operator_name" "required" "non-empty operator name required" "Connects future cutover approval to a human operator."
Add-Requirement $requirements "operator" "cutover_operator_role" "required" "operator role must be recorded" "Supports review of authority for a future live change."
Add-Requirement $requirements "operator" "cutover_confirmation_phrase" "required" "must match WRITE BRIDGE ROUTING LIVE for future live write" "Separates final cutover from design-only approval."
Add-Requirement $requirements "timing" "cutover_window_start" "required" "must be within approved operator window" "Prevents stale or unscheduled future live write attempts."
Add-Requirement $requirements "timing" "cutover_window_end" "required" "must bound the future cutover window" "Prevents indefinite cutover authorization."
Add-Requirement $requirements "request" "canonical_request_hash" "required" "must match future request that will be sent" "Prevents approving one request while sending another."
Add-Requirement $requirements "request" "idempotency_key" "required" "must be stable and unique for future live execution" "Prevents duplicate bridge writes."
Add-Requirement $requirements "network" "bridge_base_url" "required" "must be explicit and approved" "Prevents implicit bridge destinations."
Add-Requirement $requirements "network" "bridge_allowed_host_match" "required true" "host must be in approved allow-list" "Prevents transport to arbitrary hosts."
Add-Requirement $requirements "network" "network_transport_enabled" "required false until final future step" "must remain false in prerequisite design" "Preserves disabled default."
Add-Requirement $requirements "network" "network_transport_armed" "required false until final future step" "must remain false in prerequisite design" "Preserves two-gate arming."
Add-Requirement $requirements "network" "network_socket_opened" "required false until future live execution" "must be recorded accurately" "Makes network boundary crossing explicit."
Add-Requirement $requirements "bridge" "bridge_post_called" "required false until future live execution" "must be recorded accurately" "Makes bridge mutation boundary explicit."
Add-Requirement $requirements "audit" "audit_row_id" "required before future execution" "must exist before future live bridge POST" "Ensures execution is auditable."
Add-Requirement $requirements "rollback" "rollback_snapshot_id" "required before future execution" "must exist before future live bridge POST" "Ensures rollback readiness."
Add-Requirement $requirements "response" "response_capture_plan_hash" "required before future execution" "must exist before future live bridge POST" "Ensures response capture readiness."
Add-Requirement $requirements "rollback" "rollback_plan_hash" "required before future execution" "must exist before future live bridge POST" "Ensures rollback plan is known."
Add-Requirement $requirements "review" "final_operator_summary_preview" "required" "operator must see final preview before future approval" "Gives a final human review of action, risk, evidence, and rollback readiness."
Add-Requirement $requirements "review" "cutover_packet_append_only" "true" "future cutover packets must be append-only" "Prevents cutover evidence from being overwritten."
Add-Requirement $requirements "boundary" "phase20_step29_cutover_packet_not_created" "true" "Step 29 must not create or approve a cutover packet" "This step is only a cutover packet prerequisite gate design." $false $false

Add-Gate $gates "cutover_packet_requirement_count_minimum" (@($requirements).Count -ge 24) "blocker" "requirements=$(@($requirements).Count)" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "cutover_packet_not_created" $true "blocker" "cutover_packet_created=False" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "cutover_approval_not_recorded" $true "blocker" "cutover_approval_recorded=False" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "bridge_response_not_captured" $true "blocker" "bridge_response_captured=False" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "response_capture_records_not_created" $true "blocker" "response_capture_record_created=False" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "operator_approvals_not_recorded" $true "blocker" "operator_approval_recorded=False" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "confirmation_records_not_created" $true "blocker" "confirmation_record_created=False" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "environment_variables_not_set" $true "blocker" "environment_variables_set=False" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "cutover_gate_no_audit_rows" $true "blocker" "audit_row_created=False" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "cutover_gate_no_rollback_rows" $true "blocker" "rollback_row_created=False" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "cutover_gate_no_rollback_snapshots" $true "blocker" "rollback_snapshot_created=False" "cutover_packet_prerequisite_gate_design"

# Convert failed gates into issues.
foreach ($gate in @($gates)) {
    if ($gate.passed -ne $true) {
        Add-Issue $issues $gate.severity $gate.gate $gate.evidence $gate.source
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$gateStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "cutover_packet_prerequisite_gate_design_ready_for_review_no_write"
} elseif ($blockerCount -eq 0) {
    "cutover_packet_prerequisite_gate_design_review_required_no_write"
} else {
    "cutover_packet_prerequisite_gate_design_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="response_capture_gate_design"; json_path=$responsePath; sha256=Get-FileSha256 $responsePath },
    [ordered]@{ key="operator_confirmation_gate_design"; json_path=$operatorPath; sha256=Get-FileSha256 $operatorPath },
    [ordered]@{ key="environment_gate_design"; json_path=$environmentPath; sha256=Get-FileSha256 $environmentPath },
    [ordered]@{ key="rollback_snapshot_prerequisite_gate"; json_path=$rollbackPath; sha256=Get-FileSha256 $rollbackPath },
    [ordered]@{ key="audit_prerequisite_gate"; json_path=$auditPath; sha256=Get-FileSha256 $auditPath },
    [ordered]@{ key="dry_run_invocation_path_release_checkpoint"; json_path=$releasePath; sha256=Get-FileSha256 $releasePath }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 29"
    purpose = "Bridge routing network transport cutover packet prerequisite gate design"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_cutover_packet_prerequisite_gate_design_only = $true
        bridge_get_only = $true
        cutover_packet_created = $false
        cutover_approval_recorded = $false
        bridge_response_captured = $false
        response_capture_record_created = $false
        operator_approval_recorded = $false
        confirmation_record_created = $false
        environment_variables_set = $false
        audit_row_created = $false
        rollback_row_created = $false
        rollback_snapshot_created = $false
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
    cutover_packet_prerequisite_gate_design = [ordered]@{
        status = $gateStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        gate_count = @($gates).Count
        requirement_count = @($requirements).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        can_add_bridge_post_now = $false
        can_create_cutover_packet_now = $false
        can_record_cutover_approval_now = $false
        can_capture_bridge_response_now = $false
        can_create_response_capture_records_now = $false
        can_record_operator_approval_now = $false
        can_create_confirmation_records_now = $false
        can_set_environment_variables_now = $false
        can_create_audit_rows_now = $false
        can_create_rollback_rows_now = $false
        can_create_rollback_snapshots_now = $false
        reason = if ($blockerCount -eq 0) {
            "Cutover packet prerequisite gate design is ready for review. Phase 20 Step 29 creates no cutover packet, opens no socket, calls no bridge POST, and authorizes no execution."
        } else {
            "Cutover packet prerequisite gate design has blockers. Resolve blockers before any future real network transport design."
        }
    }
    source_artifacts = $sourceArtifacts
    cutover_packet_requirements = @($requirements)
    gates = @($gates)
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
        source_artifacts = @($sourceArtifacts).Count
        cutover_packet_requirements = @($requirements).Count
        gates = @($gates).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this cutover packet prerequisite gate design before implementing any future cutover packet records.",
        "Do not create cutover packets from Phase 20 Step 29.",
        "Do not capture bridge responses from Phase 20 Step 29.",
        "Do not record operator approvals from Phase 20 Step 29.",
        "Do not set environment variables from Phase 20 Step 29.",
        "Do not create audit rows or rollback snapshots from Phase 20 Step 29.",
        "Do not call bridge POST endpoints from Phase 20 Step 29.",
        "Future real transport work must prove audit, rollback, environment, operator confirmation, response capture, and cutover prerequisites before execution.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design.json"
$requirementsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design_requirements.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design_artifacts.csv"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$requirements | Export-Csv -LiteralPath $requirementsCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$requirementText = (@($requirements) | ForEach-Object { "- [$($_.category)] $($_.field_name): required=$($_.required_value); future=$($_.future_live_requirement); implemented now=$($_.implemented_now)" }) -join "`n"
$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Cutover Packet Prerequisite Gate Design

Generated: $($report.generated_at)

Source response capture gate design:

``````
$responsePath
``````

## Safety

- Bridge routing network transport cutover packet prerequisite gate design only: true
- Bridge GET only: true
- Cutover packet created: false
- Cutover approval recorded: false
- Bridge response captured: false
- Response capture record created: false
- Operator approval recorded: false
- Confirmation record created: false
- Environment variables set: false
- Rollback snapshot created: false
- Rollback row created: false
- Audit row created: false
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

## Cutover packet prerequisite gate design

- Status: $gateStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Requirements: $(@($requirements).Count)
- Can execute bridge write now: false
- Can add network transport now: false
- Can enable network transport now: false
- Can arm network transport now: false
- Can open network socket now: false
- Can add real bridge HTTP client now: false
- Can add bridge POST now: false
- Can create cutover packet now: false
- Can record cutover approval now: false
- Can capture bridge response now: false
- Can create response capture records now: false
- Can record operator approval now: false
- Can create confirmation records now: false
- Can set environment variables now: false
- Can create audit rows now: false
- Can create rollback rows now: false
- Can create rollback snapshots now: false

## Source artifacts

$artifactText

## Future cutover packet requirements

$requirementText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_cutover_packet_prerequisite_gate_design=$OutputDir | status=$gateStatus | bridge_post_called=False | cutover_packet_created=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_cutover_packet_prerequisite_gate_design=$OutputDir | status=$gateStatus | blockers=$blockerCount | bridge_post_called=False | cutover_packet_created=False"
}

Write-Host ""
Write-Host "Cutover packet prerequisite gate design files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
