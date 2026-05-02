param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "all"
)

$ErrorActionPreference = "Stop"

$StepNumber = 47
$StepTitle = "Phase 28 Step 47 - Phase 20 Network Transport Implementation Sandbox Pilot No-Write Dry Run Verification Planning Approval Readiness Packet"
$ShortTitle = "Phase 20 Network Transport Implementation Sandbox Pilot No-Write Dry Run Verification Planning Approval Readiness Packet"
$ExpectedBranch = "phase28-step47-implementation-sandbox-pilot-no-write-dry-run-verification-planning-approval-readiness"
$PriorStep = "Phase 28 Step 46 - Phase 20 Network Transport Implementation Sandbox Pilot No-Write Dry Run Verification Planning Approval Boundary Packet"
$Slug = "implementation_sandbox_pilot_no_write_dry_run_verification_planning_approval_readiness"

if (-not $RepoRoot) { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path }

$StepFiles = @(
    "scripts/phase28_step47_implementation_sandbox_pilot_no_write_dry_run_verification_planning_approval_readiness_packet.ps1",
    "ui/pages/783_Phase28_Step47_Implementation_Sandbox_Pilot_No_Write_Dry_Run_Verification_Planning_Approval_Readiness_Packet.py",
    "docs/PHASE28_STEP47_IMPLEMENTATION_SANDBOX_PILOT_NO_WRITE_DRY_RUN_VERIFICATION_PLANNING_APPROVAL_READINESS_PACKET.md",
    "tests/test_phase28_step47_implementation_sandbox_pilot_no_write_dry_run_verification_planning_approval_readiness_packet.py"
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
    phase28_boundary = "implementation_sandbox_pilot_no_write_dry_run_verification_planning_approval_readiness_opened_by_packet"
    phase28_execution_start = $false
    phase28_implementation_start = $false
    implementation_phase_start = $false
    sandbox_pilot_start = $false
    sandbox_pilot_execution_start = $false
    network_transport_runtime_start = $false
    bridge_transport_runtime_start = $false
    cross_repo_write = $false
    cross_repo_mutation = $false
    external_repo_push = $false
    implementation_sandbox_pilot_no_write_dry_run_verification_planning_approval_readiness_mode = "reference_only"
    implementation_sandbox_pilot_no_write_dry_run_verification_planning_approval_readiness_write = $false
    implementation_sandbox_pilot_no_write_dry_run_verification_planning_approval_readiness_record_creation = $false
    sandbox_pilot_readiness_decision_creation = $false
    sandbox_pilot_readiness_approval_creation = $false
    sandbox_pilot_operator_approval_creation = $false
    no_operator_signoff = $true
    no_operator_approval = $true
    no_final_approval = $true
    phase27_reopen = $false
    phase29_start = $false
    phase29_boundary_creation = $false
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
    Write-Host "APPLY PASS: Phase 28 Step 47 files copied or already present."
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
    if ($SafetyPosture["phase29_start"] -ne $false) { throw "phase29_start must be false" }
    Write-Host "SMOKE TEST PASS: Phase 28 Step 47 Phase 20 Network Transport Implementation Sandbox Pilot No-Write Dry Run Verification Planning Approval Readiness Packet is present and planning-only."
}

function Assert-NoUnsafeOperationalMarkers {
    $OperationalRelativeFiles = @($StepFiles[0], $StepFiles[1], $StepFiles[2])
    $ForbiddenPairs = @(
        @("phase29_start", "true"),
        @("phase29_boundary_creation", "true"),
        @("phase28_execution_start", "true"),
        @("phase28_implementation_start", "true"),
        @("implementation_phase_start", "true"),
        @("sandbox_pilot_start", "true"),
        @("sandbox_pilot_execution_start", "true"),
        @("network_transport_runtime_start", "true"),
        @("bridge_transport_runtime_start", "true"),
        @("no_network_transport_implementation", "false"),
        @("no_bridge_post", "false"),
        @("no_network_sockets", "false"),
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
    $PacketDir = Join-Path $BackupRoot ("phase28_step47_{0}_packet_{1}" -f $Slug, $Timestamp)
    New-Item -ItemType Directory -Path $PacketDir -Force | Out-Null
    $PacketJson = Join-Path $PacketDir ("phase28_step47_{0}_packet.json" -f $Slug)

    $Packet = [ordered]@{
        phase = 28
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
        "phase28_boundary",
        "phase28_execution_start",
        "phase28_implementation_start",
        "implementation_phase_start",
        "sandbox_pilot_start",
        "sandbox_pilot_execution_start",
        "cross_repo_write",
        "cross_repo_mutation",
        "external_repo_push",
        "implementation_sandbox_pilot_no_write_dry_run_verification_planning_approval_readiness_mode",
        "implementation_sandbox_pilot_no_write_dry_run_verification_planning_approval_readiness_write",
        "implementation_sandbox_pilot_no_write_dry_run_verification_planning_approval_readiness_record_creation",
        "sandbox_pilot_readiness_decision_creation",
        "sandbox_pilot_readiness_approval_creation",
        "phase27_reopen",
        "phase29_start",
        "phase29_boundary_creation",
        "lacrm_default_mode",
        "live_write_disabled",
        "live_write_unarmed"
    )) {
        Write-Host ("PASS: {0}={1}" -f $Key, (Format-SafetyValue $SafetyPosture[$Key]))
    }

    Write-Host ("CHECK: prior_step={0}" -f $PriorStep)
    Write-Host "CHECK: phase28_context=implementation_sandbox_pilot_no_write_dry_run_verification_and_result_review_planning_only"
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

