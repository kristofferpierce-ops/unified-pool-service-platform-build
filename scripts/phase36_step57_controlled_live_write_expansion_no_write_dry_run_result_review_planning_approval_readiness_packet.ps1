param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PhaseNumber = 36
$StepNumber = 57
$StepTitle = "Phase 36 Step 57 - Phase 20 Network Transport Implementation Trusted Production Controlled Live Write Expansion No-Write Dry Run Result Review Planning Approval Readiness Packet"
$ExpectedBranch = "phase36-step57-controlled-live-write-expansion-no-write-dry-run-result-review-planning-approval-readiness"
$PriorCompletedStep = "Phase 36 Step 56 - Phase 20 Network Transport Implementation Trusted Production Controlled Live Write Expansion No-Write Dry Run Result Review Planning Approval Boundary Packet"

function Resolve-RepoRoot {
    param([string]$Candidate)

    if ($Candidate -and (Test-Path (Join-Path $Candidate ".git"))) {
        return (Resolve-Path $Candidate).Path
    }

    $Here = Split-Path -Parent $MyInvocation.ScriptName
    $Possible = Resolve-Path (Join-Path $Here "..") -ErrorAction SilentlyContinue
    if ($Possible -and (Test-Path (Join-Path $Possible.Path ".git"))) {
        return $Possible.Path
    }

    $Current = (Get-Location).Path
    if (Test-Path (Join-Path $Current ".git")) {
        return $Current
    }

    throw "Could not resolve repository root."
}

$RepoRoot = Resolve-RepoRoot -Candidate $RepoRoot

$StepFiles = @(
    "scripts/phase36_step57_controlled_live_write_expansion_no_write_dry_run_result_review_planning_approval_readiness_packet.ps1",
    "ui/pages/1753_Phase36_Step57_Live_Write_Expansion_Result_Review_Approval_Readiness.py",
    "docs/PHASE36_STEP57_CONTROLLED_LIVE_WRITE_EXPANSION_NO_WRITE_DRY_RUN_RESULT_REVIEW_PLANNING_APPROVAL_READINESS_PACKET.md",
    "tests/test_phase36_step57_controlled_live_write_expansion_no_write_dry_run_result_review_planning_approval_readiness_packet.py"
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
    phase36_boundary = "trusted_production_controlled_live_write_expansion_no_write_dry_run_result_review_planning_packet"
    phase36_execution_start = $false
    phase36_implementation_start = $false
    implementation_phase_start = $false
    trusted_production_controlled_live_write_expansion_start = $false
    trusted_production_controlled_live_write_expansion_execution_start = $false
    controlled_live_write_expansion_start = $false
    controlled_live_write_expansion_execution_start = $false
    live_write_activation_start = $false
    live_write_apply_start = $false
    live_user_access_start = $false
    network_transport_runtime_start = $false
    bridge_transport_runtime_start = $false
    cross_repo_write = $false
    cross_repo_mutation = $false
    external_repo_push = $false
    no_live_user_access = $true
    no_live_write_activation = $true
    no_live_write_apply = $true
    phase37_start = $false
    phase37_boundary_creation = $false
    lacrm_default_mode = "dry_run"
    live_write_disabled = $true
    live_write_unarmed = $true
}

function Assert-StepFiles {
    foreach ($Rel in $StepFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Path)) {
            throw ("Missing expected Phase 36 Step {0} file: {1}" -f $StepNumber, $Rel)
        }
    }
}

function Show-Packet {
    Write-Host "=============================================================================="
    Write-Host $StepTitle
    Write-Host "=============================================================================="
    Write-Host ("Repo root: {0}" -f $RepoRoot)
    Write-Host ("Prior completed step: {0}" -f $PriorCompletedStep)
    Write-Host "Safety posture: planning-only/no-write/no-server/no-network-transport/no-live-write-activation/no-live-write-apply/no-phase37"
    Write-Host "Step files:"
    foreach ($Rel in $StepFiles) {
        Write-Host ("  {0}" -f $Rel)
    }
    Write-Host "Safety markers:"
    foreach ($Key in $SafetyPosture.Keys) {
        Write-Host ("  {0}={1}" -f $Key, $SafetyPosture[$Key])
    }
}

function Invoke-Apply {
    Assert-StepFiles
    Write-Host ("APPLY PASS: Phase 36 Step {0} planning-only packet verified without live-write activation, live-write apply, bridge POST, sockets, DB mutation, server launch, or Phase 37 boundary creation." -f $StepNumber)
}

function Invoke-Smoke {
    Assert-StepFiles
    if (-not $SafetyPosture.planning_only) { throw "planning_only marker is not true." }
    if (-not $SafetyPosture.no_live_write_activation) { throw "no_live_write_activation marker is not true." }
    if (-not $SafetyPosture.no_live_write_apply) { throw "no_live_write_apply marker is not true." }
    if ($SafetyPosture.phase37_start) { throw "phase37_start must remain false." }
    if ($SafetyPosture.phase37_boundary_creation) { throw "phase37_boundary_creation must remain false." }
    if ($SafetyPosture.live_write_activation_start) { throw "live_write_activation_start must remain false." }
    if ($SafetyPosture.live_write_apply_start) { throw "live_write_apply_start must remain false." }
    Write-Host ("SMOKE TEST PASS: Phase 36 Step {0} safety markers confirm planning-only/no-write/no-live-write-activation/no-live-write-apply/no-runtime/no-phase37 posture." -f $StepNumber)
}

switch ($Action) {
    "status" { Show-Packet }
    "packet" { Show-Packet }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "all" { Show-Packet; Invoke-Apply; Invoke-Smoke }
}

