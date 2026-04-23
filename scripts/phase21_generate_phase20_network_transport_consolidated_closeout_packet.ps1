param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$EvidenceIndexDir = "",
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
        [bool]$Required = $true
    )

    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter $FolderFilter -ErrorAction SilentlyContinue |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName $JsonName) } |
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

if ([string]::IsNullOrWhiteSpace($EvidenceIndexDir)) {
    $EvidenceIndexDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_evidence_index_*" -JsonName "phase21_phase20_network_transport_evidence_index.json" -Required $true
}
if ([string]::IsNullOrWhiteSpace($DesignClosurePacketDir)) {
    $DesignClosurePacketDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_design_closure_packet_*" -JsonName "phase20_bridge_routing_network_transport_design_closure_packet.json" -Required $true
}

$evidenceIndexPath = Join-Path $EvidenceIndexDir "phase21_phase20_network_transport_evidence_index.json"
$designClosurePath = Join-Path $DesignClosurePacketDir "phase20_bridge_routing_network_transport_design_closure_packet.json"

if (!(Test-Path -LiteralPath $evidenceIndexPath)) {
    throw "Evidence index JSON not found: $evidenceIndexPath"
}
if (!(Test-Path -LiteralPath $designClosurePath)) {
    throw "Design closure packet JSON not found: $designClosurePath"
}

$evidenceIndex = Read-JsonFile $evidenceIndexPath
$designClosure = Read-JsonFile $designClosurePath

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList

Add-ChecklistItem $checklist "artifact" "Evidence index exists" $true $evidenceIndexPath
Add-ChecklistItem $checklist "artifact" "Design closure packet exists" $true $designClosurePath

Add-ChecklistItem $checklist "evidence_index" "Evidence index is no-write only" ($evidenceIndex.safety.phase20_network_transport_evidence_index_only -eq $true) "phase20_network_transport_evidence_index_only=$($evidenceIndex.safety.phase20_network_transport_evidence_index_only)"
Add-ChecklistItem $checklist "evidence_index" "Evidence index did not start implementation" ($evidenceIndex.safety.implementation_phase_started -eq $false) "implementation_phase_started=$($evidenceIndex.safety.implementation_phase_started)"
Add-ChecklistItem $checklist "evidence_index" "Evidence index did not record final approval" ($evidenceIndex.safety.final_approval_recorded -eq $false) "final_approval_recorded=$($evidenceIndex.safety.final_approval_recorded)"
Add-ChecklistItem $checklist "evidence_index" "Evidence index did not create execution implementation" ($evidenceIndex.safety.execution_implementation_created -eq $false) "execution_implementation_created=$($evidenceIndex.safety.execution_implementation_created)"
Add-ChecklistItem $checklist "evidence_index" "Evidence index did not add network transport" ($evidenceIndex.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($evidenceIndex.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "evidence_index" "Evidence index did not call bridge POST" ($evidenceIndex.safety.bridge_post_called -eq $false -and $evidenceIndex.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($evidenceIndex.safety.bridge_post_called); bridge_post_call_implemented=$($evidenceIndex.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "evidence_index" "Evidence index has no blockers" ([int]$evidenceIndex.evidence_index.blocker_count -eq 0) "blocker_count=$($evidenceIndex.evidence_index.blocker_count)"

Add-ChecklistItem $checklist "design_closure" "Design closure is no-write only" ($designClosure.safety.design_closure_packet_only -eq $true) "design_closure_packet_only=$($designClosure.safety.design_closure_packet_only)"
Add-ChecklistItem $checklist "design_closure" "Design closure created no closure record" ($designClosure.safety.design_closure_record_created -eq $false) "design_closure_record_created=$($designClosure.safety.design_closure_record_created)"
Add-ChecklistItem $checklist "design_closure" "Design closure recorded no final approval" ($designClosure.safety.final_approval_recorded -eq $false) "final_approval_recorded=$($designClosure.safety.final_approval_recorded)"
Add-ChecklistItem $checklist "design_closure" "Design closure started no implementation phase" ($designClosure.safety.implementation_phase_started -eq $false) "implementation_phase_started=$($designClosure.safety.implementation_phase_started)"
Add-ChecklistItem $checklist "design_closure" "Design closure did not create execution implementation" ($designClosure.safety.execution_implementation_created -eq $false) "execution_implementation_created=$($designClosure.safety.execution_implementation_created)"
Add-ChecklistItem $checklist "design_closure" "Design closure did not add network transport" ($designClosure.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($designClosure.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "design_closure" "Design closure did not call bridge POST" ($designClosure.safety.bridge_post_called -eq $false -and $designClosure.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($designClosure.safety.bridge_post_called); bridge_post_call_implemented=$($designClosure.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "design_closure" "Design closure did not mutate bridge" ($designClosure.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($designClosure.safety.bridge_mutation_performed)"
Add-ChecklistItem $checklist "design_closure" "Design closure did not mutate platform DB" ($designClosure.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($designClosure.safety.platform_db_mutation_performed)"
Add-ChecklistItem $checklist "design_closure" "Design closure did not call LACRM" ($designClosure.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($designClosure.safety.lacrm_call_performed)"
Add-ChecklistItem $checklist "design_closure" "Design closure did not enable live write" ($designClosure.safety.live_write_enabled -eq $false) "live_write_enabled=$($designClosure.safety.live_write_enabled)"
Add-ChecklistItem $checklist "design_closure" "Design closure has no blockers" ([int]$designClosure.design_closure_packet.blocker_count -eq 0) "blocker_count=$($designClosure.design_closure_packet.blocker_count)"

$artifacts = @($evidenceIndex.artifacts)
$sourceAudits = @($evidenceIndex.source_audits)
$presentArtifacts = @($artifacts | Where-Object { $_.present -eq $true })
$missingArtifacts = @($artifacts | Where-Object { $_.present -ne $true })

$phase20Buckets = @(
    [ordered]@{
        bucket = "Prerequisite gates"
        description = "Phase 20 Step 24 through Step 31 preconditions, checkpoints, and signoff scaffolds."
        expected_keys = @(
            "audit_prerequisite_gate",
            "rollback_snapshot_prerequisite_gate",
            "environment_gate_design",
            "operator_confirmation_gate_design",
            "response_capture_gate_design",
            "cutover_packet_prerequisite_gate_design",
            "prerequisite_chain_release_checkpoint",
            "prerequisite_chain_operator_signoff"
        )
    },
    [ordered]@{
        bucket = "Boundary and contracts"
        description = "Phase 20 Step 32 through Step 35 design freeze, boundary, schema, and non-network interface stubs."
        expected_keys = @(
            "prerequisite_chain_design_freeze_packet",
            "implementation_boundary_packet",
            "contract_schema_packet",
            "interface_stub_packet"
        )
    },
    [ordered]@{
        bucket = "Preview wrappers and reporting"
        description = "Phase 20 Step 36 through Step 40 preview-only wrappers, reports, final review, and design closure."
        expected_keys = @(
            "dry_run_adapter_wrapper_packet",
            "guard_envelope_packet",
            "readiness_report_packet",
            "final_review_packet",
            "design_closure_packet"
        )
    }
)

$bucketRows = New-Object System.Collections.ArrayList
foreach ($bucket in $phase20Buckets) {
    $rows = @($artifacts | Where-Object { $bucket.expected_keys -contains $_.key })
    $present = @($rows | Where-Object { $_.present -eq $true }).Count
    $missing = @($rows | Where-Object { $_.present -ne $true }).Count
    [void]$bucketRows.Add([ordered]@{
        bucket = $bucket.bucket
        description = $bucket.description
        expected_count = @($bucket.expected_keys).Count
        present_count = $present
        missing_count = $missing
        all_present = ($missing -eq 0)
    })
}

Add-ChecklistItem $checklist "consolidation" "At least one artifact exists in each closeout bucket" (@($bucketRows | Where-Object { $_.present_count -gt 0 }).Count -eq @($bucketRows).Count) ("bucket_presence=" + ((@($bucketRows) | ForEach-Object { "$($_.bucket):$($_.present_count)" }) -join "; ")) "recommended"
Add-ChecklistItem $checklist "consolidation" "All Phase 20 source audits are clean" (@($sourceAudits | Where-Object { $_.clean -eq $false }).Count -eq 0) ("unclean_source_audits=" + @($sourceAudits | Where-Object { $_.clean -eq $false }).Count) "recommended"

$invocationStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

if ($invocationStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Dry-run invocation status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status" "recommended"
    Add-ChecklistItem $checklist "runtime" "Runtime dry-run invocation has no bridge POST" ($invocationStatus.value.bridge_post_called -eq $false -and $invocationStatus.value.bridge_post_call_implemented -eq $false) "bridge_post_called=$($invocationStatus.value.bridge_post_called); bridge_post_call_implemented=$($invocationStatus.value.bridge_post_call_implemented)" "recommended"
} else {
    Add-ChecklistItem $checklist "runtime" "Dry-run invocation status readable" $false $invocationStatus.error "recommended"
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
    Add-ChecklistItem $checklist "runtime" "Guard status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status" "recommended"
} else {
    Add-ChecklistItem $checklist "runtime" "Guard status readable" $false $guardStatus.error "recommended"
}

if ($httpDryRunStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "HTTP dry-run status readable" $true "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status" "recommended"
} else {
    Add-ChecklistItem $checklist "runtime" "HTTP dry-run status readable" $false $httpDryRunStatus.error "recommended"
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
    "phase20_closeout_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "phase20_closeout_packet_review_required_no_write"
} else {
    "phase20_closeout_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase21_phase20_network_transport_consolidated_closeout_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 21 Step 2"
    purpose = "Phase 20 bridge routing network transport consolidated closeout packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        phase20_network_transport_consolidated_closeout_packet_only = $true
        consolidated_closeout_packet_only = $true
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
    closeout_packet = [ordered]@{
        status = $packetStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        bucket_count = @($bucketRows).Count
        artifact_count = @($artifacts).Count
        present_artifact_count = @($presentArtifacts).Count
        missing_artifact_count = @($missingArtifacts).Count
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
        packet_label = "phase21_phase20_network_transport_consolidated_closeout_no_write"
        reason = if ($blockerCount -eq 0) {
            "Phase 21 Step 2 consolidated the Phase 20 no-write network transport evidence chain into a single closeout packet. It does not authorize approvals, implementation, network transport, sockets, bridge POST, response capture, mutations, LACRM calls, or live writes."
        } else {
            "Phase 21 Step 2 found blockers in the Phase 20 consolidated closeout packet. Resolve blockers before proceeding with additional closeout work."
        }
    }
    buckets = @($bucketRows)
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
        buckets = @($bucketRows).Count
        artifacts = @($artifacts).Count
        present_artifacts = @($presentArtifacts).Count
        missing_artifacts = @($missingArtifacts).Count
        source_audits = @($sourceAudits).Count
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this closeout packet as the second Phase 21 cleanup artifact.",
        "Use it to confirm that the Phase 20 chain is consolidated before building a final closeout summary or navigation page cleanup.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 21 Step 2.",
        "Do not call interface execution methods from Phase 21 Step 2.",
        "Do not record final approvals from Phase 21 Step 2.",
        "Do not start an implementation phase from Phase 21 Step 2.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase21_phase20_network_transport_consolidated_closeout_packet.json"
$bucketsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_consolidated_closeout_packet_buckets.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_consolidated_closeout_packet_artifacts.csv"
$sourceCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_consolidated_closeout_packet_source_audits.csv"
$checklistCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_consolidated_closeout_packet_checklist.csv"
$issuesCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_consolidated_closeout_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase21_phase20_network_transport_consolidated_closeout_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$bucketRows | Export-Csv -LiteralPath $bucketsCsvPath -NoTypeInformation -Encoding UTF8
$artifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$sourceAudits | Export-Csv -LiteralPath $sourceCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$bucketText = (@($bucketRows) | ForEach-Object { "- $($_.bucket): present=$($_.present_count); missing=$($_.missing_count); all_present=$($_.all_present)" }) -join "`n"
$artifactText = (@($artifacts) | ForEach-Object { "- $($_.step) / $($_.key): $($_.status) - $($_.json_path)" }) -join "`n"
$sourceText = (@($sourceAudits) | ForEach-Object { "- $($_.path): clean=$($_.clean) - $($_.evidence)" }) -join "`n"
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 21 Step 2 - Phase 20 Network Transport Consolidated Closeout Packet

Generated: $($report.generated_at)

Source evidence index:

``````
$evidenceIndexPath
``````

Source design closure packet:

``````
$designClosurePath
``````

## Safety

- Phase 20 network transport consolidated closeout packet only: true
- Consolidated closeout packet only: true
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

## Consolidated closeout packet

- Status: $packetStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Buckets: $(@($bucketRows).Count)
- Artifacts indexed: $(@($artifacts).Count)
- Present artifacts: $(@($presentArtifacts).Count)
- Missing artifacts: $(@($missingArtifacts).Count)
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

## Buckets

$bucketText

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
    Write-Host "PASS | phase20_network_transport_consolidated_closeout_packet=$OutputDir | status=$packetStatus | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
} else {
    Write-Host "CHECK | phase20_network_transport_consolidated_closeout_packet=$OutputDir | status=$packetStatus | blockers=$blockerCount | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
}

Write-Host ""
Write-Host "Consolidated closeout packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
