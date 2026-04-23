param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$DesignClosurePacketDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"
$PlatformDir = Join-Path $Workspace "unified_pool_service_platform_build"

function Get-LatestArtifactDir {
    param(
        [string]$FolderFilter,
        [string]$JsonName,
        [bool]$Required = $false
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

function Add-Artifact {
    param(
        [System.Collections.ArrayList]$Artifacts,
        [string]$Step,
        [string]$Key,
        [string]$FolderFilter,
        [string]$JsonName,
        [bool]$Required = $false
    )

    $dir = Get-LatestArtifactDir -FolderFilter $FolderFilter -JsonName $JsonName -Required $Required
    $path = ""
    $exists = $false
    $sha = ""
    $status = "missing"

    if (![string]::IsNullOrWhiteSpace($dir)) {
        $path = Join-Path $dir $JsonName
        $exists = Test-Path -LiteralPath $path
        if ($exists) {
            $sha = Get-FileSha256 $path
            $status = "present"
        }
    }

    [void]$Artifacts.Add([ordered]@{
        step = $Step
        key = $Key
        folder_filter = $FolderFilter
        json_name = $JsonName
        folder_path = $dir
        json_path = $path
        present = $exists
        required = $Required
        sha256 = $sha
        status = $status
    })
}

function Test-SourceFileClean {
    param(
        [string]$Path,
        [string[]]$ForbiddenPatterns
    )

    if (!(Test-Path -LiteralPath $Path)) {
        return @{ ok = $false; evidence = "missing: $Path" }
    }

    $text = Get-Content -LiteralPath $Path -Raw
    $hits = @()
    foreach ($pattern in $ForbiddenPatterns) {
        if ($text -match $pattern) {
            $hits += $pattern
        }
    }

    if ($hits.Count -gt 0) {
        return @{ ok = $false; evidence = "forbidden patterns: $($hits -join ', ')" }
    }

    return @{ ok = $true; evidence = "clean: $Path" }
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($DesignClosurePacketDir)) {
    $DesignClosurePacketDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_design_closure_packet_*" -JsonName "phase20_bridge_routing_network_transport_design_closure_packet.json" -Required $true
}

$designClosurePath = Join-Path $DesignClosurePacketDir "phase20_bridge_routing_network_transport_design_closure_packet.json"
if (!(Test-Path -LiteralPath $designClosurePath)) {
    throw "Phase 20 design closure packet JSON not found: $designClosurePath"
}

$designClosure = Read-JsonFile $designClosurePath

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList
$artifacts = New-Object System.Collections.ArrayList

Add-Artifact $artifacts "Phase 20 Step 24" "audit_prerequisite_gate" "phase20_bridge_routing_network_transport_audit_prerequisite_gate_*" "phase20_bridge_routing_network_transport_audit_prerequisite_gate.json"
Add-Artifact $artifacts "Phase 20 Step 25" "rollback_snapshot_prerequisite_gate" "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate_*" "phase20_bridge_routing_network_transport_rollback_snapshot_prerequisite_gate.json"
Add-Artifact $artifacts "Phase 20 Step 26" "environment_gate_design" "phase20_bridge_routing_network_transport_environment_gate_design_*" "phase20_bridge_routing_network_transport_environment_gate_design.json"
Add-Artifact $artifacts "Phase 20 Step 27" "operator_confirmation_gate_design" "phase20_bridge_routing_network_transport_operator_confirmation_gate_design_*" "phase20_bridge_routing_network_transport_operator_confirmation_gate_design.json"
Add-Artifact $artifacts "Phase 20 Step 28" "response_capture_gate_design" "phase20_bridge_routing_network_transport_response_capture_gate_design_*" "phase20_bridge_routing_network_transport_response_capture_gate_design.json"
Add-Artifact $artifacts "Phase 20 Step 29" "cutover_packet_prerequisite_gate_design" "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design_*" "phase20_bridge_routing_network_transport_cutover_packet_prerequisite_gate_design.json"
Add-Artifact $artifacts "Phase 20 Step 30" "prerequisite_chain_release_checkpoint" "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint_*" "phase20_bridge_routing_network_transport_prerequisite_chain_release_checkpoint.json"
Add-Artifact $artifacts "Phase 20 Step 31" "prerequisite_chain_operator_signoff" "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff_*" "phase20_bridge_routing_network_transport_prerequisite_chain_operator_signoff.json"
Add-Artifact $artifacts "Phase 20 Step 32" "prerequisite_chain_design_freeze_packet" "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet_*" "phase20_bridge_routing_network_transport_prerequisite_chain_design_freeze_packet.json"
Add-Artifact $artifacts "Phase 20 Step 33" "implementation_boundary_packet" "phase20_bridge_routing_network_transport_implementation_boundary_packet_*" "phase20_bridge_routing_network_transport_implementation_boundary_packet.json"
Add-Artifact $artifacts "Phase 20 Step 34" "contract_schema_packet" "phase20_bridge_routing_network_transport_contract_schema_packet_*" "phase20_bridge_routing_network_transport_contract_schema_packet.json"
Add-Artifact $artifacts "Phase 20 Step 35" "interface_stub_packet" "phase20_bridge_routing_network_transport_interface_stub_packet_*" "phase20_bridge_routing_network_transport_interface_stub_packet.json"
Add-Artifact $artifacts "Phase 20 Step 36" "dry_run_adapter_wrapper_packet" "phase20_bridge_routing_network_transport_dry_run_adapter_wrapper_packet_*" "phase20_bridge_routing_network_transport_dry_run_adapter_wrapper_packet.json"
Add-Artifact $artifacts "Phase 20 Step 37" "guard_envelope_packet" "phase20_bridge_routing_network_transport_guard_envelope_packet_*" "phase20_bridge_routing_network_transport_guard_envelope_packet.json"
Add-Artifact $artifacts "Phase 20 Step 38" "readiness_report_packet" "phase20_bridge_routing_network_transport_readiness_report_packet_*" "phase20_bridge_routing_network_transport_readiness_report_packet.json"
Add-Artifact $artifacts "Phase 20 Step 39" "final_review_packet" "phase20_bridge_routing_network_transport_final_review_packet_*" "phase20_bridge_routing_network_transport_final_review_packet.json"
Add-Artifact $artifacts "Phase 20 Step 40" "design_closure_packet" "phase20_bridge_routing_network_transport_design_closure_packet_*" "phase20_bridge_routing_network_transport_design_closure_packet.json" $true

Add-ChecklistItem $checklist "artifact" "Required Phase 20 Step 40 design closure packet exists" $true $designClosurePath
Add-ChecklistItem $checklist "closure" "Design closure packet is closure-only" ($designClosure.safety.design_closure_packet_only -eq $true) "design_closure_packet_only=$($designClosure.safety.design_closure_packet_only)"
Add-ChecklistItem $checklist "closure" "Design closure packet created no closure record" ($designClosure.safety.design_closure_record_created -eq $false) "design_closure_record_created=$($designClosure.safety.design_closure_record_created)"
Add-ChecklistItem $checklist "closure" "Design closure packet recorded no final approval" ($designClosure.safety.final_approval_recorded -eq $false) "final_approval_recorded=$($designClosure.safety.final_approval_recorded)"
Add-ChecklistItem $checklist "closure" "Design closure packet did not start implementation" ($designClosure.safety.implementation_phase_started -eq $false) "implementation_phase_started=$($designClosure.safety.implementation_phase_started)"
Add-ChecklistItem $checklist "closure" "Design closure packet has no execution implementation" ($designClosure.safety.execution_implementation_created -eq $false) "execution_implementation_created=$($designClosure.safety.execution_implementation_created)"
Add-ChecklistItem $checklist "closure" "Design closure packet has no bridge POST" ($designClosure.safety.bridge_post_called -eq $false -and $designClosure.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($designClosure.safety.bridge_post_called); bridge_post_call_implemented=$($designClosure.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "closure" "Design closure packet has no network transport" ($designClosure.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($designClosure.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "closure" "Design closure packet has no socket opened" ($designClosure.safety.network_socket_opened -eq $false) "network_socket_opened=$($designClosure.safety.network_socket_opened)"
Add-ChecklistItem $checklist "closure" "Design closure packet has no platform DB mutation" ($designClosure.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($designClosure.safety.platform_db_mutation_performed)"
Add-ChecklistItem $checklist "closure" "Design closure packet has no bridge mutation" ($designClosure.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($designClosure.safety.bridge_mutation_performed)"
Add-ChecklistItem $checklist "closure" "Design closure packet has no LACRM call" ($designClosure.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($designClosure.safety.lacrm_call_performed)"
Add-ChecklistItem $checklist "closure" "Design closure packet has no live write" ($designClosure.safety.live_write_enabled -eq $false) "live_write_enabled=$($designClosure.safety.live_write_enabled)"

$presentArtifacts = @($artifacts | Where-Object { $_.present -eq $true }).Count
$missingArtifacts = @($artifacts | Where-Object { $_.present -ne $true }).Count
Add-ChecklistItem $checklist "artifact" "At least Phase 20 Step 40 and closeout chain artifacts are indexed" ($presentArtifacts -ge 1) "present_artifacts=$presentArtifacts"
Add-ChecklistItem $checklist "artifact" "No Phase 20 evidence artifacts missing from index" ($missingArtifacts -eq 0) "missing_artifacts=$missingArtifacts" "recommended"

foreach ($artifact in @($artifacts)) {
    if ($artifact.present -ne $true -and $artifact.required -eq $true) {
        Add-Issue $issues "blocker" "required_artifact_missing_$($artifact.key)" "$($artifact.step) artifact missing: $($artifact.folder_filter)" "artifact"
    } elseif ($artifact.present -ne $true) {
        Add-Issue $issues "review" "optional_artifact_missing_$($artifact.key)" "$($artifact.step) artifact missing or not generated yet: $($artifact.folder_filter)" "artifact"
    }
}

$sourceFiles = @(
    "app\services\routing_bridge_network_transport_contract_schema.py",
    "app\services\routing_bridge_network_transport_interface_stub.py",
    "app\services\routing_bridge_network_transport_dry_run_adapter_wrapper.py",
    "app\services\routing_bridge_network_transport_guard_envelope.py",
    "app\services\routing_bridge_network_transport_readiness_report.py",
    "app\services\routing_bridge_network_transport_final_review_packet.py",
    "app\services\routing_bridge_network_transport_design_closure_packet.py"
)

$forbiddenPatterns = @(
    "import requests",
    "requests\.",
    "import httpx",
    "httpx\.",
    "import socket",
    "socket\.",
    "\.commit\(",
    "\.add\(",
    "Session\("
)

$sourceAudits = New-Object System.Collections.ArrayList
foreach ($rel in $sourceFiles) {
    $path = Join-Path $PlatformDir $rel
    $audit = Test-SourceFileClean -Path $path -ForbiddenPatterns $forbiddenPatterns
    [void]$sourceAudits.Add([ordered]@{
        path = $rel
        clean = $audit.ok
        evidence = $audit.evidence
        sha256 = Get-FileSha256 $path
    })
    Add-ChecklistItem $checklist "source" "Source clean: $rel" $audit.ok $audit.evidence "recommended"
}

$invocationStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

if ($invocationStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Dry-run invocation path status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status" "recommended"
    Add-ChecklistItem $checklist "runtime" "Runtime dry-run invocation has no bridge POST" ($invocationStatus.value.bridge_post_called -eq $false -and $invocationStatus.value.bridge_post_call_implemented -eq $false) "bridge_post_called=$($invocationStatus.value.bridge_post_called); bridge_post_call_implemented=$($invocationStatus.value.bridge_post_call_implemented)" "recommended"
} else {
    Add-ChecklistItem $checklist "runtime" "Dry-run invocation path status readable" $false $invocationStatus.error "recommended"
}

if ($scaffoldStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Interface scaffold status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status" "recommended"
} else {
    Add-ChecklistItem $checklist "runtime" "Interface scaffold status readable" $false $scaffoldStatus.error "recommended"
}

if ($adapterStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Dry-run adapter status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status" "recommended"
} else {
    Add-ChecklistItem $checklist "runtime" "Dry-run adapter status readable" $false $adapterStatus.error "recommended"
}

if ($guardStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Network transport guard status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status" "recommended"
} else {
    Add-ChecklistItem $checklist "runtime" "Network transport guard status readable" $false $guardStatus.error "recommended"
}

if ($httpDryRunStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "HTTP client dry-run status readable" $true "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status" "recommended"
} else {
    Add-ChecklistItem $checklist "runtime" "HTTP client dry-run status readable" $false $httpDryRunStatus.error "recommended"
}

if ($executorStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Executor status readable" $true "$PlatformApi/front-desk/routing/bridge-write-executor/status" "recommended"
    Add-ChecklistItem $checklist "runtime" "Executor has no execution endpoint" ($executorStatus.value.execution_endpoint_available -eq $false) "execution_endpoint_available=$($executorStatus.value.execution_endpoint_available)" "recommended"
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
    "phase20_evidence_index_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "phase20_evidence_index_review_required_no_write"
} else {
    "phase20_evidence_index_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase21_phase20_network_transport_evidence_index_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 21 Step 1"
    purpose = "Phase 20 bridge routing network transport evidence index"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        phase20_network_transport_evidence_index_only = $true
        evidence_index_only = $true
        bridge_get_only = $true
        design_closure_record_created = $false
        final_approval_recorded = $false
        implementation_phase_started = $false
        execution_implementation_created = $false
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
    evidence_index = [ordered]@{
        status = $packetStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        artifact_count = @($artifacts).Count
        present_artifact_count = $presentArtifacts
        missing_artifact_count = $missingArtifacts
        source_audit_count = @($sourceAudits).Count
        checklist_count = @($checklist).Count
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
        packet_label = "phase21_phase20_network_transport_evidence_index_no_write"
        reason = if ($blockerCount -eq 0) {
            "Phase 21 Step 1 indexed the Phase 20 no-write network transport evidence chain. It does not authorize approvals, implementation, network transport, sockets, bridge POST, response capture, mutations, LACRM calls, or live writes."
        } else {
            "Phase 21 Step 1 found blockers in the Phase 20 evidence index. Resolve blockers before proceeding with further closeout work."
        }
    }
    artifacts = @($artifacts)
    source_audits = @($sourceAudits)
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
        artifacts = @($artifacts).Count
        present_artifacts = $presentArtifacts
        missing_artifacts = $missingArtifacts
        source_audits = @($sourceAudits).Count
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this evidence index as the first Phase 21 closeout artifact.",
        "Use it to identify missing Phase 20 generated artifacts before creating a consolidated closeout packet.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 21 Step 1.",
        "Do not call interface execution methods from Phase 21 Step 1.",
        "Do not record final approvals from Phase 21 Step 1.",
        "Do not start an implementation phase from Phase 21 Step 1.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase21_phase20_network_transport_evidence_index.json"
$artifactsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_evidence_index_artifacts.csv"
$sourceCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_evidence_index_source_audits.csv"
$checklistCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_evidence_index_checklist.csv"
$issuesCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_evidence_index_issues.csv"
$mdPath = Join-Path $OutputDir "phase21_phase20_network_transport_evidence_index.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$artifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$sourceAudits | Export-Csv -LiteralPath $sourceCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$artifactText = (@($artifacts) | ForEach-Object { "- $($_.step) / $($_.key): $($_.status) - $($_.json_path)" }) -join "`n"
$sourceText = (@($sourceAudits) | ForEach-Object { "- $($_.path): clean=$($_.clean) - $($_.evidence)" }) -join "`n"
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 21 Step 1 - Phase 20 Network Transport Evidence Index

Generated: $($report.generated_at)

Source design closure packet:

``````
$designClosurePath
``````

## Safety

- Phase 20 network transport evidence index only: true
- Evidence index only: true
- Bridge GET only: true
- Design closure record created: false
- Final approval recorded: false
- Implementation phase started: false
- Execution implementation created: false
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

## Evidence index

- Status: $packetStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Artifacts indexed: $(@($artifacts).Count)
- Present artifacts: $presentArtifacts
- Missing artifacts: $missingArtifacts
- Source audits: $(@($sourceAudits).Count)
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

## Artifacts

$artifactText

## Source audits

$sourceText

## Checklist

$checklistText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | phase20_network_transport_evidence_index=$OutputDir | status=$packetStatus | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
} else {
    Write-Host "CHECK | phase20_network_transport_evidence_index=$OutputDir | status=$packetStatus | blockers=$blockerCount | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
}

Write-Host ""
Write-Host "Evidence index files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
