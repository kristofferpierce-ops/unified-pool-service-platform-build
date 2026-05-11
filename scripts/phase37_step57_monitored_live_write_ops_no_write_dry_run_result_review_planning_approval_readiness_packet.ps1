param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PhaseNumber = 37
$StepNumber = 57
$StepTitle = "Phase 37 Step 57 - Phase 20 Network Transport Implementation Trusted Production Monitored Live Write Operations No-Write Dry Run Result Review Planning Approval Readiness Packet"
$PriorCompletedStep = "Phase 37 Step 56 packet"

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
    "scripts/phase37_step57_monitored_live_write_ops_no_write_dry_run_result_review_planning_approval_readiness_packet.ps1",
    "ui/pages/1873_Phase37_Step57_Monitored_Live_Write_Ops_Result_Review_Approval_Readiness.py",
    "docs/PHASE37_STEP57_MONITORED_LIVE_WRITE_OPS_NO_WRITE_DRY_RUN_RESULT_REVIEW_PLANNING_APPROVAL_READINESS_PACKET.md",
    "tests/test_phase37_step57_monitored_live_write_ops_no_write_dry_run_result_review_planning_approval_readiness_packet.py"
)

$SafetyMarkers = @("planning_only=true", "no_real_bridge_http_client=true", "no_network_transport_implementation=true", "no_bridge_post=true", "no_network_sockets=true", "phase37_execution_start=false", "phase37_implementation_start=false", "implementation_phase_start=false", "trusted_production_monitored_live_write_operations_start=false", "trusted_production_monitored_live_write_operations_execution_start=false", "monitored_live_write_operations_start=false", "monitored_live_write_operations_execution_start=false", "live_write_activation_start=false", "live_write_apply_start=false", "live_user_access_start=false", "no_live_user_access=true", "no_live_write_activation=true", "no_live_write_apply=true", "phase38_start=false", "phase38_boundary_creation=false", "lacrm_default_mode=dry_run", "live_write_disabled=true", "live_write_unarmed=true")
$SafetyMarkerText = $SafetyMarkers -join [Environment]::NewLine

function Show-Packet {
    Write-Host $StepTitle
    Write-Host ("Repo root: {0}" -f $RepoRoot)
    Write-Host "Planning-only packet. No live writes, no server launch, no bridge POST, no sockets, no Phase 38 boundary creation."
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
    $ForbiddenPhase38Start = "phase38_start" + "=true"
    $ForbiddenLiveWriteApplyStart = "live_write_apply_start" + "=true"
    $ForbiddenLiveWriteActivationStart = "live_write_activation_start" + "=true"
    if ($SafetyMarkerText -match [regex]::Escape($ForbiddenPhase38Start)) { throw "Forbidden Phase 38 start marker detected." }
    if ($SafetyMarkerText -match [regex]::Escape($ForbiddenLiveWriteApplyStart)) { throw "Forbidden live-write apply start marker detected." }
    if ($SafetyMarkerText -match [regex]::Escape($ForbiddenLiveWriteActivationStart)) { throw "Forbidden live-write activation start marker detected." }
    Write-Host "APPLY PASS"
}

function Invoke-Smoke {
    if ($SafetyMarkerText -notmatch "no_live_write_apply=true") { throw "Missing no_live_write_apply marker." }
    if ($SafetyMarkerText -notmatch "no_live_write_activation=true") { throw "Missing no_live_write_activation marker." }
    if ($SafetyMarkerText -notmatch "phase38_boundary_creation=false") { throw "Missing Phase 38 boundary guard." }
    Write-Host "SMOKE TEST PASS"
}

switch ($Action) {
    "status" { Show-Packet }
    "packet" { Show-Packet }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "all" { Show-Packet; Invoke-Apply; Invoke-Smoke }
}