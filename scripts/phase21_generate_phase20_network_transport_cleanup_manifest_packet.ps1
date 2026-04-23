param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$ReviewBoardPacketDir = "",
    [string]$ArtifactGapPacketDir = "",
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

function Get-ArtifactFamilyInfo {
    param(
        [string]$FolderFilter,
        [string]$JsonName
    )

    $dirs = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter $FolderFilter -ErrorAction SilentlyContinue |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName $JsonName) } |
        Sort-Object LastWriteTime -Descending

    $latest = $dirs | Select-Object -First 1
    $folderPath = if ($latest) { $latest.FullName } else { "" }
    $jsonPath = if ($latest) { Join-Path $latest.FullName $JsonName } else { "" }

    return [ordered]@{
        folder_filter = $FolderFilter
        json_name = $JsonName
        folder_count = @($dirs).Count
        latest_folder = $folderPath
        latest_json_path = $jsonPath
        latest_json_sha256 = if ($jsonPath) { Get-FileSha256 $jsonPath } else { "" }
    }
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
if ([string]::IsNullOrWhiteSpace($ArtifactGapPacketDir)) {
    $ArtifactGapPacketDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_artifact_gap_packet_*" -JsonName "phase21_phase20_network_transport_artifact_gap_packet.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($DesignClosurePacketDir)) {
    $DesignClosurePacketDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_design_closure_packet_*" -JsonName "phase20_bridge_routing_network_transport_design_closure_packet.json" -Required $false
}

$reviewBoardPacketPath = Join-Path $ReviewBoardPacketDir "phase21_phase20_network_transport_review_board_packet.json"
$artifactGapPacketPath = if (![string]::IsNullOrWhiteSpace($ArtifactGapPacketDir)) { Join-Path $ArtifactGapPacketDir "phase21_phase20_network_transport_artifact_gap_packet.json" } else { "" }
$designClosurePath = if (![string]::IsNullOrWhiteSpace($DesignClosurePacketDir)) { Join-Path $DesignClosurePacketDir "phase20_bridge_routing_network_transport_design_closure_packet.json" } else { "" }

if (!(Test-Path -LiteralPath $reviewBoardPacketPath)) {
    throw "Review board packet JSON not found: $reviewBoardPacketPath"
}

$reviewBoardPacket = Read-JsonFile $reviewBoardPacketPath
$artifactGapPacket = if (![string]::IsNullOrWhiteSpace($artifactGapPacketPath) -and (Test-Path -LiteralPath $artifactGapPacketPath)) { Read-JsonFile $artifactGapPacketPath } else { $null }
$designClosure = if (![string]::IsNullOrWhiteSpace($designClosurePath) -and (Test-Path -LiteralPath $designClosurePath)) { Read-JsonFile $designClosurePath } else { $null }

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList
$manifestSections = New-Object System.Collections.ArrayList
$manifestEntries = New-Object System.Collections.ArrayList
$artifactFamilies = New-Object System.Collections.ArrayList

Add-ChecklistItem $checklist "artifact" "Review board packet exists" $true $reviewBoardPacketPath
Add-ChecklistItem $checklist "artifact" "Artifact gap packet exists" ($artifactGapPacket -ne $null) $artifactGapPacketPath "recommended"
Add-ChecklistItem $checklist "artifact" "Design closure packet exists" ($designClosure -ne $null) $designClosurePath "recommended"

Add-ChecklistItem $checklist "review_board" "Review board packet is cleanup-manifest-safe" ($reviewBoardPacket.safety.phase20_network_transport_review_board_packet_only -eq $true) "phase20_network_transport_review_board_packet_only=$($reviewBoardPacket.safety.phase20_network_transport_review_board_packet_only)"
Add-ChecklistItem $checklist "review_board" "Review board packet created no closure record" ($reviewBoardPacket.safety.design_closure_record_created -eq $false) "design_closure_record_created=$($reviewBoardPacket.safety.design_closure_record_created)"
Add-ChecklistItem $checklist "review_board" "Review board packet recorded no final approval" ($reviewBoardPacket.safety.final_approval_recorded -eq $false) "final_approval_recorded=$($reviewBoardPacket.safety.final_approval_recorded)"
Add-ChecklistItem $checklist "review_board" "Review board packet started no implementation phase" ($reviewBoardPacket.safety.implementation_phase_started -eq $false) "implementation_phase_started=$($reviewBoardPacket.safety.implementation_phase_started)"
Add-ChecklistItem $checklist "review_board" "Review board packet has no execution implementation" ($reviewBoardPacket.safety.execution_implementation_created -eq $false) "execution_implementation_created=$($reviewBoardPacket.safety.execution_implementation_created)"
Add-ChecklistItem $checklist "review_board" "Review board packet has no bridge POST" ($reviewBoardPacket.safety.bridge_post_called -eq $false -and $reviewBoardPacket.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($reviewBoardPacket.safety.bridge_post_called); bridge_post_call_implemented=$($reviewBoardPacket.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "review_board" "Review board packet has no network transport" ($reviewBoardPacket.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($reviewBoardPacket.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "review_board" "Review board packet has no socket opened" ($reviewBoardPacket.safety.network_socket_opened -eq $false) "network_socket_opened=$($reviewBoardPacket.safety.network_socket_opened)"
Add-ChecklistItem $checklist "review_board" "Review board packet has no platform DB mutation" ($reviewBoardPacket.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($reviewBoardPacket.safety.platform_db_mutation_performed)"
Add-ChecklistItem $checklist "review_board" "Review board packet has no bridge mutation" ($reviewBoardPacket.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($reviewBoardPacket.safety.bridge_mutation_performed)"
Add-ChecklistItem $checklist "review_board" "Review board packet has no LACRM call" ($reviewBoardPacket.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($reviewBoardPacket.safety.lacrm_call_performed)"
Add-ChecklistItem $checklist "review_board" "Review board packet has no blockers" ([int]$reviewBoardPacket.review_board_packet.blocker_count -eq 0) "blocker_count=$($reviewBoardPacket.review_board_packet.blocker_count)"

if ($artifactGapPacket -ne $null) {
    Add-ChecklistItem $checklist "artifact_gap" "Artifact gap packet is no-write only" ($artifactGapPacket.safety.phase20_network_transport_artifact_gap_packet_only -eq $true) "phase20_network_transport_artifact_gap_packet_only=$($artifactGapPacket.safety.phase20_network_transport_artifact_gap_packet_only)" "recommended"
}
if ($designClosure -ne $null) {
    Add-ChecklistItem $checklist "design_closure" "Design closure packet is no-write only" ($designClosure.safety.design_closure_packet_only -eq $true) "design_closure_packet_only=$($designClosure.safety.design_closure_packet_only)" "recommended"
    Add-ChecklistItem $checklist "design_closure" "Design closure packet started no implementation phase" ($designClosure.safety.implementation_phase_started -eq $false) "implementation_phase_started=$($designClosure.safety.implementation_phase_started)" "recommended"
}

$artifacts = @($reviewBoardPacket.artifacts)
$sourceAudits = @($reviewBoardPacket.source_audits)
$buckets = @($reviewBoardPacket.buckets)
$sections = @($reviewBoardPacket.sections)

$presentArtifacts = @($artifacts | Where-Object { $_.present -eq $true }).Count
$missingArtifacts = @($artifacts | Where-Object { $_.present -ne $true }).Count
$uncleanSourceAudits = @($sourceAudits | Where-Object { $_.clean -eq $false }).Count
$completeBuckets = @($buckets | Where-Object { $_.all_present -eq $true }).Count

[void]$manifestSections.Add([ordered]@{
    section = "Retain latest packets"
    status = "review"
    summary = "Keep the latest review packets and supporting no-write closeout artifacts."
})
[void]$manifestSections.Add([ordered]@{
    section = "Older generated folder cleanup"
    status = if ($missingArtifacts -eq 0) { "review" } else { "partial" }
    summary = "Older generated packet folders can be manually archived after review; no deletion is performed here."
})
[void]$manifestSections.Add([ordered]@{
    section = "Do-not-stage runtime paths"
    status = "required"
    summary = "Runtime databases, backups, env files, bridge folders, and unrelated files remain excluded from commits."
})
[void]$manifestSections.Add([ordered]@{
    section = "Source audit cleanliness"
    status = if ($uncleanSourceAudits -eq 0) { "clean" } else { "check" }
    summary = "Carry forward the source-audit cleanliness from the review board packet."
})
[void]$manifestSections.Add([ordered]@{
    section = "Runtime guard state"
    status = "review"
    summary = "Runtime endpoints remain checked by GET-only calls."
})

$manifestItemSpecs = @(
    [ordered]@{ category="retain_latest_packets"; action="keep"; item="Latest Phase 20 design closure packet"; evidence=$designClosurePath; required="yes" },
    [ordered]@{ category="retain_latest_packets"; action="keep"; item="Latest Phase 21 evidence index"; evidence=$(if ($reviewBoardPacket.source_artifacts[1].json_path) { $reviewBoardPacket.source_artifacts[1].json_path } else { "" }); required="recommended" },
    [ordered]@{ category="retain_latest_packets"; action="keep"; item="Latest Phase 21 consolidated closeout packet"; evidence=$reviewBoardPacket.source_artifacts[0].json_path; required="yes" },
    [ordered]@{ category="retain_latest_packets"; action="keep"; item="Latest Phase 21 review board packet"; evidence=$reviewBoardPacketPath; required="yes" },
    [ordered]@{ category="retain_latest_packets"; action="keep"; item="Latest Phase 21 artifact gap packet"; evidence=$artifactGapPacketPath; required="recommended" },

    [ordered]@{ category="do_not_stage_paths"; action="exclude"; item="data/unified_pool_service_platform.db"; evidence="runtime sqlite database"; required="yes" },
    [ordered]@{ category="do_not_stage_paths"; action="exclude"; item=".env"; evidence="local environment file"; required="yes" },
    [ordered]@{ category="do_not_stage_paths"; action="exclude"; item=".venv"; evidence="local virtual environment"; required="yes" },
    [ordered]@{ category="do_not_stage_paths"; action="exclude"; item="backups"; evidence="generated evidence and backup folders"; required="yes" },
    [ordered]@{ category="do_not_stage_paths"; action="exclude"; item="front_desk_bridge"; evidence="bridge runtime workspace"; required="yes" },
    [ordered]@{ category="do_not_stage_paths"; action="exclude"; item="front_desk_bridge_repo"; evidence="bridge repo copy when present"; required="recommended" },
    [ordered]@{ category="do_not_stage_paths"; action="exclude"; item="app/services/tools.py"; evidence="unrelated local modifications possible"; required="recommended" },
    [ordered]@{ category="do_not_stage_paths"; action="exclude"; item="app/services/replaster_quote.py"; evidence="unrelated feature files"; required="recommended" },
    [ordered]@{ category="do_not_stage_paths"; action="exclude"; item="docs/26_REPLASTER_QUOTE_TOOL_PLAN.md"; evidence="unrelated feature files"; required="recommended" },
    [ordered]@{ category="do_not_stage_paths"; action="exclude"; item="tests/test_replaster_quote.py"; evidence="unrelated feature files"; required="recommended" },
    [ordered]@{ category="do_not_stage_paths"; action="exclude"; item="ui/pages/13_Replaster_Quote.py"; evidence="unrelated feature files"; required="recommended" }
)

foreach ($spec in $manifestItemSpecs) {
    [void]$manifestEntries.Add([ordered]@{
        category = $spec.category
        action = $spec.action
        item = $spec.item
        evidence = $spec.evidence
        required = $spec.required
    })
}

$familySpecs = @(
    [ordered]@{ filter="phase20_bridge_routing_network_transport_design_closure_packet_*"; json="phase20_bridge_routing_network_transport_design_closure_packet.json" },
    [ordered]@{ filter="phase21_phase20_network_transport_evidence_index_*"; json="phase21_phase20_network_transport_evidence_index.json" },
    [ordered]@{ filter="phase21_phase20_network_transport_consolidated_closeout_packet_*"; json="phase21_phase20_network_transport_consolidated_closeout_packet.json" },
    [ordered]@{ filter="phase21_phase20_network_transport_review_board_packet_*"; json="phase21_phase20_network_transport_review_board_packet.json" },
    [ordered]@{ filter="phase21_phase20_network_transport_artifact_gap_packet_*"; json="phase21_phase20_network_transport_artifact_gap_packet.json" }
)

foreach ($spec in $familySpecs) {
    $info = Get-ArtifactFamilyInfo -FolderFilter $spec.filter -JsonName $spec.json
    [void]$artifactFamilies.Add($info)
    $olderCount = [Math]::Max([int]$info.folder_count - 1, 0)
    [void]$manifestEntries.Add([ordered]@{
        category = "older_generated_folder_cleanup"
        action = "review_archive"
        item = $spec.filter
        evidence = "older_generated_folders=$olderCount; latest=$($info.latest_folder)"
        required = "recommended"
    })
}

Add-ChecklistItem $checklist "cleanup_manifest" "At least one manifest section exists" (@($manifestSections).Count -gt 0) "manifest_sections=$(@($manifestSections).Count)"
Add-ChecklistItem $checklist "cleanup_manifest" "At least one manifest entry exists" (@($manifestEntries).Count -gt 0) "manifest_entries=$(@($manifestEntries).Count)"
Add-ChecklistItem $checklist "cleanup_manifest" "All source audits remain clean" ($uncleanSourceAudits -eq 0) "unclean_source_audits=$uncleanSourceAudits" "recommended"
Add-ChecklistItem $checklist "cleanup_manifest" "At least one artifact exists in each bucket" (@($buckets | Where-Object { $_.present_count -gt 0 }).Count -eq @($buckets).Count) ("bucket_presence=" + ((@($buckets) | ForEach-Object { "$($_.bucket):$($_.present_count)" }) -join "; ")) "recommended"

foreach ($family in @($artifactFamilies)) {
    if ([int]$family.folder_count -eq 0) {
        Add-Issue $issues "review" ("artifact_family_missing_" + ($family.folder_filter -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) "No packet folders found for $($family.folder_filter)" "artifact_family"
    }
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
    "phase20_cleanup_manifest_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "phase20_cleanup_manifest_packet_review_required_no_write"
} else {
    "phase20_cleanup_manifest_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase21_phase20_network_transport_cleanup_manifest_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="review_board_packet"; json_path=$reviewBoardPacketPath; sha256=Get-FileSha256 $reviewBoardPacketPath },
    [ordered]@{ key="artifact_gap_packet"; json_path=$artifactGapPacketPath; sha256=Get-FileSha256 $artifactGapPacketPath },
    [ordered]@{ key="design_closure_packet"; json_path=$designClosurePath; sha256=Get-FileSha256 $designClosurePath }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 21 Step 5"
    purpose = "Phase 20 bridge routing network transport cleanup manifest packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        phase20_network_transport_cleanup_manifest_packet_only = $true
        cleanup_manifest_only = $true
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
    cleanup_manifest_packet = [ordered]@{
        status = $packetStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        section_count = @($manifestSections).Count
        manifest_entry_count = @($manifestEntries).Count
        artifact_family_count = @($artifactFamilies).Count
        artifact_count = @($artifacts).Count
        present_artifact_count = $presentArtifacts
        missing_artifact_count = $missingArtifacts
        source_audit_count = @($sourceAudits).Count
        unclean_source_audit_count = $uncleanSourceAudits
        checklist_count = @($checklist).Count
        stage_guard_count = @($manifestEntries | Where-Object { $_.category -eq "do_not_stage_paths" }).Count
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
        packet_label = "phase21_phase20_network_transport_cleanup_manifest_no_write"
        reason = if ($blockerCount -eq 0) {
            "Phase 21 Step 5 created a no-write cleanup manifest for the Phase 20 network transport evidence chain. It does not authorize approvals, implementation, transport, sockets, bridge POST, response capture, mutations, LACRM calls, or live writes."
        } else {
            "Phase 21 Step 5 found blockers in the Phase 20 cleanup manifest packet. Resolve blockers before proceeding with more cleanup work."
        }
    }
    manifest_sections = @($manifestSections)
    manifest_entries = @($manifestEntries)
    artifact_families = @($artifactFamilies)
    artifacts = @($artifacts)
    source_audits = @($sourceAudits)
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
        sections = @($manifestSections).Count
        manifest_entries = @($manifestEntries).Count
        artifact_families = @($artifactFamilies).Count
        artifacts = @($artifacts).Count
        present_artifacts = $presentArtifacts
        missing_artifacts = $missingArtifacts
        source_audits = @($sourceAudits).Count
        unclean_source_audits = $uncleanSourceAudits
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this cleanup manifest before any further Phase 21 closeout cleanup or manual backup archiving.",
        "Use the do-not-stage entries as the commit guard for future cleanup steps.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 21 Step 5.",
        "Do not call interface execution methods from Phase 21 Step 5.",
        "Do not record final approvals from Phase 21 Step 5.",
        "Do not start an implementation phase from Phase 21 Step 5.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_manifest_packet.json"
$sectionsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_manifest_packet_sections.csv"
$entriesCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_manifest_packet_entries.csv"
$familiesCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_manifest_packet_artifact_families.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_manifest_packet_artifacts.csv"
$sourceCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_manifest_packet_source_audits.csv"
$checklistCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_manifest_packet_checklist.csv"
$issuesCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_manifest_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_manifest_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$manifestSections | Export-Csv -LiteralPath $sectionsCsvPath -NoTypeInformation -Encoding UTF8
$manifestEntries | Export-Csv -LiteralPath $entriesCsvPath -NoTypeInformation -Encoding UTF8
$artifactFamilies | Export-Csv -LiteralPath $familiesCsvPath -NoTypeInformation -Encoding UTF8
$artifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$sourceAudits | Export-Csv -LiteralPath $sourceCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$sectionText = (@($manifestSections) | ForEach-Object { "- $($_.section): $($_.status); $($_.summary)" }) -join "`n"
$entryText = (@($manifestEntries) | ForEach-Object { "- [$($_.category)] $($_.action) $($_.item): $($_.evidence)" }) -join "`n"
$familyText = (@($artifactFamilies) | ForEach-Object { "- $($_.folder_filter): folder_count=$($_.folder_count); latest=$($_.latest_folder)" }) -join "`n"
$artifactText = (@($artifacts) | ForEach-Object { "- $($_.step) / $($_.key): $($_.status) - $($_.json_path)" }) -join "`n"
$sourceText = (@($sourceAudits) | ForEach-Object { "- $($_.path): clean=$($_.clean) - $($_.evidence)" }) -join "`n"
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 21 Step 5 - Phase 20 Network Transport Cleanup Manifest Packet

Generated: $($report.generated_at)

Source review board packet:

``````
$reviewBoardPacketPath
``````

## Safety

- Phase 20 network transport cleanup manifest packet only: true
- Cleanup manifest only: true
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

## Cleanup manifest packet

- Status: $packetStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Sections: $(@($manifestSections).Count)
- Manifest entries: $(@($manifestEntries).Count)
- Artifact families: $(@($artifactFamilies).Count)
- Artifacts: $(@($artifacts).Count)
- Present artifacts: $presentArtifacts
- Missing artifacts: $missingArtifacts
- Source audits: $(@($sourceAudits).Count)
- Unclean source audits: $uncleanSourceAudits
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

## Manifest sections

$sectionText

## Manifest entries

$entryText

## Artifact families

$familyText

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
    Write-Host "PASS | phase20_network_transport_cleanup_manifest_packet=$OutputDir | status=$packetStatus | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
} else {
    Write-Host "CHECK | phase20_network_transport_cleanup_manifest_packet=$OutputDir | status=$packetStatus | blockers=$blockerCount | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
}

Write-Host ""
Write-Host "Cleanup manifest packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime

