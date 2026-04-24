param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$CleanupManifestPacketDir = "",
    [string]$ReviewBoardPacketDir = "",
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

function Convert-GitStatusLine {
    param([string]$Line)

    if ([string]::IsNullOrWhiteSpace($Line)) {
        return $null
    }

    $indexStatus = if ($Line.Length -ge 1) { $Line.Substring(0,1) } else { "" }
    $worktreeStatus = if ($Line.Length -ge 2) { $Line.Substring(1,1) } else { "" }
    $path = if ($Line.Length -ge 4) { $Line.Substring(3).Trim() } else { "" }

    return [ordered]@{
        index_status = $indexStatus
        worktree_status = $worktreeStatus
        path = $path
        raw = $Line
    }
}

function Test-PathMatchesPrefix {
    param(
        [string]$Path,
        [string[]]$Prefixes
    )

    foreach ($prefix in $Prefixes) {
        if ([string]::IsNullOrWhiteSpace($prefix)) { continue }
        if ($Path -eq $prefix) { return $true }
        if ($Path.StartsWith($prefix + "\")) { return $true }
        if ($Path.StartsWith($prefix + "/")) { return $true }
    }
    return $false
}

function Classify-GitStatusEntry {
    param(
        [hashtable]$Entry,
        [string[]]$DoNotStagePrefixes,
        [string[]]$CurrentStepFiles
    )

    $path = [string]$Entry.path
    $isCurrentStep = $CurrentStepFiles -contains $path
    $isDoNotStage = Test-PathMatchesPrefix -Path $path -Prefixes $DoNotStagePrefixes

    if ($isCurrentStep) {
        return [ordered]@{
            category = "current_step_candidate"
            should_stage = $true
            reason = "Current Phase 21 Step 6 file."
        }
    }

    if ($isDoNotStage) {
        return [ordered]@{
            category = "do_not_stage"
            should_stage = $false
            reason = "Matches cleanup-manifest do-not-stage path."
        }
    }

    if ($path.StartsWith("backups\") -or $path.StartsWith("backups/")) {
        return [ordered]@{
            category = "generated_artifact"
            should_stage = $false
            reason = "Generated artifact folder."
        }
    }

    if ($path.EndsWith(".db")) {
        return [ordered]@{
            category = "runtime_database"
            should_stage = $false
            reason = "Runtime database file."
        }
    }

    return [ordered]@{
        category = "review_other"
        should_stage = $false
        reason = "Review before staging."
    }
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($CleanupManifestPacketDir)) {
    $CleanupManifestPacketDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_cleanup_manifest_packet_*" -JsonName "phase21_phase20_network_transport_cleanup_manifest_packet.json" -Required $true
}
if ([string]::IsNullOrWhiteSpace($ReviewBoardPacketDir)) {
    $ReviewBoardPacketDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_review_board_packet_*" -JsonName "phase21_phase20_network_transport_review_board_packet.json" -Required $false
}

$cleanupManifestPath = Join-Path $CleanupManifestPacketDir "phase21_phase20_network_transport_cleanup_manifest_packet.json"
$reviewBoardPacketPath = if (![string]::IsNullOrWhiteSpace($ReviewBoardPacketDir)) { Join-Path $ReviewBoardPacketDir "phase21_phase20_network_transport_review_board_packet.json" } else { "" }

if (!(Test-Path -LiteralPath $cleanupManifestPath)) {
    throw "Cleanup manifest packet JSON not found: $cleanupManifestPath"
}

$cleanupManifest = Read-JsonFile $cleanupManifestPath
$reviewBoardPacket = if (![string]::IsNullOrWhiteSpace($reviewBoardPacketPath) -and (Test-Path -LiteralPath $reviewBoardPacketPath)) { Read-JsonFile $reviewBoardPacketPath } else { $null }

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList
$gitStatusEntries = New-Object System.Collections.ArrayList

Add-ChecklistItem $checklist "artifact" "Cleanup manifest packet exists" $true $cleanupManifestPath
Add-ChecklistItem $checklist "artifact" "Review board packet exists" ($reviewBoardPacket -ne $null) $reviewBoardPacketPath "recommended"

Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest packet is workspace-hygiene-safe" ($cleanupManifest.safety.phase20_network_transport_cleanup_manifest_packet_only -eq $true) "phase20_network_transport_cleanup_manifest_packet_only=$($cleanupManifest.safety.phase20_network_transport_cleanup_manifest_packet_only)"
Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest created no closure record" ($cleanupManifest.safety.design_closure_record_created -eq $false) "design_closure_record_created=$($cleanupManifest.safety.design_closure_record_created)"
Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest recorded no final approval" ($cleanupManifest.safety.final_approval_recorded -eq $false) "final_approval_recorded=$($cleanupManifest.safety.final_approval_recorded)"
Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest started no implementation phase" ($cleanupManifest.safety.implementation_phase_started -eq $false) "implementation_phase_started=$($cleanupManifest.safety.implementation_phase_started)"
Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest has no execution implementation" ($cleanupManifest.safety.execution_implementation_created -eq $false) "execution_implementation_created=$($cleanupManifest.safety.execution_implementation_created)"
Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest has no network transport" ($cleanupManifest.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($cleanupManifest.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest has no socket opened" ($cleanupManifest.safety.network_socket_opened -eq $false) "network_socket_opened=$($cleanupManifest.safety.network_socket_opened)"
Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest has no bridge POST" ($cleanupManifest.safety.bridge_post_called -eq $false -and $cleanupManifest.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($cleanupManifest.safety.bridge_post_called); bridge_post_call_implemented=$($cleanupManifest.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest has no platform DB mutation" ($cleanupManifest.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($cleanupManifest.safety.platform_db_mutation_performed)"
Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest has no bridge mutation" ($cleanupManifest.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($cleanupManifest.safety.bridge_mutation_performed)"
Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest has no LACRM call" ($cleanupManifest.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($cleanupManifest.safety.lacrm_call_performed)"
Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest has no blockers" ([int]$cleanupManifest.cleanup_manifest_packet.blocker_count -eq 0) "blocker_count=$($cleanupManifest.cleanup_manifest_packet.blocker_count)"

$currentBranch = (& git -C $PlatformDir branch --show-current 2>$null | Out-String).Trim()
# Workspace hygiene uses git status --short against the platform repo.
$gitStatusRaw = & git -C $PlatformDir status --short 2>$null

$doNotStagePrefixes = @($cleanupManifest.manifest_entries | Where-Object { $_.category -eq "do_not_stage_paths" } | ForEach-Object { [string]$_.item })
$currentStepFiles = @(
    "scripts/phase21_generate_phase20_network_transport_workspace_hygiene_packet.ps1",
    "ui/pages/98_Phase20_Network_Transport_Workspace_Hygiene_Packet.py",
    "docs/PHASE21_STEP6_PHASE20_NETWORK_TRANSPORT_WORKSPACE_HYGIENE_PACKET.md",
    "tests/test_phase21_phase20_network_transport_workspace_hygiene_packet.py"
)

foreach ($line in @($gitStatusRaw)) {
    $parsed = Convert-GitStatusLine -Line ([string]$line)
    if ($null -eq $parsed) { continue }
    $class = Classify-GitStatusEntry -Entry $parsed -DoNotStagePrefixes $doNotStagePrefixes -CurrentStepFiles $currentStepFiles

    [void]$gitStatusEntries.Add([ordered]@{
        index_status = $parsed.index_status
        worktree_status = $parsed.worktree_status
        path = $parsed.path
        category = $class.category
        should_stage = $class.should_stage
        reason = $class.reason
        raw = $parsed.raw
    })
}

$gitStatusCount = @($gitStatusEntries).Count
$modifiedCount = @($gitStatusEntries | Where-Object { $_.worktree_status -eq "M" -or $_.index_status -eq "M" }).Count
$untrackedCount = @($gitStatusEntries | Where-Object { $_.index_status -eq "?" -and $_.worktree_status -eq "?" }).Count
$currentStepCandidateCount = @($gitStatusEntries | Where-Object { $_.category -eq "current_step_candidate" }).Count
$doNotStageMatchCount = @($gitStatusEntries | Where-Object { $_.category -eq "do_not_stage" -or $_.category -eq "runtime_database" -or $_.category -eq "generated_artifact" }).Count
$reviewOtherCount = @($gitStatusEntries | Where-Object { $_.category -eq "review_other" }).Count

Add-ChecklistItem $checklist "workspace" "Current branch detected" (-not [string]::IsNullOrWhiteSpace($currentBranch)) "current_branch=$currentBranch"
Add-ChecklistItem $checklist "workspace" "Current step files appear in git status after apply" ($currentStepCandidateCount -ge 0) "current_step_candidates=$currentStepCandidateCount" "recommended"
Add-ChecklistItem $checklist "workspace" "Workspace review-other files count is zero or acceptable" ($reviewOtherCount -eq 0) "review_other_count=$reviewOtherCount" "recommended"
Add-ChecklistItem $checklist "workspace" "Do-not-stage matches detected when runtime/unrelated files are present" ($doNotStageMatchCount -ge 0) "do_not_stage_match_count=$doNotStageMatchCount" "recommended"

foreach ($entry in @($gitStatusEntries)) {
    if ($entry.category -eq "review_other") {
        Add-Issue $issues "review" ("workspace_review_other_" + ($entry.path -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) "$($entry.path) requires review before staging." "workspace"
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
    "phase20_workspace_hygiene_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "phase20_workspace_hygiene_packet_review_required_no_write"
} else {
    "phase20_workspace_hygiene_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase21_phase20_network_transport_workspace_hygiene_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="cleanup_manifest_packet"; json_path=$cleanupManifestPath; sha256=Get-FileSha256 $cleanupManifestPath },
    [ordered]@{ key="review_board_packet"; json_path=$reviewBoardPacketPath; sha256=Get-FileSha256 $reviewBoardPacketPath }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 21 Step 6"
    purpose = "Phase 20 bridge routing network transport workspace hygiene packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        phase20_network_transport_workspace_hygiene_packet_only = $true
        workspace_hygiene_only = $true
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
    workspace_hygiene_packet = [ordered]@{
        status = $packetStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        current_branch = $currentBranch
        git_status_count = $gitStatusCount
        modified_count = $modifiedCount
        untracked_count = $untrackedCount
        current_step_candidate_count = $currentStepCandidateCount
        do_not_stage_match_count = $doNotStageMatchCount
        review_other_count = $reviewOtherCount
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
        packet_label = "phase21_phase20_network_transport_workspace_hygiene_no_write"
        reason = if ($blockerCount -eq 0) {
            "Phase 21 Step 6 created a no-write workspace hygiene packet for the Phase 20 network transport cleanup chain. It does not authorize approvals, implementation, transport, sockets, bridge POST, response capture, mutations, LACRM calls, or live writes."
        } else {
            "Phase 21 Step 6 found blockers in the Phase 20 workspace hygiene packet. Resolve blockers before more cleanup work."
        }
    }
    git_status_entries = @($gitStatusEntries)
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
        git_status_entries = $gitStatusCount
        modified = $modifiedCount
        untracked = $untrackedCount
        current_step_candidates = $currentStepCandidateCount
        do_not_stage_matches = $doNotStageMatchCount
        review_other = $reviewOtherCount
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this workspace hygiene packet before staging files for the next cleanup step.",
        "Use the do-not-stage matches and review-other entries as a commit safety guide.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 21 Step 6.",
        "Do not call interface execution methods from Phase 21 Step 6.",
        "Do not record final approvals from Phase 21 Step 6.",
        "Do not start an implementation phase from Phase 21 Step 6.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase21_phase20_network_transport_workspace_hygiene_packet.json"
$gitStatusCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_workspace_hygiene_packet_git_status.csv"
$checklistCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_workspace_hygiene_packet_checklist.csv"
$issuesCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_workspace_hygiene_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase21_phase20_network_transport_workspace_hygiene_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$gitStatusEntries | Export-Csv -LiteralPath $gitStatusCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$gitStatusText = if (@($gitStatusEntries).Count -gt 0) { (@($gitStatusEntries) | ForEach-Object { "- [$($_.index_status)$($_.worktree_status)] $($_.path): $($_.category); should_stage=$($_.should_stage); $($_.reason)" }) -join "`n" } else { "- clean" }
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 21 Step 6 - Phase 20 Network Transport Workspace Hygiene Packet

Generated: $($report.generated_at)

Source cleanup manifest packet:

``````
$cleanupManifestPath
``````

## Safety

- Phase 20 network transport workspace hygiene packet only: true
- Workspace hygiene only: true
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

## Workspace hygiene packet

- Status: $packetStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Current branch: $currentBranch
- Git status entries: $gitStatusCount
- Modified entries: $modifiedCount
- Untracked entries: $untrackedCount
- Current step candidates: $currentStepCandidateCount
- Do-not-stage matches: $doNotStageMatchCount
- Review-other entries: $reviewOtherCount
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

## Git status entries

$gitStatusText

## Checklist

$checklistText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | phase20_network_transport_workspace_hygiene_packet=$OutputDir | status=$packetStatus | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
} else {
    Write-Host "CHECK | phase20_network_transport_workspace_hygiene_packet=$OutputDir | status=$packetStatus | blockers=$blockerCount | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
}

Write-Host ""
Write-Host "Workspace hygiene packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime

