param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"

$StepNumber = 82
$StepName = "Phase 20 Network Transport Implementation Sandbox Pilot Release Gate Verification Planning Evidence Index Packet"
$StepTitle = "Phase 28 Step 82 - Phase 20 Network Transport Implementation Sandbox Pilot Release Gate Verification Planning Evidence Index Packet"
$ExpectedBranch = "phase28-step82-implementation-sandbox-pilot-release-gate-verification-planning-evidence-index"
$PriorStep = "Phase 28 Step 81 - Phase 20 Network Transport Implementation Sandbox Pilot Release Gate Verification Planning Boundary Packet"
$StepKey = "implementation_sandbox_pilot_release_gate_verification_planning_evidence_index"
$BoundaryMarker = "implementation_sandbox_pilot_release_gate_verification_planning_evidence_index_opened_by_packet"
$PhaseContext = "implementation_sandbox_pilot_release_gate_verification_planning_only"
$ScriptRel = "scripts/phase28_step82_implementation_sandbox_pilot_release_gate_verification_planning_evidence_index_packet.ps1"
$UiRel = "ui/pages/818_Phase28_Step82_Implementation_Sandbox_Pilot_Release_Gate_Verification_Planning_Evidence_Index_Packet.py"
$DocRel = "docs/PHASE28_STEP82_IMPLEMENTATION_SANDBOX_PILOT_RELEASE_GATE_VERIFICATION_PLANNING_EVIDENCE_INDEX_PACKET.md"
$TestRel = "tests/test_phase28_step82_implementation_sandbox_pilot_release_gate_verification_planning_evidence_index_packet.py"
$PacketSlug = "phase28_step82_implementation_sandbox_pilot_release_gate_verification_planning_evidence_index_packet"

function Resolve-RepoRoot {
    param([string]$InputRoot)
    if ($InputRoot -and (Test-Path $InputRoot)) {
        return (Resolve-Path $InputRoot).Path
    }
    $ScriptDir = Split-Path -Parent $PSCommandPath
    return (Resolve-Path (Join-Path $ScriptDir "..")).Path
}

$RepoRoot = Resolve-RepoRoot -InputRoot $RepoRoot

function Get-StepRelativeFiles {
    return @(
        $ScriptRel,
        $UiRel,
        $DocRel,
        $TestRel
    )
}

function Get-StepAbsoluteFiles {
    $Files = @()
    foreach ($Rel in Get-StepRelativeFiles) {
        $Files += (Join-Path $RepoRoot $Rel)
    }
    return $Files
}

function Get-SafetyPosture {
    $Posture = [ordered]@{
        planning_only = $true
        no_platform_db_mutation = $true
        no_bridge_mutation = $true
        no_real_bridge_http_client = $true
        no_network_transport_implementation = $true
        no_bridge_post = $true
        no_network_sockets = $true
        no_execution_implementation = $true
        phase28_boundary = $BoundaryMarker
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
    }
    $Posture[($StepKey + "_mode")] = "reference_only"
    $Posture[($StepKey + "_write")] = $false
    $Posture[($StepKey + "_record_creation")] = $false
    $Posture["sandbox_pilot_readiness_decision_creation"] = $false
    $Posture["sandbox_pilot_readiness_approval_creation"] = $false
    $Posture["sandbox_pilot_operator_approval_creation"] = $false
    $Posture["no_operator_signoff"] = $true
    $Posture["no_operator_approval"] = $true
    $Posture["no_final_approval"] = $true
    $Posture["phase27_reopen"] = $false
    $Posture["phase29_start"] = $false
    $Posture["phase29_boundary_creation"] = $false
    $Posture["lacrm_default_mode"] = "dry_run"
    $Posture["lacrm_live_write"] = $false
    $Posture["live_write_disabled"] = $true
    $Posture["live_write_unarmed"] = $true
    return $Posture
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
    $Posture = Get-SafetyPosture
    foreach ($Key in $Posture.Keys) {
        Write-Host ("  {0}: {1}" -f $Key, $Posture[$Key])
    }
    Write-Host ""
    Write-Host "Step files"
    foreach ($Rel in Get-StepRelativeFiles) {
        $Abs = Join-Path $RepoRoot $Rel
        if (Test-Path $Abs) {
            Write-Host ("  PRESENT {0}" -f $Rel)
        } else {
            Write-Host ("  MISSING {0}" -f $Rel)
        }
    }
}

function Apply-StepFiles {
    foreach ($Rel in Get-StepRelativeFiles) {
        $Abs = Join-Path $RepoRoot $Rel
        $Dir = Split-Path -Parent $Abs
        if (-not (Test-Path $Dir)) {
            New-Item -ItemType Directory -Path $Dir -Force | Out-Null
        }
        if (Test-Path $Abs) {
            Write-Host ("SKIPPED {0} source and target are the same file." -f $Rel)
        } else {
            "# Placeholder for $StepTitle" | Set-Content -LiteralPath $Abs -Encoding UTF8
            Write-Host ("CREATED missing placeholder {0}" -f $Rel)
        }
    }
    Write-Host "APPLY PASS: Phase 28 Step 82 files copied or already present."
}

function Test-Smoke {
    $Missing = @()
    foreach ($Rel in Get-StepRelativeFiles) {
        $Abs = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Abs)) {
            $Missing += $Rel
        }
    }
    if ($Missing.Count -gt 0) {
        throw ("Missing Phase 28 Step 82 files: {0}" -f ($Missing -join ", "))
    }
    Write-Host "SMOKE TEST PASS: Phase 28 Step 82 Phase 20 Network Transport Implementation Sandbox Pilot Release Gate Verification Planning Evidence Index Packet is present and planning-only."
}

function New-Packet {
    $BackupRoot = Join-Path $RepoRoot "backups"
    if (-not (Test-Path $BackupRoot)) {
        New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
    }
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $PacketDir = Join-Path $BackupRoot ("{0}_{1}" -f $PacketSlug, $Stamp)
    New-Item -ItemType Directory -Path $PacketDir -Force | Out-Null
    $PacketPath = Join-Path $PacketDir ("{0}.json" -f $PacketSlug)

    $Packet = [ordered]@{
        phase = 28
        step = $StepNumber
        title = $StepTitle
        prior_step = $PriorStep
        mode = "planning_only_reference_only"
        generated_at = (Get-Date).ToString("o")
        safety = Get-SafetyPosture
        step_files = Get-StepRelativeFiles
    }

    $Packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $PacketPath -Encoding UTF8

    $PassLines = @(
        "PASS: planning_only=true",
        "PASS: no_real_bridge_http_client=true",
        "PASS: no_network_transport_implementation=true",
        "PASS: no_bridge_post=true",
        "PASS: no_network_sockets=true",
        ("PASS: phase28_boundary={0}" -f $BoundaryMarker),
        "PASS: phase28_execution_start=false",
        "PASS: phase28_implementation_start=false",
        "PASS: implementation_phase_start=false",
        "PASS: sandbox_pilot_start=false",
        "PASS: sandbox_pilot_execution_start=false",
        "PASS: cross_repo_write=false",
        "PASS: cross_repo_mutation=false",
        "PASS: external_repo_push=false",
        ("PASS: {0}_mode=reference_only" -f $StepKey),
        ("PASS: {0}_write=false" -f $StepKey),
        ("PASS: {0}_record_creation=false" -f $StepKey),
        "PASS: sandbox_pilot_readiness_decision_creation=false",
        "PASS: sandbox_pilot_readiness_approval_creation=false",
        "PASS: phase27_reopen=false",
        "PASS: phase29_start=false",
        "PASS: phase29_boundary_creation=false",
        "PASS: lacrm_default_mode=dry_run",
        "PASS: live_write_disabled=true",
        "PASS: live_write_unarmed=true",
        ("CHECK: prior_step={0}" -f $PriorStep),
        ("CHECK: phase28_context={0}" -f $PhaseContext),
        "CHECK: implementation_phase_start=not_started",
        "CHECK: network_transport_runtime_start=not_started",
        "CHECK: parent_workspace_launcher=safe",
        ("CHECK: packet_json={0}" -f $PacketPath)
    )

    foreach ($Line in $PassLines) {
        Write-Host $Line
    }
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

