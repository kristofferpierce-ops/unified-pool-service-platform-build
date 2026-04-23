param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$ReviewBoardPacketDir = "",
    [string]$CloseoutPacketDir = "",
    [string]$EvidenceIndexDir = "",
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

if ([string]::IsNullOrWhiteSpace($ReviewBoardPacketDir)) {
    $ReviewBoardPacketDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_review_board_packet_*" -JsonName "phase21_phase20_network_transport_review_board_packet.json" -Required $true
}
if ([string]::IsNullOrWhiteSpace($CloseoutPacketDir)) {
    $CloseoutPacketDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_consolidated_closeout_packet_*" -JsonName "phase21_phase20_network_transport_consolidated_closeout_packet.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($EvidenceIndexDir)) {
    $EvidenceIndexDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_evidence_index_*" -JsonName "phase21_phase20_network_transport_evidence_index.json" -Required $false
}

$reviewBoardPacketPath = Join-Path $ReviewBoardPacketDir "phase21_phase20_network_transport_review_board_packet.json"
$closeoutPacketPath = if (![string]::IsNullOrWhiteSpace($CloseoutPacketDir)) { Join-Path $CloseoutPacketDir "phase21_phase20_network_transport_consolidated_closeout_packet.json" } else { "" }
$evidenceIndexPath = if (![string]::IsNullOrWhiteSpace($EvidenceIndexDir)) { Join-Path $EvidenceIndexDir "phase21_phase20_network_transport_evidence_index.json" } else { "" }

if (!(Test-Path -LiteralPath $reviewBoardPacketPath)) {
    throw "Review board packet JSON not found: $reviewBoardPacketPath"
}

$reviewBoard = Read-JsonFile $reviewBoardPacketPath
$closeoutPacket = if (![string]::IsNullOrWhiteSpace($closeoutPacketPath) -and (Test-Path -LiteralPath $closeoutPacketPath)) { Read-JsonFile $closeoutPacketPath } else { $null }
$evidenceIndex = if (![string]::IsNullOrWhiteSpace($evidenceIndexPath) -and (Test-Path -LiteralPath $evidenceIndexPath)) { Read-JsonFile $evidenceIndexPath } else { $null }

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList
$gaps = New-Object System.Collections.ArrayList

Add-ChecklistItem $checklist "artifact" "Review board packet exists" $true $reviewBoardPacketPath
Add-ChecklistItem $checklist "artifact" "Consolidated closeout packet exists" ($closeoutPacket -ne $null) $closeoutPacketPath "recommended"
Add-ChecklistItem $checklist "artifact" "Evidence index exists" ($evidenceIndex -ne $null) $evidenceIndexPath "recommended"

Add-ChecklistItem $checklist "review_board" "Review board packet is no-write only" ($reviewBoard.safety.phase20_network_transport_review_board_packet_only -eq $true) "phase20_network_transport_review_board_packet_only=$($reviewBoard.safety.phase20_network_transport_review_board_packet_only)"
Add-ChecklistItem $checklist "review_board" "Review board created no closure record" ($reviewBoard.safety.design_closure_record_created -eq $false) "design_closure_record_created=$($reviewBoard.safety.design_closure_record_created)"
Add-ChecklistItem $checklist "review_board" "Review board recorded no final approval" ($reviewBoard.safety.final_approval_recorded -eq $false) "final_approval_recorded=$($reviewBoard.safety.final_approval_recorded)"
Add-ChecklistItem $checklist "review_board" "Review board started no implementation phase" ($reviewBoard.safety.implementation_phase_started -eq $false) "implementation_phase_started=$($reviewBoard.safety.implementation_phase_started)"
Add-ChecklistItem $checklist "review_board" "Review board has no execution implementation" ($reviewBoard.safety.execution_implementation_created -eq $false) "execution_implementation_created=$($reviewBoard.safety.execution_implementation_created)"
Add-ChecklistItem $checklist "review_board" "Review board has no network transport" ($reviewBoard.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($reviewBoard.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "review_board" "Review board has no socket opened" ($reviewBoard.safety.network_socket_opened -eq $false) "network_socket_opened=$($reviewBoard.safety.network_socket_opened)"
Add-ChecklistItem $checklist "review_board" "Review board has no bridge POST" ($reviewBoard.safety.bridge_post_called -eq $false -and $reviewBoard.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($reviewBoard.safety.bridge_post_called); bridge_post_call_implemented=$($reviewBoard.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "review_board" "Review board has no platform DB mutation" ($reviewBoard.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($reviewBoard.safety.platform_db_mutation_performed)"
Add-ChecklistItem $checklist "review_board" "Review board has no bridge mutation" ($reviewBoard.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($reviewBoard.safety.bridge_mutation_performed)"
Add-ChecklistItem $checklist "review_board" "Review board has no LACRM call" ($reviewBoard.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($reviewBoard.safety.lacrm_call_performed)"
Add-ChecklistItem $checklist "review_board" "Review board has no blockers" ([int]$reviewBoard.review_board_packet.blocker_count -eq 0) "blocker_count=$($reviewBoard.review_board_packet.blocker_count)"

$sections = @($reviewBoard.sections)
$buckets = @($reviewBoard.buckets)
$artifacts = @($reviewBoard.artifacts)
$sourceAudits = @($reviewBoard.source_audits)

$missingArtifacts = @($artifacts | Where-Object { $_.present -ne $true })
$uncleanSourceAudits = @($sourceAudits | Where-Object { $_.clean -eq $false })
$incompleteBuckets = @($buckets | Where-Object { $_.all_present -ne $true })

foreach ($artifact in $missingArtifacts) {
    [void]$gaps.Add([ordered]@{
        gap_type = "missing_artifact"
        severity = if ($artifact.required -eq $true) { "blocker" } else { "review" }
        label = "$($artifact.step) / $($artifact.key)"
        evidence = $artifact.folder_filter
        suggested_action = "Regenerate or confirm whether this artifact is intentionally absent."
    })
}

foreach ($bucket in $incompleteBuckets) {
    [void]$gaps.Add([ordered]@{
        gap_type = "incomplete_bucket"
        severity = "review"
        label = $bucket.bucket
        evidence = "present=$($bucket.present_count); missing=$($bucket.missing_count)"
        suggested_action = "Review whether missing artifacts in this bucket matter for closeout."
    })
}

foreach ($audit in $uncleanSourceAudits) {
    [void]$gaps.Add([ordered]@{
        gap_type = "unclean_source_audit"
        severity = "blocker"
        label = $audit.path
        evidence = $audit.evidence
        suggested_action = "Inspect this source file before any further transport planning."
    })
}

$regenerationOrder = New-Object System.Collections.ArrayList
$missingArtifactsSorted = @($missingArtifacts | Sort-Object step, key)
$rank = 1
foreach ($artifact in $missingArtifactsSorted) {
    [void]$regenerationOrder.Add([ordered]@{
        rank = $rank
        step = $artifact.step
        key = $artifact.key
        required = $artifact.required
        folder_filter = $artifact.folder_filter
        rationale = if ($artifact.required -eq $true) { "Required artifact missing." } else { "Optional artifact missing; review whether regeneration is needed." }
    })
    $rank += 1
}

Add-ChecklistItem $checklist "gap_analysis" "Gap packet identified missing artifacts count" $true "missing_artifacts=$(@($missingArtifacts).Count)"
Add-ChecklistItem $checklist "gap_analysis" "Gap packet identified incomplete buckets count" $true "incomplete_buckets=$(@($incompleteBuckets).Count)"
Add-ChecklistItem $checklist "gap_analysis" "All source audits remain clean" ($uncleanSourceAudits.Count -eq 0) "unclean_source_audits=$($uncleanSourceAudits.Count)" "recommended"

$invocationStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

if ($invocationStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Dry-run invocation path status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status" "recommended"
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

foreach ($gap in @($gaps)) {
    if ($gap.severity -eq "blocker") {
        Add-Issue $issues "blocker" ("gap_" + ($gap.gap_type + "_" + $gap.label -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $gap.evidence "gap"
    } elseif ($gap.severity -eq "review") {
        Add-Issue $issues "review" ("gap_" + ($gap.gap_type + "_" + $gap.label -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $gap.evidence "gap"
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$packetStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "phase20_artifact_gap_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "phase20_artifact_gap_packet_review_required_no_write"
} else {
    "phase20_artifact_gap_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase21_phase20_network_transport_artifact_gap_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="review_board_packet"; json_path=$reviewBoardPacketPath; sha256=Get-FileSha256 $reviewBoardPacketPath },
    [ordered]@{ key="consolidated_closeout_packet"; json_path=$closeoutPacketPath; sha256=Get-FileSha256 $closeoutPacketPath },
    [ordered]@{ key="evidence_index"; json_path=$evidenceIndexPath; sha256=Get-FileSha256 $evidenceIndexPath }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 21 Step 4"
    purpose = "Phase 20 bridge routing network transport artifact gap packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        phase20_network_transport_artifact_gap_packet_only = $true
        artifact_gap_packet_only = $true
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
    artifact_gap_packet = [ordered]@{
        status = $packetStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        section_count = @($sections).Count
        bucket_count = @($buckets).Count
        artifact_count = @($artifacts).Count
        missing_artifact_count = @($missingArtifacts).Count
        incomplete_bucket_count = @($incompleteBuckets).Count
        source_audit_count = @($sourceAudits).Count
        unclean_source_audit_count = @($uncleanSourceAudits).Count
        gap_count = @($gaps).Count
        checklist_count = @($checklist).Count
        regeneration_order_count = @($regenerationOrder).Count
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
        packet_label = "phase21_phase20_network_transport_artifact_gap_no_write"
        reason = if ($blockerCount -eq 0) {
            "Phase 21 Step 4 created a no-write artifact gap packet for the Phase 20 network transport evidence chain. It does not authorize approvals, implementation, transport, sockets, bridge POST, response capture, mutations, LACRM calls, or live writes."
        } else {
            "Phase 21 Step 4 found blockers in the Phase 20 artifact gap packet. Resolve blockers before further closeout work."
        }
    }
    sections = @($sections)
    buckets = @($buckets)
    artifacts = @($artifacts)
    source_audits = @($sourceAudits)
    gaps = @($gaps)
    regeneration_order = @($regenerationOrder)
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
        sections = @($sections).Count
        buckets = @($buckets).Count
        artifacts = @($artifacts).Count
        missing_artifacts = @($missingArtifacts).Count
        incomplete_buckets = @($incompleteBuckets).Count
        source_audits = @($sourceAudits).Count
        unclean_source_audits = @($uncleanSourceAudits).Count
        gaps = @($gaps).Count
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this packet to see which optional Phase 20 artifacts are actually worth regenerating.",
        "Use the regeneration order only for missing artifacts that matter to the final closeout story.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 21 Step 4.",
        "Do not call interface execution methods from Phase 21 Step 4.",
        "Do not record final approvals from Phase 21 Step 4.",
        "Do not start an implementation phase from Phase 21 Step 4.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase21_phase20_network_transport_artifact_gap_packet.json"
$gapsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_artifact_gap_packet_gaps.csv"
$regenCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_artifact_gap_packet_regeneration_order.csv"
$sectionsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_artifact_gap_packet_sections.csv"
$bucketsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_artifact_gap_packet_buckets.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_artifact_gap_packet_artifacts.csv"
$sourceCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_artifact_gap_packet_source_audits.csv"
$checklistCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_artifact_gap_packet_checklist.csv"
$issuesCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_artifact_gap_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase21_phase20_network_transport_artifact_gap_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$gaps | Export-Csv -LiteralPath $gapsCsvPath -NoTypeInformation -Encoding UTF8
$regenerationOrder | Export-Csv -LiteralPath $regenCsvPath -NoTypeInformation -Encoding UTF8
$sections | Export-Csv -LiteralPath $sectionsCsvPath -NoTypeInformation -Encoding UTF8
$buckets | Export-Csv -LiteralPath $bucketsCsvPath -NoTypeInformation -Encoding UTF8
$artifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$sourceAudits | Export-Csv -LiteralPath $sourceCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$gapText = if (@($gaps).Count -gt 0) { (@($gaps) | ForEach-Object { "- $($_.gap_type): $($_.label) [$($_.severity)] - $($_.evidence)" }) -join "`n" } else { "- none" }
$regenText = if (@($regenerationOrder).Count -gt 0) { (@($regenerationOrder) | ForEach-Object { "- #$($_.rank) $($_.step) / $($_.key) - $($_.rationale)" }) -join "`n" } else { "- none" }
$artifactText = (@($artifacts) | ForEach-Object { "- $($_.step) / $($_.key): $($_.status) - $($_.json_path)" }) -join "`n"
$sourceText = (@($sourceAudits) | ForEach-Object { "- $($_.path): clean=$($_.clean) - $($_.evidence)" }) -join "`n"
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 21 Step 4 - Phase 20 Network Transport Artifact Gap Packet

Generated: $($report.generated_at)

Source review board packet:

``````
$reviewBoardPacketPath
``````

## Safety

- Phase 20 network transport artifact gap packet only: true
- Artifact gap packet only: true
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

## Artifact gap packet

- Status: $packetStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Gaps: $(@($gaps).Count)
- Missing artifacts: $(@($missingArtifacts).Count)
- Incomplete buckets: $(@($incompleteBuckets).Count)
- Unclean source audits: $($uncleanSourceAudits.Count)
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

## Gaps

$gapText

## Suggested regeneration order

$regenText

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
    Write-Host "PASS | phase20_network_transport_artifact_gap_packet=$OutputDir | status=$packetStatus | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
} else {
    Write-Host "CHECK | phase20_network_transport_artifact_gap_packet=$OutputDir | status=$packetStatus | blockers=$blockerCount | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
}

Write-Host ""
Write-Host "Artifact gap packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
