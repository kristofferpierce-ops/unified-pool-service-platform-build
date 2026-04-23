param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$DryRunAdapterWrapperPacketDir = "",
    [string]$InterfaceStubPacketDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"
$PlatformDir = Join-Path $Workspace "unified_pool_service_platform_build"
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

if ([string]::IsNullOrWhiteSpace($DryRunAdapterWrapperPacketDir)) {
    $DryRunAdapterWrapperPacketDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_adapter_wrapper_packet_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_adapter_wrapper_packet.json"
}
if ([string]::IsNullOrWhiteSpace($InterfaceStubPacketDir)) {
    $InterfaceStubPacketDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_interface_stub_packet_*" -JsonName "phase20_bridge_routing_network_transport_interface_stub_packet.json" -Required $false
}

$wrapperPacketPath = Join-Path $DryRunAdapterWrapperPacketDir "phase20_bridge_routing_network_transport_dry_run_adapter_wrapper_packet.json"
$interfacePacketPath = if (![string]::IsNullOrWhiteSpace($InterfaceStubPacketDir)) { Join-Path $InterfaceStubPacketDir "phase20_bridge_routing_network_transport_interface_stub_packet.json" } else { "" }

if (!(Test-Path -LiteralPath $wrapperPacketPath)) {
    throw "Dry-run adapter wrapper packet JSON not found: $wrapperPacketPath"
}
if (!(Test-Path -LiteralPath $GuardPath)) {
    throw "Guard envelope module not found: $GuardPath"
}
if (!(Test-Path -LiteralPath $WrapperPath)) {
    throw "Dry-run adapter wrapper module not found: $WrapperPath"
}

$wrapperPacket = Read-JsonFile $wrapperPacketPath
$interfacePacket = if (![string]::IsNullOrWhiteSpace($interfacePacketPath) -and (Test-Path -LiteralPath $interfacePacketPath)) { Read-JsonFile $interfacePacketPath } else { $null }

$invocationStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList

$guardText = Get-Content -LiteralPath $GuardPath -Raw
$wrapperText = Get-Content -LiteralPath $WrapperPath -Raw

Add-ChecklistItem $checklist "artifact" "Dry-run adapter wrapper packet exists" $true $wrapperPacketPath
Add-ChecklistItem $checklist "artifact" "Interface stub packet exists" ($interfacePacket -ne $null) $interfacePacketPath "recommended"
Add-ChecklistItem $checklist "artifact" "Guard envelope module exists" $true $GuardPath
Add-ChecklistItem $checklist "artifact" "Dry-run adapter wrapper module exists" $true $WrapperPath
Add-ChecklistItem $checklist "artifact" "Interface stub module exists" (Test-Path -LiteralPath $InterfaceStubPath) $InterfaceStubPath "recommended"
Add-ChecklistItem $checklist "artifact" "Contract schema module exists" (Test-Path -LiteralPath $ContractSchemaPath) $ContractSchemaPath "recommended"

# Wrapper source packet checks.
Add-ChecklistItem $checklist "wrapper_packet" "Wrapper source packet is dry-run-adapter-wrapper-only" ($wrapperPacket.safety.dry_run_adapter_wrapper_only -eq $true) "dry_run_adapter_wrapper_only=$($wrapperPacket.safety.dry_run_adapter_wrapper_only)"
Add-ChecklistItem $checklist "wrapper_packet" "Wrapper source packet has dry-run preview" ($wrapperPacket.safety.dry_run_preview_created -eq $true) "dry_run_preview_created=$($wrapperPacket.safety.dry_run_preview_created)"
Add-ChecklistItem $checklist "wrapper_packet" "Wrapper source packet has no execution implementation" ($wrapperPacket.safety.execution_implementation_created -eq $false) "execution_implementation_created=$($wrapperPacket.safety.execution_implementation_created)"
Add-ChecklistItem $checklist "wrapper_packet" "Wrapper source packet has no real bridge HTTP client" ($wrapperPacket.safety.real_bridge_http_client_implemented -eq $false) "real_bridge_http_client_implemented=$($wrapperPacket.safety.real_bridge_http_client_implemented)"
Add-ChecklistItem $checklist "wrapper_packet" "Wrapper source packet has no network transport" ($wrapperPacket.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($wrapperPacket.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "wrapper_packet" "Wrapper source packet has no socket opened" ($wrapperPacket.safety.network_socket_opened -eq $false) "network_socket_opened=$($wrapperPacket.safety.network_socket_opened)"
Add-ChecklistItem $checklist "wrapper_packet" "Wrapper source packet has no bridge POST" ($wrapperPacket.safety.bridge_post_called -eq $false -and $wrapperPacket.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($wrapperPacket.safety.bridge_post_called); bridge_post_call_implemented=$($wrapperPacket.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "wrapper_packet" "Wrapper source packet blocks execution implementation" ($wrapperPacket.dry_run_adapter_wrapper_packet.can_create_execution_implementation_now -eq $false) "can_create_execution_implementation_now=$($wrapperPacket.dry_run_adapter_wrapper_packet.can_create_execution_implementation_now)"
Add-ChecklistItem $checklist "wrapper_packet" "Wrapper source packet has no blockers" ([int]$wrapperPacket.dry_run_adapter_wrapper_packet.blocker_count -eq 0) "blocker_count=$($wrapperPacket.dry_run_adapter_wrapper_packet.blocker_count)"

foreach ($issue in @($wrapperPacket.issues)) {
    if ($issue.severity -eq "blocker") {
        Add-Issue $issues "blocker" "wrapper_$($issue.code)" "$($issue.message)" "dry_run_adapter_wrapper_packet"
    } elseif ($issue.severity -eq "review") {
        Add-Issue $issues "review" "wrapper_$($issue.code)" "$($issue.message)" "dry_run_adapter_wrapper_packet"
    }
}

# Guard module checks.
Add-ChecklistItem $checklist "guard" "Guard version constant exists" ($guardText -match "ROUTING_BRIDGE_NETWORK_TRANSPORT_GUARD_ENVELOPE_VERSION") "version constant present"
Add-ChecklistItem $checklist "guard" "Guard result class exists" ($guardText -match "class BridgeRoutingNetworkTransportGuardEnvelopeDecisionResult") "decision result class present"
Add-ChecklistItem $checklist "guard" "Guard class exists" ($guardText -match "class BridgeRoutingNetworkTransportGuardEnvelope") "guard class present"
Add-ChecklistItem $checklist "guard" "Guard blocked exception exists" ($guardText -match "class BridgeRoutingNetworkTransportGuardBlocked") "guard blocked exception present"
Add-ChecklistItem $checklist "guard" "Evaluate preview method exists" ($guardText -match "def evaluate_preview") "evaluate_preview present"
Add-ChecklistItem $checklist "guard" "Preview safety validation exists" ($guardText -match "def _validate_preview_safety") "preview safety validation present"
Add-ChecklistItem $checklist "guard" "Future execution blocker exists" ($guardText -match "def block_future_execution_attempt") "block_future_execution_attempt present"
Add-ChecklistItem $checklist "guard" "Guard envelope-only flag exists" ($guardText -match '"guard_envelope_only": guard.guard_envelope_only') "guard_envelope_only present"
Add-ChecklistItem $checklist "guard" "Execution implementation stays false" ($guardText -match '"execution_implementation_created": guard.execution_implementation_created') "execution_implementation_created false"
Add-ChecklistItem $checklist "guard" "Real bridge HTTP client stays false" ($guardText -match '"real_bridge_http_client_implemented": guard.real_bridge_http_client_implemented') "real_bridge_http_client_implemented false"
Add-ChecklistItem $checklist "guard" "Network transport stays false" ($guardText -match '"network_transport_implemented": guard.network_transport_implemented') "network_transport_implemented false"
Add-ChecklistItem $checklist "guard" "Socket opening stays false" ($guardText -match '"network_socket_opened": guard.network_socket_opened') "network_socket_opened false"
Add-ChecklistItem $checklist "guard" "Bridge POST stays false" ($guardText -match '"bridge_post_called": guard.bridge_post_called') "bridge_post_called false"
Add-ChecklistItem $checklist "guard" "Routing write endpoint stays false" ($guardText -match '"routing_write_endpoint_implemented": guard.routing_write_endpoint_implemented') "routing_write_endpoint_implemented false"
Add-ChecklistItem $checklist "guard" "No interface execution method call" ($guardText -notmatch "\.execute_bridge_routing_transport\(") "execute_bridge_routing_transport not called"
Add-ChecklistItem $checklist "guard" "No socket boundary method call" ($guardText -notmatch "\.open_network_boundary\(") "open_network_boundary not called"
Add-ChecklistItem $checklist "guard" "No bridge POST method call" ($guardText -notmatch "\.call_bridge_post\(") "call_bridge_post not called"
Add-ChecklistItem $checklist "guard" "No requests import or use" (($guardText -notmatch "import requests") -and ($guardText -notmatch "requests\.")) "requests not present"
Add-ChecklistItem $checklist "guard" "No httpx import or use" (($guardText -notmatch "import httpx") -and ($guardText -notmatch "httpx\.")) "httpx not present"
Add-ChecklistItem $checklist "guard" "No socket import or use" (($guardText -notmatch "import socket") -and ($guardText -notmatch "socket\.")) "socket import/use not present"
Add-ChecklistItem $checklist "guard" "No database commit" ($guardText -notmatch "\.commit\(") ".commit not present"
Add-ChecklistItem $checklist "guard" "No database add" ($guardText -notmatch "\.add\(") ".add not present"

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
    "guard_envelope_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "guard_envelope_packet_review_required_no_write"
} else {
    "guard_envelope_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_guard_envelope_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="dry_run_adapter_wrapper_packet"; json_path=$wrapperPacketPath; sha256=Get-FileSha256 $wrapperPacketPath },
    [ordered]@{ key="interface_stub_packet"; json_path=$interfacePacketPath; sha256=Get-FileSha256 $interfacePacketPath },
    [ordered]@{ key="guard_envelope_module"; json_path=$GuardPath; sha256=Get-FileSha256 $GuardPath },
    [ordered]@{ key="dry_run_adapter_wrapper_module"; json_path=$WrapperPath; sha256=Get-FileSha256 $WrapperPath },
    [ordered]@{ key="interface_stub_module"; json_path=$InterfaceStubPath; sha256=Get-FileSha256 $InterfaceStubPath },
    [ordered]@{ key="contract_schema_module"; json_path=$ContractSchemaPath; sha256=Get-FileSha256 $ContractSchemaPath }
)

$guardMethods = @(
    [ordered]@{ method_name="evaluate_preview"; purpose="Evaluate preview-only dry-run wrapper output"; calls_execution=$false; network_now=$false; writes_now=$false },
    [ordered]@{ method_name="_validate_preview_safety"; purpose="Block any preview that reports execution or mutation"; calls_execution=$false; network_now=$false; writes_now=$false },
    [ordered]@{ method_name="block_future_execution_attempt"; purpose="Explicitly block future execution attempts"; calls_execution=$false; network_now=$false; writes_now=$false },
    [ordered]@{ method_name="bridge_routing_network_transport_guard_envelope_status"; purpose="Expose no-write guard status"; calls_execution=$false; network_now=$false; writes_now=$false },
    [ordered]@{ method_name="bridge_routing_network_transport_guard_envelope_packet_dict"; purpose="Expose sample no-write guard packet"; calls_execution=$false; network_now=$false; writes_now=$false }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 37"
    purpose = "Bridge routing network transport guard envelope packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_guard_envelope_packet_only = $true
        guard_envelope_only = $true
        guard_preview_created = $true
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
    guard_envelope_packet = [ordered]@{
        status = $packetStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        checklist_count = @($checklist).Count
        guard_method_count = @($guardMethods).Count
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
        packet_label = "phase20_bridge_routing_network_transport_guard_envelope_no_write"
        reason = if ($blockerCount -eq 0) {
            "Guard envelope packet is ready for review. Phase 20 Step 37 creates a preview-only guard envelope, but no execution implementation, no network transport, no socket, no bridge POST, and no live write."
        } else {
            "Guard envelope packet has blockers. Resolve blockers before future readiness report design."
        }
    }
    source_artifacts = $sourceArtifacts
    guard_methods = $guardMethods
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
        guard_methods = @($guardMethods).Count
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this guard envelope packet before creating any future readiness report.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 20 Step 37.",
        "Do not call interface execution methods from Phase 20 Step 37.",
        "Do not create execution implementation from Phase 20 Step 37.",
        "Do not capture bridge responses from Phase 20 Step 37.",
        "Do not set environment variables from Phase 20 Step 37.",
        "Do not create audit rows or rollback snapshots from Phase 20 Step 37.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_guard_envelope_packet.json"
$methodsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_guard_envelope_packet_methods.csv"
$checklistCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_guard_envelope_packet_checklist.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_guard_envelope_packet_artifacts.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_guard_envelope_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_guard_envelope_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$guardMethods | Export-Csv -LiteralPath $methodsCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$methodsText = (@($guardMethods) | ForEach-Object { "- $($_.method_name): $($_.purpose); calls_execution=$($_.calls_execution); network_now=$($_.network_now); writes_now=$($_.writes_now)" }) -join "`n"
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Guard Envelope Packet

Generated: $($report.generated_at)

Source dry-run adapter wrapper packet:

``````
$wrapperPacketPath
``````

## Safety

- Bridge routing network transport guard envelope packet only: true
- Guard envelope only: true
- Guard preview created: true
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

## Guard envelope packet

- Status: $packetStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Guard methods: $(@($guardMethods).Count)
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

## Source artifacts

$artifactText

## Guard methods

$methodsText

## Checklist

$checklistText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_guard_envelope_packet=$OutputDir | status=$packetStatus | bridge_post_called=False | execution_implementation_created=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_guard_envelope_packet=$OutputDir | status=$packetStatus | blockers=$blockerCount | bridge_post_called=False | execution_implementation_created=False"
}

Write-Host ""
Write-Host "Guard envelope packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
