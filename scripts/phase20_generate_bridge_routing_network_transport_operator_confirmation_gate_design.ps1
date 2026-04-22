param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
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
        [string]$ControlName,
        [string]$RequiredValue,
        [string]$FutureLiveRequirement,
        [string]$Reason,
        [bool]$ImplementedNow = $false,
        [bool]$AllowsLiveWriteNow = $false
    )

    [void]$Requirements.Add([ordered]@{
        category = $Category
        control_name = $ControlName
        required_value = $RequiredValue
        future_live_requirement = $FutureLiveRequirement
        reason = $Reason
        implemented_now = $ImplementedNow
        allows_live_write_now = $AllowsLiveWriteNow
    })
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($EnvironmentGateDesignDir)) {
    $EnvironmentGateDesignDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_environment_gate_design_*" -JsonName "phase20_bridge_routing_network_transport_environment_gate_design.json"
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

$environmentPath = Join-Path $EnvironmentGateDesignDir "phase20_bridge_routing_network_transport_environment_gate_design.json"
$rollbackPath = if (![string]::IsNullOrWhiteSpace($RollbackSnapshotPrerequisiteGateDir)) { Join-Path $RollbackSnapshotPrerequisiteGateDir "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.json" } else { "" }
$auditPath = if (![string]::IsNullOrWhiteSpace($AuditPrerequisiteGateDir)) { Join-Path $AuditPrerequisiteGateDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($DryRunInvocationReleaseCheckpointDir)) { Join-Path $DryRunInvocationReleaseCheckpointDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $environmentPath)) {
    throw "Environment gate design JSON not found: $environmentPath"
}

$environment = Read-JsonFile $environmentPath
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

# Source environment gate safety.
Add-Gate $gates "environment_gate_design_exists" $true "blocker" $environmentPath "environment_gate_design"
Add-Gate $gates "environment_gate_is_design_only" ($environment.safety.bridge_routing_network_transport_environment_gate_design_only -eq $true) "blocker" "bridge_routing_network_transport_environment_gate_design_only=$($environment.safety.bridge_routing_network_transport_environment_gate_design_only)" "environment_gate_design"
Add-Gate $gates "environment_gate_bridge_get_only" ($environment.safety.bridge_get_only -eq $true) "blocker" "bridge_get_only=$($environment.safety.bridge_get_only)" "environment_gate_design"
Add-Gate $gates "environment_gate_no_environment_variables_set" ($environment.safety.environment_variables_set -eq $false) "blocker" "environment_variables_set=$($environment.safety.environment_variables_set)" "environment_gate_design"
Add-Gate $gates "environment_gate_no_rollback_snapshot" ($environment.safety.rollback_snapshot_created -eq $false) "blocker" "rollback_snapshot_created=$($environment.safety.rollback_snapshot_created)" "environment_gate_design"
Add-Gate $gates "environment_gate_no_rollback_row" ($environment.safety.rollback_row_created -eq $false) "blocker" "rollback_row_created=$($environment.safety.rollback_row_created)" "environment_gate_design"
Add-Gate $gates "environment_gate_no_audit_row" ($environment.safety.audit_row_created -eq $false) "blocker" "audit_row_created=$($environment.safety.audit_row_created)" "environment_gate_design"
Add-Gate $gates "environment_gate_no_network_transport" ($environment.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($environment.safety.network_transport_implemented)" "environment_gate_design"
Add-Gate $gates "environment_gate_no_network_enabled" ($environment.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($environment.safety.network_transport_enabled)" "environment_gate_design"
Add-Gate $gates "environment_gate_no_network_armed" ($environment.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($environment.safety.network_transport_armed)" "environment_gate_design"
Add-Gate $gates "environment_gate_no_socket" ($environment.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($environment.safety.network_socket_opened)" "environment_gate_design"
Add-Gate $gates "environment_gate_no_real_http_client" ($environment.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($environment.safety.real_bridge_http_client_implemented)" "environment_gate_design"
Add-Gate $gates "environment_gate_no_bridge_post" ($environment.safety.bridge_post_called -eq $false -and $environment.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($environment.safety.bridge_post_called); bridge_post_call_implemented=$($environment.safety.bridge_post_call_implemented)" "environment_gate_design"
Add-Gate $gates "environment_gate_no_mutation" ($environment.safety.platform_db_mutation_performed -eq $false -and $environment.safety.bridge_mutation_performed -eq $false) "blocker" "platform_db_mutation=$($environment.safety.platform_db_mutation_performed); bridge_mutation=$($environment.safety.bridge_mutation_performed)" "environment_gate_design"
Add-Gate $gates "environment_gate_no_lacrm" ($environment.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($environment.safety.lacrm_call_performed)" "environment_gate_design"
Add-Gate $gates "environment_gate_blocks_execution" ($environment.environment_gate_design.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($environment.environment_gate_design.can_execute_bridge_write_now)" "environment_gate_design"
Add-Gate $gates "environment_gate_blocks_network_transport" ($environment.environment_gate_design.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($environment.environment_gate_design.can_add_network_transport_now)" "environment_gate_design"
Add-Gate $gates "environment_gate_blocks_enable_network" ($environment.environment_gate_design.can_enable_network_transport_now -eq $false) "blocker" "can_enable_network_transport_now=$($environment.environment_gate_design.can_enable_network_transport_now)" "environment_gate_design"
Add-Gate $gates "environment_gate_blocks_arm_network" ($environment.environment_gate_design.can_arm_network_transport_now -eq $false) "blocker" "can_arm_network_transport_now=$($environment.environment_gate_design.can_arm_network_transport_now)" "environment_gate_design"
Add-Gate $gates "environment_gate_blocks_socket" ($environment.environment_gate_design.can_open_network_socket_now -eq $false) "blocker" "can_open_network_socket_now=$($environment.environment_gate_design.can_open_network_socket_now)" "environment_gate_design"
Add-Gate $gates "environment_gate_blocks_bridge_post" ($environment.environment_gate_design.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($environment.environment_gate_design.can_add_bridge_post_now)" "environment_gate_design"
Add-Gate $gates "environment_gate_blocks_env_setting" ($environment.environment_gate_design.can_set_environment_variables_now -eq $false) "blocker" "can_set_environment_variables_now=$($environment.environment_gate_design.can_set_environment_variables_now)" "environment_gate_design"
Add-Gate $gates "environment_gate_has_no_blockers" ([int]$environment.environment_gate_design.blocker_count -eq 0) "blocker" "blocker_count=$($environment.environment_gate_design.blocker_count)" "environment_gate_design"

foreach ($issue in @($environment.issues)) {
    if ($issue.severity -eq "blocker") {
        Add-Issue $issues "blocker" "environment_gate_$($issue.code)" "$($issue.message)" "environment_gate_design"
    } elseif ($issue.severity -eq "review") {
        Add-Issue $issues "review" "environment_gate_$($issue.code)" "$($issue.message)" "environment_gate_design"
    }
}

# Optional upstream evidence.
if ($rollback -ne $null) {
    Add-Gate $gates "rollback_snapshot_prerequisite_gate_present" $true "review" $rollbackPath "rollback_snapshot_prerequisite_gate"
    Add-Gate $gates "rollback_gate_blocks_snapshots" ($rollback.rollback_snapshot_prerequisite_gate.can_create_rollback_snapshots_now -eq $false) "blocker" "can_create_rollback_snapshots_now=$($rollback.rollback_snapshot_prerequisite_gate.can_create_rollback_snapshots_now)" "rollback_snapshot_prerequisite_gate"
    Add-Gate $gates "rollback_gate_blocks_execution" ($rollback.rollback_snapshot_prerequisite_gate.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($rollback.rollback_snapshot_prerequisite_gate.can_execute_bridge_write_now)" "rollback_snapshot_prerequisite_gate"
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
    Add-Gate $gates "dry_run_release_blocks_bridge_post" ($release.release_checkpoint.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($release.release_checkpoint.can_add_bridge_post_now)" "dry_run_release_checkpoint"
} else {
    Add-Gate $gates "dry_run_release_checkpoint_present" $false "review" "Phase 20 Step 23 release checkpoint not found." "dry_run_release_checkpoint"
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

# Future operator confirmation gate design requirements only. Step 27 does not accept or store operator approvals.
Add-Requirement $requirements "phrase" "transport_design_confirmation_phrase" "ENABLE BRIDGE TRANSPORT DESIGN" "must match exactly before future transport design can continue" "Separates design review from live write approval."
Add-Requirement $requirements "phrase" "live_write_confirmation_phrase" "WRITE BRIDGE ROUTING LIVE" "must match exactly before any future live bridge routing write" "Prevents accidental live writes."
Add-Requirement $requirements "phrase" "rollback_confirmation_phrase" "ROLL BACK BRIDGE ROUTING" "must match exactly before any future rollback action" "Prevents accidental rollback execution."
Add-Requirement $requirements "identity" "operator_name_required" "true" "operator name must be non-empty for future design/live approval" "Links approval to a human operator."
Add-Requirement $requirements "identity" "operator_role_required" "true" "operator role must be recorded before live approval" "Supports review of authority for future live changes."
Add-Requirement $requirements "identity" "operator_session_id_required" "true" "operator session id must be recorded for future live approval" "Connects approval to a UI/session context."
Add-Requirement $requirements "timing" "confirmation_created_at_required" "true" "confirmation timestamp must be captured before execution" "Proves confirmation happened before a future network boundary crossing."
Add-Requirement $requirements "timing" "confirmation_expires_after_minutes" "10" "confirmation expires before future live transport if stale" "Prevents old confirmations being reused later."
Add-Requirement $requirements "request" "request_hash_confirmation_required" "true" "operator must confirm the exact request hash" "Prevents approving one request while executing another."
Add-Requirement $requirements "request" "source_checkpoint_hash_confirmation_required" "true" "operator must confirm the reviewed checkpoint hashes" "Binds confirmation to reviewed evidence."
Add-Requirement $requirements "safety" "audit_prerequisite_confirmation_required" "true" "operator must confirm audit prerequisite gate exists" "Ensures audit readiness is visible."
Add-Requirement $requirements "safety" "rollback_prerequisite_confirmation_required" "true" "operator must confirm rollback prerequisite gate exists" "Ensures rollback readiness is visible."
Add-Requirement $requirements "safety" "environment_gate_confirmation_required" "true" "operator must confirm environment gate status" "Ensures environment readiness is visible."
Add-Requirement $requirements "boundary" "socket_open_confirmation_required" "true" "operator must explicitly confirm before any future socket opening" "Makes network boundary crossing explicit."
Add-Requirement $requirements "boundary" "bridge_post_confirmation_required" "true" "operator must explicitly confirm before any future bridge POST" "Makes bridge mutation boundary explicit."
Add-Requirement $requirements "review" "two_step_confirmation_required" "true" "future live writes require design confirmation plus live confirmation" "Avoids single-click live writes."
Add-Requirement $requirements "review" "confirmation_summary_preview_required" "true" "operator must see a summary preview before approval" "Allows final review of action, evidence, and rollback readiness."
Add-Requirement $requirements "storage" "confirmation_record_append_only" "true" "future confirmation records must be append-only" "Prevents confirmation history from being overwritten."
Add-Requirement $requirements "boundary" "phase20_step27_operator_approval_not_recorded" "true" "Step 27 must not record operator approvals" "This step is only an operator confirmation gate design." $false $false

Add-Gate $gates "operator_confirmation_requirement_count_minimum" (@($requirements).Count -ge 15) "blocker" "requirements=$(@($requirements).Count)" "operator_confirmation_gate_design"
Add-Gate $gates "operator_approvals_not_recorded" $true "blocker" "operator_approval_recorded=False" "operator_confirmation_gate_design"
Add-Gate $gates "confirmation_records_not_created" $true "blocker" "confirmation_record_created=False" "operator_confirmation_gate_design"
Add-Gate $gates "environment_variables_not_set" $true "blocker" "environment_variables_set=False" "operator_confirmation_gate_design"
Add-Gate $gates "operator_gate_no_audit_rows" $true "blocker" "audit_row_created=False" "operator_confirmation_gate_design"
Add-Gate $gates "operator_gate_no_rollback_rows" $true "blocker" "rollback_row_created=False" "operator_confirmation_gate_design"
Add-Gate $gates "operator_gate_no_rollback_snapshots" $true "blocker" "rollback_snapshot_created=False" "operator_confirmation_gate_design"

# Convert failed gates into issues.
foreach ($gate in @($gates)) {
    if ($gate.passed -ne $true) {
        Add-Issue $issues $gate.severity $gate.gate $gate.evidence $gate.source
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$gateStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "operator_confirmation_gate_design_ready_for_review_no_write"
} elseif ($blockerCount -eq 0) {
    "operator_confirmation_gate_design_review_required_no_write"
} else {
    "operator_confirmation_gate_design_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="environment_gate_design"; json_path=$environmentPath; sha256=Get-FileSha256 $environmentPath },
    [ordered]@{ key="rollback_snapshot_prerequisite_gate"; json_path=$rollbackPath; sha256=Get-FileSha256 $rollbackPath },
    [ordered]@{ key="audit_prerequisite_gate"; json_path=$auditPath; sha256=Get-FileSha256 $auditPath },
    [ordered]@{ key="dry_run_invocation_path_release_checkpoint"; json_path=$releasePath; sha256=Get-FileSha256 $releasePath }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 27"
    purpose = "Bridge routing network transport operator confirmation gate design"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_operator_confirmation_gate_design_only = $true
        bridge_get_only = $true
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
    operator_confirmation_gate_design = [ordered]@{
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
        can_record_operator_approval_now = $false
        can_create_confirmation_records_now = $false
        can_set_environment_variables_now = $false
        can_create_audit_rows_now = $false
        can_create_rollback_rows_now = $false
        can_create_rollback_snapshots_now = $false
        reason = if ($blockerCount -eq 0) {
            "Operator confirmation gate design is ready for review. Phase 20 Step 27 records no approvals, opens no socket, calls no bridge POST, and authorizes no execution."
        } else {
            "Operator confirmation gate design has blockers. Resolve blockers before any future real network transport design."
        }
    }
    source_artifacts = $sourceArtifacts
    operator_confirmation_requirements = @($requirements)
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
        operator_confirmation_requirements = @($requirements).Count
        gates = @($gates).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this operator confirmation gate design before implementing any confirmation-record writes.",
        "Do not record operator approvals from Phase 20 Step 27.",
        "Do not set environment variables from Phase 20 Step 27.",
        "Do not create audit rows or rollback snapshots from Phase 20 Step 27.",
        "Do not call bridge POST endpoints from Phase 20 Step 27.",
        "Future real transport work must prove audit, rollback, environment, operator confirmation, response capture, and cutover prerequisites before execution.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_operator_confirmation_gate_design.json"
$requirementsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_requirements.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_artifacts.csv"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_operator_confirmation_gate_design.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$requirements | Export-Csv -LiteralPath $requirementsCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$requirementText = (@($requirements) | ForEach-Object { "- [$($_.category)] $($_.control_name): required=$($_.required_value); future=$($_.future_live_requirement); implemented now=$($_.implemented_now)" }) -join "`n"
$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Operator Confirmation Gate Design

Generated: $($report.generated_at)

Source environment gate design:

``````
$environmentPath
``````

## Safety

- Bridge routing network transport operator confirmation gate design only: true
- Bridge GET only: true
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

## Operator confirmation gate design

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
- Can record operator approval now: false
- Can create confirmation records now: false
- Can set environment variables now: false
- Can create audit rows now: false
- Can create rollback rows now: false
- Can create rollback snapshots now: false

## Source artifacts

$artifactText

## Future operator confirmation requirements

$requirementText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_operator_confirmation_gate_design=$OutputDir | status=$gateStatus | bridge_post_called=False | operator_approval_recorded=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_operator_confirmation_gate_design=$OutputDir | status=$gateStatus | blockers=$blockerCount | bridge_post_called=False | operator_approval_recorded=False"
}

Write-Host ""
Write-Host "Operator confirmation gate design files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
