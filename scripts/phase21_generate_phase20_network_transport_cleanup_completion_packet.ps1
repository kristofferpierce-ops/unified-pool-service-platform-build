param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$ArchiveDecisionPacketDir = "",
    [string]$CleanupManifestPacketDir = "",
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

function Classify-RepoPath {
    param(
        [string]$Path,
        [string[]]$DoNotStagePrefixes,
        [string[]]$CurrentStepFiles
    )

    if ($CurrentStepFiles -contains $Path) {
        return [ordered]@{
            category = "current_step_candidate"
            should_stage = $true
            reason = "Current Phase 21 Step 12 file."
        }
    }

    if (Test-PathMatchesPrefix -Path $Path -Prefixes $DoNotStagePrefixes) {
        return [ordered]@{
            category = "do_not_stage"
            should_stage = $false
            reason = "Matches cleanup-manifest do-not-stage path."
        }
    }

    if ($Path.StartsWith("backups\") -or $Path.StartsWith("backups/")) {
        return [ordered]@{
            category = "generated_artifact"
            should_stage = $false
            reason = "Generated artifact folder."
        }
    }

    if ($Path.EndsWith(".db")) {
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

if ([string]::IsNullOrWhiteSpace($ArchiveDecisionPacketDir)) {
    $ArchiveDecisionPacketDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_archive_decision_packet_*" -JsonName "phase21_phase20_network_transport_archive_decision_packet.json" -Required $true
}
if ([string]::IsNullOrWhiteSpace($CleanupManifestPacketDir)) {
    $CleanupManifestPacketDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_cleanup_manifest_packet_*" -JsonName "phase21_phase20_network_transport_cleanup_manifest_packet.json" -Required $false
}

$archiveDecisionPath = Join-Path $ArchiveDecisionPacketDir "phase21_phase20_network_transport_archive_decision_packet.json"
$cleanupManifestPath = if (![string]::IsNullOrWhiteSpace($CleanupManifestPacketDir)) { Join-Path $CleanupManifestPacketDir "phase21_phase20_network_transport_cleanup_manifest_packet.json" } else { "" }

if (!(Test-Path -LiteralPath $archiveDecisionPath)) {
    throw "Archive decision packet JSON not found: $archiveDecisionPath"
}

$archiveDecision = Read-JsonFile $archiveDecisionPath
$cleanupManifest = if (![string]::IsNullOrWhiteSpace($cleanupManifestPath) -and (Test-Path -LiteralPath $cleanupManifestPath)) { Read-JsonFile $cleanupManifestPath } else { $null }

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList
$completionSections = New-Object System.Collections.ArrayList
$completionEntries = New-Object System.Collections.ArrayList
$archiveDecisions = New-Object System.Collections.ArrayList
$artifactFamilies = New-Object System.Collections.ArrayList
$gitStatusEntries = New-Object System.Collections.ArrayList
$stagedEntries = New-Object System.Collections.ArrayList
$sourceArtifacts = New-Object System.Collections.ArrayList

Add-ChecklistItem $checklist "artifact" "Archive decision packet exists" $true $archiveDecisionPath
Add-ChecklistItem $checklist "artifact" "Cleanup manifest packet exists" ($cleanupManifest -ne $null) $cleanupManifestPath "recommended"

Add-ChecklistItem $checklist "archive_decision" "Archive decision packet is cleanup-completion-safe" ($archiveDecision.safety.phase20_network_transport_archive_decision_packet_only -eq $true) "phase20_network_transport_archive_decision_packet_only=$($archiveDecision.safety.phase20_network_transport_archive_decision_packet_only)"
Add-ChecklistItem $checklist "archive_decision" "Archive decision recorded no closure record" ($archiveDecision.safety.design_closure_record_created -eq $false) "design_closure_record_created=$($archiveDecision.safety.design_closure_record_created)"
Add-ChecklistItem $checklist "archive_decision" "Archive decision recorded no final approval" ($archiveDecision.safety.final_approval_recorded -eq $false) "final_approval_recorded=$($archiveDecision.safety.final_approval_recorded)"
Add-ChecklistItem $checklist "archive_decision" "Archive decision started no implementation phase" ($archiveDecision.safety.implementation_phase_started -eq $false) "implementation_phase_started=$($archiveDecision.safety.implementation_phase_started)"
Add-ChecklistItem $checklist "archive_decision" "Archive decision has no execution implementation" ($archiveDecision.safety.execution_implementation_created -eq $false) "execution_implementation_created=$($archiveDecision.safety.execution_implementation_created)"
Add-ChecklistItem $checklist "archive_decision" "Archive decision has no network transport" ($archiveDecision.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($archiveDecision.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "archive_decision" "Archive decision has no socket opened" ($archiveDecision.safety.network_socket_opened -eq $false) "network_socket_opened=$($archiveDecision.safety.network_socket_opened)"
Add-ChecklistItem $checklist "archive_decision" "Archive decision has no bridge POST" ($archiveDecision.safety.bridge_post_called -eq $false -and $archiveDecision.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($archiveDecision.safety.bridge_post_called); bridge_post_call_implemented=$($archiveDecision.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "archive_decision" "Archive decision has no platform DB mutation" ($archiveDecision.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($archiveDecision.safety.platform_db_mutation_performed)"
Add-ChecklistItem $checklist "archive_decision" "Archive decision has no bridge mutation" ($archiveDecision.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($archiveDecision.safety.bridge_mutation_performed)"
Add-ChecklistItem $checklist "archive_decision" "Archive decision has no LACRM call" ($archiveDecision.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($archiveDecision.safety.lacrm_call_performed)"
Add-ChecklistItem $checklist "archive_decision" "Archive decision has no blockers" ([int]$archiveDecision.archive_decision_packet.blocker_count -eq 0) "blocker_count=$($archiveDecision.archive_decision_packet.blocker_count)"

if ($cleanupManifest -ne $null) {
    Add-ChecklistItem $checklist "cleanup_manifest" "Cleanup manifest packet is no-write only" ($cleanupManifest.safety.phase20_network_transport_cleanup_manifest_packet_only -eq $true) "phase20_network_transport_cleanup_manifest_packet_only=$($cleanupManifest.safety.phase20_network_transport_cleanup_manifest_packet_only)" "recommended"
}

$doNotStagePrefixes = @(
    "data/unified_pool_service_platform.db",
    ".env",
    ".venv",
    "backups",
    "front_desk_bridge",
    "front_desk_bridge_repo",
    "app/services/tools.py",
    "app/services/replaster_quote.py",
    "docs/26_REPLASTER_QUOTE_TOOL_PLAN.md",
    "tests/test_replaster_quote.py",
    "ui/pages/13_Replaster_Quote.py"
)
if ($cleanupManifest -ne $null) {
    $manifestPrefixes = @($cleanupManifest.manifest_entries | Where-Object { $_.category -eq "do_not_stage_paths" } | ForEach-Object { [string]$_.item })
    if (@($manifestPrefixes).Count -gt 0) {
        $doNotStagePrefixes = $manifestPrefixes
    }
} else {
    $decisionPrefixes = @($archiveDecision.decision_entries | Where-Object { $_.category -eq "do_not_stage" } | ForEach-Object { [string]$_.item })
    if (@($decisionPrefixes).Count -gt 0) {
        $doNotStagePrefixes = $decisionPrefixes
    }
}

$currentStepFiles = @(
    "scripts/phase21_generate_phase20_network_transport_cleanup_completion_packet.ps1",
    "ui/pages/104_Phase20_Network_Transport_Cleanup_Completion_Packet.py",
    "docs/PHASE21_STEP12_PHASE20_NETWORK_TRANSPORT_CLEANUP_COMPLETION_PACKET.md",
    "tests/test_phase21_phase20_network_transport_cleanup_completion_packet.py"
)

$currentBranch = (& git -C $PlatformDir branch --show-current 2>$null | Out-String).Trim()

# Cleanup completion uses git status --short against the platform repo.
$gitStatusRaw = & git -C $PlatformDir status --short 2>$null
$stagedNamesRaw = & git -C $PlatformDir diff --cached --name-only 2>$null

foreach ($line in @($gitStatusRaw)) {
    $parsed = Convert-GitStatusLine -Line ([string]$line)
    if ($null -eq $parsed) { continue }

    $class = Classify-RepoPath -Path $parsed.path -DoNotStagePrefixes $doNotStagePrefixes -CurrentStepFiles $currentStepFiles

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

foreach ($name in @($stagedNamesRaw)) {
    $path = ([string]$name).Trim()
    if ([string]::IsNullOrWhiteSpace($path)) { continue }

    $class = Classify-RepoPath -Path $path -DoNotStagePrefixes $doNotStagePrefixes -CurrentStepFiles $currentStepFiles

    [void]$stagedEntries.Add([ordered]@{
        path = $path
        category = $class.category
        should_stage = $class.should_stage
        reason = $class.reason
    })
}

$artifactFamilies = @($archiveDecision.artifact_families | Sort-Object @{Expression = {[int]$_.older_generated_folder_count}; Descending = $true}, @{Expression = {[string]$_.folder_filter}; Descending = $false})
$archiveDecisions = @($archiveDecision.archive_decisions | Sort-Object @{Expression = {[int]$_.archive_order}; Descending = $false}, @{Expression = {[string]$_.folder_filter}; Descending = $false})

$keepLatestOnlyCount = @($archiveDecisions | Where-Object { $_.decision -eq "keep_latest_only" }).Count
$manualArchiveReviewCount = @($archiveDecisions | Where-Object { $_.decision -eq "manual_archive_review" }).Count

$gitStatusCount = @($gitStatusEntries).Count
$stagedCount = @($stagedEntries).Count
$stagedForbiddenCount = @($stagedEntries | Where-Object { $_.category -eq "do_not_stage" -or $_.category -eq "runtime_database" -or $_.category -eq "generated_artifact" }).Count
$stagedReviewOtherCount = @($stagedEntries | Where-Object { $_.category -eq "review_other" }).Count
$reviewOtherCount = @($gitStatusEntries | Where-Object { $_.category -eq "review_other" }).Count
$currentStepCandidateCount = @($gitStatusEntries | Where-Object { $_.category -eq "current_step_candidate" }).Count

[void]$completionSections.Add([ordered]@{
    section = "Cleanup completion state"
    status = if ($manualArchiveReviewCount -gt 0) { "review" } else { "clean" }
    summary = "Phase 20 cleanup completion stays no-write. Archive decisions are carried forward without performing archive actions."
})
[void]$completionSections.Add([ordered]@{
    section = "Keep-latest boundary"
    status = "required"
    summary = "Keep the latest packet folder in every family."
})
[void]$completionSections.Add([ordered]@{
    section = "Manual archive review carry-forward"
    status = if ($manualArchiveReviewCount -gt 0) { "review" } else { "clean" }
    summary = "Families with older generated folders remain manual-review items only."
})
[void]$completionSections.Add([ordered]@{
    section = "Do-not-stage boundary"
    status = "required"
    summary = "Carry forward the do-not-stage paths while cleanup remains review-only."
})
[void]$completionSections.Add([ordered]@{
    section = "Runtime guard state"
    status = "review"
    summary = "Runtime endpoints remain checked by GET-only calls."
})

foreach ($file in $currentStepFiles) {
    [void]$completionEntries.Add([ordered]@{
        category = "stage_now"
        action = "stage"
        item = $file
        evidence = "Current Phase 21 Step 12 file."
        required = "yes"
    })
}

foreach ($prefix in @($doNotStagePrefixes)) {
    [void]$completionEntries.Add([ordered]@{
        category = "do_not_stage"
        action = "exclude"
        item = $prefix
        evidence = "Cleanup boundary do-not-stage path."
        required = "yes"
    })
}

foreach ($decision in @($archiveDecisions)) {
    if ($decision.decision -eq "manual_archive_review") {
        [void]$completionEntries.Add([ordered]@{
            category = "manual_archive_review"
            action = "review_archive_older_generated_folders"
            item = [string]$decision.folder_filter
            evidence = "older_generated_folders=$($decision.older_generated_folder_count); latest=$($decision.latest_folder); archive_order=$($decision.archive_order)"
            required = "recommended"
        })
    } else {
        [void]$completionEntries.Add([ordered]@{
            category = "keep_latest_only"
            action = "keep_latest"
            item = [string]$decision.folder_filter
            evidence = "older_generated_folders=$($decision.older_generated_folder_count); latest=$($decision.latest_folder)"
            required = "recommended"
        })
    }
}

foreach ($entry in @($gitStatusEntries | Where-Object { $_.category -eq "review_other" })) {
    [void]$completionEntries.Add([ordered]@{
        category = "review_before_stage"
        action = "review"
        item = [string]$entry.path
        evidence = [string]$entry.reason
        required = "recommended"
    })
}

$nextCommitCommands = @(
    'cd "C:\Users\krist\Desktop\unified_pool_service_platform_build\unified_pool_service_platform_build"',
    "git status --short",
    "git add scripts/phase21_generate_phase20_network_transport_cleanup_completion_packet.ps1",
    "git add ui/pages/104_Phase20_Network_Transport_Cleanup_Completion_Packet.py",
    "git add docs/PHASE21_STEP12_PHASE20_NETWORK_TRANSPORT_CLEANUP_COMPLETION_PACKET.md",
    "git add tests/test_phase21_phase20_network_transport_cleanup_completion_packet.py",
    "git diff --cached --name-only",
    'git commit -m "Phase 21 Step 12 phase20 network transport cleanup completion packet"',
    "git push -u origin phase21-step12-phase20-network-transport-cleanup-completion-packet"
)

Add-ChecklistItem $checklist "cleanup_completion" "Current branch detected" (-not [string]::IsNullOrWhiteSpace($currentBranch)) "current_branch=$currentBranch"
Add-ChecklistItem $checklist "cleanup_completion" "At least one cleanup-completion section exists" (@($completionSections).Count -gt 0) "cleanup_completion_sections=$(@($completionSections).Count)"
Add-ChecklistItem $checklist "cleanup_completion" "Exactly four stage-now entries exist" (@($completionEntries | Where-Object { $_.category -eq "stage_now" }).Count -eq 4) "stage_now_entries=$(@($completionEntries | Where-Object { $_.category -eq "stage_now" }).Count)"
Add-ChecklistItem $checklist "cleanup_completion" "Archive decisions were carried forward" (@($archiveDecisions).Count -eq @($artifactFamilies).Count) "archive_decisions=$(@($archiveDecisions).Count); artifact_families=$(@($artifactFamilies).Count)" "recommended"
Add-ChecklistItem $checklist "cleanup_completion" "Commit commands exist" (@($nextCommitCommands).Count -gt 0) "commit_commands=$(@($nextCommitCommands).Count)"
Add-ChecklistItem $checklist "cleanup_completion" "No forbidden paths are currently staged" ($stagedForbiddenCount -eq 0) "staged_forbidden_count=$stagedForbiddenCount"
Add-ChecklistItem $checklist "cleanup_completion" "No review-other paths are currently staged" ($stagedReviewOtherCount -eq 0) "staged_review_other_count=$stagedReviewOtherCount" "recommended"
Add-ChecklistItem $checklist "cleanup_completion" "Workspace review-other files count is zero or acceptable" ($reviewOtherCount -eq 0) "review_other_count=$reviewOtherCount" "recommended"

$archiveDecisionStatus = [string]$archiveDecision.archive_decision_packet.status
if ($archiveDecisionStatus -eq "phase20_archive_decision_packet_blocked") {
    Add-Issue $issues "blocker" "archive_decision_packet_blocked" "Archive decision packet is blocked." "archive_decision"
} elseif ($archiveDecisionStatus -eq "phase20_archive_decision_packet_review_required_no_write") {
    Add-Issue $issues "review" "archive_decision_packet_review_required" "Archive decision packet has review items." "archive_decision"
}

if ([string]::IsNullOrWhiteSpace($currentBranch)) {
    Add-Issue $issues "blocker" "current_branch_missing" "Current branch was not detected for cleanup completion." "workspace"
}

foreach ($decision in @($archiveDecisions | Where-Object { $_.decision -eq "manual_archive_review" })) {
    Add-Issue $issues "review" ("manual_archive_review_" + ($decision.folder_filter -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) "$($decision.folder_filter) still has older generated folders to review manually." "archive_decision"
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

[void]$sourceArtifacts.Add([ordered]@{ key="archive_decision_packet"; json_path=$archiveDecisionPath; sha256=Get-FileSha256 $archiveDecisionPath })
[void]$sourceArtifacts.Add([ordered]@{ key="cleanup_manifest_packet"; json_path=$cleanupManifestPath; sha256=Get-FileSha256 $cleanupManifestPath })

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
    "phase20_cleanup_completion_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "phase20_cleanup_completion_packet_review_required_no_write"
} else {
    "phase20_cleanup_completion_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase21_phase20_network_transport_cleanup_completion_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 21 Step 12"
    purpose = "Phase 20 bridge routing network transport cleanup completion packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        phase20_network_transport_cleanup_completion_packet_only = $true
        cleanup_completion_only = $true
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
    cleanup_completion_packet = [ordered]@{
        status = $packetStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        current_branch = $currentBranch
        section_count = @($completionSections).Count
        entry_count = @($completionEntries).Count
        archive_decision_count = @($archiveDecisions).Count
        artifact_family_count = @($artifactFamilies).Count
        keep_latest_only_count = $keepLatestOnlyCount
        manual_archive_review_count = $manualArchiveReviewCount
        git_status_count = $gitStatusCount
        staged_count = $stagedCount
        current_step_candidate_count = $currentStepCandidateCount
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
        packet_label = "phase21_phase20_network_transport_cleanup_completion_no_write"
        reason = if ($blockerCount -eq 0) {
            "Phase 21 Step 12 created a no-write cleanup completion packet for the Phase 20 network transport cleanup chain. It does not authorize approvals, implementation, transport, sockets, bridge POST, response capture, mutations, LACRM calls, or live writes."
        } else {
            "Phase 21 Step 12 found blockers in the Phase 20 cleanup completion packet. Resolve blockers before further cleanup work."
        }
    }
    completion_sections = @($completionSections)
    completion_entries = @($completionEntries)
    archive_decisions = @($archiveDecisions)
    artifact_families = @($artifactFamilies)
    git_status_entries = @($gitStatusEntries)
    staged_entries = @($stagedEntries)
    completion_commands = $nextCommitCommands
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
        sections = @($completionSections).Count
        entries = @($completionEntries).Count
        archive_decisions = @($archiveDecisions).Count
        artifact_families = @($artifactFamilies).Count
        keep_latest_only = $keepLatestOnlyCount
        manual_archive_review = $manualArchiveReviewCount
        git_status_entries = $gitStatusCount
        staged_entries = $stagedCount
        checklist = @($checklist).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this cleanup completion packet before any final Phase 21 exit or manual backup-folder archiving.",
        "Keep the latest packet folder in each family and only review older generated folders for manual archive actions.",
        "Use the stage-now entries as the only files to add for the Step 12 commit.",
        "Carry the do-not-stage entries forward as the hard commit boundary.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 21 Step 12.",
        "Do not call interface execution methods from Phase 21 Step 12.",
        "Do not record final approvals from Phase 21 Step 12.",
        "Do not start an implementation phase from Phase 21 Step 12.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_completion_packet.json"
$sectionsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_completion_packet_sections.csv"
$entriesCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_completion_packet_entries.csv"
$decisionsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_completion_packet_decisions.csv"
$familiesCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_completion_packet_artifact_families.csv"
$gitStatusCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_completion_packet_git_status.csv"
$stagedCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_completion_packet_staged.csv"
$sourceArtifactsCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_completion_packet_source_artifacts.csv"
$checklistCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_completion_packet_checklist.csv"
$issuesCsvPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_completion_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase21_phase20_network_transport_cleanup_completion_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$completionSections | Export-Csv -LiteralPath $sectionsCsvPath -NoTypeInformation -Encoding UTF8
$completionEntries | Export-Csv -LiteralPath $entriesCsvPath -NoTypeInformation -Encoding UTF8
$archiveDecisions | Export-Csv -LiteralPath $decisionsCsvPath -NoTypeInformation -Encoding UTF8
$artifactFamilies | Export-Csv -LiteralPath $familiesCsvPath -NoTypeInformation -Encoding UTF8
$gitStatusEntries | Export-Csv -LiteralPath $gitStatusCsvPath -NoTypeInformation -Encoding UTF8
$stagedEntries | Export-Csv -LiteralPath $stagedCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $sourceArtifactsCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$sectionText = (@($completionSections) | ForEach-Object { "- $($_.section): $($_.status); $($_.summary)" }) -join "`n"
$entryText = (@($completionEntries) | ForEach-Object { "- [$($_.category)] $($_.action) $($_.item): $($_.evidence)" }) -join "`n"
$decisionText = (@($archiveDecisions) | ForEach-Object { "- $($_.folder_filter): decision=$($_.decision); older_generated_folders=$($_.older_generated_folder_count); archive_order=$($_.archive_order)" }) -join "`n"
$familyText = (@($artifactFamilies) | ForEach-Object { "- $($_.folder_filter): folder_count=$($_.folder_count); older_generated_folders=$($_.older_generated_folder_count); latest=$($_.latest_folder)" }) -join "`n"
$gitStatusText = if (@($gitStatusEntries).Count -gt 0) { (@($gitStatusEntries) | ForEach-Object { "- $($_.path): category=$($_.category); should_stage=$($_.should_stage); reason=$($_.reason)" }) -join "`n" } else { "- none" }
$stagedText = if (@($stagedEntries).Count -gt 0) { (@($stagedEntries) | ForEach-Object { "- $($_.path): category=$($_.category); should_stage=$($_.should_stage); reason=$($_.reason)" }) -join "`n" } else { "- none" }
$sourceArtifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }
$commandText = (@($nextCommitCommands) | ForEach-Object { "- $_" }) -join "`n"

$md = @"
# Phase 21 Step 12 - Phase 20 Network Transport Cleanup Completion Packet

Generated: $($report.generated_at)

Source archive decision packet:

``````
$archiveDecisionPath
``````

## Safety

- Phase 20 network transport cleanup completion packet only: true
- Cleanup completion only: true
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

## Cleanup completion packet

- Status: $packetStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Current branch: $currentBranch
- Sections: $(@($completionSections).Count)
- Entries: $(@($completionEntries).Count)
- Archive decisions: $(@($archiveDecisions).Count)
- Artifact families: $(@($artifactFamilies).Count)
- Keep-latest-only decisions: $keepLatestOnlyCount
- Manual-archive-review decisions: $manualArchiveReviewCount
- Git status entries: $gitStatusCount
- Staged entries: $stagedCount
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

## Completion sections

$sectionText

## Completion entries

$entryText

## Archive decisions

$decisionText

## Artifact families

$familyText

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
    Write-Host "PASS | phase20_network_transport_cleanup_completion_packet=$OutputDir | status=$packetStatus | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
} else {
    Write-Host "CHECK | phase20_network_transport_cleanup_completion_packet=$OutputDir | status=$packetStatus | blockers=$blockerCount | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
}

Write-Host ""
Write-Host "Cleanup completion packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
