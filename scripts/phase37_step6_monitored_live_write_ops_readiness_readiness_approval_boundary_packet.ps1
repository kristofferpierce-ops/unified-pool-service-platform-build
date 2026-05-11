param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PhaseNumber = 37
$StepNumber = 6
$StepTitle = "Phase 37 Step 6 - Phase 20 Network Transport Implementation Trusted Production Monitored Live Write Operations Readiness Approval Boundary Packet"
$PriorCompletedStep = "Phase 37 Step 5 - Phase 20 Network Transport Implementation Trusted Production Monitored Live Write Operations Readiness Safety Disposition Review Packet"

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
    "scripts/phase37_step6_monitored_live_write_ops_readiness_readiness_approval_boundary_packet.ps1",
    "ui/pages/1822_Phase37_Step6_Monitored_Live_Write_Ops_Readiness_Approval_Boundary.py",
    "docs/PHASE37_STEP6_MONITORED_LIVE_WRITE_OPS_READINESS_READINESS_APPROVAL_BOUNDARY_PACKET.md",
    "tests/test_phase37_step6_monitored_live_write_ops_readiness_readiness_approval_boundary_packet.py"
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
    phase37_boundary = "trusted_production_monitored_live_write_operations_readiness_approval_boundary_opened_by_packet"
    phase37_execution_start = $false
    phase37_implementation_start = $false
    implementation_phase_start = $false
    trusted_production_monitored_live_write_operations_start = $false
    trusted_production_monitored_live_write_operations_execution_start = $false
    monitored_live_write_operations_start = $false
    monitored_live_write_operations_execution_start = $false
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
    phase38_start = $false
    phase38_boundary_creation = $false
    lacrm_default_mode = "dry_run"
    live_write_disabled = $true
    live_write_unarmed = $true
}

function Assert-StepFiles {
    foreach ($Rel in $StepFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Path)) {
            throw ("Missing expected Phase 37 Step 6 file: {0}" -f $Rel)
        }
    }
}

function Show-Packet {
    Write-Host "=============================================================================="
    Write-Host $StepTitle
    Write-Host "=============================================================================="
    Write-Host ("Repo root: {0}" -f $RepoRoot)
    Write-Host ("Prior completed step: {0}" -f $PriorCompletedStep)
    Write-Host "Safety posture: planning-only/no-write/no-server/no-network-transport/no-live-write-activation/no-live-write-apply/no-phase38"
    Write-Host "Step files:"
    foreach ($Rel in $StepFiles) { Write-Host ("  {0}" -f $Rel) }
    Write-Host "Safety markers:"
    foreach ($Key in $SafetyPosture.Keys) { Write-Host ("  {0}={1}" -f $Key, $SafetyPosture[$Key]) }
}

function Invoke-Apply {
    Assert-StepFiles
    Write-Host "APPLY PASS: Phase 37 Step 6 planning-only packet verified without live-write activation, live-write apply, live-user access, bridge POST, sockets, DB mutation, server launch, or Phase 38 boundary creation."
}

function Invoke-Smoke {
    Assert-StepFiles
    if (-not $SafetyPosture.planning_only) { throw "planning_only marker is not true." }
    if (-not $SafetyPosture.no_live_write_activation) { throw "no_live_write_activation marker is not true." }
    if (-not $SafetyPosture.no_live_write_apply) { throw "no_live_write_apply marker is not true." }
    if ($SafetyPosture.phase38_start) { throw "phase38_start must remain false." }
    if ($SafetyPosture.phase38_boundary_creation) { throw "phase38_boundary_creation must remain false." }
    if ($SafetyPosture.phase37_execution_start) { throw "phase37_execution_start must remain false." }
    if ($SafetyPosture.phase37_implementation_start) { throw "phase37_implementation_start must remain false." }
    if ($SafetyPosture.live_write_activation_start) { throw "live_write_activation_start must remain false." }
    if ($SafetyPosture.live_write_apply_start) { throw "live_write_apply_start must remain false." }
    if ($SafetyPosture.live_user_access_start) { throw "live_user_access_start must remain false." }
    Write-Host "SMOKE TEST PASS: Phase 37 Step 6 safety markers confirm planning-only/no-write/no-live-write-activation/no-live-write-apply/no-runtime/no-phase38 posture."
}

switch ($Action) {
    "status" { Show-Packet }
    "packet" { Show-Packet }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "all" { Show-Packet; Invoke-Apply; Invoke-Smoke }
}
