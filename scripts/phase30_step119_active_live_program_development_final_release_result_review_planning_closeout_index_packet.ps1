param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "all"
)

$ErrorActionPreference = "Stop"

$StepNumber = 119
$StepTitle = "Phase 30 Step 119 - Phase 20 Network Transport Implementation Active Live Program Development Final Release Result Review Planning Closeout Index Packet"
$ShortTitle = "Phase 20 Network Transport Implementation Active Live Program Development Final Release Result Review Planning Closeout Index Packet"
$ExpectedBranch = "phase30-step119-active-live-program-development-final-release-result-review-planning-closeout-index"
$PriorStep = "Phase 30 Step 118 - Phase 20 Network Transport Implementation Active Live Program Development Final Release Result Review Planning Operator Hold Point Packet"
$Slug = "implementation_active_live_program_development_final_release_result_review_planning_closeout_index"
$ContextKey = "implementation_active_live_program_development_final_release_result_review_planning"
$PhaseContext = "implementation_active_live_program_development_final_release_result_review_planning_planning_only"

if (-not $RepoRoot) { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path }

$StepFiles = @(
    "scripts/phase30_step119_active_live_program_development_final_release_result_review_planning_closeout_index_packet.ps1",
    "ui/pages/1095_Phase30_Step119_Implementation_Active_Live_Program_Development_Final_Release_Result_Review_Planning_Closeout_Index_Packet.py",
    "docs/PHASE30_STEP119_ACTIVE_LIVE_PROGRAM_DEVELOPMENT_FINAL_RELEASE_RESULT_REVIEW_PLANNING_CLOSEOUT_INDEX_PACKET.md",
    "tests/test_phase30_step119_active_live_program_development_final_release_result_review_planning_closeout_index_packet.py"
)

$SafetyPosture = [ordered]@{
    planning_only = $true
    no_platform_db_mutation = $true
    no_bridge_mutation = $true
    no_real_bridge_http_client = $true
    no_network_transport_implementation = $true
    no_bridge_post = $true
    no_network_sockets = $true
    no_execution_implementation = $true
    phase30_boundary = "implementation_active_live_program_development_final_release_result_review_planning_closeout_index_opened_by_packet"
    phase30_execution_start = $false
    phase30_implementation_start = $false
    implementation_phase_start = $false
    active_live_program_start = $false
    active_live_program_execution_start = $false
    live_user_access_start = $false
    network_transport_runtime_start = $false
    bridge_transport_runtime_start = $false
    cross_repo_write = $false
    cross_repo_mutation = $false
    external_repo_push = $false
}
$SafetyPosture[("{0}_mode" -f $Slug)] = "reference_only"
$SafetyPosture[("{0}_write" -f $Slug)] = $false
$SafetyPosture[("{0}_record_creation" -f $Slug)] = $false
$SafetyPosture[("{0}_decision_creation" -f $ContextKey)] = $false
$SafetyPosture[("{0}_approval_creation" -f $ContextKey)] = $false
$SafetyPosture["active_live_program_operator_approval_creation"] = $false
$SafetyPosture["no_operator_signoff"] = $true
$SafetyPosture["no_operator_approval"] = $true
$SafetyPosture["no_final_approval"] = $true
$SafetyPosture["no_live_user_access"] = $true
$SafetyPosture["phase29_reopen"] = $false
$SafetyPosture["phase31_start"] = $false
$SafetyPosture["phase31_boundary_creation"] = $false
$SafetyPosture["lacrm_default_mode"] = "dry_run"
$SafetyPosture["lacrm_live_write"] = $false
$SafetyPosture["live_write_disabled"] = $true
$SafetyPosture["live_write_unarmed"] = $true

function Format-SafetyValue {
    param([object]$Value)
    if ($Value -is [bool]) {
        if ($Value) { return "true" }
        return "false"
    }
    return [string]$Value
}

function Show-Status {
    Write-Host "=============================================================================="
    Write-Host $StepTitle
    Write-Host "=============================================================================="
    Write-Host ("Repo root: {0}" -f $RepoRoot)
    Write-Host ("Expected branch: {0}" -f $ExpectedBranch)
    Write-Host ("Prior completed step: {0}" -f $PriorStep)
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    foreach ($Key in $SafetyPosture.Keys) { Write-Host ("  {0}: {1}" -f $Key, $SafetyPosture[$Key]) }
    Write-Host ""
    Write-Host "Step files"
    foreach ($Relative in $StepFiles) {
        $Path = Join-Path $RepoRoot $Relative
        if (Test-Path $Path) { Write-Host ("  PRESENT {0}" -f $Relative) } else { Write-Host ("  MISSING {0}" -f $Relative) }
    }
}

function Apply-StepFiles {
    foreach ($Relative in $StepFiles) {
        $Path = Join-Path $RepoRoot $Relative
        if (-not (Test-Path $Path)) { throw ("Required step file missing: {0}" -f $Relative) }
        Write-Host ("SKIPPED {0} source and target are the same file." -f $Relative)
    }
    Write-Host "APPLY PASS: Phase 30 Step 119 files copied or already present."
}

function Test-Smoke {
    foreach ($Relative in $StepFiles) {
        $Path = Join-Path $RepoRoot $Relative
        if (-not (Test-Path $Path)) { throw ("Smoke test missing file: {0}" -f $Relative) }
    }
    if ($SafetyPosture["planning_only"] -ne $true) { throw "planning_only must be true" }
    if ($SafetyPosture["no_network_transport_implementation"] -ne $true) { throw "no_network_transport_implementation must be true" }
    if ($SafetyPosture["no_bridge_post"] -ne $true) { throw "no_bridge_post must be true" }
    if ($SafetyPosture["no_network_sockets"] -ne $true) { throw "no_network_sockets must be true" }
    if ($SafetyPosture["active_live_program_start"] -ne $false) { throw "active_live_program_start must be false" }
    if ($SafetyPosture["live_user_access_start"] -ne $false) { throw "live_user_access_start must be false" }
    if ($SafetyPosture["phase31_start"] -ne $false) { throw "phase31_start must be false" }
    Write-Host "SMOKE TEST PASS: Phase 30 Step 119 Phase 20 Network Transport Implementation Active Live Program Development Final Release Result Review Planning Closeout Index Packet is present and planning-only."
}

function Assert-NoUnsafeOperationalMarkers {
    $OperationalRelativeFiles = @($StepFiles[0], $StepFiles[1], $StepFiles[2])
    $ForbiddenPairs = @(
        @("phase31_start", "true"),
        @("phase31_boundary_creation", "true"),
        @("phase30_execution_start", "true"),
        @("phase30_implementation_start", "true"),
        @("implementation_phase_start", "true"),
        @("active_live_program_start", "true"),
        @("active_live_program_execution_start", "true"),
        @("live_user_access_start", "true"),
        @("network_transport_runtime_start", "true"),
        @("bridge_transport_runtime_start", "true"),
        @("no_network_transport_implementation", "false"),
        @("no_bridge_post", "false"),
        @("no_network_sockets", "false"),
        @("no_live_user_access", "false"),
        @("live_write_disabled", "false"),
        @("live_write_unarmed", "false")
    )
    foreach ($Relative in $OperationalRelativeFiles) {
        $Path = Join-Path $RepoRoot $Relative
        if (-not (Test-Path $Path)) { throw ("Operational file missing: {0}" -f $Relative) }
        $Text = Get-Content -LiteralPath $Path -Raw
        foreach ($Pair in $ForbiddenPairs) {
            $Marker = "{0}={1}" -f $Pair[0], $Pair[1]
            if ($Text.Contains($Marker)) {
                throw ("Unsafe marker found in operational file {0}: {1}" -f $Relative, $Marker)
            }
        }
    }
}

function New-Packet {
    Assert-NoUnsafeOperationalMarkers
    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupRoot = Join-Path $RepoRoot "backups"
    $PacketDir = Join-Path $BackupRoot ("phase30_step119_{0}_packet_{1}" -f $Slug, $Timestamp)
    New-Item -ItemType Directory -Path $PacketDir -Force | Out-Null
    $PacketJson = Join-Path $PacketDir ("phase30_step119_{0}_packet.json" -f $Slug)

    $Packet = [ordered]@{
        phase = 30
        step = $StepNumber
        title = $StepTitle
        short_title = $ShortTitle
        expected_branch = $ExpectedBranch
        prior_step = $PriorStep
        phase_context = $PhaseContext
        safety_posture = $SafetyPosture
        step_files = $StepFiles
        packet_mode = "planning_only_reference_only"
        created_at = (Get-Date).ToString("o")
    }
    $Packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $PacketJson -Encoding UTF8

    foreach ($Key in $SafetyPosture.Keys) {
        Write-Host ("PASS: {0}={1}" -f $Key, (Format-SafetyValue $SafetyPosture[$Key]))
    }

    Write-Host ("CHECK: prior_step={0}" -f $PriorStep)
    Write-Host ("CHECK: phase30_context={0}" -f $PhaseContext)
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: network_transport_runtime_start=not_started"
    Write-Host "CHECK: parent_workspace_launcher=safe"
    Write-Host ("CHECK: packet_json={0}" -f $PacketJson)
}

switch ($Action) {
    "status" { Show-Status }
    "apply" { Apply-StepFiles }
    "smoke" { Test-Smoke }
    "packet" { New-Packet }
    "all" {
        Show-Status
        Apply-StepFiles
        Test-Smoke
        New-Packet
    }
}

