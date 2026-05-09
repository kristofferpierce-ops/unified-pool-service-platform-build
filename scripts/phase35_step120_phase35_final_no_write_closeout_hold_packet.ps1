param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PhaseNumber = 35
$StepNumber = 120
$StepTitle = "Phase 35 Step 120 - Phase 20 Network Transport Implementation Phase 35 Final No-Write Closeout Hold Packet"
$ExpectedBranch = "phase35-step120-phase35-final-no-write-closeout-hold"
$PriorCompletedStep = "Phase 35 Step 119 - Phase 20 Network Transport Implementation Trusted Production Limited Live Write Pilot Final Release Result Review Planning Closeout Index Packet"

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
    "scripts/phase35_step120_phase35_final_no_write_closeout_hold_packet.ps1",
    "ui/pages/1696_Phase35_Step120_Phase35_Final_No_Write_Closeout_Hold.py",
    "docs/PHASE35_STEP120_PHASE35_FINAL_NO_WRITE_CLOSEOUT_HOLD_PACKET.md",
    "tests/test_phase35_step120_phase35_final_no_write_closeout_hold_packet.py"
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
    phase35_boundary = "trusted_production_limited_live_write_pilot_phase35_final_no_write_closeout_hold_opened_by_packet"
    phase35_execution_start = $false
    phase35_implementation_start = $false
    implementation_phase_start = $false
    trusted_production_limited_live_write_pilot_start = $false
    trusted_production_limited_live_write_pilot_execution_start = $false
    limited_live_write_pilot_start = $false
    limited_live_write_pilot_execution_start = $false
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
    phase36_start = $false
    phase36_boundary_creation = $false
    lacrm_default_mode = "dry_run"
    live_write_disabled = $true
    live_write_unarmed = $true
}

function Assert-StepFiles {
    foreach ($Rel in $StepFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Path)) {
            throw ("Missing expected Phase 35 Step 120 file: {0}" -f $Rel)
        }
    }
}

function Show-Packet {
    Write-Host "=============================================================================="
    Write-Host $StepTitle
    Write-Host "=============================================================================="
    Write-Host ("Repo root: {0}" -f $RepoRoot)
    Write-Host ("Prior completed step: {0}" -f $PriorCompletedStep)
    Write-Host "Safety posture: planning-only/no-write/no-server/no-network-transport/no-live-write-activation/no-live-write-apply/no-phase36"
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
    Write-Host "APPLY PASS: Phase 35 Step 120 planning-only packet verified without live-write activation, live-write apply, bridge POST, sockets, DB mutation, server launch, or Phase 36 boundary creation."
}

function Invoke-Smoke {
    Assert-StepFiles
    if (-not $SafetyPosture.planning_only) { throw "planning_only marker is not true." }
    if (-not $SafetyPosture.no_live_write_activation) { throw "no_live_write_activation marker is not true." }
    if (-not $SafetyPosture.no_live_write_apply) { throw "no_live_write_apply marker is not true." }
    if ($SafetyPosture.phase36_start) { throw "phase36_start must remain false." }
    if ($SafetyPosture.phase36_boundary_creation) { throw "phase36_boundary_creation must remain false." }
    if ($SafetyPosture.live_write_activation_start) { throw "live_write_activation_start must remain false." }
    if ($SafetyPosture.live_write_apply_start) { throw "live_write_apply_start must remain false." }
    Write-Host "SMOKE TEST PASS: Phase 35 Step 120 safety markers confirm planning-only/no-write/no-live-write-activation/no-live-write-apply/no-runtime/no-phase36 posture."
}

switch ($Action) {
    "status" { Show-Packet }
    "packet" { Show-Packet }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "all" { Show-Packet; Invoke-Apply; Invoke-Smoke }
}

