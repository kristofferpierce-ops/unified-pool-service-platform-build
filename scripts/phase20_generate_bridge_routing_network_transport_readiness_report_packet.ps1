param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$GuardEnvelopePacketDir = "",
    [string]$DryRunAdapterWrapperPacketDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"
$PlatformDir = Join-Path $Workspace "unified_pool_service_platform_build"
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

if ([string]::IsNullOrWhiteSpace($GuardEnvelopePacketDir)) {
    $GuardEnvelopePacketDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_guard_envelope_packet_*" -JsonName "phase20_bridge_routing_network_transport_guard_envelope_packet.json"
}
if ([string]::IsNullOrWhiteSpace($DryRunAdapterWrapperPacketDir)) {
    $DryRunAdapterWrapperPacketDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_adapter_wrapper_packet_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_adapter_wrapper_packet.json" -Required $false
}

$guardPacketPath = Join-Path $GuardEnvelopePacketDir "phase20_bridge_routing_network_transport_guard_envelope_packet.json"
$wrapperPacketPath = if (![string]::IsNullOrWhiteSpace($DryRunAdapterWrapperPacketDir)) { Join-Path $DryRunAdapterWrapperPacketDir "phase20_bridge_routing_network_transport_dry_run_adapter_wrapper_packet.json" } else { "" }

if (!(Test-Path -LiteralPath $guardPacketPath)) {
    throw "Guard envelope packet JSON not found: $guardPacketPath"
}
if (!(Test-Path -LiteralPath $ReadinessPath)) {
    throw "Readiness report module not found: $ReadinessPath"
}
if (!(Test-Path -LiteralPath $GuardPath)) {
    throw "Guard envelope module not found: $GuardPath"
}

$guardPacket = Read-JsonFile $guardPacketPath
$wrapperPacket = if (![string]::IsNullOrWhiteSpace($wrapperPacketPath) -and (Test-Path -LiteralPath $wrapperPacketPath)) { Read-JsonFile $wrapperPacketPath } else { $null }

$invocationStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList

$readinessText = Get-Content -LiteralPath $ReadinessPath -Raw
$guardText = Get-Content -LiteralPath $GuardPath -Raw

Add-ChecklistItem $checklist "artifact" "Guard envelope packet exists" $true $guardPacketPath
Add-ChecklistItem $checklist "artifact" "Dry-run adapter wrapper packet exists" ($wrapperPacket -ne $null) $wrapperPacketPath "recommended"
Add-ChecklistItem $checklist "artifact" "Readiness report module exists" $true $ReadinessPath
Add-ChecklistItem $checklist "artifact" "Guard envelope module exists" $true $GuardPath
Add-ChecklistItem $checklist "artifact" "Dry-run adapter wrapper module exists" (Test-Path -LiteralPath $WrapperPath) $WrapperPath "recommended"
Add-ChecklistItem $checklist "artifact" "Interface stub module exists" (Test-Path -LiteralPath $InterfaceStubPath) $InterfaceStubPath "recommended"
Add-ChecklistItem $checklist "artifact" "Contract schema module exists" (Test-Path -LiteralPath $ContractSchemaPath) $ContractSchemaPath "recommended"

# Guard source packet checks.
Add-ChecklistItem $checklist "guard_packet" "Guard source packet is guard-envelope-only" ($guardPacket.safety.guard_envelope_only -eq $true) "guard_envelope_only=$($guardPacket.safety.guard_envelope_only)"
Add-ChecklistItem $checklist "guard_packet" "Guard source packet has preview" ($guardPacket.safety.guard_preview_created -eq $true) "guard_preview_created=$($guardPacket.safety.guard_preview_created)"
Add-ChecklistItem $checklist "guard_packet" "Guard source packet has no execution implementation" ($guardPacket.safety.execution_implementation_created -eq $false) "execution_implementation_created=$($guardPacket.safety.execution_implementation_created)"
Add-ChecklistItem $checklist "guard_packet" "Guard source packet has no real bridge HTTP client" ($guardPacket.safety.real_bridge_http_client_implemented -eq $false) "real_bridge_http_client_implemented=$($guardPacket.safety.real_bridge_http_client_implemented)"
Add-ChecklistItem $checklist "guard_packet" "Guard source packet has no network transport" ($guardPacket.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($guardPacket.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "guard_packet" "Guard source packet has no socket opened" ($guardPacket.safety.network_socket_opened -eq $false) "network_socket_opened=$($guardPacket.safety.network_socket_opened)"
Add-ChecklistItem $checklist "guard_packet" "Guard source packet has no bridge POST" ($guardPacket.safety.bridge_post_called -eq $false -and $guardPacket.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($guardPacket.safety.bridge_post_called); bridge_post_call_implemented=$($guardPacket.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "guard_packet" "Guard source packet blocks execution implementation" ($guardPacket.guard_envelope_packet.can_create_execution_implementation_now -eq $false) "can_create_execution_implementation_now=$($guardPacket.guard_envelope_packet.can_create_execution_implementation_now)"
Add-ChecklistItem $checklist "guard_packet" "Guard source packet has no blockers" ([int]$guardPacket.guard_envelope_packet.blocker_count -eq 0) "blocker_count=$($guardPacket.guard_envelope_packet.blocker_count)"

foreach ($issue in @($guardPacket.issues)) {
    if ($issue.severity -eq "blocker") {
        Add-Issue $issues "blocker" "guard_$($issue.code)" "$($issue.message)" "guard_envelope_packet"
    } elseif ($issue.severity -eq "review") {
        Add-Issue $issues "review" "guard_$($issue.code)" "$($issue.message)" "guard_envelope_packet"
    }
}

# Readiness report module checks.
Add-ChecklistItem $checklist "readiness" "Readiness version constant exists" ($readinessText -match "ROUTING_BRIDGE_NETWORK_TRANSPORT_READINESS_REPORT_VERSION") "version constant present"
Add-ChecklistItem $checklist "readiness" "Readiness result class exists" ($readinessText -match "class BridgeRoutingNetworkTransportReadinessReportResult") "readiness result class present"
Add-ChecklistItem $checklist "readiness" "Readiness report class exists" ($readinessText -match "class BridgeRoutingNetworkTransportReadinessReport") "readiness report class present"
Add-ChecklistItem $checklist "readiness" "Build report method exists" ($readinessText -match "def build_report") "build_report present"
Add-ChecklistItem $checklist "readiness" "Guard decision validation exists" ($readinessText -match "def _validate_guard_decision") "guard decision validation present"
Add-ChecklistItem $checklist "readiness" "Status function exists" ($readinessText -match "bridge_routing_network_transport_readiness_report_status") "status function present"
Add-ChecklistItem $checklist "readiness" "Packet dict function exists" ($readinessText -match "bridge_routing_network_transport_readiness_report_packet_dict") "packet dict function present"
Add-ChecklistItem $checklist "readiness" "Readiness report-only flag exists" ($readinessText -match '"readiness_report_only": report.readiness_report_only') "readiness_report_only present"
Add-ChecklistItem $checklist "readiness" "Execution implementation stays false" ($readinessText -match '"execution_implementation_created": report.execution_implementation_created') "execution_implementation_created false"
Add-ChecklistItem $checklist "readiness" "Real bridge HTTP client stays false" ($readinessText -match '"real_bridge_http_client_implemented": report.real_bridge_http_client_implemented') "real_bridge_http_client_implemented false"
Add-ChecklistItem $checklist "readiness" "Network transport stays false" ($readinessText -match '"network_transport_implemented": report.network_transport_implemented') "network_transport_implemented false"
Add-ChecklistItem $checklist "readiness" "Socket opening stays false" ($readinessText -match '"network_socket_opened": report.network_socket_opened') "network_socket_opened false"
Add-ChecklistItem $checklist "readiness" "Bridge POST stays false" ($readinessText -match '"bridge_post_called": report.bridge_post_called') "bridge_post_called false"
Add-ChecklistItem $checklist "readiness" "Routing write endpoint stays false" ($readinessText -match '"routing_write_endpoint_implemented": report.routing_write_endpoint_implemented') "routing_write_endpoint false"
Add-ChecklistItem $checklist "readiness" "No interface execution method call" ($readinessText -notmatch "\.execute_bridge_routing_transport\(") "execute_bridge_routing_transport not called"
Add-ChecklistItem $checklist "readiness" "No socket boundary method call" ($readinessText -notmatch "\.open_network_boundary\(") "open_network_boundary not called"
Add-ChecklistItem $checklist "readiness" "No bridge POST method call" ($readinessText -notmatch "\.call_bridge_post\(") "call_bridge_post not called"
Add-ChecklistItem $checklist "readiness" "No requests import or use" (($readinessText -notmatch "import requests") -and ($readinessText -notmatch "requests\.")) "requests not present"
Add-ChecklistItem $checklist "readiness" "No httpx import or use" (($readinessText -notmatch "import httpx") -and ($readinessText -notmatch "httpx\.")) "httpx not present"
Add-ChecklistItem $checklist "readiness" "No socket import or use" (($readinessText -notmatch "import socket") -and ($readinessText -notmatch "socket\.")) "socket import/use not present"
Add-ChecklistItem $checklist "readiness" "No database commit" ($readinessText -notmatch "\.commit\(") ".commit not present"
Add-ChecklistItem $checklist "readiness" "No database add" ($readinessText -notmatch "\.add\(") ".add not present"

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
    "readiness_report_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "readiness_report_packet_review_required_no_write"
} else {
    "readiness_report_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_readiness_report_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="guard_envelope_packet"; json_path=$guardPacketPath; sha256=Get-FileSha256 $guardPacketPath },
    [ordered]@{ key="dry_run_adapter_wrapper_packet"; json_path=$wrapperPacketPath; sha256=Get-FileSha256 $wrapperPacketPath },
    [ordered]@{ key="readiness_report_module"; json_path=$ReadinessPath; sha256=Get-FileSha256 $ReadinessPath },
    [ordered]@{ key="guard_envelope_module"; json_path=$GuardPath; sha256=Get-FileSha256 $GuardPath },
    [ordered]@{ key="dry_run_adapter_wrapper_module"; json_path=$WrapperPath; sha256=Get-FileSha256 $WrapperPath },
    [ordered]@{ key="interface_stub_module"; json_path=$InterfaceStubPath; sha256=Get-FileSha256 $InterfaceStubPath },
    [ordered]@{ key="contract_schema_module"; json_path=$ContractSchemaPath; sha256=Get-FileSha256 $ContractSchemaPath }
)

$reportMethods = @(
    [ordered]@{ method_name="build_report"; purpose="Build no-write readiness report from guard decision"; calls_execution=$false; network_now=$false; writes_now=$false },
    [ordered]@{ method_name="_validate_guard_decision"; purpose="Block any guard decision that reports execution or mutation"; calls_execution=$false; network_now=$false; writes_now=$false },
    [ordered]@{ method_name="bridge_routing_network_transport_readiness_report_status"; purpose="Expose no-write readiness report status"; calls_execution=$false; network_now=$false; writes_now=$false },
    [ordered]@{ method_name="bridge_routing_network_transport_readiness_report_packet_dict"; purpose="Expose sample no-write readiness report packet"; calls_execution=$false; network_now=$false; writes_now=$false }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 38"
    purpose = "Bridge routing network transport readiness report packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_readiness_report_packet_only = $true
        readiness_report_only = $true
        readiness_preview_created = $true
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
    readiness_report_packet = [ordered]@{
        status = $packetStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        checklist_count = @($checklist).Count
        report_method_count = @($reportMethods).Count
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
        packet_label = "phase20_bridge_routing_network_transport_readiness_report_no_write"
        reason = if ($blockerCount -eq 0) {
            "Readiness report packet is ready for review. Phase 20 Step 38 creates a no-write readiness report, but no execution implementation, no network transport, no socket, no bridge POST, and no live write."
        } else {
            "Readiness report packet has blockers. Resolve blockers before future final review packet design."
        }
    }
    source_artifacts = $sourceArtifacts
    report_methods = $reportMethods
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
        report_methods = @($reportMethods).Count
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this readiness report packet before creating any future final review packet.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 20 Step 38.",
        "Do not call interface execution methods from Phase 20 Step 38.",
        "Do not create execution implementation from Phase 20 Step 38.",
        "Do not capture bridge responses from Phase 20 Step 38.",
        "Do not set environment variables from Phase 20 Step 38.",
        "Do not create audit rows or rollback snapshots from Phase 20 Step 38.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_readiness_report_packet.json"
$methodsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_readiness_report_packet_methods.csv"
$checklistCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_readiness_report_packet_checklist.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_readiness_report_packet_artifacts.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_readiness_report_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_readiness_report_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$reportMethods | Export-Csv -LiteralPath $methodsCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$methodsText = (@($reportMethods) | ForEach-Object { "- $($_.method_name): $($_.purpose); calls_execution=$($_.calls_execution); network_now=$($_.network_now); writes_now=$($_.writes_now)" }) -join "`n"
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Readiness Report Packet

Generated: $($report.generated_at)

Source guard envelope packet:

``````
$guardPacketPath
``````

## Safety

- Bridge routing network transport readiness report packet only: true
- Readiness report only: true
- Readiness preview created: true
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

## Readiness report packet

- Status: $packetStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Report methods: $(@($reportMethods).Count)
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

## Source artifacts

$artifactText

## Report methods

$methodsText

## Checklist

$checklistText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_readiness_report_packet=$OutputDir | status=$packetStatus | bridge_post_called=False | execution_implementation_created=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_readiness_report_packet=$OutputDir | status=$packetStatus | blockers=$blockerCount | bridge_post_called=False | execution_implementation_created=False"
}

Write-Host ""
Write-Host "Readiness report packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
