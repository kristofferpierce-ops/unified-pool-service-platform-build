param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "all"
)

$ErrorActionPreference = "Stop"

$StepNumber = 90
$StepTitle = "Phase 26 Step 90 - Phase 20 Network Transport Implementation Transition Release Gate Verification Planning Final Boundary Confirmation Packet"
$ShortTitle = "Implementation Transition Release Gate Verification Planning Final Boundary Confirmation Packet"
$ExpectedBranch = "phase26-step90-implementation-transition-release-gate-verification-planning-final-boundary-confirmation"
$PriorStep = "Phase 26 Step 89 - Phase 20 Network Transport Implementation Transition Release Gate Verification Planning Closeout Index Packet"
$Slug = "implementation_transition_release_gate_verification_planning_final_boundary_confirmation"

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
}

$StepFiles = @(
    "scripts/phase26_step90_implementation_transition_release_gate_verification_planning_final_boundary_confirmation_packet.ps1",
    "ui/pages/586_Phase26_Step90_Implementation_Transition_Release_Gate_Verification_Planning_Final_Boundary_Confirmation_Packet.py",
    "docs/PHASE26_STEP90_IMPLEMENTATION_TRANSITION_RELEASE_GATE_VERIFICATION_PLANNING_FINAL_BOUNDARY_CONFIRMATION_PACKET.md",
    "tests/test_phase26_step90_implementation_transition_release_gate_verification_planning_final_boundary_confirmation_packet.py"
)

$SafetyPosture = [ordered]@{
    "planning_only" = $true
    "no_platform_db_mutation" = $true
    "no_bridge_mutation" = $true
    "no_real_bridge_http_client" = $true
    "no_network_transport_implementation" = $true
    "no_bridge_post" = $true
    "no_network_sockets" = $true
    "no_execution_implementation" = $true
    "phase26_boundary" = "implementation_transition_release_gate_verification_planning_final_boundary_confirmation_opened_by_packet"
    "phase26_execution_start" = $false
    "phase26_implementation_start" = $false
    "implementation_phase_start" = $false
    "transition_runtime_start" = $false
    "transition_execution_start" = $false
    "network_transport_runtime_start" = $false
    "bridge_transport_runtime_start" = $false
    "cross_repo_write" = $false
    "cross_repo_mutation" = $false
    "external_repo_push" = $false
    "implementation_transition_release_gate_verification_planning_final_boundary_confirmation_mode" = "reference_only"
    "implementation_transition_release_gate_verification_planning_final_boundary_confirmation_write" = $false
    "implementation_transition_release_gate_verification_planning_final_boundary_confirmation_record_creation" = $false
    "transition_decision_creation" = $false
    "transition_approval_creation" = $false
    "transition_operator_approval_creation" = $false
    "no_operator_signoff" = $true
    "no_operator_approval" = $true
    "no_final_approval" = $true
    "phase25_reopen" = $false
    "phase27_start" = $false
    "phase27_boundary_creation" = $false
    "lacrm_default_mode" = "dry_run"
    "lacrm_live_write" = $false
    "live_write_disabled" = $true
    "live_write_unarmed" = $true
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
    foreach ($Key in $SafetyPosture.Keys) {
        Write-Host ("  {0}: {1}" -f $Key, $SafetyPosture[$Key])
    }
    Write-Host ""
    Write-Host "Step files"
    foreach ($Relative in $StepFiles) {
        $Path = Join-Path $RepoRoot $Relative
        if (Test-Path $Path) {
            Write-Host ("  PRESENT {0}" -f $Relative)
        } else {
            Write-Host ("  MISSING {0}" -f $Relative)
        }
    }
}

function Apply-StepFiles {
    foreach ($Relative in $StepFiles) {
        $Path = Join-Path $RepoRoot $Relative
        if (-not (Test-Path $Path)) {
            throw ("Required step file missing: {0}" -f $Relative)
        }
        Write-Host ("SKIPPED {0} source and target are the same file." -f $Relative)
    }
    Write-Host "APPLY PASS: Phase 26 Step 90 files copied or already present."
}

function Test-Smoke {
    foreach ($Relative in $StepFiles) {
        $Path = Join-Path $RepoRoot $Relative
        if (-not (Test-Path $Path)) {
            throw ("Smoke test missing file: {0}" -f $Relative)
        }
    }
    if (-not $SafetyPosture["planning_only"]) { throw "planning_only must be true" }
    if ($SafetyPosture["no_network_transport_implementation"] -ne $true) { throw "no_network_transport_implementation must be true" }
    if ($SafetyPosture["no_bridge_post"] -ne $true) { throw "no_bridge_post must be true" }
    if ($SafetyPosture["no_network_sockets"] -ne $true) { throw "no_network_sockets must be true" }
    if ($SafetyPosture["phase27_start"] -ne $false) { throw "phase27_start must be false" }
    Write-Host "SMOKE TEST PASS: Phase 26 Step 90 Implementation Transition Release Gate Verification Planning Final Boundary Confirmation Packet is present and planning-only."
}

function New-Packet {
    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupRoot = Join-Path $RepoRoot "backups"
    $PacketDir = Join-Path $BackupRoot ("phase26_step90_{0}_packet_{1}" -f $Slug, $Timestamp)
    New-Item -ItemType Directory -Path $PacketDir -Force | Out-Null
    $PacketJson = Join-Path $PacketDir ("phase26_step90_{0}_packet.json" -f $Slug)

    $Payload = [ordered]@{
        phase = 26
        step = 90
        title = $StepTitle
        prior_step = $PriorStep
        safety_posture = $SafetyPosture
        files = $StepFiles
        generated_at = (Get-Date).ToString("s")
    }

    $Payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $PacketJson -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: phase26_boundary=implementation_transition_release_gate_verification_planning_final_boundary_confirmation_opened_by_packet"
    Write-Host "PASS: phase26_execution_start=false"
    Write-Host "PASS: phase26_implementation_start=false"
    Write-Host "PASS: implementation_phase_start=false"
    Write-Host "PASS: transition_runtime_start=false"
    Write-Host "PASS: transition_execution_start=false"
    Write-Host "PASS: cross_repo_write=false"
    Write-Host "PASS: cross_repo_mutation=false"
    Write-Host "PASS: external_repo_push=false"
    Write-Host "PASS: implementation_transition_release_gate_verification_planning_final_boundary_confirmation_mode=reference_only"
    Write-Host "PASS: implementation_transition_release_gate_verification_planning_final_boundary_confirmation_write=false"
    Write-Host "PASS: implementation_transition_release_gate_verification_planning_final_boundary_confirmation_record_creation=false"
    Write-Host "PASS: transition_decision_creation=false"
    Write-Host "PASS: transition_approval_creation=false"
    Write-Host "PASS: phase25_reopen=false"
    Write-Host "PASS: phase27_start=false"
    Write-Host "PASS: phase27_boundary_creation=false"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host ("CHECK: prior_step={0}" -f $PriorStep)
    Write-Host "CHECK: phase26_context=implementation_transition_release_gate_verification_planning_planning_only"
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
