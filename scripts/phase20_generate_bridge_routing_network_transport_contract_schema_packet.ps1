param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$ImplementationBoundaryPacketDir = "",
    [string]$DesignFreezePacketDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"
$PlatformDir = Join-Path $Workspace "unified_pool_service_platform_build"
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

if ([string]::IsNullOrWhiteSpace($ImplementationBoundaryPacketDir)) {
    $ImplementationBoundaryPacketDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_implementation_boundary_packet_*" -JsonName "phase20_bridge_routing_network_transport_implementation_boundary_packet.json"
}
if ([string]::IsNullOrWhiteSpace($DesignFreezePacketDir)) {
    $DesignFreezePacketDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_*" -JsonName "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet.json" -Required $false
}

$boundaryPath = Join-Path $ImplementationBoundaryPacketDir "phase20_bridge_routing_network_transport_implementation_boundary_packet.json"
$freezePath = if (![string]::IsNullOrWhiteSpace($DesignFreezePacketDir)) { Join-Path $DesignFreezePacketDir "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet.json" } else { "" }

if (!(Test-Path -LiteralPath $boundaryPath)) {
    throw "Implementation boundary packet JSON not found: $boundaryPath"
}
if (!(Test-Path -LiteralPath $ContractSchemaPath)) {
    throw "Contract schema module not found: $ContractSchemaPath"
}

$boundary = Read-JsonFile $boundaryPath
$freeze = if (![string]::IsNullOrWhiteSpace($freezePath) -and (Test-Path -LiteralPath $freezePath)) { Read-JsonFile $freezePath } else { $null }

$invocationStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList

$schemaText = Get-Content -LiteralPath $ContractSchemaPath -Raw

Add-ChecklistItem $checklist "artifact" "Implementation boundary packet exists" $true $boundaryPath
Add-ChecklistItem $checklist "artifact" "Design freeze packet exists" ($freeze -ne $null) $freezePath "recommended"
Add-ChecklistItem $checklist "artifact" "Contract schema module exists" $true $ContractSchemaPath

# Boundary source checks.
Add-ChecklistItem $checklist "boundary" "Implementation boundary source is boundary-only" ($boundary.safety.bridge_routing_network_transport_implementation_boundary_packet_only -eq $true) "bridge_routing_network_transport_implementation_boundary_packet_only=$($boundary.safety.bridge_routing_network_transport_implementation_boundary_packet_only)"
Add-ChecklistItem $checklist "boundary" "Implementation boundary source is bridge GET only" ($boundary.safety.bridge_get_only -eq $true) "bridge_get_only=$($boundary.safety.bridge_get_only)"
Add-ChecklistItem $checklist "boundary" "Boundary source has no implementation code" ($boundary.safety.implementation_code_created -eq $false) "implementation_code_created=$($boundary.safety.implementation_code_created)"
Add-ChecklistItem $checklist "boundary" "Boundary source has no real bridge HTTP client" ($boundary.safety.real_bridge_http_client_implemented -eq $false) "real_bridge_http_client_implemented=$($boundary.safety.real_bridge_http_client_implemented)"
Add-ChecklistItem $checklist "boundary" "Boundary source has no network transport" ($boundary.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($boundary.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "boundary" "Boundary source has no socket opened" ($boundary.safety.network_socket_opened -eq $false) "network_socket_opened=$($boundary.safety.network_socket_opened)"
Add-ChecklistItem $checklist "boundary" "Boundary source has no bridge POST" ($boundary.safety.bridge_post_called -eq $false -and $boundary.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($boundary.safety.bridge_post_called); bridge_post_call_implemented=$($boundary.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "boundary" "Boundary source blocks implementation code" ($boundary.implementation_boundary_packet.can_create_implementation_code_now -eq $false) "can_create_implementation_code_now=$($boundary.implementation_boundary_packet.can_create_implementation_code_now)"
Add-ChecklistItem $checklist "boundary" "Boundary source has no blockers" ([int]$boundary.implementation_boundary_packet.blocker_count -eq 0) "blocker_count=$($boundary.implementation_boundary_packet.blocker_count)"

foreach ($issue in @($boundary.issues)) {
    if ($issue.severity -eq "blocker") {
        Add-Issue $issues "blocker" "boundary_$($issue.code)" "$($issue.message)" "implementation_boundary_packet"
    } elseif ($issue.severity -eq "review") {
        Add-Issue $issues "review" "boundary_$($issue.code)" "$($issue.message)" "implementation_boundary_packet"
    }
}

# Contract schema source checks.
Add-ChecklistItem $checklist "schema" "Contract schema version constant exists" ($schemaText -match "ROUTING_BRIDGE_NETWORK_TRANSPORT_CONTRACT_SCHEMA_VERSION") "version constant present"
Add-ChecklistItem $checklist "schema" "Request contract exists" ($schemaText -match "class BridgeRoutingTransportRequestContract") "BridgeRoutingTransportRequestContract present"
Add-ChecklistItem $checklist "schema" "Response contract exists" ($schemaText -match "class BridgeRoutingTransportResponseContract") "BridgeRoutingTransportResponseContract present"
Add-ChecklistItem $checklist "schema" "Audit contract exists" ($schemaText -match "class BridgeRoutingAuditContract") "BridgeRoutingAuditContract present"
Add-ChecklistItem $checklist "schema" "Rollback contract exists" ($schemaText -match "class BridgeRoutingRollbackContract") "BridgeRoutingRollbackContract present"
Add-ChecklistItem $checklist "schema" "Cutover contract exists" ($schemaText -match "class BridgeRoutingCutoverContract") "BridgeRoutingCutoverContract present"
Add-ChecklistItem $checklist "schema" "Packet contract exists" ($schemaText -match "class BridgeRoutingNetworkTransportContractPacket") "BridgeRoutingNetworkTransportContractPacket present"
Add-ChecklistItem $checklist "schema" "Schema status function exists" ($schemaText -match "bridge_routing_network_transport_contract_schema_status") "status function present"
Add-ChecklistItem $checklist "schema" "Schema dict function exists" ($schemaText -match "bridge_routing_network_transport_contract_schema_dict") "schema dict function present"
Add-ChecklistItem $checklist "schema" "Schema-only flag exists" ($schemaText -match '"contract_schema_scaffold_only": True') "contract_schema_scaffold_only present"
Add-ChecklistItem $checklist "schema" "Execution implementation stays false" ($schemaText -match '"execution_implementation_created": False') "execution_implementation_created false"
Add-ChecklistItem $checklist "schema" "Real bridge HTTP client stays false" ($schemaText -match '"real_bridge_http_client_implemented": False') "real_bridge_http_client_implemented false"
Add-ChecklistItem $checklist "schema" "Network transport stays false" ($schemaText -match '"network_transport_implemented": False') "network_transport_implemented false"
Add-ChecklistItem $checklist "schema" "Socket opening stays false" ($schemaText -match '"network_socket_opened": False') "network_socket_opened false"
Add-ChecklistItem $checklist "schema" "Bridge POST stays false" ($schemaText -match '"bridge_post_called": False') "bridge_post_called false"
Add-ChecklistItem $checklist "schema" "Routing write endpoint stays false" ($schemaText -match '"routing_write_endpoint_implemented": False') "routing_write_endpoint_implemented false"
Add-ChecklistItem $checklist "schema" "No requests import or use" (($schemaText -notmatch "import requests") -and ($schemaText -notmatch "requests\.")) "requests not present"
Add-ChecklistItem $checklist "schema" "No httpx import or use" (($schemaText -notmatch "import httpx") -and ($schemaText -notmatch "httpx\.")) "httpx not present"
Add-ChecklistItem $checklist "schema" "No socket import or use" (($schemaText -notmatch "import socket") -and ($schemaText -notmatch "socket\.")) "socket import/use not present"
Add-ChecklistItem $checklist "schema" "No database commit" ($schemaText -notmatch "\.commit\(") ".commit not present"
Add-ChecklistItem $checklist "schema" "No database add" ($schemaText -notmatch "\.add\(") ".add not present"

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
    "contract_schema_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "contract_schema_packet_review_required_no_write"
} else {
    "contract_schema_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_contract_schema_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="implementation_boundary_packet"; json_path=$boundaryPath; sha256=Get-FileSha256 $boundaryPath },
    [ordered]@{ key="design_freeze_packet"; json_path=$freezePath; sha256=Get-FileSha256 $freezePath },
    [ordered]@{ key="contract_schema_module"; json_path=$ContractSchemaPath; sha256=Get-FileSha256 $ContractSchemaPath }
)

$schemaContracts = @(
    [ordered]@{ contract_type="BridgeRoutingTransportRequestContract"; purpose="Future request shape only"; writes_now=$false; network_now=$false },
    [ordered]@{ contract_type="BridgeRoutingTransportResponseContract"; purpose="Future response evidence shape only"; writes_now=$false; network_now=$false },
    [ordered]@{ contract_type="BridgeRoutingAuditContract"; purpose="Future audit linkage shape only"; writes_now=$false; network_now=$false },
    [ordered]@{ contract_type="BridgeRoutingRollbackContract"; purpose="Future rollback linkage shape only"; writes_now=$false; network_now=$false },
    [ordered]@{ contract_type="BridgeRoutingCutoverContract"; purpose="Future cutover linkage shape only"; writes_now=$false; network_now=$false },
    [ordered]@{ contract_type="BridgeRoutingNetworkTransportContractPacket"; purpose="Future packet composition shape only"; writes_now=$false; network_now=$false }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 34"
    purpose = "Bridge routing network transport contract schema packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_contract_schema_packet_only = $true
        contract_schema_scaffold_only = $true
        schema_only_code_created = $true
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
    contract_schema_packet = [ordered]@{
        status = $packetStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        checklist_count = @($checklist).Count
        contract_type_count = @($schemaContracts).Count
        artifact_count = @($sourceArtifacts).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        can_add_bridge_post_now = $false
        can_create_execution_implementation_now = $false
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
        packet_label = "phase20_bridge_routing_network_transport_contract_schema_no_write"
        reason = if ($blockerCount -eq 0) {
            "Contract schema packet is ready for review. Phase 20 Step 34 creates schema-only contract code, but no execution implementation, no network transport, no socket, no bridge POST, and no live write."
        } else {
            "Contract schema packet has blockers. Resolve blockers before future transport implementation design."
        }
    }
    source_artifacts = $sourceArtifacts
    schema_contracts = $schemaContracts
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
        schema_contracts = @($schemaContracts).Count
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this contract schema packet before creating any future non-network interface stubs.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 20 Step 34.",
        "Do not create execution implementation from Phase 20 Step 34.",
        "Do not create design-freeze records from Phase 20 Step 34.",
        "Do not create cutover packets from Phase 20 Step 34.",
        "Do not capture bridge responses from Phase 20 Step 34.",
        "Do not set environment variables from Phase 20 Step 34.",
        "Do not create audit rows or rollback snapshots from Phase 20 Step 34.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_contract_schema_packet.json"
$contractsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_contract_schema_packet_contracts.csv"
$checklistCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_contract_schema_packet_checklist.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_contract_schema_packet_artifacts.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_contract_schema_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_contract_schema_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$schemaContracts | Export-Csv -LiteralPath $contractsCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$contractsText = (@($schemaContracts) | ForEach-Object { "- $($_.contract_type): $($_.purpose); writes_now=$($_.writes_now); network_now=$($_.network_now)" }) -join "`n"
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Contract Schema Packet

Generated: $($report.generated_at)

Source implementation boundary packet:

``````
$boundaryPath
``````

## Safety

- Bridge routing network transport contract schema packet only: true
- Contract schema scaffold only: true
- Schema-only code created: true
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

## Contract schema packet

- Status: $packetStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Contract types: $(@($schemaContracts).Count)
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

## Schema contracts

$contractsText

## Checklist

$checklistText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_contract_schema_packet=$OutputDir | status=$packetStatus | bridge_post_called=False | execution_implementation_created=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_contract_schema_packet=$OutputDir | status=$packetStatus | blockers=$blockerCount | bridge_post_called=False | execution_implementation_created=False"
}

Write-Host ""
Write-Host "Contract schema packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
