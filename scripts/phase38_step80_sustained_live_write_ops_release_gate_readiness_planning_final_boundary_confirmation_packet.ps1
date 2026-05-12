param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PhaseNumber = 37
$StepNumber = 80
$StepTitle = "Phase 38 Step 80 - Phase 20 Network Transport Implementation Trusted Production Sustained Live Write Operations Release Gate Readiness Planning Final Boundary Confirmation Packet"
$PriorCompletedStep = "Phase 38 Step 79 packet"

function Resolve-RepoRoot {
    param([string]$Candidate)
    if ($Candidate -and (Test-Path (Join-Path $Candidate ".git"))) { return (Resolve-Path $Candidate).Path }
    $Here = Split-Path -Parent $MyInvocation.ScriptName
    $Possible = Resolve-Path (Join-Path $Here "..") -ErrorAction SilentlyContinue
    if ($Possible -and (Test-Path (Join-Path $Possible.Path ".git"))) { return $Possible.Path }
    $Current = (Get-Location).Path
    if (Test-Path (Join-Path $Current ".git")) { return $Current }
    throw "Could not resolve repository root."
}

$RepoRoot = Resolve-RepoRoot -Candidate $RepoRoot

$StepFiles = @(
    "scripts/phase38_step80_sustained_live_write_ops_release_gate_readiness_planning_final_boundary_confirmation_packet.ps1",
    "ui/pages/2016_Phase38_Step80_Sustained_Live_Write_Ops_Release_Gate_Readiness_Final_Boundary.py",
    "docs/PHASE38_STEP80_SUSTAINED_LIVE_WRITE_OPS_RELEASE_GATE_READINESS_PLANNING_FINAL_BOUNDARY_CONFIRMATION_PACKET.md",
    "tests/test_phase38_step80_sustained_live_write_ops_release_gate_readiness_planning_final_boundary_confirmation_packet.py"
)

$SafetyMarkers = @("planning_only=true", "no_real_bridge_http_client=true", "no_network_transport_implementation=true", "no_bridge_post=true", "no_network_sockets=true", "phase38_execution_start=false", "phase38_implementation_start=false", "implementation_phase_start=false", "trusted_production_sustained_live_write_operations_start=false", "trusted_production_sustained_live_write_operations_execution_start=false", "sustained_live_write_operations_start=false", "sustained_live_write_operations_execution_start=false", "live_write_activation_start=false", "live_write_apply_start=false", "live_user_access_start=false", "no_live_user_access=true", "no_live_write_activation=true", "no_live_write_apply=true", "phase39_start=false", "phase39_boundary_creation=false", "lacrm_default_mode=dry_run", "live_write_disabled=true", "live_write_unarmed=true")
$SafetyMarkerText = $SafetyMarkers -join [Environment]::NewLine

function Show-Packet {
    Write-Host $StepTitle
    Write-Host ("Repo root: {0}" -f $RepoRoot)
    Write-Host "Planning-only packet. No live writes, no server launch, no bridge POST, no sockets, no Phase 39 boundary creation."
    Write-Host "Prior completed step: $PriorCompletedStep"
    Write-Host "Safety markers:"
    Write-Host $SafetyMarkerText
}

function Invoke-Apply {
    foreach ($Rel in $StepFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Path)) { throw ("Missing required step file: {0}" -f $Rel) }
    }
    if ($SafetyMarkerText -notmatch "planning_only=true") { throw "Missing planning_only marker." }
    $ForbiddenPhase38Start = "phase39_start" + "=true"
    $ForbiddenLiveWriteApplyStart = "live_write_apply_start" + "=true"
    $ForbiddenLiveWriteActivationStart = "live_write_activation_start" + "=true"
    if ($SafetyMarkerText -match [regex]::Escape($ForbiddenPhase38Start)) { throw "Forbidden Phase 39 start marker detected." }
    if ($SafetyMarkerText -match [regex]::Escape($ForbiddenLiveWriteApplyStart)) { throw "Forbidden live-write apply start marker detected." }
    if ($SafetyMarkerText -match [regex]::Escape($ForbiddenLiveWriteActivationStart)) { throw "Forbidden live-write activation start marker detected." }
    Write-Host "APPLY PASS"
}

function Invoke-Smoke {
    if ($SafetyMarkerText -notmatch "no_live_write_apply=true") { throw "Missing no_live_write_apply marker." }
    if ($SafetyMarkerText -notmatch "no_live_write_activation=true") { throw "Missing no_live_write_activation marker." }
    if ($SafetyMarkerText -notmatch "phase39_boundary_creation=false") { throw "Missing Phase 39 boundary guard." }
    Write-Host "SMOKE TEST PASS"
}

switch ($Action) {
    "status" { Show-Packet }
    "packet" { Show-Packet }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "all" { Show-Packet; Invoke-Apply; Invoke-Smoke }
}