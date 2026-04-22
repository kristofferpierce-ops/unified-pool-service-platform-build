param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$DesignFreezePacketDir = "",
    [string]$PrerequisiteChainOperatorSignoffDir = "",
    [string]$PrerequisiteChainReleaseCheckpointDir = "",
    [string]$CutoverPacketPrerequisiteGateDesignDir = "",
    [string]$ResponseCaptureGateDesignDir = "",
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

function Add-Boundary {
    param(
        [System.Collections.ArrayList]$Boundaries,
        [string]$Category,
        [string]$BoundaryName,
        [string]$CurrentStepValue,
        [string]$AllowedFutureValue,
        [string]$Reason,
        [bool]$Satisfied = $true,
        [string]$Severity = "blocker"
    )

    [void]$Boundaries.Add([ordered]@{
        category = $Category
        boundary_name = $BoundaryName
        current_step_value = $CurrentStepValue
        allowed_future_value = $AllowedFutureValue
        reason = $Reason
        satisfied = $Satisfied
        severity = $Severity
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

if ([string]::IsNullOrWhiteSpace($DesignFreezePacketDir)) {
    $DesignFreezePacketDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_*" -JsonName "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet.json"
}
if ([string]::IsNullOrWhiteSpace($PrerequisiteChainOperatorSignoffDir)) {
    $PrerequisiteChainOperatorSignoffDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff_*" -JsonName "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff.json" -Required $false
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

$freezePath = Join-Path $DesignFreezePacketDir "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet.json"
$signoffPath = if (![string]::IsNullOrWhiteSpace($PrerequisiteChainOperatorSignoffDir)) { Join-Path $PrerequisiteChainOperatorSignoffDir "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff.json" } else { "" }
$checkpointPath = if (![string]::IsNullOrWhiteSpace($PrerequisiteChainReleaseCheckpointDir)) { Join-Path $PrerequisiteChainReleaseCheckpointDir "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint.json" } else { "" }
$cutoverPath = if (![string]::IsNullOrWhiteSpace($CutoverPacketPrerequisiteGateDesignDir)) { Join-Path $CutoverPacketPrerequisiteGateDesignDir "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design.json" } else { "" }
$responsePath = if (![string]::IsNullOrWhiteSpace($ResponseCaptureGateDesignDir)) { Join-Path $ResponseCaptureGateDesignDir "phase20_bridge_routing_network_transport_response_capture_gate_design.json" } else { "" }

if (!(Test-Path -LiteralPath $freezePath)) {
    throw "Prerequisite chain design freeze packet JSON not found: $freezePath"
}

$freeze = Read-JsonFile $freezePath
$signoff = if (![string]::IsNullOrWhiteSpace($signoffPath) -and (Test-Path -LiteralPath $signoffPath)) { Read-JsonFile $signoffPath } else { $null }
$checkpoint = if (![string]::IsNullOrWhiteSpace($checkpointPath) -and (Test-Path -LiteralPath $checkpointPath)) { Read-JsonFile $checkpointPath } else { $null }
$cutover = if (![string]::IsNullOrWhiteSpace($cutoverPath) -and (Test-Path -LiteralPath $cutoverPath)) { Read-JsonFile $cutoverPath } else { $null }
$response = if (![string]::IsNullOrWhiteSpace($responsePath) -and (Test-Path -LiteralPath $responsePath)) { Read-JsonFile $responsePath } else { $null }

$invocationStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList
$boundaries = New-Object System.Collections.ArrayList

Add-ChecklistItem $checklist "artifact" "Design freeze packet exists" $true $freezePath
Add-ChecklistItem $checklist "artifact" "Prerequisite chain operator signoff exists" ($signoff -ne $null) $signoffPath "recommended"
Add-ChecklistItem $checklist "artifact" "Prerequisite chain release checkpoint exists" ($checkpoint -ne $null) $checkpointPath "recommended"
Add-ChecklistItem $checklist "artifact" "Cutover packet prerequisite gate design exists" ($cutover -ne $null) $cutoverPath "recommended"
Add-ChecklistItem $checklist "artifact" "Response capture gate design exists" ($response -ne $null) $responsePath "recommended"

# Freeze packet safety.
Add-ChecklistItem $checklist "safety" "Source packet is design-freeze-packet-only" ($freeze.safety.bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_only -eq $true) "bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_only=$($freeze.safety.bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_only)"
Add-ChecklistItem $checklist "safety" "Source packet is bridge GET only" ($freeze.safety.bridge_get_only -eq $true) "bridge_get_only=$($freeze.safety.bridge_get_only)"
Add-ChecklistItem $checklist "safety" "No design-freeze record created" ($freeze.safety.design_freeze_record_created -eq $false) "design_freeze_record_created=$($freeze.safety.design_freeze_record_created)"
Add-ChecklistItem $checklist "safety" "No operator signoff recorded" ($freeze.safety.operator_signoff_recorded -eq $false) "operator_signoff_recorded=$($freeze.safety.operator_signoff_recorded)"
Add-ChecklistItem $checklist "safety" "No cutover packet created" ($freeze.safety.cutover_packet_created -eq $false) "cutover_packet_created=$($freeze.safety.cutover_packet_created)"
Add-ChecklistItem $checklist "safety" "No cutover approval recorded" ($freeze.safety.cutover_approval_recorded -eq $false) "cutover_approval_recorded=$($freeze.safety.cutover_approval_recorded)"
Add-ChecklistItem $checklist "safety" "No bridge response captured" ($freeze.safety.bridge_response_captured -eq $false) "bridge_response_captured=$($freeze.safety.bridge_response_captured)"
Add-ChecklistItem $checklist "safety" "No response capture record created" ($freeze.safety.response_capture_record_created -eq $false) "response_capture_record_created=$($freeze.safety.response_capture_record_created)"
Add-ChecklistItem $checklist "safety" "No operator approval recorded" ($freeze.safety.operator_approval_recorded -eq $false) "operator_approval_recorded=$($freeze.safety.operator_approval_recorded)"
Add-ChecklistItem $checklist "safety" "No confirmation record created" ($freeze.safety.confirmation_record_created -eq $false) "confirmation_record_created=$($freeze.safety.confirmation_record_created)"
Add-ChecklistItem $checklist "safety" "No environment variables set" ($freeze.safety.environment_variables_set -eq $false) "environment_variables_set=$($freeze.safety.environment_variables_set)"
Add-ChecklistItem $checklist "safety" "No audit row created" ($freeze.safety.audit_row_created -eq $false) "audit_row_created=$($freeze.safety.audit_row_created)"
Add-ChecklistItem $checklist "safety" "No rollback row created" ($freeze.safety.rollback_row_created -eq $false) "rollback_row_created=$($freeze.safety.rollback_row_created)"
Add-ChecklistItem $checklist "safety" "No rollback snapshot created" ($freeze.safety.rollback_snapshot_created -eq $false) "rollback_snapshot_created=$($freeze.safety.rollback_snapshot_created)"
Add-ChecklistItem $checklist "safety" "No platform DB mutation" ($freeze.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($freeze.safety.platform_db_mutation_performed)"
Add-ChecklistItem $checklist "safety" "No bridge mutation" ($freeze.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($freeze.safety.bridge_mutation_performed)"
Add-ChecklistItem $checklist "safety" "No bridge POST called" ($freeze.safety.bridge_post_called -eq $false) "bridge_post_called=$($freeze.safety.bridge_post_called)"
Add-ChecklistItem $checklist "safety" "No LACRM call" ($freeze.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($freeze.safety.lacrm_call_performed)"
Add-ChecklistItem $checklist "safety" "No real bridge HTTP client" ($freeze.safety.real_bridge_http_client_implemented -eq $false) "real_bridge_http_client_implemented=$($freeze.safety.real_bridge_http_client_implemented)"
Add-ChecklistItem $checklist "safety" "No network transport" ($freeze.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($freeze.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "safety" "No network transport enabled" ($freeze.safety.network_transport_enabled -eq $false) "network_transport_enabled=$($freeze.safety.network_transport_enabled)"
Add-ChecklistItem $checklist "safety" "No network transport armed" ($freeze.safety.network_transport_armed -eq $false) "network_transport_armed=$($freeze.safety.network_transport_armed)"
Add-ChecklistItem $checklist "safety" "No socket opened" ($freeze.safety.network_socket_opened -eq $false) "network_socket_opened=$($freeze.safety.network_socket_opened)"
Add-ChecklistItem $checklist "safety" "No bridge POST implementation" ($freeze.safety.bridge_post_call_implemented -eq $false) "bridge_post_call_implemented=$($freeze.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "safety" "No routing write endpoint" ($freeze.safety.routing_write_endpoint_implemented -eq $false) "routing_write_endpoint_implemented=$($freeze.safety.routing_write_endpoint_implemented)"
Add-ChecklistItem $checklist "safety" "Live write remains disabled" ($freeze.safety.live_write_enabled -eq $false) "live_write_enabled=$($freeze.safety.live_write_enabled)"

# Freeze packet gates.
Add-ChecklistItem $checklist "gate" "Design freeze blocks bridge write execution" ($freeze.prerequisite_chain_design_freeze_packet.can_execute_bridge_write_now -eq $false) "can_execute_bridge_write_now=$($freeze.prerequisite_chain_design_freeze_packet.can_execute_bridge_write_now)"
Add-ChecklistItem $checklist "gate" "Design freeze blocks network transport" ($freeze.prerequisite_chain_design_freeze_packet.can_add_network_transport_now -eq $false) "can_add_network_transport_now=$($freeze.prerequisite_chain_design_freeze_packet.can_add_network_transport_now)"
Add-ChecklistItem $checklist "gate" "Design freeze blocks network enablement" ($freeze.prerequisite_chain_design_freeze_packet.can_enable_network_transport_now -eq $false) "can_enable_network_transport_now=$($freeze.prerequisite_chain_design_freeze_packet.can_enable_network_transport_now)"
Add-ChecklistItem $checklist "gate" "Design freeze blocks network arming" ($freeze.prerequisite_chain_design_freeze_packet.can_arm_network_transport_now -eq $false) "can_arm_network_transport_now=$($freeze.prerequisite_chain_design_freeze_packet.can_arm_network_transport_now)"
Add-ChecklistItem $checklist "gate" "Design freeze blocks socket opening" ($freeze.prerequisite_chain_design_freeze_packet.can_open_network_socket_now -eq $false) "can_open_network_socket_now=$($freeze.prerequisite_chain_design_freeze_packet.can_open_network_socket_now)"
Add-ChecklistItem $checklist "gate" "Design freeze blocks bridge POST" ($freeze.prerequisite_chain_design_freeze_packet.can_add_bridge_post_now -eq $false) "can_add_bridge_post_now=$($freeze.prerequisite_chain_design_freeze_packet.can_add_bridge_post_now)"
Add-ChecklistItem $checklist "gate" "Design freeze blocks design-freeze record creation" ($freeze.prerequisite_chain_design_freeze_packet.can_create_design_freeze_record_now -eq $false) "can_create_design_freeze_record_now=$($freeze.prerequisite_chain_design_freeze_packet.can_create_design_freeze_record_now)"
Add-ChecklistItem $checklist "gate" "Design freeze has no blockers" ([int]$freeze.prerequisite_chain_design_freeze_packet.blocker_count -eq 0) "blocker_count=$($freeze.prerequisite_chain_design_freeze_packet.blocker_count)"
Add-ChecklistItem $checklist "gate" "Design freeze has no review items" ([int]$freeze.prerequisite_chain_design_freeze_packet.review_count -eq 0) "review_count=$($freeze.prerequisite_chain_design_freeze_packet.review_count)" "recommended"

foreach ($issue in @($freeze.issues)) {
    if ($issue.severity -eq "blocker") {
        Add-Issue $issues "blocker" "source_freeze_$($issue.code)" "$($issue.message)" "design_freeze_packet"
    } elseif ($issue.severity -eq "review") {
        Add-Issue $issues "review" "source_freeze_$($issue.code)" "$($issue.message)" "design_freeze_packet"
    }
}

# Step 33 implementation boundaries. These are design boundaries only, not code implementation.
Add-Boundary $boundaries "allowed_next_work" "Allowed future work: dataclass/schema-only transport request models" "not implemented in Step 33" "allowed only in a future reviewed step with no socket and no POST" "Defines what can be safely designed without network IO."
Add-Boundary $boundaries "allowed_next_work" "Allowed future work: typed response-capture schema only" "not implemented in Step 33" "allowed only as schema/test/doc work, not runtime capture" "Separates design from response capture records."
Add-Boundary $boundaries "allowed_next_work" "Allowed future work: interface stubs with explicit NotImplementedError" "not implemented in Step 33" "allowed only if tests prove no requests/httpx/socket usage" "Keeps future code non-network until explicit cutover."
Add-Boundary $boundaries "forbidden_now" "Real bridge HTTP client implementation" "false" "forbidden until explicit live cutover packet and operator approval" "Prevents accidental network client introduction."
Add-Boundary $boundaries "forbidden_now" "requests/httpx/socket network transport" "false" "forbidden until explicit live cutover packet and operator approval" "Prevents socket-opening code from entering the prerequisite chain."
Add-Boundary $boundaries "forbidden_now" "Bridge POST route call implementation" "false" "forbidden until explicit live cutover packet and operator approval" "Prevents bridge mutation boundary crossing."
Add-Boundary $boundaries "forbidden_now" "Bridge write execution endpoint" "false" "forbidden until explicit live cutover packet and operator approval" "Prevents platform from offering a live execution route."
Add-Boundary $boundaries "forbidden_now" "Environment variable setting or enabling" "false" "forbidden from Step 33" "Step 33 cannot set or arm transport variables."
Add-Boundary $boundaries "forbidden_now" "Audit row creation" "false" "forbidden from Step 33" "Step 33 cannot write audit rows."
Add-Boundary $boundaries "forbidden_now" "Rollback snapshot creation" "false" "forbidden from Step 33" "Step 33 cannot create rollback snapshots."
Add-Boundary $boundaries "forbidden_now" "Operator signoff record creation" "false" "forbidden from Step 33" "Step 33 cannot record approvals."
Add-Boundary $boundaries "forbidden_now" "Cutover packet creation" "false" "forbidden from Step 33" "Step 33 cannot create cutover packets."
Add-Boundary $boundaries "forbidden_now" "Bridge response capture" "false" "forbidden from Step 33" "Step 33 cannot capture bridge responses."
Add-Boundary $boundaries "forbidden_now" "LACRM calls" "false" "forbidden from Step 33" "Step 33 remains unrelated to live CRM operations."

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

foreach ($boundary in @($boundaries)) {
    if ($boundary.satisfied -ne $true) {
        Add-Issue $issues $boundary.severity ("boundary_" + ($boundary.boundary_name -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $boundary.reason $boundary.category
    }
}

foreach ($item in @($checklist)) {
    if ($item.passed -ne $true -and $item.required -eq "yes") {
        Add-Issue $issues "blocker" ("checklist_" + ($item.item -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $item.evidence $item.category
    } elseif ($item.passed -ne $true -and $item.required -eq "recommended") {
        Add-Issue $issues "review" ("checklist_" + ($item.item -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $item.evidence $item.category
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$boundaryStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "implementation_boundary_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "implementation_boundary_packet_review_required_no_write"
} else {
    "implementation_boundary_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_implementation_boundary_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="prerequisite_chain_design_freeze_packet"; json_path=$freezePath; sha256=Get-FileSha256 $freezePath },
    [ordered]@{ key="prerequisite_chain_operator_signoff"; json_path=$signoffPath; sha256=Get-FileSha256 $signoffPath },
    [ordered]@{ key="prerequisite_chain_release_checkpoint"; json_path=$checkpointPath; sha256=Get-FileSha256 $checkpointPath },
    [ordered]@{ key="cutover_packet_prerequisite_gate_design"; json_path=$cutoverPath; sha256=Get-FileSha256 $cutoverPath },
    [ordered]@{ key="response_capture_gate_design"; json_path=$responsePath; sha256=Get-FileSha256 $responsePath }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 33"
    purpose = "Bridge routing network transport implementation boundary packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_implementation_boundary_packet_only = $true
        bridge_get_only = $true
        implementation_boundary_packet_only = $true
        implementation_code_created = $false
        real_bridge_http_client_implemented = $false
        network_transport_implemented = $false
        network_transport_enabled = $false
        network_transport_armed = $false
        network_socket_opened = $false
        bridge_post_call_implemented = $false
        bridge_post_called = $false
        routing_write_endpoint_implemented = $false
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
        lacrm_call_performed = $false
        live_write_enabled = $false
    }
    implementation_boundary_packet = [ordered]@{
        status = $boundaryStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        checklist_count = @($checklist).Count
        boundary_count = @($boundaries).Count
        artifact_count = @($sourceArtifacts).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        can_add_bridge_post_now = $false
        can_create_implementation_code_now = $false
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
        boundary_label = "phase20_bridge_routing_network_transport_implementation_boundary_no_write"
        reason = if ($blockerCount -eq 0) {
            "Implementation boundary packet is ready for review. Phase 20 Step 33 creates no implementation code, opens no socket, calls no bridge POST, and authorizes no execution."
        } else {
            "Implementation boundary packet has blockers. Resolve blockers before any future real network transport implementation design."
        }
    }
    source_artifacts = $sourceArtifacts
    boundaries = @($boundaries)
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
        boundaries = @($boundaries).Count
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this implementation boundary packet before creating any future implementation-code scaffold.",
        "Do not create implementation code from Phase 20 Step 33.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 20 Step 33.",
        "Do not create design-freeze records from Phase 20 Step 33.",
        "Do not record operator signoffs from Phase 20 Step 33.",
        "Do not create cutover packets from Phase 20 Step 33.",
        "Do not capture bridge responses from Phase 20 Step 33.",
        "Do not set environment variables from Phase 20 Step 33.",
        "Do not create audit rows or rollback snapshots from Phase 20 Step 33.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_implementation_boundary_packet.json"
$boundariesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_implementation_boundary_packet_boundaries.csv"
$checklistCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_implementation_boundary_packet_checklist.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_implementation_boundary_packet_artifacts.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_implementation_boundary_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_implementation_boundary_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$boundaries | Export-Csv -LiteralPath $boundariesCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$boundaryText = (@($boundaries) | ForEach-Object { "- [$($_.category)] $($_.boundary_name): current=$($_.current_step_value); future=$($_.allowed_future_value)" }) -join "`n"
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Implementation Boundary Packet

Generated: $($report.generated_at)

Source prerequisite chain design freeze packet:

``````
$freezePath
``````

## Safety

- Bridge routing network transport implementation boundary packet only: true
- Bridge GET only: true
- Implementation boundary packet only: true
- Implementation code created: false
- Real bridge HTTP client implemented: false
- Network transport implemented: false
- Network transport enabled: false
- Network transport armed: false
- Network socket opened: false
- Bridge POST call implemented: false
- Bridge POST called: false
- Routing write endpoint implemented: false
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
- LACRM call performed: false
- Live write enabled: false

## Implementation boundary packet

- Status: $boundaryStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Boundaries: $(@($boundaries).Count)
- Checklist items: $(@($checklist).Count)
- Source artifacts: $(@($sourceArtifacts).Count)
- Can execute bridge write now: false
- Can add network transport now: false
- Can enable network transport now: false
- Can arm network transport now: false
- Can open network socket now: false
- Can add real bridge HTTP client now: false
- Can add bridge POST now: false
- Can create implementation code now: false
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

## Implementation boundaries

$boundaryText

## Checklist

$checklistText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_implementation_boundary_packet=$OutputDir | status=$boundaryStatus | bridge_post_called=False | implementation_code_created=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_implementation_boundary_packet=$OutputDir | status=$boundaryStatus | blockers=$blockerCount | bridge_post_called=False | implementation_code_created=False"
}

Write-Host ""
Write-Host "Implementation boundary packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
