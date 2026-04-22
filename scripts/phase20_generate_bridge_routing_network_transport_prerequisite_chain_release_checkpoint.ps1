param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$CutoverPacketPrerequisiteGateDesignDir = "",
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

function Get-Prop {
    param($Object, [string]$Name)
    if ($null -eq $Object) { return $null }
    if ($Object.PSObject.Properties.Name -contains $Name) { return $Object.$Name }
    return $null
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($CutoverPacketPrerequisiteGateDesignDir)) {
    $CutoverPacketPrerequisiteGateDesignDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design_*" -JsonName "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design.json"
}
if ([string]::IsNullOrWhiteSpace($ResponseCaptureGateDesignDir)) {
    $ResponseCaptureGateDesignDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_response_capture_gate_design_*" -JsonName "phase20_bridge_routing_network_transport_response_capture_gate_design.json" -Required $false
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

$cutoverPath = Join-Path $CutoverPacketPrerequisiteGateDesignDir "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design.json"
$responsePath = if (![string]::IsNullOrWhiteSpace($ResponseCaptureGateDesignDir)) { Join-Path $ResponseCaptureGateDesignDir "phase20_bridge_routing_network_transport_response_capture_gate_design.json" } else { "" }
$operatorPath = if (![string]::IsNullOrWhiteSpace($OperatorConfirmationGateDesignDir)) { Join-Path $OperatorConfirmationGateDesignDir "phase20_bridge_routing_network_transport_operator_confirmation_gate_design.json" } else { "" }
$environmentPath = if (![string]::IsNullOrWhiteSpace($EnvironmentGateDesignDir)) { Join-Path $EnvironmentGateDesignDir "phase20_bridge_routing_network_transport_environment_gate_design.json" } else { "" }
$rollbackPath = if (![string]::IsNullOrWhiteSpace($RollbackSnapshotPrerequisiteGateDir)) { Join-Path $RollbackSnapshotPrerequisiteGateDir "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.json" } else { "" }
$auditPath = if (![string]::IsNullOrWhiteSpace($AuditPrerequisiteGateDir)) { Join-Path $AuditPrerequisiteGateDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($DryRunInvocationReleaseCheckpointDir)) { Join-Path $DryRunInvocationReleaseCheckpointDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $cutoverPath)) {
    throw "Cutover packet prerequisite gate design JSON not found: $cutoverPath"
}

$cutover = Read-JsonFile $cutoverPath
$response = if (![string]::IsNullOrWhiteSpace($responsePath) -and (Test-Path -LiteralPath $responsePath)) { Read-JsonFile $responsePath } else { $null }
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

$artifactList = @(
    [ordered]@{ key="cutover_packet_prerequisite_gate_design"; path=$cutoverPath; data=$cutover; required=$true },
    [ordered]@{ key="response_capture_gate_design"; path=$responsePath; data=$response; required=$false },
    [ordered]@{ key="operator_confirmation_gate_design"; path=$operatorPath; data=$operator; required=$false },
    [ordered]@{ key="environment_gate_design"; path=$environmentPath; data=$environment; required=$false },
    [ordered]@{ key="rollback_snapshot_prerequisite_gate"; path=$rollbackPath; data=$rollback; required=$false },
    [ordered]@{ key="audit_prerequisite_gate"; path=$auditPath; data=$audit; required=$false },
    [ordered]@{ key="dry_run_invocation_path_release_checkpoint"; path=$releasePath; data=$release; required=$false }
)

$sourceArtifacts = @()
foreach ($artifact in $artifactList) {
    $present = (![string]::IsNullOrWhiteSpace($artifact.path) -and (Test-Path -LiteralPath $artifact.path) -and $null -ne $artifact.data)
    Add-Gate $gates "artifact_present_$($artifact.key)" $present $(if ($artifact.required) { "blocker" } else { "review" }) $(if ($present) { $artifact.path } else { "Artifact not found." }) $artifact.key

    $sourceArtifacts += [ordered]@{
        key = $artifact.key
        json_path = $artifact.path
        present = $present
        sha256 = Get-FileSha256 $artifact.path
    }

    if ($present) {
        $safety = $artifact.data.safety
        Add-Gate $gates "$($artifact.key)_bridge_get_only_or_safe" ((Get-Prop $safety "bridge_get_only") -ne $false) "review" "bridge_get_only=$((Get-Prop $safety 'bridge_get_only'))" $artifact.key

        $mustBeFalse = @(
            "cutover_packet_created",
            "cutover_approval_recorded",
            "bridge_response_captured",
            "response_capture_record_created",
            "operator_approval_recorded",
            "confirmation_record_created",
            "environment_variables_set",
            "audit_row_created",
            "rollback_row_created",
            "rollback_snapshot_created",
            "platform_db_mutation_performed",
            "bridge_mutation_performed",
            "bridge_post_called",
            "lacrm_call_performed",
            "real_bridge_http_client_implemented",
            "network_transport_implemented",
            "network_transport_enabled",
            "network_transport_armed",
            "network_socket_opened",
            "bridge_http_client_implemented",
            "bridge_post_call_implemented",
            "routing_write_endpoint_implemented",
            "live_write_enabled"
        )

        foreach ($flag in $mustBeFalse) {
            $value = Get-Prop $safety $flag
            if ($value -eq $true) {
                Add-Gate $gates "$($artifact.key)_forbidden_flag_$flag" $false "blocker" "$flag=True" $artifact.key
            }
        }

        foreach ($issue in @($artifact.data.issues)) {
            if ($issue.severity -eq "blocker") {
                Add-Issue $issues "blocker" "$($artifact.key)_$($issue.code)" "$($issue.message)" $artifact.key
            } elseif ($issue.severity -eq "review") {
                Add-Issue $issues "review" "$($artifact.key)_$($issue.code)" "$($issue.message)" $artifact.key
            }
        }
    }
}

# Source-specific hard gates for the full prerequisite chain.
Add-Gate $gates "cutover_packet_prerequisite_gate_design_only" ($cutover.safety.bridge_routing_network_transport_cutover_packet_prerequisite_gate_design_only -eq $true) "blocker" "bridge_routing_network_transport_cutover_packet_prerequisite_gate_design_only=$($cutover.safety.bridge_routing_network_transport_cutover_packet_prerequisite_gate_design_only)" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "cutover_packet_prerequisite_blocks_execution" ($cutover.cutover_packet_prerequisite_gate_design.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($cutover.cutover_packet_prerequisite_gate_design.can_execute_bridge_write_now)" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "cutover_packet_prerequisite_blocks_cutover_packet" ($cutover.cutover_packet_prerequisite_gate_design.can_create_cutover_packet_now -eq $false) "blocker" "can_create_cutover_packet_now=$($cutover.cutover_packet_prerequisite_gate_design.can_create_cutover_packet_now)" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "cutover_packet_prerequisite_blocks_cutover_approval" ($cutover.cutover_packet_prerequisite_gate_design.can_record_cutover_approval_now -eq $false) "blocker" "can_record_cutover_approval_now=$($cutover.cutover_packet_prerequisite_gate_design.can_record_cutover_approval_now)" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "cutover_packet_prerequisite_blocks_socket" ($cutover.cutover_packet_prerequisite_gate_design.can_open_network_socket_now -eq $false) "blocker" "can_open_network_socket_now=$($cutover.cutover_packet_prerequisite_gate_design.can_open_network_socket_now)" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "cutover_packet_prerequisite_blocks_bridge_post" ($cutover.cutover_packet_prerequisite_gate_design.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($cutover.cutover_packet_prerequisite_gate_design.can_add_bridge_post_now)" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "cutover_packet_prerequisite_has_no_blockers" ([int]$cutover.cutover_packet_prerequisite_gate_design.blocker_count -eq 0) "blocker" "blocker_count=$($cutover.cutover_packet_prerequisite_gate_design.blocker_count)" "cutover_packet_prerequisite_gate_design"
Add-Gate $gates "cutover_packet_prerequisite_has_no_review_items" ([int]$cutover.cutover_packet_prerequisite_gate_design.review_count -eq 0) "review" "review_count=$($cutover.cutover_packet_prerequisite_gate_design.review_count)" "cutover_packet_prerequisite_gate_design"

if ($response -ne $null) {
    Add-Gate $gates "response_capture_design_blocks_response_capture" ($response.response_capture_gate_design.can_capture_bridge_response_now -eq $false) "blocker" "can_capture_bridge_response_now=$($response.response_capture_gate_design.can_capture_bridge_response_now)" "response_capture_gate_design"
}
if ($operator -ne $null) {
    Add-Gate $gates "operator_confirmation_design_blocks_approval_records" ($operator.operator_confirmation_gate_design.can_record_operator_approval_now -eq $false) "blocker" "can_record_operator_approval_now=$($operator.operator_confirmation_gate_design.can_record_operator_approval_now)" "operator_confirmation_gate_design"
}
if ($environment -ne $null) {
    Add-Gate $gates "environment_design_blocks_environment_setting" ($environment.environment_gate_design.can_set_environment_variables_now -eq $false) "blocker" "can_set_environment_variables_now=$($environment.environment_gate_design.can_set_environment_variables_now)" "environment_gate_design"
}
if ($rollback -ne $null) {
    Add-Gate $gates "rollback_prerequisite_blocks_snapshots" ($rollback.rollback_snapshot_prerequisite_gate.can_create_rollback_snapshots_now -eq $false) "blocker" "can_create_rollback_snapshots_now=$($rollback.rollback_snapshot_prerequisite_gate.can_create_rollback_snapshots_now)" "rollback_snapshot_prerequisite_gate"
}
if ($audit -ne $null) {
    Add-Gate $gates "audit_prerequisite_blocks_audit_rows" ($audit.audit_prerequisite_gate.can_create_audit_rows_now -eq $false) "blocker" "can_create_audit_rows_now=$($audit.audit_prerequisite_gate.can_create_audit_rows_now)" "audit_prerequisite_gate"
}
if ($release -ne $null) {
    Add-Gate $gates "dry_run_release_checkpoint_blocks_execution" ($release.release_checkpoint.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($release.release_checkpoint.can_execute_bridge_write_now)" "dry_run_invocation_path_release_checkpoint"
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

# Convert failed gates into issues.
foreach ($gate in @($gates)) {
    if ($gate.passed -ne $true) {
        Add-Issue $issues $gate.severity $gate.gate $gate.evidence $gate.source
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$checkpointStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "prerequisite_chain_release_checkpoint_clean_no_write"
} elseif ($blockerCount -eq 0) {
    "prerequisite_chain_release_checkpoint_review_required_no_write"
} else {
    "prerequisite_chain_release_checkpoint_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 30"
    purpose = "Bridge routing network transport prerequisite chain release checkpoint"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_prerequisite_chain_release_checkpoint_only = $true
        bridge_get_only = $true
        prerequisite_chain_checkpoint_only = $true
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
    prerequisite_chain_release_checkpoint = [ordered]@{
        status = $checkpointStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        artifact_count = @($sourceArtifacts).Count
        gate_count = @($gates).Count
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
        release_freeze_label = "phase20_bridge_routing_network_transport_prerequisite_chain_no_write_checkpoint"
        reason = if ($blockerCount -eq 0) {
            "Prerequisite chain release checkpoint is ready for review. Phase 20 Step 30 creates no cutover packet, opens no socket, calls no bridge POST, and authorizes no execution."
        } else {
            "Prerequisite chain release checkpoint has blockers. Resolve blockers before any future real network transport design."
        }
    }
    source_artifacts = $sourceArtifacts
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
        gates = @($gates).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this prerequisite chain release checkpoint before implementing any future network transport scaffold beyond design-only evidence.",
        "Do not create cutover packets from Phase 20 Step 30.",
        "Do not capture bridge responses from Phase 20 Step 30.",
        "Do not record operator approvals from Phase 20 Step 30.",
        "Do not set environment variables from Phase 20 Step 30.",
        "Do not create audit rows or rollback snapshots from Phase 20 Step 30.",
        "Do not call bridge POST endpoints from Phase 20 Step 30.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint.json"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint_artifacts.csv"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): present=$($_.present); $($_.json_path) [$($_.sha256)]" }) -join "`n"
$gateText = (@($gates) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.gate): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Prerequisite Chain Release Checkpoint

Generated: $($report.generated_at)

Source cutover packet prerequisite gate design:

``````
$cutoverPath
``````

## Safety

- Bridge routing network transport prerequisite chain release checkpoint only: true
- Bridge GET only: true
- Prerequisite chain checkpoint only: true
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

## Prerequisite chain release checkpoint

- Status: $checkpointStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Artifacts: $(@($sourceArtifacts).Count)
- Gates: $(@($gates).Count)
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

## Gates

$gateText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_prerequisite_chain_release_checkpoint=$OutputDir | status=$checkpointStatus | bridge_post_called=False | cutover_packet_created=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_prerequisite_chain_release_checkpoint=$OutputDir | status=$checkpointStatus | blockers=$blockerCount | bridge_post_called=False | cutover_packet_created=False"
}

Write-Host ""
Write-Host "Prerequisite chain release checkpoint files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
