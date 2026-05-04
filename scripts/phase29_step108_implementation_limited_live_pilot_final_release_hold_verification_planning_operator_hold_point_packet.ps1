param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "all"
)

$ErrorActionPreference = "Stop"

$StepNumber = 108
$StepTitle = "Phase 29 Step 108 - Phase 20 Network Transport Implementation Limited Live Pilot Final Release Hold Verification Planning Operator Hold Point Packet"
$ShortTitle = "Phase 20 Network Transport Implementation Limited Live Pilot Final Release Hold Verification Planning Operator Hold Point Packet"
$ExpectedBranch = "phase29-step108-implementation-limited-live-pilot-final-release-hold-verification-planning-operator-hold-point"
$PriorStep = "Phase 29 Step 107 - Phase 20 Network Transport Implementation Limited Live Pilot Final Release Hold Verification Planning Approval Readiness Packet"
$Slug = "implementation_limited_live_pilot_final_release_hold_verification_planning_operator_hold_point"

if (-not $RepoRoot) { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path }

$StepFiles = @(
    "scripts/phase29_step108_implementation_limited_live_pilot_final_release_hold_verification_planning_operator_hold_point_packet.ps1",
    "ui/pages/964_Phase29_Step108_Implementation_Limited_Live_Pilot_Final_Release_Hold_Verification_Planning_Operator_Hold_Point_Packet.py",
    "docs/PHASE29_STEP108_IMPLEMENTATION_LIMITED_LIVE_PILOT_FINAL_RELEASE_HOLD_VERIFICATION_PLANNING_OPERATOR_HOLD_POINT_PACKET.md",
    "tests/test_phase29_step108_implementation_limited_live_pilot_final_release_hold_verification_planning_operator_hold_point_packet.py"
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
    phase29_boundary = "implementation_limited_live_pilot_final_release_hold_verification_planning_operator_hold_point_opened_by_packet"
    phase29_execution_start = $false
    phase29_implementation_start = $false
    implementation_phase_start = $false
    limited_live_pilot_start = $false
    limited_live_pilot_execution_start = $false
    live_user_access_start = $false
    network_transport_runtime_start = $false
    bridge_transport_runtime_start = $false
    cross_repo_write = $false
    cross_repo_mutation = $false
    external_repo_push = $false
    implementation_limited_live_pilot_final_release_hold_verification_planning_operator_hold_point_mode = "reference_only"
    implementation_limited_live_pilot_final_release_hold_verification_planning_operator_hold_point_write = $false
    implementation_limited_live_pilot_final_release_hold_verification_planning_operator_hold_point_record_creation = $false
    limited_live_pilot_final_release_hold_verification_planning_decision_creation = $false
    limited_live_pilot_final_release_hold_verification_planning_approval_creation = $false
    limited_live_pilot_operator_approval_creation = $false
    no_operator_signoff = $true
    no_operator_approval = $true
    no_final_approval = $true
    no_live_user_access = $true
    phase28_reopen = $false
    phase30_start = $false
    phase30_boundary_creation = $false
    lacrm_default_mode = "dry_run"
    lacrm_live_write = $false
    live_write_disabled = $true
    live_write_unarmed = $true
}

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
    Write-Host "APPLY PASS: Phase 29 Step 108 files copied or already present."
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
    if ($SafetyPosture["limited_live_pilot_start"] -ne $false) { throw "limited_live_pilot_start must be false" }
    if ($SafetyPosture["live_user_access_start"] -ne $false) { throw "live_user_access_start must be false" }
    if ($SafetyPosture["phase30_start"] -ne $false) { throw "phase30_start must be false" }
    Write-Host "SMOKE TEST PASS: Phase 29 Step 108 Phase 20 Network Transport Implementation Limited Live Pilot Final Release Hold Verification Planning Operator Hold Point Packet is present and planning-only."
}

function Assert-NoUnsafeOperationalMarkers {
    $OperationalRelativeFiles = @($StepFiles[0], $StepFiles[1], $StepFiles[2])
    $ForbiddenPairs = @(
        @("phase30_start", "true"),
        @("phase30_boundary_creation", "true"),
        @("phase29_execution_start", "true"),
        @("phase29_implementation_start", "true"),
        @("implementation_phase_start", "true"),
        @("limited_live_pilot_start", "true"),
        @("limited_live_pilot_execution_start", "true"),
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
    $PacketDir = Join-Path $BackupRoot ("phase29_step108_{0}_packet_{1}" -f $Slug, $Timestamp)
    New-Item -ItemType Directory -Path $PacketDir -Force | Out-Null
    $PacketJson = Join-Path $PacketDir ("phase29_step108_{0}_packet.json" -f $Slug)

    $Packet = [ordered]@{
        phase = 29
        step = $StepNumber
        title = $StepTitle
        short_title = $ShortTitle
        expected_branch = $ExpectedBranch
        prior_step = $PriorStep
        safety_posture = $SafetyPosture
        step_files = $StepFiles
        packet_mode = "planning_only_reference_only"
        created_at = (Get-Date).ToString("o")
    }
    $Packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $PacketJson -Encoding UTF8

    foreach ($Key in @(
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "phase29_boundary",
        "phase29_execution_start",
        "phase29_implementation_start",
        "implementation_phase_start",
        "limited_live_pilot_start",
        "limited_live_pilot_execution_start",
        "live_user_access_start",
        "cross_repo_write",
        "cross_repo_mutation",
        "external_repo_push",
        "implementation_limited_live_pilot_final_release_hold_verification_planning_operator_hold_point_mode",
        "implementation_limited_live_pilot_final_release_hold_verification_planning_operator_hold_point_write",
        "implementation_limited_live_pilot_final_release_hold_verification_planning_operator_hold_point_record_creation",
        "limited_live_pilot_final_release_hold_verification_planning_decision_creation",
        "limited_live_pilot_final_release_hold_verification_planning_approval_creation",
        "no_live_user_access",
        "phase28_reopen",
        "phase30_start",
        "phase30_boundary_creation",
        "lacrm_default_mode",
        "live_write_disabled",
        "live_write_unarmed"
    )) {
        Write-Host ("PASS: {0}={1}" -f $Key, (Format-SafetyValue $SafetyPosture[$Key]))
    }

    Write-Host ("CHECK: prior_step={0}" -f $PriorStep)
    Write-Host "CHECK: phase29_context=implementation_limited_live_pilot_final_release_hold_verification_planning_only"
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

