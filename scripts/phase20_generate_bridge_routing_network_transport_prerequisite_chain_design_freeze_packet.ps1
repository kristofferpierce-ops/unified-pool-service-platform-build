param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$PrerequisiteChainOperatorSignoffDir = "",
    [string]$PrerequisiteChainReleaseCheckpointDir = "",
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

function Add-ChecklistItem {
    param(
        [System.Collections.ArrayList]$Checklist,
        [string]$Category,
        [string]$Item,
        [bool]$Passed,
        [string]$Evidence,
        [string]$Required = "yes"
    )

    [void]$Checklist.Add([ordered]@{
        category = $Category
        item = $Item
        passed = $Passed
        evidence = $Evidence
        required = $Required
    })
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($PrerequisiteChainOperatorSignoffDir)) {
    $PrerequisiteChainOperatorSignoffDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff_*" -JsonName "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff.json"
}
if ([string]::IsNullOrWhiteSpace($PrerequisiteChainReleaseCheckpointDir)) {
    $PrerequisiteChainReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($CutoverPacketPrerequisiteGateDesignDir)) {
    $CutoverPacketPrerequisiteGateDesignDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design_*" -JsonName "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design.json" -Required $false
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

$signoffPath = Join-Path $PrerequisiteChainOperatorSignoffDir "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff.json"
$checkpointPath = if (![string]::IsNullOrWhiteSpace($PrerequisiteChainReleaseCheckpointDir)) { Join-Path $PrerequisiteChainReleaseCheckpointDir "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint.json" } else { "" }
$cutoverPath = if (![string]::IsNullOrWhiteSpace($CutoverPacketPrerequisiteGateDesignDir)) { Join-Path $CutoverPacketPrerequisiteGateDesignDir "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design.json" } else { "" }
$responsePath = if (![string]::IsNullOrWhiteSpace($ResponseCaptureGateDesignDir)) { Join-Path $ResponseCaptureGateDesignDir "phase20_bridge_routing_network_transport_response_capture_gate_design.json" } else { "" }
$operatorPath = if (![string]::IsNullOrWhiteSpace($OperatorConfirmationGateDesignDir)) { Join-Path $OperatorConfirmationGateDesignDir "phase20_bridge_routing_network_transport_operator_confirmation_gate_design.json" } else { "" }
$environmentPath = if (![string]::IsNullOrWhiteSpace($EnvironmentGateDesignDir)) { Join-Path $EnvironmentGateDesignDir "phase20_bridge_routing_network_transport_environment_gate_design.json" } else { "" }
$rollbackPath = if (![string]::IsNullOrWhiteSpace($RollbackSnapshotPrerequisiteGateDir)) { Join-Path $RollbackSnapshotPrerequisiteGateDir "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.json" } else { "" }
$auditPath = if (![string]::IsNullOrWhiteSpace($AuditPrerequisiteGateDir)) { Join-Path $AuditPrerequisiteGateDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($DryRunInvocationReleaseCheckpointDir)) { Join-Path $DryRunInvocationReleaseCheckpointDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $signoffPath)) {
    throw "Prerequisite chain operator signoff JSON not found: $signoffPath"
}

$signoff = Read-JsonFile $signoffPath
$checkpoint = if (![string]::IsNullOrWhiteSpace($checkpointPath) -and (Test-Path -LiteralPath $checkpointPath)) { Read-JsonFile $checkpointPath } else { $null }
$cutover = if (![string]::IsNullOrWhiteSpace($cutoverPath) -and (Test-Path -LiteralPath $cutoverPath)) { Read-JsonFile $cutoverPath } else { $null }
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
$checklist = New-Object System.Collections.ArrayList

Add-ChecklistItem $checklist "artifact" "Prerequisite chain operator signoff exists" $true $signoffPath
Add-ChecklistItem $checklist "artifact" "Prerequisite chain release checkpoint exists" ($checkpoint -ne $null) $checkpointPath "recommended"
Add-ChecklistItem $checklist "artifact" "Cutover packet prerequisite gate design exists" ($cutover -ne $null) $cutoverPath "recommended"
Add-ChecklistItem $checklist "artifact" "Response capture gate design exists" ($response -ne $null) $responsePath "recommended"
Add-ChecklistItem $checklist "artifact" "Operator confirmation gate design exists" ($operator -ne $null) $operatorPath "recommended"
Add-ChecklistItem $checklist "artifact" "Environment gate design exists" ($environment -ne $null) $environmentPath "recommended"
Add-ChecklistItem $checklist "artifact" "Rollback snapshot prerequisite gate exists" ($rollback -ne $null) $rollbackPath "recommended"
Add-ChecklistItem $checklist "artifact" "Audit prerequisite gate exists" ($audit -ne $null) $auditPath "recommended"
Add-ChecklistItem $checklist "artifact" "Dry-run invocation release checkpoint exists" ($release -ne $null) $releasePath "recommended"

# Signoff source safety.
Add-ChecklistItem $checklist "safety" "Source signoff is operator-signoff-only" ($signoff.safety.bridge_routing_network_transport_prerequisite_chain_operator_signoff_only -eq $true) "bridge_routing_network_transport_prerequisite_chain_operator_signoff_only=$($signoff.safety.bridge_routing_network_transport_prerequisite_chain_operator_signoff_only)"
Add-ChecklistItem $checklist "safety" "Source signoff is bridge GET only" ($signoff.safety.bridge_get_only -eq $true) "bridge_get_only=$($signoff.safety.bridge_get_only)"
Add-ChecklistItem $checklist "safety" "No source operator signoff record was written" ($signoff.safety.operator_signoff_recorded -eq $false) "operator_signoff_recorded=$($signoff.safety.operator_signoff_recorded)"
Add-ChecklistItem $checklist "safety" "No source cutover packet created" ($signoff.safety.cutover_packet_created -eq $false) "cutover_packet_created=$($signoff.safety.cutover_packet_created)"
Add-ChecklistItem $checklist "safety" "No source cutover approval recorded" ($signoff.safety.cutover_approval_recorded -eq $false) "cutover_approval_recorded=$($signoff.safety.cutover_approval_recorded)"
Add-ChecklistItem $checklist "safety" "No source bridge response captured" ($signoff.safety.bridge_response_captured -eq $false) "bridge_response_captured=$($signoff.safety.bridge_response_captured)"
Add-ChecklistItem $checklist "safety" "No source response capture record created" ($signoff.safety.response_capture_record_created -eq $false) "response_capture_record_created=$($signoff.safety.response_capture_record_created)"
Add-ChecklistItem $checklist "safety" "No source operator approval recorded" ($signoff.safety.operator_approval_recorded -eq $false) "operator_approval_recorded=$($signoff.safety.operator_approval_recorded)"
Add-ChecklistItem $checklist "safety" "No source confirmation record created" ($signoff.safety.confirmation_record_created -eq $false) "confirmation_record_created=$($signoff.safety.confirmation_record_created)"
Add-ChecklistItem $checklist "safety" "No source environment variables set" ($signoff.safety.environment_variables_set -eq $false) "environment_variables_set=$($signoff.safety.environment_variables_set)"
Add-ChecklistItem $checklist "safety" "No source audit row created" ($signoff.safety.audit_row_created -eq $false) "audit_row_created=$($signoff.safety.audit_row_created)"
Add-ChecklistItem $checklist "safety" "No source rollback row created" ($signoff.safety.rollback_row_created -eq $false) "rollback_row_created=$($signoff.safety.rollback_row_created)"
Add-ChecklistItem $checklist "safety" "No source rollback snapshot created" ($signoff.safety.rollback_snapshot_created -eq $false) "rollback_snapshot_created=$($signoff.safety.rollback_snapshot_created)"
Add-ChecklistItem $checklist "safety" "No source platform DB mutation" ($signoff.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($signoff.safety.platform_db_mutation_performed)"
Add-ChecklistItem $checklist "safety" "No source bridge mutation" ($signoff.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($signoff.safety.bridge_mutation_performed)"
Add-ChecklistItem $checklist "safety" "No source bridge POST called" ($signoff.safety.bridge_post_called -eq $false) "bridge_post_called=$($signoff.safety.bridge_post_called)"
Add-ChecklistItem $checklist "safety" "No source LACRM call" ($signoff.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($signoff.safety.lacrm_call_performed)"
Add-ChecklistItem $checklist "safety" "No source real bridge HTTP client" ($signoff.safety.real_bridge_http_client_implemented -eq $false) "real_bridge_http_client_implemented=$($signoff.safety.real_bridge_http_client_implemented)"
Add-ChecklistItem $checklist "safety" "No source network transport" ($signoff.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($signoff.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "safety" "No source network transport enabled" ($signoff.safety.network_transport_enabled -eq $false) "network_transport_enabled=$($signoff.safety.network_transport_enabled)"
Add-ChecklistItem $checklist "safety" "No source network transport armed" ($signoff.safety.network_transport_armed -eq $false) "network_transport_armed=$($signoff.safety.network_transport_armed)"
Add-ChecklistItem $checklist "safety" "No source socket opened" ($signoff.safety.network_socket_opened -eq $false) "network_socket_opened=$($signoff.safety.network_socket_opened)"
Add-ChecklistItem $checklist "safety" "No source bridge POST implementation" ($signoff.safety.bridge_post_call_implemented -eq $false) "bridge_post_call_implemented=$($signoff.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "safety" "No source routing write endpoint" ($signoff.safety.routing_write_endpoint_implemented -eq $false) "routing_write_endpoint_implemented=$($signoff.safety.routing_write_endpoint_implemented)"
Add-ChecklistItem $checklist "safety" "Source live write remains disabled" ($signoff.safety.live_write_enabled -eq $false) "live_write_enabled=$($signoff.safety.live_write_enabled)"

# Source signoff gates.
Add-ChecklistItem $checklist "gate" "Source signoff blocks bridge write execution" ($signoff.prerequisite_chain_operator_signoff.can_execute_bridge_write_now -eq $false) "can_execute_bridge_write_now=$($signoff.prerequisite_chain_operator_signoff.can_execute_bridge_write_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks network transport" ($signoff.prerequisite_chain_operator_signoff.can_add_network_transport_now -eq $false) "can_add_network_transport_now=$($signoff.prerequisite_chain_operator_signoff.can_add_network_transport_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks network enablement" ($signoff.prerequisite_chain_operator_signoff.can_enable_network_transport_now -eq $false) "can_enable_network_transport_now=$($signoff.prerequisite_chain_operator_signoff.can_enable_network_transport_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks network arming" ($signoff.prerequisite_chain_operator_signoff.can_arm_network_transport_now -eq $false) "can_arm_network_transport_now=$($signoff.prerequisite_chain_operator_signoff.can_arm_network_transport_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks socket opening" ($signoff.prerequisite_chain_operator_signoff.can_open_network_socket_now -eq $false) "can_open_network_socket_now=$($signoff.prerequisite_chain_operator_signoff.can_open_network_socket_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks bridge POST" ($signoff.prerequisite_chain_operator_signoff.can_add_bridge_post_now -eq $false) "can_add_bridge_post_now=$($signoff.prerequisite_chain_operator_signoff.can_add_bridge_post_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks cutover packet creation" ($signoff.prerequisite_chain_operator_signoff.can_create_cutover_packet_now -eq $false) "can_create_cutover_packet_now=$($signoff.prerequisite_chain_operator_signoff.can_create_cutover_packet_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks cutover approval recording" ($signoff.prerequisite_chain_operator_signoff.can_record_cutover_approval_now -eq $false) "can_record_cutover_approval_now=$($signoff.prerequisite_chain_operator_signoff.can_record_cutover_approval_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks response capture" ($signoff.prerequisite_chain_operator_signoff.can_capture_bridge_response_now -eq $false) "can_capture_bridge_response_now=$($signoff.prerequisite_chain_operator_signoff.can_capture_bridge_response_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks response capture records" ($signoff.prerequisite_chain_operator_signoff.can_create_response_capture_records_now -eq $false) "can_create_response_capture_records_now=$($signoff.prerequisite_chain_operator_signoff.can_create_response_capture_records_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks operator approval records" ($signoff.prerequisite_chain_operator_signoff.can_record_operator_approval_now -eq $false) "can_record_operator_approval_now=$($signoff.prerequisite_chain_operator_signoff.can_record_operator_approval_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks confirmation records" ($signoff.prerequisite_chain_operator_signoff.can_create_confirmation_records_now -eq $false) "can_create_confirmation_records_now=$($signoff.prerequisite_chain_operator_signoff.can_create_confirmation_records_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks environment changes" ($signoff.prerequisite_chain_operator_signoff.can_set_environment_variables_now -eq $false) "can_set_environment_variables_now=$($signoff.prerequisite_chain_operator_signoff.can_set_environment_variables_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks audit rows" ($signoff.prerequisite_chain_operator_signoff.can_create_audit_rows_now -eq $false) "can_create_audit_rows_now=$($signoff.prerequisite_chain_operator_signoff.can_create_audit_rows_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks rollback rows" ($signoff.prerequisite_chain_operator_signoff.can_create_rollback_rows_now -eq $false) "can_create_rollback_rows_now=$($signoff.prerequisite_chain_operator_signoff.can_create_rollback_rows_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks rollback snapshots" ($signoff.prerequisite_chain_operator_signoff.can_create_rollback_snapshots_now -eq $false) "can_create_rollback_snapshots_now=$($signoff.prerequisite_chain_operator_signoff.can_create_rollback_snapshots_now)"
Add-ChecklistItem $checklist "gate" "Source signoff blocks signoff records" ($signoff.prerequisite_chain_operator_signoff.can_record_operator_signoff_now -eq $false) "can_record_operator_signoff_now=$($signoff.prerequisite_chain_operator_signoff.can_record_operator_signoff_now)"
Add-ChecklistItem $checklist "gate" "Source signoff has no blockers" ([int]$signoff.prerequisite_chain_operator_signoff.blocker_count -eq 0) "blocker_count=$($signoff.prerequisite_chain_operator_signoff.blocker_count)"
Add-ChecklistItem $checklist "gate" "Source signoff has no review items" ([int]$signoff.prerequisite_chain_operator_signoff.review_count -eq 0) "review_count=$($signoff.prerequisite_chain_operator_signoff.review_count)" "recommended"

foreach ($issue in @($signoff.issues)) {
    if ($issue.severity -eq "blocker") {
        Add-Issue $issues "blocker" "source_signoff_$($issue.code)" "$($issue.message)" "prerequisite_chain_operator_signoff"
    } elseif ($issue.severity -eq "review") {
        Add-Issue $issues "review" "source_signoff_$($issue.code)" "$($issue.message)" "prerequisite_chain_operator_signoff"
    }
}

# Optional upstream cross-checks.
if ($checkpoint -ne $null) {
    Add-ChecklistItem $checklist "upstream" "Release checkpoint blocks execution" ($checkpoint.prerequisite_chain_release_checkpoint.can_execute_bridge_write_now -eq $false) "can_execute_bridge_write_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_execute_bridge_write_now)"
    Add-ChecklistItem $checklist "upstream" "Release checkpoint blocks bridge POST" ($checkpoint.prerequisite_chain_release_checkpoint.can_add_bridge_post_now -eq $false) "can_add_bridge_post_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_add_bridge_post_now)"
}
if ($cutover -ne $null) {
    Add-ChecklistItem $checklist "upstream" "Cutover prerequisite design blocks cutover packet creation" ($cutover.cutover_packet_prerequisite_gate_design.can_create_cutover_packet_now -eq $false) "can_create_cutover_packet_now=$($cutover.cutover_packet_prerequisite_gate_design.can_create_cutover_packet_now)"
}
if ($response -ne $null) {
    Add-ChecklistItem $checklist "upstream" "Response capture design blocks response capture" ($response.response_capture_gate_design.can_capture_bridge_response_now -eq $false) "can_capture_bridge_response_now=$($response.response_capture_gate_design.can_capture_bridge_response_now)"
}
if ($operator -ne $null) {
    Add-ChecklistItem $checklist "upstream" "Operator confirmation design blocks approval records" ($operator.operator_confirmation_gate_design.can_record_operator_approval_now -eq $false) "can_record_operator_approval_now=$($operator.operator_confirmation_gate_design.can_record_operator_approval_now)"
}
if ($environment -ne $null) {
    Add-ChecklistItem $checklist "upstream" "Environment design blocks environment changes" ($environment.environment_gate_design.can_set_environment_variables_now -eq $false) "can_set_environment_variables_now=$($environment.environment_gate_design.can_set_environment_variables_now)"
}
if ($rollback -ne $null) {
    Add-ChecklistItem $checklist "upstream" "Rollback prerequisite blocks rollback snapshots" ($rollback.rollback_snapshot_prerequisite_gate.can_create_rollback_snapshots_now -eq $false) "can_create_rollback_snapshots_now=$($rollback.rollback_snapshot_prerequisite_gate.can_create_rollback_snapshots_now)"
}
if ($audit -ne $null) {
    Add-ChecklistItem $checklist "upstream" "Audit prerequisite blocks audit rows" ($audit.audit_prerequisite_gate.can_create_audit_rows_now -eq $false) "can_create_audit_rows_now=$($audit.audit_prerequisite_gate.can_create_audit_rows_now)"
}
if ($release -ne $null) {
    Add-ChecklistItem $checklist "upstream" "Dry-run invocation release checkpoint blocks execution" ($release.release_checkpoint.can_execute_bridge_write_now -eq $false) "can_execute_bridge_write_now=$($release.release_checkpoint.can_execute_bridge_write_now)"
}

# Runtime checks.
if ($invocationStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Dry-run invocation path status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status" "recommended"
    Add-ChecklistItem $checklist "runtime" "Runtime dry-run invocation has no network transport" ($invocationStatus.value.network_transport_implemented -eq $false) "network_transport_implemented=$($invocationStatus.value.network_transport_implemented)"
    Add-ChecklistItem $checklist "runtime" "Runtime dry-run invocation has no socket opened" ($invocationStatus.value.network_socket_opened -eq $false) "network_socket_opened=$($invocationStatus.value.network_socket_opened)"
    Add-ChecklistItem $checklist "runtime" "Runtime dry-run invocation has no bridge POST" ($invocationStatus.value.bridge_post_called -eq $false -and $invocationStatus.value.bridge_post_call_implemented -eq $false) "bridge_post_called=$($invocationStatus.value.bridge_post_called); bridge_post_call_implemented=$($invocationStatus.value.bridge_post_call_implemented)"
} else {
    Add-ChecklistItem $checklist "runtime" "Dry-run invocation path status readable" $false $invocationStatus.error "recommended"
}

if ($scaffoldStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Interface scaffold status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status" "recommended"
    Add-ChecklistItem $checklist "runtime" "Runtime scaffold has no network transport" ($scaffoldStatus.value.network_transport_implemented -eq $false) "network_transport_implemented=$($scaffoldStatus.value.network_transport_implemented)"
} else {
    Add-ChecklistItem $checklist "runtime" "Interface scaffold status readable" $false $scaffoldStatus.error "recommended"
}

if ($adapterStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Dry-run adapter status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status" "recommended"
    Add-ChecklistItem $checklist "runtime" "Runtime adapter has no network transport" ($adapterStatus.value.network_transport_implemented -eq $false) "network_transport_implemented=$($adapterStatus.value.network_transport_implemented)"
} else {
    Add-ChecklistItem $checklist "runtime" "Dry-run adapter status readable" $false $adapterStatus.error "recommended"
}

if ($guardStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Network transport guard status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status" "recommended"
    Add-ChecklistItem $checklist "runtime" "Runtime guard has no network transport" ($guardStatus.value.network_transport_implemented -eq $false) "network_transport_implemented=$($guardStatus.value.network_transport_implemented)"
} else {
    Add-ChecklistItem $checklist "runtime" "Network transport guard status readable" $false $guardStatus.error "recommended"
}

if ($httpDryRunStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "HTTP client dry-run status readable" $true "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status" "recommended"
    Add-ChecklistItem $checklist "runtime" "HTTP client dry-run has no network transport" ($httpDryRunStatus.value.network_transport_implemented -eq $false) "network_transport_implemented=$($httpDryRunStatus.value.network_transport_implemented)"
} else {
    Add-ChecklistItem $checklist "runtime" "HTTP client dry-run status readable" $false $httpDryRunStatus.error "recommended"
}

if ($executorStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Executor status readable" $true "$PlatformApi/front-desk/routing/bridge-write-executor/status" "recommended"
    Add-ChecklistItem $checklist "runtime" "Executor has no execution endpoint" ($executorStatus.value.execution_endpoint_available -eq $false) "execution_endpoint_available=$($executorStatus.value.execution_endpoint_available)"
    Add-ChecklistItem $checklist "runtime" "Executor has no bridge POST implementation" ($executorStatus.value.bridge_post_call_implemented -eq $false) "bridge_post_call_implemented=$($executorStatus.value.bridge_post_call_implemented)"
} else {
    Add-ChecklistItem $checklist "runtime" "Executor status readable" $false $executorStatus.error "recommended"
}

Add-ChecklistItem $checklist "runtime" "Bridge health readable" $bridgeHealth.ok $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "recommended"

# Convert failed checklist entries into issues.
foreach ($item in @($checklist)) {
    if ($item.passed -ne $true -and $item.required -eq "yes") {
        Add-Issue $issues "blocker" ("checklist_" + ($item.item -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $item.evidence $item.category
    } elseif ($item.passed -ne $true -and $item.required -eq "recommended") {
        Add-Issue $issues "review" ("checklist_" + ($item.item -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $item.evidence $item.category
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$freezeStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "design_freeze_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "design_freeze_packet_review_required_no_write"
} else {
    "design_freeze_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="prerequisite_chain_operator_signoff"; json_path=$signoffPath; sha256=Get-FileSha256 $signoffPath },
    [ordered]@{ key="prerequisite_chain_release_checkpoint"; json_path=$checkpointPath; sha256=Get-FileSha256 $checkpointPath },
    [ordered]@{ key="cutover_packet_prerequisite_gate_design"; json_path=$cutoverPath; sha256=Get-FileSha256 $cutoverPath },
    [ordered]@{ key="response_capture_gate_design"; json_path=$responsePath; sha256=Get-FileSha256 $responsePath },
    [ordered]@{ key="operator_confirmation_gate_design"; json_path=$operatorPath; sha256=Get-FileSha256 $operatorPath },
    [ordered]@{ key="environment_gate_design"; json_path=$environmentPath; sha256=Get-FileSha256 $environmentPath },
    [ordered]@{ key="rollback_snapshot_prerequisite_gate"; json_path=$rollbackPath; sha256=Get-FileSha256 $rollbackPath },
    [ordered]@{ key="audit_prerequisite_gate"; json_path=$auditPath; sha256=Get-FileSha256 $auditPath },
    [ordered]@{ key="dry_run_invocation_release_checkpoint"; json_path=$releasePath; sha256=Get-FileSha256 $releasePath }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 32"
    purpose = "Bridge routing network transport prerequisite chain design freeze packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_only = $true
        bridge_get_only = $true
        design_freeze_packet_only = $true
        design_freeze_record_created = $false
        operator_signoff_recorded = $false
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
    prerequisite_chain_design_freeze_packet = [ordered]@{
        status = $freezeStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        checklist_count = @($checklist).Count
        artifact_count = @($sourceArtifacts).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        can_add_bridge_post_now = $false
        can_create_design_freeze_record_now = $false
        can_record_operator_signoff_now = $false
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
        freeze_label = "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_no_write"
        reason = if ($blockerCount -eq 0) {
            "Prerequisite chain design freeze packet is ready for review. Phase 20 Step 32 creates no design-freeze record, no signoff record, no cutover packet, opens no socket, calls no bridge POST, and authorizes no execution."
        } else {
            "Prerequisite chain design freeze packet has blockers. Resolve blockers before any future real network transport design."
        }
    }
    source_artifacts = $sourceArtifacts
    checklist = @($checklist)
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
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this design freeze packet before starting any future implementation step.",
        "Do not create design-freeze records from Phase 20 Step 32.",
        "Do not record operator signoffs from Phase 20 Step 32.",
        "Do not create cutover packets from Phase 20 Step 32.",
        "Do not capture bridge responses from Phase 20 Step 32.",
        "Do not set environment variables from Phase 20 Step 32.",
        "Do not create audit rows or rollback snapshots from Phase 20 Step 32.",
        "Do not call bridge POST endpoints from Phase 20 Step 32.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet.json"
$checklistCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_checklist.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_artifacts.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Prerequisite Chain Design Freeze Packet

Generated: $($report.generated_at)

Source prerequisite chain operator signoff:

``````
$signoffPath
``````

## Safety

- Bridge routing network transport prerequisite chain design freeze packet only: true
- Bridge GET only: true
- Design freeze packet only: true
- Design freeze record created: false
- Operator signoff recorded: false
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

## Design freeze packet

- Status: $freezeStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Checklist items: $(@($checklist).Count)
- Source artifacts: $(@($sourceArtifacts).Count)
- Can execute bridge write now: false
- Can add network transport now: false
- Can enable network transport now: false
- Can arm network transport now: false
- Can open network socket now: false
- Can add real bridge HTTP client now: false
- Can add bridge POST now: false
- Can create design freeze record now: false
- Can record operator signoff now: false
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

## Checklist

$checklistText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_prerequisite_chain_design_freeze_packet=$OutputDir | status=$freezeStatus | bridge_post_called=False | design_freeze_record_created=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_prerequisite_chain_design_freeze_packet=$OutputDir | status=$freezeStatus | blockers=$blockerCount | bridge_post_called=False | design_freeze_record_created=False"
}

Write-Host ""
Write-Host "Prerequisite chain design freeze packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
