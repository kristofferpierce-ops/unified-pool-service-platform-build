param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$AuditPrerequisiteGateDir = "",
    [string]$DryRunInvocationReleaseCheckpointDir = "",
    [string]$DryRunInvocationOperatorSignoffDir = "",
    [string]$DryRunInvocationPreflightMatrixDir = "",
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
        [string]$Requirement,
        [string]$FieldName,
        [string]$Reason,
        [string]$Status = "required_for_future",
        [bool]$ImplementedNow = $false,
        [bool]$AllowsLiveWriteNow = $false
    )

    [void]$Requirements.Add([ordered]@{
        category = $Category
        requirement = $Requirement
        field_name = $FieldName
        reason = $Reason
        status = $Status
        implemented_now = $ImplementedNow
        allows_live_write_now = $AllowsLiveWriteNow
    })
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($AuditPrerequisiteGateDir)) {
    $AuditPrerequisiteGateDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_audit_prerequisite_gate_*" -JsonName "phase20_bridge_routing_network_transport_audit_prerequisite_gate.json"
}
if ([string]::IsNullOrWhiteSpace($DryRunInvocationReleaseCheckpointDir)) {
    $DryRunInvocationReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($DryRunInvocationOperatorSignoffDir)) {
    $DryRunInvocationOperatorSignoffDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_operator_signoff_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path_operator_signoff.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($DryRunInvocationPreflightMatrixDir)) {
    $DryRunInvocationPreflightMatrixDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix.json" -Required $false
}

$auditPath = Join-Path $AuditPrerequisiteGateDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate.json"
$releasePath = if (![string]::IsNullOrWhiteSpace($DryRunInvocationReleaseCheckpointDir)) { Join-Path $DryRunInvocationReleaseCheckpointDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json" } else { "" }
$signoffPath = if (![string]::IsNullOrWhiteSpace($DryRunInvocationOperatorSignoffDir)) { Join-Path $DryRunInvocationOperatorSignoffDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_operator_signoff.json" } else { "" }
$preflightPath = if (![string]::IsNullOrWhiteSpace($DryRunInvocationPreflightMatrixDir)) { Join-Path $DryRunInvocationPreflightMatrixDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix.json" } else { "" }

if (!(Test-Path -LiteralPath $auditPath)) {
    throw "Audit prerequisite gate JSON not found: $auditPath"
}

$audit = Read-JsonFile $auditPath
$release = if (![string]::IsNullOrWhiteSpace($releasePath) -and (Test-Path -LiteralPath $releasePath)) { Read-JsonFile $releasePath } else { $null }
$signoff = if (![string]::IsNullOrWhiteSpace($signoffPath) -and (Test-Path -LiteralPath $signoffPath)) { Read-JsonFile $signoffPath } else { $null }
$preflight = if (![string]::IsNullOrWhiteSpace($preflightPath) -and (Test-Path -LiteralPath $preflightPath)) { Read-JsonFile $preflightPath } else { $null }

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

# Source audit prerequisite gate safety.
Add-Gate $gates "audit_prerequisite_gate_exists" $true "blocker" $auditPath "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_is_gate_only" ($audit.safety.bridge_routing_network_transport_audit_prerequisite_gate_only -eq $true) "blocker" "bridge_routing_network_transport_audit_prerequisite_gate_only=$($audit.safety.bridge_routing_network_transport_audit_prerequisite_gate_only)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_bridge_get_only" ($audit.safety.bridge_get_only -eq $true) "blocker" "bridge_get_only=$($audit.safety.bridge_get_only)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_no_audit_row" ($audit.safety.audit_row_created -eq $false) "blocker" "audit_row_created=$($audit.safety.audit_row_created)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_no_rollback_row" ($audit.safety.rollback_row_created -eq $false) "blocker" "rollback_row_created=$($audit.safety.rollback_row_created)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_no_network_transport" ($audit.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($audit.safety.network_transport_implemented)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_no_network_enabled" ($audit.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($audit.safety.network_transport_enabled)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_no_network_armed" ($audit.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($audit.safety.network_transport_armed)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_no_socket" ($audit.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($audit.safety.network_socket_opened)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_no_real_http_client" ($audit.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($audit.safety.real_bridge_http_client_implemented)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_no_bridge_post" ($audit.safety.bridge_post_called -eq $false -and $audit.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($audit.safety.bridge_post_called); bridge_post_call_implemented=$($audit.safety.bridge_post_call_implemented)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_no_mutation" ($audit.safety.platform_db_mutation_performed -eq $false -and $audit.safety.bridge_mutation_performed -eq $false) "blocker" "platform_db_mutation=$($audit.safety.platform_db_mutation_performed); bridge_mutation=$($audit.safety.bridge_mutation_performed)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_no_lacrm" ($audit.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($audit.safety.lacrm_call_performed)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_blocks_execution" ($audit.audit_prerequisite_gate.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($audit.audit_prerequisite_gate.can_execute_bridge_write_now)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_blocks_network_transport" ($audit.audit_prerequisite_gate.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($audit.audit_prerequisite_gate.can_add_network_transport_now)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_blocks_audit_rows" ($audit.audit_prerequisite_gate.can_create_audit_rows_now -eq $false) "blocker" "can_create_audit_rows_now=$($audit.audit_prerequisite_gate.can_create_audit_rows_now)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_blocks_rollback_rows" ($audit.audit_prerequisite_gate.can_create_rollback_rows_now -eq $false) "blocker" "can_create_rollback_rows_now=$($audit.audit_prerequisite_gate.can_create_rollback_rows_now)" "audit_prerequisite_gate"
Add-Gate $gates "audit_gate_has_no_blockers" ([int]$audit.audit_prerequisite_gate.blocker_count -eq 0) "blocker" "blocker_count=$($audit.audit_prerequisite_gate.blocker_count)" "audit_prerequisite_gate"

foreach ($issue in @($audit.issues)) {
    if ($issue.severity -eq "blocker") {
        Add-Issue $issues "blocker" "audit_gate_$($issue.code)" "$($issue.message)" "audit_prerequisite_gate"
    } elseif ($issue.severity -eq "review") {
        Add-Issue $issues "review" "audit_gate_$($issue.code)" "$($issue.message)" "audit_prerequisite_gate"
    }
}

# Optional upstream evidence.
if ($release -ne $null) {
    Add-Gate $gates "dry_run_release_checkpoint_present" $true "review" $releasePath "dry_run_release_checkpoint"
    Add-Gate $gates "dry_run_release_blocks_execution" ($release.release_checkpoint.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($release.release_checkpoint.can_execute_bridge_write_now)" "dry_run_release_checkpoint"
    Add-Gate $gates "dry_run_release_blocks_bridge_post" ($release.release_checkpoint.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($release.release_checkpoint.can_add_bridge_post_now)" "dry_run_release_checkpoint"
} else {
    Add-Gate $gates "dry_run_release_checkpoint_present" $false "review" "Phase 20 Step 23 release checkpoint not found." "dry_run_release_checkpoint"
}

if ($signoff -ne $null) {
    Add-Gate $gates "dry_run_operator_signoff_present" $true "review" $signoffPath "dry_run_operator_signoff"
    Add-Gate $gates "dry_run_operator_signoff_not_live_approved" ($signoff.signoff.approved_for_live_bridge_write -ne $true) "blocker" "approved_for_live_bridge_write=$($signoff.signoff.approved_for_live_bridge_write)" "dry_run_operator_signoff"
    Add-Gate $gates "dry_run_operator_signoff_not_socket_approved" ($signoff.signoff.approved_to_open_network_socket -ne $true) "blocker" "approved_to_open_network_socket=$($signoff.signoff.approved_to_open_network_socket)" "dry_run_operator_signoff"
} else {
    Add-Gate $gates "dry_run_operator_signoff_present" $false "review" "Phase 20 Step 22 operator signoff not found." "dry_run_operator_signoff"
}

if ($preflight -ne $null) {
    Add-Gate $gates "dry_run_preflight_matrix_present" $true "review" $preflightPath "dry_run_preflight_matrix"
    Add-Gate $gates "dry_run_preflight_blocks_network" ($preflight.preflight.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($preflight.preflight.can_add_network_transport_now)" "dry_run_preflight_matrix"
} else {
    Add-Gate $gates "dry_run_preflight_matrix_present" $false "review" "Phase 20 Step 21 preflight matrix not found." "dry_run_preflight_matrix"
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

# Rollback snapshot prerequisites for future real transport. These are requirements only, not writes.
Add-Requirement $requirements "identity" "Every future rollback snapshot must have a stable rollback snapshot id." "rollback_snapshot_id" "Allows a future transport execution to prove a rollback point exists before any live call."
Add-Requirement $requirements "identity" "Every future rollback snapshot must link to a transport execution id." "transport_execution_id" "Connects the future snapshot to the exact transport attempt it protects."
Add-Requirement $requirements "timing" "Every future rollback snapshot must store when it was captured." "snapshot_created_at" "Allows review of whether the snapshot predates any future network action."
Add-Requirement $requirements "source" "Every future rollback snapshot must store source artifact hashes." "source_artifact_hashes" "Prevents future rollback evidence from drifting away from reviewed release/signoff artifacts."
Add-Requirement $requirements "state" "Every future snapshot must store the bridge routing state before a live attempt." "bridge_routing_state_before_hash" "Allows comparison and rollback if bridge routing is mutated in future work."
Add-Requirement $requirements "state" "Every future snapshot must store the platform routing state before a live attempt." "platform_routing_state_before_hash" "Allows rollback review across platform and bridge views."
Add-Requirement $requirements "state" "Every future snapshot must capture phone, mode, owner type, label, contact ids, and notes before mutation." "phone,mode,owner_type,label,default_contact_ids,notes" "Captures the fields most likely to be changed by routing transport."
Add-Requirement $requirements "request" "Every future rollback plan must have a canonical rollback plan hash." "rollback_plan_hash" "Makes the rollback plan tamper-evident before execution."
Add-Requirement $requirements "request" "Every future rollback action must have a rollback idempotency key." "rollback_idempotency_key" "Prevents duplicate rollback actions if a future rollback is retried."
Add-Requirement $requirements "operator" "Every future rollback snapshot must record the operator responsible." "rollback_operator_name" "Connects future rollback readiness to a human review action."
Add-Requirement $requirements "operator" "Every future rollback action must require a typed confirmation phrase." "rollback_confirmation_phrase" "Prevents accidental rollback execution in a future live path."
Add-Requirement $requirements "safety" "Every future live transport attempt must require rollback snapshot existence before socket opening." "rollback_snapshot_required_before_socket" "Keeps rollback readiness ahead of any future network boundary crossing."
Add-Requirement $requirements "safety" "Every future live transport attempt must prove dry-run rollback preview was performed first." "rollback_dry_run_first" "Confirms a future rollback path was simulated before any live transport action."
Add-Requirement $requirements "response" "Every future rollback attempt must capture response status and response hash." "rollback_response_status_code,rollback_response_hash" "Supports rollback response evidence without needing to disclose full raw response in summaries."
Add-Requirement $requirements "error" "Every future rollback failure must capture error code and message." "rollback_error_code,rollback_error_message" "Supports troubleshooting without rerunning a write."
Add-Requirement $requirements "immutability" "Rollback snapshots must be append-only in future work." "rollback_append_only" "Prevents a future rollback system from overwriting historical state."
Add-Requirement $requirements "boundary" "Phase 20 Step 25 must not create rollback snapshots." "rollback_snapshot_created" "This step is only a rollback snapshot prerequisite gate." "not_created_in_step_25" $false $false

Add-Gate $gates "rollback_requirement_count_minimum" (@($requirements).Count -ge 12) "blocker" "requirements=$(@($requirements).Count)" "rollback_prerequisites"
Add-Gate $gates "rollback_snapshots_not_created" $true "blocker" "rollback_snapshot_created=False" "rollback_prerequisites"
Add-Gate $gates "rollback_rows_not_created" $true "blocker" "rollback_row_created=False" "rollback_prerequisites"
Add-Gate $gates "audit_rows_not_created" $true "blocker" "audit_row_created=False" "rollback_prerequisites"

# Convert failed gates into issues.
foreach ($gate in @($gates)) {
    if ($gate.passed -ne $true) {
        Add-Issue $issues $gate.severity $gate.gate $gate.evidence $gate.source
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$gateStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "rollback_snapshot_prerequisite_ready_for_review_no_write"
} elseif ($blockerCount -eq 0) {
    "rollback_snapshot_prerequisite_review_required_no_write"
} else {
    "rollback_snapshot_prerequisite_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="audit_prerequisite_gate"; json_path=$auditPath; sha256=Get-FileSha256 $auditPath },
    [ordered]@{ key="dry_run_invocation_path_release_checkpoint"; json_path=$releasePath; sha256=Get-FileSha256 $releasePath },
    [ordered]@{ key="dry_run_invocation_path_operator_signoff"; json_path=$signoffPath; sha256=Get-FileSha256 $signoffPath },
    [ordered]@{ key="dry_run_invocation_path_preflight_matrix"; json_path=$preflightPath; sha256=Get-FileSha256 $preflightPath }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 25"
    purpose = "Bridge routing network transport rollback snapshot prerequisite gate"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_only = $true
        bridge_get_only = $true
        rollback_snapshot_created = $false
        rollback_row_created = $false
        audit_row_created = $false
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
    rollback_snapshot_prerequisite_gate = [ordered]@{
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
        can_create_audit_rows_now = $false
        can_create_rollback_rows_now = $false
        can_create_rollback_snapshots_now = $false
        reason = if ($blockerCount -eq 0) {
            "Rollback snapshot prerequisites are ready for review. Phase 20 Step 25 still creates no rollback snapshots, opens no socket, calls no bridge POST, and authorizes no execution."
        } else {
            "Rollback snapshot prerequisite gate has blockers. Resolve blockers before any future real network transport design."
        }
    }
    source_artifacts = $sourceArtifacts
    rollback_requirements = @($requirements)
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
        rollback_requirements = @($requirements).Count
        gates = @($gates).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this rollback snapshot prerequisite gate before designing future rollback snapshot writes.",
        "Do not create rollback snapshots from Phase 20 Step 25.",
        "Do not create audit rows from Phase 20 Step 25.",
        "Do not call bridge POST endpoints from Phase 20 Step 25.",
        "Future real transport work must prove audit and rollback prerequisites before execution.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.json"
$requirementsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_requirements.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_artifacts.csv"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$requirements | Export-Csv -LiteralPath $requirementsCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$requirementText = (@($requirements) | ForEach-Object { "- [$($_.category)] $($_.field_name): $($_.requirement) (implemented now: $($_.implemented_now))" }) -join "`n"
$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Rollback Snapshot Prerequisite Gate

Generated: $($report.generated_at)

Source audit prerequisite gate:

``````
$auditPath
``````

## Safety

- Bridge routing network transport rollback snapshot prerequisite gate only: true
- Bridge GET only: true
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

## Rollback snapshot prerequisite gate

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
- Can create audit rows now: false
- Can create rollback rows now: false
- Can create rollback snapshots now: false

## Source artifacts

$artifactText

## Future rollback requirements

$requirementText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_rollback_snapshot_prerequisite_gate=$OutputDir | status=$gateStatus | bridge_post_called=False | rollback_snapshot_created=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_rollback_snapshot_prerequisite_gate=$OutputDir | status=$gateStatus | blockers=$blockerCount | bridge_post_called=False | rollback_snapshot_created=False"
}

Write-Host ""
Write-Host "Rollback snapshot prerequisite gate files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
