param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$FinalReviewPacketDir = "",
    [string]$ReadinessReportPacketDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"
$PlatformDir = Join-Path $Workspace "unified_pool_service_platform_build"
$DesignClosurePath = Join-Path $PlatformDir "app\services\routing_bridge_network_transport_design_closure_packet.py"
$FinalReviewPath = Join-Path $PlatformDir "app\services\routing_bridge_network_transport_final_review_packet.py"
$ReadinessPath = Join-Path $PlatformDir "app\services\routing_bridge_network_transport_readiness_report.py"
$GuardPath = Join-Path $PlatformDir "app\services\routing_bridge_network_transport_guard_envelope.py"
$WrapperPath = Join-Path $PlatformDir "app\services\routing_bridge_network_transport_dry_run_adapter_wrapper.py"
$InterfaceStubPath = Join-Path $PlatformDir "app\services\routing_bridge_network_transport_interface_stub.py"
$ContractSchemaPath = Join-Path $PlatformDir "app\services\routing_bridge_network_transport_contract_schema.py"

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

if ([string]::IsNullOrWhiteSpace($FinalReviewPacketDir)) {
    $FinalReviewPacketDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_final_review_packet_*" -JsonName "phase20_bridge_routing_network_transport_final_review_packet.json"
}
if ([string]::IsNullOrWhiteSpace($ReadinessReportPacketDir)) {
    $ReadinessReportPacketDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_readiness_report_packet_*" -JsonName "phase20_bridge_routing_network_transport_readiness_report_packet.json" -Required $false
}

$finalReviewPacketPath = Join-Path $FinalReviewPacketDir "phase20_bridge_routing_network_transport_final_review_packet.json"
$readinessPacketPath = if (![string]::IsNullOrWhiteSpace($ReadinessReportPacketDir)) { Join-Path $ReadinessReportPacketDir "phase20_bridge_routing_network_transport_readiness_report_packet.json" } else { "" }

if (!(Test-Path -LiteralPath $finalReviewPacketPath)) {
    throw "Final review packet JSON not found: $finalReviewPacketPath"
}
if (!(Test-Path -LiteralPath $DesignClosurePath)) {
    throw "Design closure packet module not found: $DesignClosurePath"
}
if (!(Test-Path -LiteralPath $FinalReviewPath)) {
    throw "Final review packet module not found: $FinalReviewPath"
}

$finalReviewPacket = Read-JsonFile $finalReviewPacketPath
$readinessPacket = if (![string]::IsNullOrWhiteSpace($readinessPacketPath) -and (Test-Path -LiteralPath $readinessPacketPath)) { Read-JsonFile $readinessPacketPath } else { $null }

$invocationStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList

$designClosureText = Get-Content -LiteralPath $DesignClosurePath -Raw

Add-ChecklistItem $checklist "artifact" "Final review packet exists" $true $finalReviewPacketPath
Add-ChecklistItem $checklist "artifact" "Readiness report packet exists" ($readinessPacket -ne $null) $readinessPacketPath "recommended"
Add-ChecklistItem $checklist "artifact" "Design closure module exists" $true $DesignClosurePath
Add-ChecklistItem $checklist "artifact" "Final review module exists" $true $FinalReviewPath
Add-ChecklistItem $checklist "artifact" "Readiness report module exists" (Test-Path -LiteralPath $ReadinessPath) $ReadinessPath "recommended"
Add-ChecklistItem $checklist "artifact" "Guard envelope module exists" (Test-Path -LiteralPath $GuardPath) $GuardPath "recommended"
Add-ChecklistItem $checklist "artifact" "Dry-run adapter wrapper module exists" (Test-Path -LiteralPath $WrapperPath) $WrapperPath "recommended"
Add-ChecklistItem $checklist "artifact" "Interface stub module exists" (Test-Path -LiteralPath $InterfaceStubPath) $InterfaceStubPath "recommended"
Add-ChecklistItem $checklist "artifact" "Contract schema module exists" (Test-Path -LiteralPath $ContractSchemaPath) $ContractSchemaPath "recommended"

# Final review source packet checks.
Add-ChecklistItem $checklist "final_review_packet" "Final review source packet is packet-only" ($finalReviewPacket.safety.final_review_packet_only -eq $true) "final_review_packet_only=$($finalReviewPacket.safety.final_review_packet_only)"
Add-ChecklistItem $checklist "final_review_packet" "Final review source packet has preview" ($finalReviewPacket.safety.final_review_preview_created -eq $true) "final_review_preview_created=$($finalReviewPacket.safety.final_review_preview_created)"
Add-ChecklistItem $checklist "final_review_packet" "Final review source packet recorded no approval" ($finalReviewPacket.safety.final_approval_recorded -eq $false) "final_approval_recorded=$($finalReviewPacket.safety.final_approval_recorded)"
Add-ChecklistItem $checklist "final_review_packet" "Final review source packet has no execution implementation" ($finalReviewPacket.safety.execution_implementation_created -eq $false) "execution_implementation_created=$($finalReviewPacket.safety.execution_implementation_created)"
Add-ChecklistItem $checklist "final_review_packet" "Final review source packet has no real bridge HTTP client" ($finalReviewPacket.safety.real_bridge_http_client_implemented -eq $false) "real_bridge_http_client_implemented=$($finalReviewPacket.safety.real_bridge_http_client_implemented)"
Add-ChecklistItem $checklist "final_review_packet" "Final review source packet has no network transport" ($finalReviewPacket.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($finalReviewPacket.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "final_review_packet" "Final review source packet has no socket opened" ($finalReviewPacket.safety.network_socket_opened -eq $false) "network_socket_opened=$($finalReviewPacket.safety.network_socket_opened)"
Add-ChecklistItem $checklist "final_review_packet" "Final review source packet has no bridge POST" ($finalReviewPacket.safety.bridge_post_called -eq $false -and $finalReviewPacket.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($finalReviewPacket.safety.bridge_post_called); bridge_post_call_implemented=$($finalReviewPacket.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "final_review_packet" "Final review source packet blocks final approval" ($finalReviewPacket.final_review_packet.can_record_final_approval_now -eq $false) "can_record_final_approval_now=$($finalReviewPacket.final_review_packet.can_record_final_approval_now)"
Add-ChecklistItem $checklist "final_review_packet" "Final review source packet blocks execution implementation" ($finalReviewPacket.final_review_packet.can_create_execution_implementation_now -eq $false) "can_create_execution_implementation_now=$($finalReviewPacket.final_review_packet.can_create_execution_implementation_now)"
Add-ChecklistItem $checklist "final_review_packet" "Final review source packet has no blockers" ([int]$finalReviewPacket.final_review_packet.blocker_count -eq 0) "blocker_count=$($finalReviewPacket.final_review_packet.blocker_count)"

foreach ($issue in @($finalReviewPacket.issues)) {
    if ($issue.severity -eq "blocker") {
        Add-Issue $issues "blocker" "final_review_$($issue.code)" "$($issue.message)" "final_review_packet"
    } elseif ($issue.severity -eq "review") {
        Add-Issue $issues "review" "final_review_$($issue.code)" "$($issue.message)" "final_review_packet"
    }
}

# Design closure module checks.
Add-ChecklistItem $checklist "design_closure" "Design closure version constant exists" ($designClosureText -match "ROUTING_BRIDGE_NETWORK_TRANSPORT_DESIGN_CLOSURE_PACKET_VERSION") "version constant present"
Add-ChecklistItem $checklist "design_closure" "Design closure result class exists" ($designClosureText -match "class BridgeRoutingNetworkTransportDesignClosurePacketResult") "design closure result class present"
Add-ChecklistItem $checklist "design_closure" "Design closure packet class exists" ($designClosureText -match "class BridgeRoutingNetworkTransportDesignClosurePacket") "design closure packet class present"
Add-ChecklistItem $checklist "design_closure" "Build design closure method exists" ($designClosureText -match "def build_design_closure") "build_design_closure present"
Add-ChecklistItem $checklist "design_closure" "Final review validation exists" ($designClosureText -match "def _validate_final_review_packet") "final review validation present"
Add-ChecklistItem $checklist "design_closure" "Status function exists" ($designClosureText -match "bridge_routing_network_transport_design_closure_packet_status") "status function present"
Add-ChecklistItem $checklist "design_closure" "Packet dict function exists" ($designClosureText -match "bridge_routing_network_transport_design_closure_packet_dict") "packet dict function present"
Add-ChecklistItem $checklist "design_closure" "Design closure packet-only flag exists" ($designClosureText -match '"design_closure_packet_only": packet.design_closure_packet_only') "design_closure_packet_only present"
Add-ChecklistItem $checklist "design_closure" "Design closure record stays false" ($designClosureText -match '"design_closure_record_created": packet.design_closure_record_created') "design_closure_record_created false"
Add-ChecklistItem $checklist "design_closure" "Final approval stays false" ($designClosureText -match '"final_approval_recorded": packet.final_approval_recorded') "final_approval_recorded false"
Add-ChecklistItem $checklist "design_closure" "Implementation phase stays false" ($designClosureText -match '"implementation_phase_started": packet.implementation_phase_started') "implementation_phase_started false"
Add-ChecklistItem $checklist "design_closure" "Execution implementation stays false" ($designClosureText -match '"execution_implementation_created": packet.execution_implementation_created') "execution_implementation_created false"
Add-ChecklistItem $checklist "design_closure" "Real bridge HTTP client stays false" ($designClosureText -match '"real_bridge_http_client_implemented": packet.real_bridge_http_client_implemented') "real_bridge_http_client_implemented false"
Add-ChecklistItem $checklist "design_closure" "Network transport stays false" ($designClosureText -match '"network_transport_implemented": packet.network_transport_implemented') "network_transport_implemented false"
Add-ChecklistItem $checklist "design_closure" "Socket opening stays false" ($designClosureText -match '"network_socket_opened": packet.network_socket_opened') "network_socket_opened false"
Add-ChecklistItem $checklist "design_closure" "Bridge POST stays false" ($designClosureText -match '"bridge_post_called": packet.bridge_post_called') "bridge_post_called false"
Add-ChecklistItem $checklist "design_closure" "Routing write endpoint stays false" ($designClosureText -match '"routing_write_endpoint_implemented": packet.routing_write_endpoint_implemented') "routing_write_endpoint false"
Add-ChecklistItem $checklist "design_closure" "No interface execution method call" ($designClosureText -notmatch "\.execute_bridge_routing_transport\(") "execute_bridge_routing_transport not called"
Add-ChecklistItem $checklist "design_closure" "No socket boundary method call" ($designClosureText -notmatch "\.open_network_boundary\(") "open_network_boundary not called"
Add-ChecklistItem $checklist "design_closure" "No bridge POST method call" ($designClosureText -notmatch "\.call_bridge_post\(") "call_bridge_post not called"
Add-ChecklistItem $checklist "design_closure" "No requests import or use" (($designClosureText -notmatch "import requests") -and ($designClosureText -notmatch "requests\.")) "requests not present"
Add-ChecklistItem $checklist "design_closure" "No httpx import or use" (($designClosureText -notmatch "import httpx") -and ($designClosureText -notmatch "httpx\.")) "httpx not present"
Add-ChecklistItem $checklist "design_closure" "No socket import or use" (($designClosureText -notmatch "import socket") -and ($designClosureText -notmatch "socket\.")) "socket import/use not present"
Add-ChecklistItem $checklist "design_closure" "No database commit" ($designClosureText -notmatch "\.commit\(") ".commit not present"
Add-ChecklistItem $checklist "design_closure" "No database add" ($designClosureText -notmatch "\.add\(") ".add not present"

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

foreach ($item in @($checklist)) {
    if ($item.passed -ne $true -and $item.required -eq "yes") {
        Add-Issue $issues "blocker" ("checklist_" + ($item.item -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $item.evidence $item.category
    } elseif ($item.passed -ne $true -and $item.required -eq "recommended") {
        Add-Issue $issues "review" ("checklist_" + ($item.item -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $item.evidence $item.category
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$packetStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "design_closure_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "design_closure_packet_review_required_no_write"
} else {
    "design_closure_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_design_closure_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="final_review_packet"; json_path=$finalReviewPacketPath; sha256=Get-FileSha256 $finalReviewPacketPath },
    [ordered]@{ key="readiness_report_packet"; json_path=$readinessPacketPath; sha256=Get-FileSha256 $readinessPacketPath },
    [ordered]@{ key="design_closure_module"; json_path=$DesignClosurePath; sha256=Get-FileSha256 $DesignClosurePath },
    [ordered]@{ key="final_review_module"; json_path=$FinalReviewPath; sha256=Get-FileSha256 $FinalReviewPath },
    [ordered]@{ key="readiness_report_module"; json_path=$ReadinessPath; sha256=Get-FileSha256 $ReadinessPath },
    [ordered]@{ key="guard_envelope_module"; json_path=$GuardPath; sha256=Get-FileSha256 $GuardPath },
    [ordered]@{ key="dry_run_adapter_wrapper_module"; json_path=$WrapperPath; sha256=Get-FileSha256 $WrapperPath },
    [ordered]@{ key="interface_stub_module"; json_path=$InterfaceStubPath; sha256=Get-FileSha256 $InterfaceStubPath },
    [ordered]@{ key="contract_schema_module"; json_path=$ContractSchemaPath; sha256=Get-FileSha256 $ContractSchemaPath }
)

$packetMethods = @(
    [ordered]@{ method_name="build_design_closure"; purpose="Build no-write design closure packet from final review packet"; calls_execution=$false; network_now=$false; writes_now=$false },
    [ordered]@{ method_name="_validate_final_review_packet"; purpose="Block any final review that reports execution, mutation, approval, cutover, or implementation start"; calls_execution=$false; network_now=$false; writes_now=$false },
    [ordered]@{ method_name="bridge_routing_network_transport_design_closure_packet_status"; purpose="Expose no-write design closure status"; calls_execution=$false; network_now=$false; writes_now=$false },
    [ordered]@{ method_name="bridge_routing_network_transport_design_closure_packet_dict"; purpose="Expose sample no-write design closure packet"; calls_execution=$false; network_now=$false; writes_now=$false }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 40"
    purpose = "Bridge routing network transport design closure packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_design_closure_packet_only = $true
        design_closure_packet_only = $true
        design_closure_preview_created = $true
        design_closure_record_created = $false
        final_approval_recorded = $false
        implementation_phase_started = $false
        execution_implementation_created = $false
        bridge_get_only = $true
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
    design_closure_packet = [ordered]@{
        status = $packetStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        checklist_count = @($checklist).Count
        packet_method_count = @($packetMethods).Count
        artifact_count = @($sourceArtifacts).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        can_add_bridge_post_now = $false
        can_create_execution_implementation_now = $false
        can_capture_bridge_response_now = $false
        can_create_response_capture_records_now = $false
        can_create_audit_rows_now = $false
        can_create_rollback_rows_now = $false
        can_create_rollback_snapshots_now = $false
        can_set_environment_variables_now = $false
        can_create_cutover_packets_now = $false
        can_record_final_approval_now = $false
        can_create_design_closure_record_now = $false
        can_start_implementation_phase_now = $false
        packet_label = "phase20_bridge_routing_network_transport_design_closure_no_write"
        reason = if ($blockerCount -eq 0) {
            "Design closure packet is ready for review. Phase 20 Step 40 closes the no-write design evidence chain, but records no approvals, creates no implementation, starts no implementation phase, opens no socket, calls no bridge POST, and enables no live write."
        } else {
            "Design closure packet has blockers. Resolve blockers before future closure or implementation planning."
        }
    }
    source_artifacts = $sourceArtifacts
    packet_methods = $packetMethods
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
        packet_methods = @($packetMethods).Count
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this design closure packet as the closeout for Phase 20 no-write network transport design evidence.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 20 Step 40.",
        "Do not call interface execution methods from Phase 20 Step 40.",
        "Do not record final approvals from Phase 20 Step 40.",
        "Do not start an implementation phase from Phase 20 Step 40.",
        "Do not create execution implementation from Phase 20 Step 40.",
        "Do not capture bridge responses from Phase 20 Step 40.",
        "Do not set environment variables from Phase 20 Step 40.",
        "Do not create audit rows or rollback snapshots from Phase 20 Step 40.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_design_closure_packet.json"
$methodsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_design_closure_packet_methods.csv"
$checklistCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_design_closure_packet_checklist.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_design_closure_packet_artifacts.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_design_closure_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_design_closure_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$packetMethods | Export-Csv -LiteralPath $methodsCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$methodsText = (@($packetMethods) | ForEach-Object { "- $($_.method_name): $($_.purpose); calls_execution=$($_.calls_execution); network_now=$($_.network_now); writes_now=$($_.writes_now)" }) -join "`n"
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Design Closure Packet

Generated: $($report.generated_at)

Source final review packet:

``````
$finalReviewPacketPath
``````

## Safety

- Bridge routing network transport design closure packet only: true
- Design closure packet only: true
- Design closure preview created: true
- Design closure record created: false
- Final approval recorded: false
- Implementation phase started: false
- Execution implementation created: false
- Bridge GET only: true
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

## Design closure packet

- Status: $packetStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Packet methods: $(@($packetMethods).Count)
- Checklist items: $(@($checklist).Count)
- Source artifacts: $(@($sourceArtifacts).Count)
- Can execute bridge write now: false
- Can add network transport now: false
- Can enable network transport now: false
- Can arm network transport now: false
- Can open network socket now: false
- Can add real bridge HTTP client now: false
- Can add bridge POST now: false
- Can create execution implementation now: false
- Can capture bridge response now: false
- Can create response capture records now: false
- Can create audit rows now: false
- Can create rollback rows now: false
- Can create rollback snapshots now: false
- Can set environment variables now: false
- Can create cutover packets now: false
- Can record final approval now: false
- Can create design closure record now: false
- Can start implementation phase now: false

## Source artifacts

$artifactText

## Packet methods

$methodsText

## Checklist

$checklistText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_design_closure_packet=$OutputDir | status=$packetStatus | bridge_post_called=False | execution_implementation_created=False | final_approval_recorded=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_design_closure_packet=$OutputDir | status=$packetStatus | blockers=$blockerCount | bridge_post_called=False | execution_implementation_created=False | final_approval_recorded=False"
}

Write-Host ""
Write-Host "Design closure packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
