param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
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
        [string]$VariableName,
        [string]$RequiredDefault,
        [string]$FutureLiveRequirement,
        [string]$Reason,
        [bool]$SetNow = $false,
        [bool]$AllowsLiveWriteNow = $false
    )

    [void]$Requirements.Add([ordered]@{
        category = $Category
        variable_name = $VariableName
        required_default = $RequiredDefault
        future_live_requirement = $FutureLiveRequirement
        reason = $Reason
        set_now = $SetNow
        allows_live_write_now = $AllowsLiveWriteNow
    })
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($RollbackSnapshotPrerequisiteGateDir)) {
    $RollbackSnapshotPrerequisiteGateDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_*" -JsonName "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.json"
}
if ([string]::IsNullOrWhiteSpace($AuditPrerequisiteGateDir)) {
    $AuditPrerequisiteGateDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_audit_prerequisite_gate_*" -JsonName "phase20_bridge_routing_network_transport_audit_prerequisite_gate.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($DryRunInvocationReleaseCheckpointDir)) {
    $DryRunInvocationReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json" -Required $false
}

$rollbackPath = Join-Path $RollbackSnapshotPrerequisiteGateDir "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.json"
$auditPath = if (![string]::IsNullOrWhiteSpace($AuditPrerequisiteGateDir)) { Join-Path $AuditPrerequisiteGateDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($DryRunInvocationReleaseCheckpointDir)) { Join-Path $DryRunInvocationReleaseCheckpointDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $rollbackPath)) {
    throw "Rollback snapshot prerequisite gate JSON not found: $rollbackPath"
}

$rollback = Read-JsonFile $rollbackPath
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

# Source rollback prerequisite gate safety.
Add-Gate $gates "rollback_snapshot_prerequisite_gate_exists" $true "blocker" $rollbackPath "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_is_gate_only" ($rollback.safety.bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_only -eq $true) "blocker" "bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_only=$($rollback.safety.bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_only)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_bridge_get_only" ($rollback.safety.bridge_get_only -eq $true) "blocker" "bridge_get_only=$($rollback.safety.bridge_get_only)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_no_rollback_snapshot" ($rollback.safety.rollback_snapshot_created -eq $false) "blocker" "rollback_snapshot_created=$($rollback.safety.rollback_snapshot_created)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_no_rollback_row" ($rollback.safety.rollback_row_created -eq $false) "blocker" "rollback_row_created=$($rollback.safety.rollback_row_created)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_no_audit_row" ($rollback.safety.audit_row_created -eq $false) "blocker" "audit_row_created=$($rollback.safety.audit_row_created)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_no_network_transport" ($rollback.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($rollback.safety.network_transport_implemented)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_no_network_enabled" ($rollback.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($rollback.safety.network_transport_enabled)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_no_network_armed" ($rollback.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($rollback.safety.network_transport_armed)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_no_socket" ($rollback.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($rollback.safety.network_socket_opened)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_no_real_http_client" ($rollback.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($rollback.safety.real_bridge_http_client_implemented)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_no_bridge_post" ($rollback.safety.bridge_post_called -eq $false -and $rollback.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($rollback.safety.bridge_post_called); bridge_post_call_implemented=$($rollback.safety.bridge_post_call_implemented)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_no_mutation" ($rollback.safety.platform_db_mutation_performed -eq $false -and $rollback.safety.bridge_mutation_performed -eq $false) "blocker" "platform_db_mutation=$($rollback.safety.platform_db_mutation_performed); bridge_mutation=$($rollback.safety.bridge_mutation_performed)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_no_lacrm" ($rollback.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($rollback.safety.lacrm_call_performed)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_blocks_execution" ($rollback.rollback_snapshot_prerequisite_gate.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($rollback.rollback_snapshot_prerequisite_gate.can_execute_bridge_write_now)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_blocks_network_transport" ($rollback.rollback_snapshot_prerequisite_gate.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($rollback.rollback_snapshot_prerequisite_gate.can_add_network_transport_now)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_blocks_audit_rows" ($rollback.rollback_snapshot_prerequisite_gate.can_create_audit_rows_now -eq $false) "blocker" "can_create_audit_rows_now=$($rollback.rollback_snapshot_prerequisite_gate.can_create_audit_rows_now)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_blocks_rollback_rows" ($rollback.rollback_snapshot_prerequisite_gate.can_create_rollback_rows_now -eq $false) "blocker" "can_create_rollback_rows_now=$($rollback.rollback_snapshot_prerequisite_gate.can_create_rollback_rows_now)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_blocks_rollback_snapshots" ($rollback.rollback_snapshot_prerequisite_gate.can_create_rollback_snapshots_now -eq $false) "blocker" "can_create_rollback_snapshots_now=$($rollback.rollback_snapshot_prerequisite_gate.can_create_rollback_snapshots_now)" "rollback_snapshot_prerequisite_gate"
Add-Gate $gates "rollback_gate_has_no_blockers" ([int]$rollback.rollback_snapshot_prerequisite_gate.blocker_count -eq 0) "blocker" "blocker_count=$($rollback.rollback_snapshot_prerequisite_gate.blocker_count)" "rollback_snapshot_prerequisite_gate"

foreach ($issue in @($rollback.issues)) {
    if ($issue.severity -eq "blocker") {
        Add-Issue $issues "blocker" "rollback_gate_$($issue.code)" "$($issue.message)" "rollback_snapshot_prerequisite_gate"
    } elseif ($issue.severity -eq "review") {
        Add-Issue $issues "review" "rollback_gate_$($issue.code)" "$($issue.message)" "rollback_snapshot_prerequisite_gate"
    }
}

# Optional upstream evidence.
if ($audit -ne $null) {
    Add-Gate $gates "audit_prerequisite_gate_present" $true "review" $auditPath "audit_prerequisite_gate"
    Add-Gate $gates "audit_gate_blocks_audit_rows" ($audit.audit_prerequisite_gate.can_create_audit_rows_now -eq $false) "blocker" "can_create_audit_rows_now=$($audit.audit_prerequisite_gate.can_create_audit_rows_now)" "audit_prerequisite_gate"
    Add-Gate $gates "audit_gate_blocks_execution" ($audit.audit_prerequisite_gate.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($audit.audit_prerequisite_gate.can_execute_bridge_write_now)" "audit_prerequisite_gate"
} else {
    Add-Gate $gates "audit_prerequisite_gate_present" $false "review" "Phase 20 Step 24 audit prerequisite gate not found." "audit_prerequisite_gate"
}

if ($release -ne $null) {
    Add-Gate $gates "dry_run_release_checkpoint_present" $true "review" $releasePath "dry_run_release_checkpoint"
    Add-Gate $gates "dry_run_release_blocks_execution" ($release.release_checkpoint.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($release.release_checkpoint.can_execute_bridge_write_now)" "dry_run_release_checkpoint"
    Add-Gate $gates "dry_run_release_blocks_network_transport" ($release.release_checkpoint.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($release.release_checkpoint.can_add_network_transport_now)" "dry_run_release_checkpoint"
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

# Future environment gate design requirements only. Step 26 does not set any environment variables.
Add-Requirement $requirements "mode" "PLATFORM_BRIDGE_NETWORK_TRANSPORT_MODE" "dry_run" "live only after explicit cutover approval" "Keeps network transport in dry-run mode by default."
Add-Requirement $requirements "mode" "PLATFORM_BRIDGE_NETWORK_TRANSPORT_DESIGN_ENABLED" "false" "true only in a future design-only validation step" "Prevents accidental network transport design activation."
Add-Requirement $requirements "mode" "PLATFORM_BRIDGE_NETWORK_TRANSPORT_DESIGN_ARMED" "false" "true only with operator signoff and matching confirmation phrase" "Requires a second gate before any future transport path can be armed."
Add-Requirement $requirements "live" "PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED" "false" "true only after audit, rollback, response capture, and cutover packet approval" "Prevents live routing writes by default."
Add-Requirement $requirements "live" "PLATFORM_BRIDGE_ROUTING_WRITE_ARMED" "false" "true only after final cutover approval" "Second live write gate to avoid one-variable activation."
Add-Requirement $requirements "network" "PLATFORM_BRIDGE_BASE_URL" "" "explicit http://127.0.0.1:8000 or approved bridge URL" "Prevents implicit bridge destinations."
Add-Requirement $requirements "network" "PLATFORM_BRIDGE_ALLOWED_HOSTS" "127.0.0.1,localhost" "approved host allow-list only" "Prevents transport from reaching arbitrary hosts."
Add-Requirement $requirements "network" "PLATFORM_BRIDGE_NETWORK_TIMEOUT_SECONDS" "5" "bounded timeout only" "Prevents future transport from hanging operator workflows."
Add-Requirement $requirements "auth" "PLATFORM_BRIDGE_ADMIN_TOKEN" "" "configured secret only in environment, never committed" "Future bridge calls must be authenticated without storing secrets in git."
Add-Requirement $requirements "auth" "PLATFORM_BRIDGE_TOKEN_HEADER" "X-Bridge-Admin-Token" "approved header name only" "Keeps future bridge authentication explicit."
Add-Requirement $requirements "operator" "PLATFORM_BRIDGE_NETWORK_TRANSPORT_CONFIRMATION_PHRASE" "ENABLE BRIDGE TRANSPORT DESIGN" "exact phrase required before design can proceed" "Prevents accidental operator activation."
Add-Requirement $requirements "operator" "PLATFORM_BRIDGE_LIVE_WRITE_CONFIRMATION_PHRASE" "WRITE BRIDGE ROUTING LIVE" "exact phrase required before any future live write" "Separates design confirmation from live write confirmation."
Add-Requirement $requirements "audit" "PLATFORM_BRIDGE_REQUIRE_AUDIT_PREREQUISITE_GATE" "true" "must remain true" "Future live transport must prove audit prerequisites first."
Add-Requirement $requirements "rollback" "PLATFORM_BRIDGE_REQUIRE_ROLLBACK_SNAPSHOT" "true" "must remain true" "Future live transport must prove rollback snapshot readiness first."
Add-Requirement $requirements "response" "PLATFORM_BRIDGE_REQUIRE_RESPONSE_CAPTURE" "true" "must remain true" "Future live transport must capture response status and hash."
Add-Requirement $requirements "cutover" "PLATFORM_BRIDGE_REQUIRE_CUTOVER_PACKET" "true" "must remain true" "Future live transport must be tied to a cutover packet."
Add-Requirement $requirements "boundary" "PLATFORM_BRIDGE_ENVIRONMENT_GATE_VERSION" "phase20-step26-no-write" "updated only by future reviewed step" "Makes environment gate design version visible in future reports."

Add-Gate $gates "environment_requirement_count_minimum" (@($requirements).Count -ge 15) "blocker" "requirements=$(@($requirements).Count)" "environment_gate_design"
Add-Gate $gates "environment_variables_not_set_by_step_26" $true "blocker" "environment_variables_set=False" "environment_gate_design"
Add-Gate $gates "environment_gate_no_audit_rows" $true "blocker" "audit_row_created=False" "environment_gate_design"
Add-Gate $gates "environment_gate_no_rollback_rows" $true "blocker" "rollback_row_created=False" "environment_gate_design"
Add-Gate $gates "environment_gate_no_rollback_snapshots" $true "blocker" "rollback_snapshot_created=False" "environment_gate_design"

# Convert failed gates into issues.
foreach ($gate in @($gates)) {
    if ($gate.passed -ne $true) {
        Add-Issue $issues $gate.severity $gate.gate $gate.evidence $gate.source
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$gateStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "environment_gate_design_ready_for_review_no_write"
} elseif ($blockerCount -eq 0) {
    "environment_gate_design_review_required_no_write"
} else {
    "environment_gate_design_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_environment_gate_design_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="rollback_snapshot_prerequisite_gate"; json_path=$rollbackPath; sha256=Get-FileSha256 $rollbackPath },
    [ordered]@{ key="audit_prerequisite_gate"; json_path=$auditPath; sha256=Get-FileSha256 $auditPath },
    [ordered]@{ key="dry_run_invocation_path_release_checkpoint"; json_path=$releasePath; sha256=Get-FileSha256 $releasePath }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 26"
    purpose = "Bridge routing network transport environment gate design"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_environment_gate_design_only = $true
        bridge_get_only = $true
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
    environment_gate_design = [ordered]@{
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
        can_set_environment_variables_now = $false
        can_create_audit_rows_now = $false
        can_create_rollback_rows_now = $false
        can_create_rollback_snapshots_now = $false
        reason = if ($blockerCount -eq 0) {
            "Environment gate design is ready for review. Phase 20 Step 26 sets no environment variables, opens no socket, calls no bridge POST, and authorizes no execution."
        } else {
            "Environment gate design has blockers. Resolve blockers before any future real network transport design."
        }
    }
    source_artifacts = $sourceArtifacts
    environment_requirements = @($requirements)
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
        environment_requirements = @($requirements).Count
        gates = @($gates).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this environment gate design before setting or changing any transport environment variables.",
        "Do not set environment variables from Phase 20 Step 26.",
        "Do not create audit rows or rollback snapshots from Phase 20 Step 26.",
        "Do not call bridge POST endpoints from Phase 20 Step 26.",
        "Future real transport work must prove audit, rollback, response capture, and cutover prerequisites before execution.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_environment_gate_design.json"
$requirementsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_environment_gate_design_requirements.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_environment_gate_design_artifacts.csv"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_environment_gate_design_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_environment_gate_design_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_environment_gate_design.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$requirements | Export-Csv -LiteralPath $requirementsCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$requirementText = (@($requirements) | ForEach-Object { "- [$($_.category)] $($_.variable_name): default=$($_.required_default); future=$($_.future_live_requirement); set now=$($_.set_now)" }) -join "`n"
$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Environment Gate Design

Generated: $($report.generated_at)

Source rollback snapshot prerequisite gate:

``````
$rollbackPath
``````

## Safety

- Bridge routing network transport environment gate design only: true
- Bridge GET only: true
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

## Environment gate design

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
- Can set environment variables now: false
- Can create audit rows now: false
- Can create rollback rows now: false
- Can create rollback snapshots now: false

## Source artifacts

$artifactText

## Future environment requirements

$requirementText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_environment_gate_design=$OutputDir | status=$gateStatus | bridge_post_called=False | environment_variables_set=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_environment_gate_design=$OutputDir | status=$gateStatus | blockers=$blockerCount | bridge_post_called=False | environment_variables_set=False"
}

Write-Host ""
Write-Host "Environment gate design files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
