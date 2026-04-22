param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$PrerequisiteChainReleaseCheckpointDir = "",
    [string]$CutoverPacketPrerequisiteGateDesignDir = "",
    [string]$ResponseCaptureGateDesignDir = "",
    [string]$OperatorConfirmationGateDesignDir = "",
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
        [string]$Required = "yes",
        [string]$OperatorNote = ""
    )

    [void]$Checklist.Add([ordered]@{
        category = $Category
        item = $Item
        passed = $Passed
        evidence = $Evidence
        required = $Required
        operator_note = $OperatorNote
    })
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($PrerequisiteChainReleaseCheckpointDir)) {
    $PrerequisiteChainReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint.json"
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

$checkpointPath = Join-Path $PrerequisiteChainReleaseCheckpointDir "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint.json"
$cutoverPath = if (![string]::IsNullOrWhiteSpace($CutoverPacketPrerequisiteGateDesignDir)) { Join-Path $CutoverPacketPrerequisiteGateDesignDir "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design.json" } else { "" }
$responsePath = if (![string]::IsNullOrWhiteSpace($ResponseCaptureGateDesignDir)) { Join-Path $ResponseCaptureGateDesignDir "phase20_bridge_routing_network_transport_response_capture_gate_design.json" } else { "" }
$operatorPath = if (![string]::IsNullOrWhiteSpace($OperatorConfirmationGateDesignDir)) { Join-Path $OperatorConfirmationGateDesignDir "phase20_bridge_routing_network_transport_operator_confirmation_gate_design.json" } else { "" }

if (!(Test-Path -LiteralPath $checkpointPath)) {
    throw "Prerequisite chain release checkpoint JSON not found: $checkpointPath"
}

$checkpoint = Read-JsonFile $checkpointPath
$cutover = if (![string]::IsNullOrWhiteSpace($cutoverPath) -and (Test-Path -LiteralPath $cutoverPath)) { Read-JsonFile $cutoverPath } else { $null }
$response = if (![string]::IsNullOrWhiteSpace($responsePath) -and (Test-Path -LiteralPath $responsePath)) { Read-JsonFile $responsePath } else { $null }
$operator = if (![string]::IsNullOrWhiteSpace($operatorPath) -and (Test-Path -LiteralPath $operatorPath)) { Read-JsonFile $operatorPath } else { $null }

$invocationStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList

Add-ChecklistItem $checklist "artifact" "Prerequisite chain release checkpoint exists" $true $checkpointPath
Add-ChecklistItem $checklist "artifact" "Cutover packet prerequisite gate design exists" ($cutover -ne $null) $cutoverPath "recommended"
Add-ChecklistItem $checklist "artifact" "Response capture gate design exists" ($response -ne $null) $responsePath "recommended"
Add-ChecklistItem $checklist "artifact" "Operator confirmation gate design exists" ($operator -ne $null) $operatorPath "recommended"

# Checkpoint safety.
Add-ChecklistItem $checklist "safety" "Checkpoint is prerequisite-chain-release-checkpoint-only" ($checkpoint.safety.bridge_routing_network_transport_prerequisite_chain_release_checkpoint_only -eq $true) "bridge_routing_network_transport_prerequisite_chain_release_checkpoint_only=$($checkpoint.safety.bridge_routing_network_transport_prerequisite_chain_release_checkpoint_only)"
Add-ChecklistItem $checklist "safety" "Checkpoint is bridge GET only" ($checkpoint.safety.bridge_get_only -eq $true) "bridge_get_only=$($checkpoint.safety.bridge_get_only)"
Add-ChecklistItem $checklist "safety" "No cutover packet created" ($checkpoint.safety.cutover_packet_created -eq $false) "cutover_packet_created=$($checkpoint.safety.cutover_packet_created)"
Add-ChecklistItem $checklist "safety" "No cutover approval recorded" ($checkpoint.safety.cutover_approval_recorded -eq $false) "cutover_approval_recorded=$($checkpoint.safety.cutover_approval_recorded)"
Add-ChecklistItem $checklist "safety" "No bridge response captured" ($checkpoint.safety.bridge_response_captured -eq $false) "bridge_response_captured=$($checkpoint.safety.bridge_response_captured)"
Add-ChecklistItem $checklist "safety" "No response capture record created" ($checkpoint.safety.response_capture_record_created -eq $false) "response_capture_record_created=$($checkpoint.safety.response_capture_record_created)"
Add-ChecklistItem $checklist "safety" "No operator approval recorded" ($checkpoint.safety.operator_approval_recorded -eq $false) "operator_approval_recorded=$($checkpoint.safety.operator_approval_recorded)"
Add-ChecklistItem $checklist "safety" "No confirmation record created" ($checkpoint.safety.confirmation_record_created -eq $false) "confirmation_record_created=$($checkpoint.safety.confirmation_record_created)"
Add-ChecklistItem $checklist "safety" "No environment variables set" ($checkpoint.safety.environment_variables_set -eq $false) "environment_variables_set=$($checkpoint.safety.environment_variables_set)"
Add-ChecklistItem $checklist "safety" "No audit row created" ($checkpoint.safety.audit_row_created -eq $false) "audit_row_created=$($checkpoint.safety.audit_row_created)"
Add-ChecklistItem $checklist "safety" "No rollback row created" ($checkpoint.safety.rollback_row_created -eq $false) "rollback_row_created=$($checkpoint.safety.rollback_row_created)"
Add-ChecklistItem $checklist "safety" "No rollback snapshot created" ($checkpoint.safety.rollback_snapshot_created -eq $false) "rollback_snapshot_created=$($checkpoint.safety.rollback_snapshot_created)"
Add-ChecklistItem $checklist "safety" "No platform DB mutation" ($checkpoint.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($checkpoint.safety.platform_db_mutation_performed)"
Add-ChecklistItem $checklist "safety" "No bridge mutation" ($checkpoint.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($checkpoint.safety.bridge_mutation_performed)"
Add-ChecklistItem $checklist "safety" "No bridge POST called" ($checkpoint.safety.bridge_post_called -eq $false) "bridge_post_called=$($checkpoint.safety.bridge_post_called)"
Add-ChecklistItem $checklist "safety" "No LACRM call" ($checkpoint.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($checkpoint.safety.lacrm_call_performed)"
Add-ChecklistItem $checklist "safety" "No real bridge HTTP client" ($checkpoint.safety.real_bridge_http_client_implemented -eq $false) "real_bridge_http_client_implemented=$($checkpoint.safety.real_bridge_http_client_implemented)"
Add-ChecklistItem $checklist "safety" "No network transport" ($checkpoint.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($checkpoint.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "safety" "No network transport enabled" ($checkpoint.safety.network_transport_enabled -eq $false) "network_transport_enabled=$($checkpoint.safety.network_transport_enabled)"
Add-ChecklistItem $checklist "safety" "No network transport armed" ($checkpoint.safety.network_transport_armed -eq $false) "network_transport_armed=$($checkpoint.safety.network_transport_armed)"
Add-ChecklistItem $checklist "safety" "No socket opened" ($checkpoint.safety.network_socket_opened -eq $false) "network_socket_opened=$($checkpoint.safety.network_socket_opened)"
Add-ChecklistItem $checklist "safety" "No bridge POST implementation" ($checkpoint.safety.bridge_post_call_implemented -eq $false) "bridge_post_call_implemented=$($checkpoint.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "safety" "No routing write endpoint" ($checkpoint.safety.routing_write_endpoint_implemented -eq $false) "routing_write_endpoint_implemented=$($checkpoint.safety.routing_write_endpoint_implemented)"
Add-ChecklistItem $checklist "safety" "Live write remains disabled" ($checkpoint.safety.live_write_enabled -eq $false) "live_write_enabled=$($checkpoint.safety.live_write_enabled)"

# Checkpoint gates.
Add-ChecklistItem $checklist "gate" "Checkpoint blocks bridge write execution" ($checkpoint.prerequisite_chain_release_checkpoint.can_execute_bridge_write_now -eq $false) "can_execute_bridge_write_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_execute_bridge_write_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks network transport" ($checkpoint.prerequisite_chain_release_checkpoint.can_add_network_transport_now -eq $false) "can_add_network_transport_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_add_network_transport_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks network enablement" ($checkpoint.prerequisite_chain_release_checkpoint.can_enable_network_transport_now -eq $false) "can_enable_network_transport_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_enable_network_transport_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks network arming" ($checkpoint.prerequisite_chain_release_checkpoint.can_arm_network_transport_now -eq $false) "can_arm_network_transport_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_arm_network_transport_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks socket opening" ($checkpoint.prerequisite_chain_release_checkpoint.can_open_network_socket_now -eq $false) "can_open_network_socket_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_open_network_socket_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks bridge POST" ($checkpoint.prerequisite_chain_release_checkpoint.can_add_bridge_post_now -eq $false) "can_add_bridge_post_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_add_bridge_post_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks cutover packet creation" ($checkpoint.prerequisite_chain_release_checkpoint.can_create_cutover_packet_now -eq $false) "can_create_cutover_packet_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_create_cutover_packet_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks cutover approval recording" ($checkpoint.prerequisite_chain_release_checkpoint.can_record_cutover_approval_now -eq $false) "can_record_cutover_approval_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_record_cutover_approval_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks response capture" ($checkpoint.prerequisite_chain_release_checkpoint.can_capture_bridge_response_now -eq $false) "can_capture_bridge_response_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_capture_bridge_response_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks response capture records" ($checkpoint.prerequisite_chain_release_checkpoint.can_create_response_capture_records_now -eq $false) "can_create_response_capture_records_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_create_response_capture_records_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks operator approval records" ($checkpoint.prerequisite_chain_release_checkpoint.can_record_operator_approval_now -eq $false) "can_record_operator_approval_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_record_operator_approval_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks confirmation records" ($checkpoint.prerequisite_chain_release_checkpoint.can_create_confirmation_records_now -eq $false) "can_create_confirmation_records_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_create_confirmation_records_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks environment changes" ($checkpoint.prerequisite_chain_release_checkpoint.can_set_environment_variables_now -eq $false) "can_set_environment_variables_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_set_environment_variables_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks audit rows" ($checkpoint.prerequisite_chain_release_checkpoint.can_create_audit_rows_now -eq $false) "can_create_audit_rows_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_create_audit_rows_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks rollback rows" ($checkpoint.prerequisite_chain_release_checkpoint.can_create_rollback_rows_now -eq $false) "can_create_rollback_rows_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_create_rollback_rows_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint blocks rollback snapshots" ($checkpoint.prerequisite_chain_release_checkpoint.can_create_rollback_snapshots_now -eq $false) "can_create_rollback_snapshots_now=$($checkpoint.prerequisite_chain_release_checkpoint.can_create_rollback_snapshots_now)"
Add-ChecklistItem $checklist "gate" "Checkpoint has no blockers" ([int]$checkpoint.prerequisite_chain_release_checkpoint.blocker_count -eq 0) "blocker_count=$($checkpoint.prerequisite_chain_release_checkpoint.blocker_count)"
Add-ChecklistItem $checklist "gate" "Checkpoint has no review items" ([int]$checkpoint.prerequisite_chain_release_checkpoint.review_count -eq 0) "review_count=$($checkpoint.prerequisite_chain_release_checkpoint.review_count)" "recommended"

foreach ($issue in @($checkpoint.issues)) {
    if ($issue.severity -eq "blocker") {
        Add-Issue $issues "blocker" "checkpoint_$($issue.code)" "$($issue.message)" "prerequisite_chain_release_checkpoint"
    } elseif ($issue.severity -eq "review") {
        Add-Issue $issues "review" "checkpoint_$($issue.code)" "$($issue.message)" "prerequisite_chain_release_checkpoint"
    }
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

$signoffStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "operator_signoff_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "operator_signoff_review_required_no_write"
} else {
    "operator_signoff_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="prerequisite_chain_release_checkpoint"; json_path=$checkpointPath; sha256=Get-FileSha256 $checkpointPath },
    [ordered]@{ key="cutover_packet_prerequisite_gate_design"; json_path=$cutoverPath; sha256=Get-FileSha256 $cutoverPath },
    [ordered]@{ key="response_capture_gate_design"; json_path=$responsePath; sha256=Get-FileSha256 $responsePath },
    [ordered]@{ key="operator_confirmation_gate_design"; json_path=$operatorPath; sha256=Get-FileSha256 $operatorPath }
)

$operatorAttestation = [ordered]@{
    operator_name = ""
    reviewed_at = ""
    approved_for_future_design_review_only = $false
    approved_for_live_bridge_write = $false
    approved_for_real_network_transport = $false
    approved_to_enable_network_transport = $false
    approved_to_arm_network_transport = $false
    approved_to_open_network_socket = $false
    approved_to_add_bridge_post = $false
    approved_to_create_cutover_packet = $false
    required_statement = "I reviewed the prerequisite chain release checkpoint and understand this packet does not authorize live bridge routing writes, real bridge network transport, bridge POST calls, cutover packet creation, or opening network sockets."
    notes = ""
}

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 31"
    purpose = "Bridge routing network transport prerequisite chain operator signoff"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_prerequisite_chain_operator_signoff_only = $true
        bridge_get_only = $true
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
    prerequisite_chain_operator_signoff = [ordered]@{
        status = $signoffStatus
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
        can_record_operator_signoff_now = $false
        reason = if ($blockerCount -eq 0) {
            "Prerequisite chain operator signoff dossier is ready for review. Phase 20 Step 31 records no signoff, creates no cutover packet, opens no socket, calls no bridge POST, and authorizes no execution."
        } else {
            "Prerequisite chain operator signoff dossier has blockers. Resolve blockers before any future real network transport design."
        }
    }
    source_artifacts = $sourceArtifacts
    operator_attestation = $operatorAttestation
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
        "Review this prerequisite chain operator signoff dossier before implementing any future signoff-record writes.",
        "Do not record operator signoffs from Phase 20 Step 31.",
        "Do not create cutover packets from Phase 20 Step 31.",
        "Do not capture bridge responses from Phase 20 Step 31.",
        "Do not set environment variables from Phase 20 Step 31.",
        "Do not create audit rows or rollback snapshots from Phase 20 Step 31.",
        "Do not call bridge POST endpoints from Phase 20 Step 31.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff.json"
$checklistCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff_checklist.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff_artifacts.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Prerequisite Chain Operator Signoff

Generated: $($report.generated_at)

Source prerequisite chain release checkpoint:

``````
$checkpointPath
``````

## Safety

- Bridge routing network transport prerequisite chain operator signoff only: true
- Bridge GET only: true
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

## Operator signoff dossier

- Status: $signoffStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Checklist items: $(@($checklist).Count)
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
- Can record operator signoff now: false

## Source artifacts

$artifactText

## Checklist

$checklistText

## Issues

$issueText

## Operator attestation

- Operator name:
- Reviewed at:
- Approved for future design review only: false
- Approved for live bridge write: false
- Approved for real network transport: false
- Approved to enable network transport: false
- Approved to arm network transport: false
- Approved to open network socket: false
- Approved to add bridge POST: false
- Approved to create cutover packet: false
- Required statement: I reviewed the prerequisite chain release checkpoint and understand this packet does not authorize live bridge routing writes, real bridge network transport, bridge POST calls, cutover packet creation, or opening network sockets.
- Notes:
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_prerequisite_chain_operator_signoff=$OutputDir | status=$signoffStatus | bridge_post_called=False | operator_signoff_recorded=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_prerequisite_chain_operator_signoff=$OutputDir | status=$signoffStatus | blockers=$blockerCount | bridge_post_called=False | operator_signoff_recorded=False"
}

Write-Host ""
Write-Host "Prerequisite chain operator signoff files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
