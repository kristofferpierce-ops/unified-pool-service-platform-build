param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$PlanningClosurePacketDir = "",
    [string]$PlanningApprovalPacketDir = "",
    [string]$CleanupExitPacketDir = "",
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

    $indexStatus = if ($Line.Length -ge 1) { $Line.Substring(0, 1) } else { "" }
    $worktreeStatus = if ($Line.Length -ge 2) { $Line.Substring(1, 1) } else { "" }
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
            reason = "Current Phase 22 Step 13 file."
        }
    }

    if (Test-PathMatchesPrefix -Path $Path -Prefixes $DoNotStagePrefixes) {
        return [ordered]@{
            category = "do_not_stage"
            should_stage = $false
            reason = "Matches cleanup boundary do-not-stage path."
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

if ([string]::IsNullOrWhiteSpace($PlanningClosurePacketDir)) {
    $PlanningClosurePacketDir = Get-LatestArtifactDir -FolderFilter "phase22_phase20_network_transport_planning_closure_packet_*" -JsonName "phase22_phase20_network_transport_planning_closure_packet.json" -Required $true
}
if ([string]::IsNullOrWhiteSpace($PlanningApprovalPacketDir)) {
    $PlanningApprovalPacketDir = Get-LatestArtifactDir -FolderFilter "phase22_phase20_network_transport_planning_approval_packet_*" -JsonName "phase22_phase20_network_transport_planning_approval_packet.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($CleanupExitPacketDir)) {
    $CleanupExitPacketDir = Get-LatestArtifactDir -FolderFilter "phase21_phase20_network_transport_cleanup_exit_packet_*" -JsonName "phase21_phase20_network_transport_cleanup_exit_packet.json" -Required $false
}

$planningClosurePath = Join-Path $PlanningClosurePacketDir "phase22_phase20_network_transport_planning_closure_packet.json"
$planningApprovalPath = if (![string]::IsNullOrWhiteSpace($PlanningApprovalPacketDir)) { Join-Path $PlanningApprovalPacketDir "phase22_phase20_network_transport_planning_approval_packet.json" } else { "" }
$cleanupExitPath = if (![string]::IsNullOrWhiteSpace($CleanupExitPacketDir)) { Join-Path $CleanupExitPacketDir "phase21_phase20_network_transport_cleanup_exit_packet.json" } else { "" }

if (!(Test-Path -LiteralPath $planningClosurePath)) {
    throw "Planning closure packet JSON not found: $planningClosurePath"
}

$planningClosure = Read-JsonFile $planningClosurePath
$planningApproval = if (![string]::IsNullOrWhiteSpace($planningApprovalPath) -and (Test-Path -LiteralPath $planningApprovalPath)) { Read-JsonFile $planningApprovalPath } else { $null }
$cleanupExit = if (![string]::IsNullOrWhiteSpace($cleanupExitPath) -and (Test-Path -LiteralPath $cleanupExitPath)) { Read-JsonFile $cleanupExitPath } else { $null }

$issues = New-Object System.Collections.ArrayList
$checklist = New-Object System.Collections.ArrayList
$exitSections = New-Object System.Collections.ArrayList
$exitEntries = New-Object System.Collections.ArrayList
$exitAreas = New-Object System.Collections.ArrayList
$artifactFamilies = New-Object System.Collections.ArrayList
$archiveDecisions = New-Object System.Collections.ArrayList
$gitStatusEntries = New-Object System.Collections.ArrayList
$stagedEntries = New-Object System.Collections.ArrayList
$sourceArtifacts = New-Object System.Collections.ArrayList

Add-ChecklistItem $checklist "artifact" "Planning closure packet exists" $true $planningClosurePath
Add-ChecklistItem $checklist "artifact" "Planning approval packet exists" ($planningApproval -ne $null) $planningApprovalPath "recommended"
Add-ChecklistItem $checklist "artifact" "Cleanup exit packet exists" ($cleanupExit -ne $null) $cleanupExitPath "recommended"

Add-ChecklistItem $checklist "planning_closure" "Planning closure packet is exit-safe" ($planningClosure.safety.phase20_network_transport_planning_closure_packet_only -eq $true) "phase20_network_transport_planning_closure_packet_only=$($planningClosure.safety.phase20_network_transport_planning_closure_packet_only)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure created no closure record" ($planningClosure.safety.design_closure_record_created -eq $false) "design_closure_record_created=$($planningClosure.safety.design_closure_record_created)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure recorded no final approval" ($planningClosure.safety.final_approval_recorded -eq $false) "final_approval_recorded=$($planningClosure.safety.final_approval_recorded)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure recorded no operator signoff" ($planningClosure.safety.operator_signoff_recorded -eq $false) "operator_signoff_recorded=$($planningClosure.safety.operator_signoff_recorded)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure recorded no operator approval" ($planningClosure.safety.operator_approval_recorded -eq $false) "operator_approval_recorded=$($planningClosure.safety.operator_approval_recorded)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure started no implementation phase" ($planningClosure.safety.implementation_phase_started -eq $false) "implementation_phase_started=$($planningClosure.safety.implementation_phase_started)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure has no execution implementation" ($planningClosure.safety.execution_implementation_created -eq $false) "execution_implementation_created=$($planningClosure.safety.execution_implementation_created)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure has no network transport" ($planningClosure.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($planningClosure.safety.network_transport_implemented)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure has no socket opened" ($planningClosure.safety.network_socket_opened -eq $false) "network_socket_opened=$($planningClosure.safety.network_socket_opened)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure has no bridge POST" ($planningClosure.safety.bridge_post_called -eq $false -and $planningClosure.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($planningClosure.safety.bridge_post_called); bridge_post_call_implemented=$($planningClosure.safety.bridge_post_call_implemented)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure has no platform DB mutation" ($planningClosure.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($planningClosure.safety.platform_db_mutation_performed)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure has no bridge mutation" ($planningClosure.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($planningClosure.safety.bridge_mutation_performed)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure has no LACRM call" ($planningClosure.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($planningClosure.safety.lacrm_call_performed)"
Add-ChecklistItem $checklist "planning_closure" "Planning closure has no blockers" ([int]$planningClosure.planning_closure_packet.blocker_count -eq 0) "blocker_count=$($planningClosure.planning_closure_packet.blocker_count)"

if ($planningApproval -ne $null) {
    Add-ChecklistItem $checklist "planning_approval" "Planning approval packet is planning-only" ($planningApproval.safety.planning_only -eq $true) "planning_only=$($planningApproval.safety.planning_only)" "recommended"
}
if ($cleanupExit -ne $null) {
    Add-ChecklistItem $checklist "cleanup_exit" "Cleanup exit packet is no-write only" ($cleanupExit.safety.phase20_network_transport_cleanup_exit_packet_only -eq $true) "phase20_network_transport_cleanup_exit_packet_only=$($cleanupExit.safety.phase20_network_transport_cleanup_exit_packet_only)" "recommended"
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
$closurePrefixes = @($planningClosure.planning_entries | Where-Object { $_.category -eq "do_not_stage" } | ForEach-Object { [string]$_.item })
if (@($closurePrefixes).Count -gt 0) {
    $doNotStagePrefixes = $closurePrefixes
}

$currentStepFiles = @(
    "scripts/phase22_generate_phase20_network_transport_planning_exit_packet.ps1",
    "ui/pages/119_Phase20_Network_Transport_Planning_Exit_Packet.py",
    "docs/PHASE22_STEP13_PHASE20_NETWORK_TRANSPORT_PLANNING_EXIT_PACKET.md",
    "tests/test_phase22_phase20_network_transport_planning_exit_packet.py"
)

$currentBranch = (& git -C $PlatformDir branch --show-current 2>$null | Out-String).Trim()

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

if ($planningClosure.artifact_families) {
    foreach ($family in @($planningClosure.artifact_families)) {
        [void]$artifactFamilies.Add($family)
    }
}
if ($planningClosure.archive_decisions) {
    foreach ($decision in @($planningClosure.archive_decisions)) {
        [void]$archiveDecisions.Add($decision)
    }
}

$exitSpecs = @(
    [ordered]@{ key="execution_envelope_exit"; item="Execution envelope exit review"; depends_on="Execution envelope closure review"; summary="Review execution request, result, error, and dry-run envelope completeness as exit-ready planning material only."; implementation_allowed=$false; bridge_post_allowed=$false; socket_allowed=$false; exit_level="planning_only" },
    [ordered]@{ key="transport_injection_exit"; item="Transport injection exit review"; depends_on="Transport injection closure review"; summary="Review dependency injection seams and transport-off defaults as exit-ready planning material only."; implementation_allowed=$false; bridge_post_allowed=$false; socket_allowed=$false; exit_level="planning_only" },
    [ordered]@{ key="bridge_gate_exit"; item="Bridge gate exit review"; depends_on="Bridge gate closure review"; summary="Review confirmation phrase, armed-state, environment gate, and explicit POST precondition coverage as exit-ready planning material only."; implementation_allowed=$false; bridge_post_allowed=$false; socket_allowed=$false; exit_level="planning_only" },
    [ordered]@{ key="response_storage_exit"; item="Response storage exit review"; depends_on="Response storage closure review"; summary="Review response record, storage, and idempotent capture coverage as exit-ready planning material only."; implementation_allowed=$false; bridge_post_allowed=$false; socket_allowed=$false; exit_level="planning_only" },
    [ordered]@{ key="cutover_exit"; item="Cutover exit review"; depends_on="Cutover closure review"; summary="Review cutover prerequisites, verification checkpoints, and rollback review coverage as exit-ready planning material only."; implementation_allowed=$false; bridge_post_allowed=$false; socket_allowed=$false; exit_level="planning_only" },
    [ordered]@{ key="audit_rollback_exit"; item="Audit and rollback exit review"; depends_on="Audit and rollback closure review"; summary="Review audit record, rollback record, and snapshot coverage as exit-ready planning material only."; implementation_allowed=$false; bridge_post_allowed=$false; socket_allowed=$false; exit_level="planning_only" }
)

foreach ($spec in $exitSpecs) {
    [void]$exitAreas.Add([ordered]@{
        key = $spec.key
        item = $spec.item
        depends_on = $spec.depends_on
        summary = $spec.summary
        status = "review_only"
        exit_level = $spec.exit_level
        implementation_allowed = $spec.implementation_allowed
        real_transport_allowed = $false
        bridge_post_allowed = $spec.bridge_post_allowed
        socket_allowed = $spec.socket_allowed
        live_write_allowed = $false
    })

    [void]$exitEntries.Add([ordered]@{
        category = "exit_areas"
        action = "review_only"
        item = $spec.item
        evidence = $spec.summary
        required = "recommended"
    })
}

$keepLatestOnlyCount = @($archiveDecisions | Where-Object { $_.decision -eq "keep_latest_only" }).Count
$manualArchiveReviewCount = @($archiveDecisions | Where-Object { $_.decision -eq "manual_archive_review" }).Count
$gitStatusCount = @($gitStatusEntries).Count
$stagedCount = @($stagedEntries).Count
$stagedForbiddenCount = @($stagedEntries | Where-Object { $_.category -eq "do_not_stage" -or $_.category -eq "runtime_database" -or $_.category -eq "generated_artifact" }).Count
$stagedReviewOtherCount = @($stagedEntries | Where-Object { $_.category -eq "review_other" }).Count
$reviewOtherCount = @($gitStatusEntries | Where-Object { $_.category -eq "review_other" }).Count
$currentStepCandidateCount = @($gitStatusEntries | Where-Object { $_.category -eq "current_step_candidate" }).Count

[void]$exitSections.Add([ordered]@{
    section = "Planning exit state"
    status = "review"
    summary = "Phase 22 Step 13 remains planning-only and converts planning closure areas into explicit exit-review areas."
})
[void]$exitSections.Add([ordered]@{
    section = "Exit areas"
    status = "review"
    summary = "Execution envelope, transport injection, bridge gate, response storage, cutover, and audit/rollback exit areas remain review-only."
})
[void]$exitSections.Add([ordered]@{
    section = "Carry-forward cleanup boundary"
    status = "required"
    summary = "Keep latest packet folders and preserve manual archive review items as review-only."
})
[void]$exitSections.Add([ordered]@{
    section = "Do-not-stage boundary"
    status = "required"
    summary = "Carry forward the do-not-stage paths while Phase 22 remains planning-only."
})
[void]$exitSections.Add([ordered]@{
    section = "Runtime guard state"
    status = "review"
    summary = "Runtime endpoints remain checked by GET-only calls."
})

foreach ($file in @($currentStepFiles)) {
    [void]$exitEntries.Add([ordered]@{
        category = "stage_now"
        action = "stage"
        item = $file
        evidence = "Current Phase 22 Step 13 file."
        required = "yes"
    })
}

foreach ($prefix in @($doNotStagePrefixes)) {
    [void]$exitEntries.Add([ordered]@{
        category = "do_not_stage"
        action = "exclude"
        item = $prefix
        evidence = "Cleanup boundary do-not-stage path."
        required = "yes"
    })
}

foreach ($decision in @($archiveDecisions)) {
    if ($decision.decision -eq "manual_archive_review") {
        [void]$exitEntries.Add([ordered]@{
            category = "manual_archive_review"
            action = "review_archive_older_generated_folders"
            item = [string]$decision.folder_filter
            evidence = "older_generated_folders=$($decision.older_generated_folder_count); latest=$($decision.latest_folder); archive_order=$($decision.archive_order)"
            required = "recommended"
        })
    } else {
        [void]$exitEntries.Add([ordered]@{
            category = "keep_latest_only"
            action = "keep_latest"
            item = [string]$decision.folder_filter
            evidence = "older_generated_folders=$($decision.older_generated_folder_count); latest=$($decision.latest_folder)"
            required = "recommended"
        })
    }
}

foreach ($entry in @($gitStatusEntries | Where-Object { $_.category -eq "review_other" })) {
    [void]$exitEntries.Add([ordered]@{
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
    "git add scripts/phase22_generate_phase20_network_transport_planning_exit_packet.ps1",
    "git add ui/pages/119_Phase20_Network_Transport_Planning_Exit_Packet.py",
    "git add docs/PHASE22_STEP13_PHASE20_NETWORK_TRANSPORT_PLANNING_EXIT_PACKET.md",
    "git add tests/test_phase22_phase20_network_transport_planning_exit_packet.py",
    "git diff --cached --name-only",
    'git commit -m "Phase 22 Step 13 phase20 network transport planning exit packet"',
    "git push -u origin phase22-step13-phase20-network-transport-planning-exit-packet"
)

Add-ChecklistItem $checklist "planning_exit" "Current branch detected" (-not [string]::IsNullOrWhiteSpace($currentBranch)) "current_branch=$currentBranch"
Add-ChecklistItem $checklist "planning_exit" "At least one planning-exit section exists" (@($exitSections).Count -gt 0) "planning_exit_sections=$(@($exitSections).Count)"
Add-ChecklistItem $checklist "planning_exit" "Exactly four stage-now entries exist" (@($exitEntries | Where-Object { $_.category -eq "stage_now" }).Count -eq 4) "stage_now_entries=$(@($exitEntries | Where-Object { $_.category -eq "stage_now" }).Count)"
Add-ChecklistItem $checklist "planning_exit" "Exit areas were generated" (@($exitAreas).Count -ge 6) "exit_areas=$(@($exitAreas).Count)" "recommended"
Add-ChecklistItem $checklist "planning_exit" "Archive decisions were carried forward" (@($archiveDecisions).Count -eq @($artifactFamilies).Count) "archive_decisions=$(@($archiveDecisions).Count); artifact_families=$(@($artifactFamilies).Count)" "recommended"
Add-ChecklistItem $checklist "planning_exit" "Commit commands exist" (@($nextCommitCommands).Count -gt 0) "commit_commands=$(@($nextCommitCommands).Count)"
Add-ChecklistItem $checklist "planning_exit" "No forbidden paths are currently staged" ($stagedForbiddenCount -eq 0) "staged_forbidden_count=$stagedForbiddenCount"
Add-ChecklistItem $checklist "planning_exit" "No review-other paths are currently staged" ($stagedReviewOtherCount -eq 0) "staged_review_other_count=$stagedReviewOtherCount" "recommended"
Add-ChecklistItem $checklist "planning_exit" "Workspace review-other files count is zero or acceptable" ($reviewOtherCount -eq 0) "review_other_count=$reviewOtherCount" "recommended"

$planningClosureStatus = [string]$planningClosure.planning_closure_packet.status
if ($planningClosureStatus -eq "phase20_planning_closure_packet_blocked") {
    Add-Issue $issues "blocker" "planning_closure_packet_blocked" "Planning closure packet is blocked." "planning_closure"
} elseif ($planningClosureStatus -eq "phase20_planning_closure_packet_review_required_no_write") {
    Add-Issue $issues "review" "planning_closure_packet_review_required" "Planning closure packet has review items." "planning_closure"
}

if ([string]::IsNullOrWhiteSpace($currentBranch)) {
    Add-Issue $issues "blocker" "current_branch_missing" "Current branch was not detected for planning exit." "workspace"
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

[void]$sourceArtifacts.Add([ordered]@{ key="planning_closure_packet"; json_path=$planningClosurePath; sha256=Get-FileSha256 $planningClosurePath })
[void]$sourceArtifacts.Add([ordered]@{ key="planning_approval_packet"; json_path=$planningApprovalPath; sha256=Get-FileSha256 $planningApprovalPath })
[void]$sourceArtifacts.Add([ordered]@{ key="cleanup_exit_packet"; json_path=$cleanupExitPath; sha256=Get-FileSha256 $cleanupExitPath })

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

$bridgeHealthEvidence = if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }
Add-ChecklistItem $checklist "runtime" "Bridge health readable" $bridgeHealth.ok $bridgeHealthEvidence "recommended"

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
    "phase20_planning_exit_packet_ready_no_write"
} elseif ($blockerCount -eq 0) {
    "phase20_planning_exit_packet_review_required_no_write"
} else {
    "phase20_planning_exit_packet_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase22_phase20_network_transport_planning_exit_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 22 Step 13"
    purpose = "Phase 20 bridge routing network transport planning exit packet"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        phase20_network_transport_planning_exit_packet_only = $true
        planning_exit_only = $true
        planning_only = $true
        bridge_get_only = $true
        design_closure_record_created = $false
        final_approval_recorded = $false
        operator_signoff_recorded = $false
        operator_approval_recorded = $false
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
        cutover_packet_created = $false
        cutover_approval_recorded = $false
        bridge_response_captured = $false
        response_capture_record_created = $false
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
    planning_exit_packet = [ordered]@{
        status = $packetStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        current_branch = $currentBranch
        section_count = @($exitSections).Count
        entry_count = @($exitEntries).Count
        exit_area_count = @($exitAreas).Count
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
        can_record_operator_approval_now = $false
        can_record_final_approval_now = $false
        can_record_operator_signoff_now = $false
        can_create_design_closure_record_now = $false
        can_start_implementation_phase_now = $false
        packet_label = "phase22_phase20_network_transport_planning_exit_no_write"
        reason = if ($blockerCount -eq 0) {
            "Phase 22 Step 13 created a no-write planning exit packet for the Phase 20 network transport chain. It does not authorize exit records, approvals, implementation, transport, sockets, bridge POST, response capture, mutations, LACRM calls, or live writes."
        } else {
            "Phase 22 Step 13 found blockers in the Phase 20 planning exit packet. Resolve blockers before continuing planning."
        }
    }
    planning_sections = @($exitSections)
    planning_entries = @($exitEntries)
    exit_areas = @($exitAreas)
    archive_decisions = @($archiveDecisions)
    artifact_families = @($artifactFamilies)
    git_status_entries = @($gitStatusEntries)
    staged_entries = @($stagedEntries)
    planning_commands = $nextCommitCommands
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
        sections = @($exitSections).Count
        entries = @($exitEntries).Count
        exit_areas = @($exitAreas).Count
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
        "Review this planning exit packet before any Phase 22 transition or implementation-gate packet is drafted.",
        "Keep the latest packet folder in each family and only review older generated folders for manual archive actions.",
        "Use the stage-now entries as the only files to add for the Phase 22 Step 13 commit.",
        "Carry the do-not-stage entries forward as the hard commit boundary.",
        "Do not add requests, httpx, socket use, bridge POST calls, or routing write endpoints from Phase 22 Step 13.",
        "Do not call interface execution methods from Phase 22 Step 13.",
        "Do not record operator signoffs, operator approvals, final approvals, or design closure records from Phase 22 Step 13.",
        "Do not start an implementation phase from Phase 22 Step 13.",
        "Review exit-ready planning only: execution envelope, transport injection, bridge gate, response storage, cutover, and audit/rollback exit areas."
    )
}

$jsonPath = Join-Path $OutputDir "phase22_phase20_network_transport_planning_exit_packet.json"
$sectionsCsvPath = Join-Path $OutputDir "phase22_phase20_network_transport_planning_exit_packet_sections.csv"
$entriesCsvPath = Join-Path $OutputDir "phase22_phase20_network_transport_planning_exit_packet_entries.csv"
$areasCsvPath = Join-Path $OutputDir "phase22_phase20_network_transport_planning_exit_packet_exit_areas.csv"
$decisionsCsvPath = Join-Path $OutputDir "phase22_phase20_network_transport_planning_exit_packet_decisions.csv"
$familiesCsvPath = Join-Path $OutputDir "phase22_phase20_network_transport_planning_exit_packet_artifact_families.csv"
$gitStatusCsvPath = Join-Path $OutputDir "phase22_phase20_network_transport_planning_exit_packet_git_status.csv"
$stagedCsvPath = Join-Path $OutputDir "phase22_phase20_network_transport_planning_exit_packet_staged.csv"
$sourceArtifactsCsvPath = Join-Path $OutputDir "phase22_phase20_network_transport_planning_exit_packet_source_artifacts.csv"
$checklistCsvPath = Join-Path $OutputDir "phase22_phase20_network_transport_planning_exit_packet_checklist.csv"
$issuesCsvPath = Join-Path $OutputDir "phase22_phase20_network_transport_planning_exit_packet_issues.csv"
$mdPath = Join-Path $OutputDir "phase22_phase20_network_transport_planning_exit_packet.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$exitSections | Export-Csv -LiteralPath $sectionsCsvPath -NoTypeInformation -Encoding UTF8
$exitEntries | Export-Csv -LiteralPath $entriesCsvPath -NoTypeInformation -Encoding UTF8
$exitAreas | Export-Csv -LiteralPath $areasCsvPath -NoTypeInformation -Encoding UTF8
$archiveDecisions | Export-Csv -LiteralPath $decisionsCsvPath -NoTypeInformation -Encoding UTF8
$artifactFamilies | Export-Csv -LiteralPath $familiesCsvPath -NoTypeInformation -Encoding UTF8
$gitStatusEntries | Export-Csv -LiteralPath $gitStatusCsvPath -NoTypeInformation -Encoding UTF8
$stagedEntries | Export-Csv -LiteralPath $stagedCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $sourceArtifactsCsvPath -NoTypeInformation -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$sectionText = (@($exitSections) | ForEach-Object { "- $($_.section): $($_.status); $($_.summary)" }) -join "`n"
$entryText = (@($exitEntries) | ForEach-Object { "- [$($_.category)] $($_.action) $($_.item): $($_.evidence)" }) -join "`n"
$exitText = (@($exitAreas) | ForEach-Object { "- $($_.item): depends_on=$($_.depends_on); status=$($_.status)" }) -join "`n"
$decisionText = (@($archiveDecisions) | ForEach-Object { "- $($_.folder_filter): decision=$($_.decision); older_generated_folders=$($_.older_generated_folder_count); archive_order=$($_.archive_order)" }) -join "`n"
$familyText = (@($artifactFamilies) | ForEach-Object { "- $($_.folder_filter): folder_count=$($_.folder_count); older_generated_folders=$($_.older_generated_folder_count); latest=$($_.latest_folder)" }) -join "`n"
$gitStatusText = if (@($gitStatusEntries).Count -gt 0) { (@($gitStatusEntries) | ForEach-Object { "- $($_.path): category=$($_.category); should_stage=$($_.should_stage); reason=$($_.reason)" }) -join "`n" } else { "- none" }
$stagedText = if (@($stagedEntries).Count -gt 0) { (@($stagedEntries) | ForEach-Object { "- $($_.path): category=$($_.category); should_stage=$($_.should_stage); reason=$($_.reason)" }) -join "`n" } else { "- none" }
$sourceArtifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$checklistText = (@($checklist) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }
$commandText = (@($nextCommitCommands) | ForEach-Object { "- $_" }) -join "`n"

$md = @"
# Phase 22 Step 13 - Phase 20 Network Transport Planning Exit Packet

Generated: $($report.generated_at)

Source planning closure packet:

``````
$planningClosurePath
``````

## Safety

- Phase 20 network transport planning exit packet only: true
- Planning exit only: true
- Planning only: true
- Bridge GET only: true
- Design closure record created: false
- Final approval recorded: false
- Operator signoff recorded: false
- Operator approval recorded: false
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
- Cutover packet created: false
- Cutover approval recorded: false
- Bridge response captured: false
- Response capture record created: false
- Confirmation record created: false
- Environment variables set: false
- Rollback snapshot created: false
- Rollback row created: false
- Audit row created: false
- Platform DB mutation performed: false
- Bridge mutation performed: false
- LACRM call performed: false
- Live write enabled: false

## Planning exit packet

- Status: $packetStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Current branch: $currentBranch
- Sections: $(@($exitSections).Count)
- Entries: $(@($exitEntries).Count)
- Exit areas: $(@($exitAreas).Count)
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
- Can record operator approval now: false
- Can record final approval now: false
- Can record operator signoff now: false
- Can create design closure record now: false
- Can start implementation phase now: false

## Planning sections

$sectionText

## Planning entries

$entryText

## Exit areas

$exitText

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
    Write-Host "PASS | phase20_network_transport_planning_exit_packet=$OutputDir | status=$packetStatus | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
} else {
    Write-Host "CHECK | phase20_network_transport_planning_exit_packet=$OutputDir | status=$packetStatus | blockers=$blockerCount | bridge_post_called=False | execution_implementation_created=False | implementation_phase_started=False"
}

Write-Host ""
Write-Host "Planning exit packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
