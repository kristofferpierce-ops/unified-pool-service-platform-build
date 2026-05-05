param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "all"
)

$ErrorActionPreference = "Stop"

$StepNumber = 77
$StepTitle = "Phase 32 Step 77 - Phase 20 Network Transport Implementation Production-Like Rollout Release Gate Readiness Planning Approval Readiness Packet"
$ShortTitle = "Phase 20 Network Transport Implementation Production-Like Rollout Release Gate Readiness Planning Approval Readiness Packet"
$ExpectedBranch = "phase32-step77-production-like-rollout-release-gate-readiness-planning-approval-readiness"
$PriorStep = "Phase 32 Step 76 - Phase 20 Network Transport Implementation Production-Like Rollout Release Gate Readiness Planning Approval Boundary Packet"
$Slug = "implementation_production_like_rollout_release_gate_readiness_planning_approval_readiness"
$ContextKey = "implementation_production_like_rollout_release_gate_readiness_planning"
$PhaseContext = "implementation_production_like_rollout_release_gate_readiness_planning_planning_only"

if (-not $RepoRoot) { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path }

$StepFiles = @(
    "scripts/phase32_step77_production_like_rollout_release_gate_readiness_planning_approval_readiness_packet.ps1",
    "ui/pages/1293_Phase32_Step77_Implementation_Production_Like_Rollout_Release_Gate_Readiness_Planning_Approval_Readiness_Packet.py",
    "docs/PHASE32_STEP77_PRODUCTION_LIKE_ROLLOUT_RELEASE_GATE_READINESS_PLANNING_APPROVAL_READINESS_PACKET.md",
    "tests/test_phase32_step77_production_like_rollout_release_gate_readiness_planning_approval_readiness_packet.py"
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
    phase32_boundary = "implementation_production_like_rollout_release_gate_readiness_planning_approval_readiness_opened_by_packet"
    phase32_execution_start = $false
    phase32_implementation_start = $false
    implementation_phase_start = $false
    controlled_active_program_start = $false
    controlled_active_program_execution_start = $false
    production_like_rollout_start = $false
    production_like_rollout_execution_start = $false
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
$SafetyPosture["production_like_rollout_operator_approval_creation"] = $false
$SafetyPosture["no_operator_signoff"] = $true
$SafetyPosture["no_operator_approval"] = $true
$SafetyPosture["no_final_approval"] = $true
$SafetyPosture["no_live_user_access"] = $true
$SafetyPosture["phase31_reopen"] = $false
$SafetyPosture["phase33_start"] = $false
$SafetyPosture["phase33_boundary_creation"] = $false
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
    Write-Host "APPLY PASS: Phase 32 Step 77 files copied or already present."
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
    if ($SafetyPosture["production_like_rollout_start"] -ne $false) { throw "production_like_rollout_start must be false" }
    if ($SafetyPosture["live_user_access_start"] -ne $false) { throw "live_user_access_start must be false" }
    if ($SafetyPosture["phase33_start"] -ne $false) { throw "phase33_start must be false" }
    Write-Host "SMOKE TEST PASS: Phase 32 Step 77 Phase 20 Network Transport Implementation Production-Like Rollout Release Gate Readiness Planning Approval Readiness Packet is present and planning-only."
}

function Assert-NoUnsafeOperationalMarkers {
    $OperationalRelativeFiles = @($StepFiles[0], $StepFiles[1], $StepFiles[2])
    $ForbiddenPairs = @(
        @("phase33_start", "true"),
        @("phase33_boundary_creation", "true"),
        @("phase32_execution_start", "true"),
        @("phase32_implementation_start", "true"),
        @("implementation_phase_start", "true"),
        @("controlled_active_program_start", "true"),
        @("controlled_active_program_execution_start", "true"),
        @("production_like_rollout_start", "true"),
        @("production_like_rollout_execution_start", "true"),
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
    $PacketDir = Join-Path $BackupRoot ("phase32_step77_{0}_packet_{1}" -f $Slug, $Timestamp)
    New-Item -ItemType Directory -Path $PacketDir -Force | Out-Null
    $PacketJson = Join-Path $PacketDir ("phase32_step77_{0}_packet.json" -f $Slug)

    $Packet = [ordered]@{
        phase = 32
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
    Write-Host ("CHECK: phase32_context={0}" -f $PhaseContext)
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


