param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$CommitGuardPacketDir = "",
    [string]$CleanupManifestPacketDir = "",
    [string]$WorkspaceHygienePacketDir = "",
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

if ([string]::IsNullOrWhiteSpace($CommitGuardPacketDir)) {
    $CommitGuardPacketDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_commit_guard_packet_*" -JsonName "phase21_phase20_network_transport_commit_guard_packet.json" -Required $true
}
if ([string]::IsNullOrWhiteSpace($CleanupManifestPacketDir)) {
    $CleanupManifestPacketDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_cleanup_manifest_packet_*" -JsonName "phase21_phase20_network_transport_cleanup_manifest_packet.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($WorkspaceHygienePacketDir)) {
    $WorkspaceHygienePacketDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_workspace_hygiene_packet_*" -JsonName "phase21_phase20_network_transport_workspace_hygiene_packet.json" -Required $false
}

$commitGuardPacketPath = Join-Path $CommitGuardPacketDir "phase21_phase20_network_transport_commit_guard_packet.json"
$cleanupManifestPath = if (![string]::IsNullOrWhiteSpace($CleanupManifestPacketDir)) { Join-Path $CleanupManifestPacketDir "phase21_phase20_network_transport_cleanup_manifest_packet.json" } else { "" }
$workspaceHygienePath = if (![string]::IsNullOrWhiteSpace($WorkspaceHygienePacketDir)) { Join-Path $WorkspaceHygienePacketDir "phase21_phase20_network_transport_workspace_hygiene_packet.json" } else { "" }

if (!(Test-Path -LiteralPath $commitGuardPacketPath)) {
    throw "Commit guard packet JSON not found: $commitGuardPacketPath"
}

$commitGuardPacket = Read-JsonFile $commitGuardPacketPath
$cleanupManifest = if (![string]::IsNullOrWhiteSpace($cleanupManifestPath) -and (Test-Path -LiteralPath $cleanupManifestPath)) { Read-JsonFile $cleanupManifestPath } else { $null }
$workspaceHygiene = if (![string]::IsNullOrWhiteSpace($workspaceHygienePath) -and (Test-Path -LiteralPath $workspaceHygienePath)) { Read-JsonFile $workspaceHygienePath } else { $null }

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList
$handoffSections = New-Object System.Collections.ArrayList
$handoffEntries = New-Object System.Collections.ArrayList
$sourceArtifacts = New-Object System.Collections.ArrayList

Add-ChecklistItem $checklist "artifact" "Commit guard packet exists" $true $commitGuardPacketPath
Add-ChecklistItem $checklist "artifact" "Cleanup manifest packet exists" ($cleanupManifest -ne $null) $cleanupManifestPath "recommended"
Add-ChecklistItem $checklist "artifact" "Workspace hygiene packet exists" ($workspaceHygiene -ne $null) $workspaceHygienePath "recommended"

Add-ChecklistItem $checklist "commit_guard" "Commit guard packet is handoff-safe" ($commitGuardPacket.safety.phase20_network_transport_commit_guard_packet_only -eq $true) "phase20_network_transport_commit_guard_packet_only=$($commitGuardPacket.safety.phase20_network_transport_commit_guard_packet_only)"
Add-ChecklistItem $checklist "commit_guard" "Commit guard created no closure record" ($commitGuardPacket.safety.design_closure_record_created -eq $false) "design_closure_record_created=$($commitGuardPacket.safety.design_closure_record_created)"
Add-ChecklistItem $checklist "commit_guard" "Commit guard recorded no final approval" ($commitGuardPacket.safety.final_approval_recorded -eq $false) "final_approval_recorded=$($commitGuardPacket.safety.final_approval_recorded)"
Add-ChecklistItem $checklist "commit_guard" "Commit guard started no implementation phase" ($commitGuardPacket.safety.implementation_phase_started -eq $false) "implementation_phase_started=$($commitGuardPacket.safety.implementation_phase_started)"
Add-ChecklistItem $checklist "commit_guard" "Commit guard has no execution implementation" ($commitGuardPacket.safety.execution_implementation_created -eq $false) "execution_implementation_created=$($commitGuardPacket.safety.execution_implementation_created)"
Add-ChecklistItem $checklist "commit_guard" "Commit guard has no network transport" ($commitGuardPacket.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($commitGuardPacket.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "commit_guard" "Commit guard has no socket opened" ($commitGuardPacket.safety.network_socket_opened -eq $false) "network_socket_opened=$($commitGuardPacket.safety.network_socket_opened)"
Add-ChecklistItem $checklist "commit_guard" "Commit guard has no bridge POST" ($commitGuardPacket.safety.bridge_post_called -eq $false -and $commitGuardPacket.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($commitGuardPacket.safety.bridge_post_called); bridge_post_call_implemented=$($commitGuardPacket.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "commit_guard" "Commit guard has no platform DB mutation" ($commitGuardPacket.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($commitGuardPacket.safety.platform_db_mutation_performed)"
Add-ChecklistItem $checklist "commit_guard" "Commit guard has no bridge mutation" ($commitGuardPacket.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($commitGuardPacket.safety.bridge_mutation_performed)"
Add-ChecklistItem $checklist "commit_guard" "Commit guard has no LACRM call" ($commitGuardPacket.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($commitGuardPacket.safety.lacrm_call_performed)"
Add-ChecklistItem $checklist "commit_guard" "Commit guard has no blockers" ([int]$commitGuardPacket.commit_guard_packet.blocker_count -eq 0) "blocker_count=$($commitGuardPacket.commit_guard_packet.blocker_count)"

if ($cleanupManifest -ne $null) {
    Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest packet is no-write only" ($cleanupManifest.safety.phase20_network_transport_cleanup_manifest_packet_only -eq $true) "phase20_network_transport_cleanup_manifest_packet_only=$($cleanupManifest.safety.phase20_network_transport_cleanup_manifest_packet_only)" "recommended"
}
if ($workspaceHygiene -ne $null) {
    Add-ChecklistItem $checklist "workspace_hygiene" "Workspace hygiene packet is no-write only" ($workspaceHygiene.safety.phase20_network_transport_workspace_hygiene_packet_only -eq $true) "phase20_network_transport_workspace_hygiene_packet_only=$($workspaceHygiene.safety.phase20_network_transport_workspace_hygiene_packet_only)" "recommended"
}

$entries = @($commitGuardPacket.commit_guard_entries)
$gitStatusEntries = @($commitGuardPacket.git_status_entries)
$stagedEntries = @($commitGuardPacket.staged_entries)
$commitCommands = @($commitGuardPacket.commit_commands)
$currentBranch = [string]$commitGuardPacket.commit_guard_packet.current_branch

$stageNowEntries = @($entries | Where-Object { $_.category -eq "stage_now" })
$doNotStageEntries = @($entries | Where-Object { $_.category -eq "do_not_stage" })
$reviewBeforeStageEntries = @($entries | Where-Object { $_.category -eq "review_before_stage" })

$gitStatusCount = @($gitStatusEntries).Count
$stagedCount = @($stagedEntries).Count
$stagedForbiddenCount = @($stagedEntries | Where-Object { $_.category -eq "do_not_stage" -or $_.category -eq "runtime_database" -or $_.category -eq "generated_artifact" }).Count
$stagedReviewOtherCount = @($stagedEntries | Where-Object { $_.category -eq "review_other" }).Count
$reviewOtherCount = @($gitStatusEntries | Where-Object { $_.category -eq "review_other" }).Count

$branchSectionStatus = "review"
if ([string]::IsNullOrWhiteSpace($currentBranch)) { $branchSectionStatus = "check" }

$stageSectionStatus = "review"
if ($stagedForbiddenCount -gt 0) { $stageSectionStatus = "check" }

$reviewSectionStatus = "review"
if ($stagedReviewOtherCount -eq 0 -and $reviewOtherCount -eq 0) { $reviewSectionStatus = "clean" }

[void]$handoffSections.Add([ordered]@{
    section = "Current branch handoff"
    status = $branchSectionStatus
    summary = "Current branch reported by the commit guard packet: $currentBranch"
})
[void]$handoffSections.Add([ordered]@{
    section = "Stage-now handoff"
    status = $stageSectionStatus
    summary = "Stage only the four Phase 21 Step 8 files."
})
[void]$handoffSections.Add([ordered]@{
    section = "Do-not-stage handoff"
    status = "required"
    summary = "Carry forward all do-not-stage paths from the commit guard packet."
})
[void]$handoffSections.Add([ordered]@{
    section = "Review-before-stage handoff"
    status = $reviewSectionStatus
    summary = "Review any non-Step-8 paths before staging them."
})
[void]$handoffSections.Add([ordered]@{
    section = "Runtime guard state"
    status = "review"
    summary = "Runtime endpoints remain checked by GET-only calls."
})

$currentStepFiles = @(
    "scripts/phase21_generate_phase20_network_transport_closeout_handoff_packet.ps1",
    "ui/pages/100_Phase20_Network_Transport_Closeout_Handoff_Packet.py",
    "docs/PHASE21_STEP8_PHASE20_NETWORK_TRANSPORT_CLOSEOUT_HANDOFF_PACKET.md",
    "tests/test_phase21_phase20_network_transport_closeout_handoff_packet.py"
)

foreach ($file in $currentStepFiles) {
    [void]$handoffEntries.Add([ordered]@{
        category = "stage_now"
        action = "stage"
        item = $file
        evidence = "Current Phase 21 Step 8 file."
        required = "yes"
    })
}

foreach ($entry in $doNotStageEntries) {
    [void]$handoffEntries.Add([ordered]@{
        category = "do_not_stage"
        action = [string]$entry.action
        item = [string]$entry.item
        evidence = [string]$entry.evidence
        required = [string]$entry.required
    })
}

foreach ($entry in $reviewBeforeStageEntries) {
    [void]$handoffEntries.Add([ordered]@{
        category = "review_before_stage"
        action = [string]$entry.action
        item = [string]$entry.item
        evidence = [string]$entry.evidence
        required = [string]$entry.required
    })
}

$nextCommitCommands = @(
    'cd "C:\Users\krist\Desktop\unified_pool_service_platform_build\unified_pool_service_platform_build"',
    "git status --short",
    "git add scripts/phase21_generate_phase20_network_transport_closeout_handoff_packet.ps1",
    "git add ui/pages/100_Phase20_Network_Transport_Closeout_Handoff_Packet.py",
    "git add docs/PHASE21_STEP8_PHASE20_NETWORK_TRANSPORT_CLOSEOUT_HANDOFF_PACKET.md",
    "git add tests/test_phase21_phase20_network_transport_closeout_handoff_packet.py",
    "git diff --cached --name-only",
    'git commit -m "Phase 21 Step 8 phase20 network transport closeout handoff packet"',
    "git push -u origin phase21-step8-phase20-network-transport-closeout-handoff-packet"
)

Add-ChecklistItem $checklist "closeout_handoff" "Current branch detected" (-not [string]::IsNullOrWhiteSpace($currentBranch)) "current_branch=$currentBranch"
Add-ChecklistItem $checklist "closeout_handoff" "At least one handoff section exists" (@($handoffSections).Count -gt 0) "handoff_sections=$(@($handoffSections).Count)"
Add-ChecklistItem $checklist "closeout_handoff" "Exactly four stage-now handoff entries exist" (@($handoffEntries | Where-Object { $_.category -eq "stage_now" }).Count -eq 4) "stage_now_entries=$(@($handoffEntries | Where-Object { $_.category -eq "stage_now" }).Count)"
Add-ChecklistItem $checklist "closeout_handoff" "At least one do-not-stage handoff entry exists" (@($handoffEntries | Where-Object { $_.category -eq "do_not_stage" }).Count -gt 0) "do_not_stage_entries=$(@($handoffEntries | Where-Object { $_.category -eq "do_not_stage" }).Count)"
Add-ChecklistItem $checklist "closeout_handoff" "Commit commands exist" (@($nextCommitCommands).Count -gt 0) "commit_commands=$(@($nextCommitCommands).Count)"
Add-ChecklistItem $checklist "closeout_handoff" "No forbidden paths are currently staged" ($stagedForbiddenCount -eq 0) "staged_forbidden_count=$stagedForbiddenCount"
Add-ChecklistItem $checklist "closeout_handoff" "No review-other paths are currently staged" ($stagedReviewOtherCount -eq 0) "staged_review_other_count=$stagedReviewOtherCount" "recommended"
Add-ChecklistItem $checklist "closeout_handoff" "Workspace review-other files count is zero or acceptable" ($reviewOtherCount -eq 0) "review_other_count=$reviewOtherCount" "recommended"

if ([string]::IsNullOrWhiteSpace($currentBranch)) {
    Add-Issue $issues "blocker" "current_branch_missing" "Current branch was not reported by the commit guard packet." "commit_guard"
}

$commitGuardStatus = [string]$commitGuardPacket.commit_guard_packet.status
if ($commitGuardStatus -eq "phase20_commit_guard_packet_blocked") {
    Add-Issue $issues "blocker" "commit_guard_packet_blocked" "Commit guard packet is blocked." "commit_guard"
} elseif ($commitGuardStatus -eq "phase20_commit_guard_packet_review_required_no_write") {
    Add-Issue $issues "review" "commit_guard_packet_review_required" "Commit guard packet has review items." "commit_guard"
}

if ($cleanupManifest -ne $null) {
    $cleanupStatus = [string]$cleanupManifest.cleanup_manifest_packet.status
    if ($cleanupStatus -eq "phase20_cleanup_manifest_packet_blocked") {
        Add-Issue $issues "blocker" "cleanup_manifest_packet_blocked" "Cleanup manifest packet is blocked." "cleanup_manifest"
    } elseif ($cleanupStatus -eq "phase20_cleanup_manifest_packet_review_required_no_write") {
        Add-Issue $issues "review" "cleanup_manifest_packet_review_required" "Cleanup manifest packet has review items." "cleanup_manifest"
    }
}

if ($workspaceHygiene -ne $null) {
    $workspaceStatus = [string]$workspaceHygiene.workspace_hygiene_packet.status
    if ($workspaceStatus -eq "phase20_workspace_hygiene_packet_blocked") {
        Add-Issue $issues "blocker" "workspace_hygiene_packet_blocked" "Workspace hygiene packet is blocked." "workspace_hygiene"
    } elseif ($workspaceStatus -eq "phase20_workspace_hygiene_packet_review_required_no_write") {
        Add-Issue $issues "review" "workspace_hygiene_packet_review_required" "Workspace hygiene packet has review items." "workspace_hygiene"
    }
}

foreach ($entry in @($stagedEntries | Where-Object { $_.category -eq "do_not_stage" -or $_.category -eq "runtime_database" -or $_.category -eq "generated_artifact" })) {
    Add-Issue $issues "blocker" ("staged_forbidden_" + ($entry.path -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) "$($entry.path) is staged but matches a forbidden category." "staged"
}
foreach ($entry in @($stagedEntries | Where-Object { $_.category -eq "review_other" })) {
    Add-Issue $issues "review" ("staged_review_other_" + ($entry.path -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) "$($entry.path) is staged but should be reviewed before commit." "staged"
}
foreach ($entry in @($gitStatusEntries | Where-Object { $_.category -eq "review_other" })) {
    Add-Issue $issues "review" ("workspace_review_other_" + ($entry.path -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) "$($entry.path) requires review before staging." "workspace"
}

[void]$sourceArtifacts.Add([ordered]@{ key="commit_guard_packet"; json_path=$commitGuardPacketPath; sha256=Get-FileSha256 $commitGuardPacketPath })
[void]$sourceArtifacts.Add([ordered]@{ key="cleanup_manifest_packet"; json_path=$cleanupManifestPath; sha256=Get-FileSha256 $cleanupManifestPath })
[void]$sourceArtifacts.Add([ordered]@{ key="workspace_hygiene_packet"; json_path=$workspaceHygienePath; sha256=Get-FileSha256 $workspaceHygienePath })

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
    "phase20_closeout_handoff_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "phase20_closeout_handoff_packet_review_required_no_write"
} else {
    "phase20_closeout_handoff_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase21_phase20_network_transport_closeout_handoff_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 21 Step 8"
    purpose = "Phase 20 bridge routing network transport closeout handoff packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        phase20_network_transport_closeout_handoff_packet_only = $true
        closeout_handoff_only = $true
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
    closeout_handoff_packet = [ordered]@{
        status = $packetStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        current_branch = $currentBranch
        section_count = @($handoffSections).Count
        entry_count = @($handoffEntries).Count
        command_count = @($nextCommitCommands).Count
        git_status_count = $gitStatusCount
        staged_count = $stagedCount
        stage_now_entry_count = @($stageNowEntries).Count
        do_not_stage_entry_count = @($doNotStageEntries).Count
        review_before_stage_entry_count = @($reviewBeforeStageEntries).Count
        staged_forbidden_count = $stagedForbiddenCount
        staged_review_other_count = $stagedReviewOtherCount
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
        packet_label = "phase21_phase20_network_transport_closeout_handoff_no_write"
        reason = if ($blockerCount -eq 0) {
            "Phase 21 Step 8 created a no-write closeout handoff for the Phase 20 network transport cleanup chain. It does not authorize approvals, implementation, transport, sockets, bridge POST, response capture, mutations, LACRM calls, or live writes."
        } else {
            "Phase 21 Step 8 found blockers in the Phase 20 closeout handoff packet. Resolve blockers before staging files."
        }
    }
    handoff_sections = @($handoffSections)
    handoff_entries = @($handoffEntries)
    git_status_entries = @($gitStatusEntries)
    staged_entries = @($stagedEntries)
    handoff_commands = $nextCommitCommands
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
        sections = @($handoffSections).Count
        entries = @($handoffEntries).Count
        git_status_entries = $gitStatusCount
        staged_entries = $stagedCount
        stage_now_entries = @($stageNowEntries).Count
        do_not_stage_entries = @($doNotStageEntries).Count
        review_before_stage_entries = @($reviewBeforeStageEntries).Count
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this closeout handoff before staging Step 8 files.",
        "Use the stage-now entries as the only files to add for the Step 8 commit.",
        "Carry the do-not-stage entries forward as the hard commit boundary.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 21 Step 8.",
        "Do not call interface execution methods from Phase 21 Step 8.",
        "Do not record final approvals from Phase 21 Step 8.",
        "Do not start an implementation phase from Phase 21 Step 8.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase21_phase20_network_transport_closeout_handoff_packet.json"
$sectionsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_closeout_handoff_packet_sections.csv"
$entriesCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_closeout_handoff_packet_entries.csv"
$gitStatusCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_closeout_handoff_packet_git_status.csv"
$stagedCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_closeout_handoff_packet_staged.csv"
$sourceArtifactsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_closeout_handoff_packet_source_artifacts.csv"
$checklistCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_closeout_handoff_packet_checklist.csv"
$issuesCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_closeout_handoff_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase21_phase20_network_transport_closeout_handoff_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$handoffSections | Export-Csv -LiteralPath $sectionsCsvPath -NoTypeInformation -Encoding UTF8
$handoffEntries | Export-Csv -LiteralPath $entriesCsvPath -NoTypeInformation -Encoding UTF8
$gitStatusEntries | Export-Csv -LiteralPath $gitStatusCsvPath -NoTypeInformation -Encoding UTF8
$stagedEntries | Export-Csv -LiteralPath $stagedCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $sourceArtifactsCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$sectionText = (@($handoffSections) | ForEach-Object { "- $($_.section): $($_.status); $($_.summary)" }) -join "`n"
$entryText = (@($handoffEntries) | ForEach-Object { "- [$($_.category)] $($_.action) $($_.item): $($_.evidence)" }) -join "`n"
$gitStatusText = if (@($gitStatusEntries).Count -gt 0) { (@($gitStatusEntries) | ForEach-Object { "- $($_.path): category=$($_.category); should_stage=$($_.should_stage); reason=$($_.reason)" }) -join "`n" } else { "- none" }
$stagedText = if (@($stagedEntries).Count -gt 0) { (@($stagedEntries) | ForEach-Object { "- $($_.path): category=$($_.category); should_stage=$($_.should_stage); reason=$($_.reason)" }) -join "`n" } else { "- none" }
$sourceArtifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }
$commandText = (@($nextCommitCommands) | ForEach-Object { "- $_" }) -join "`n"

$md = @"
# Phase 21 Step 8 - Phase 20 Network Transport Closeout Handoff Packet

Generated: $($report.generated_at)

Source commit guard packet:

``````
$commitGuardPacketPath
``````

## Safety

- Phase 20 network transport closeout handoff packet only: true
- Closeout handoff only: true
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

## Closeout handoff packet

- Status: $packetStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Current branch: $currentBranch
- Sections: $(@($handoffSections).Count)
- Entries: $(@($handoffEntries).Count)
- Git status entries: $gitStatusCount
- Staged entries: $stagedCount
- Stage-now entries: $(@($stageNowEntries).Count)
- Do-not-stage entries: $(@($doNotStageEntries).Count)
- Review-before-stage entries: $(@($reviewBeforeStageEntries).Count)
- Staged forbidden entries: $stagedForbiddenCount
- Staged review-other entries: $stagedReviewOtherCount
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

## Handoff sections

$sectionText

## Handoff entries

$entryText

## Current git status classification

$gitStatusText

## Current staged set classification

$stagedText

## Source artifacts

$sourceArtifactText

## Safe commit commands

$commandText

## Checklist

$checklistText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | phase20_network_transport_closeout_handoff_packet=$OutputDir | status=$packetStatus | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
} else {
    Write-Host "CHECK | phase20_network_transport_closeout_handoff_packet=$OutputDir | status=$packetStatus | blockers=$blockerCount | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
}

Write-Host ""
Write-Host "Closeout handoff packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
