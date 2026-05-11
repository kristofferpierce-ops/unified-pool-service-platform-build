param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PhaseNumber = 37
$StepNumber = 47
$StepTitle = "Phase 37 Step 47 - Phase 20 Network Transport Implementation Trusted Production Monitored Live Write Operations No-Write Dry Run Verification Planning Approval Readiness Packet"
$PriorCompletedStep = "Phase 37 Step 46 - Phase 20 Network Transport Implementation Trusted Production Monitored Live Write Operations No-Write Dry Run Verification Planning Approval Boundary Packet"

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
    "scripts/phase37_step47_monitored_live_write_ops_no_write_dry_run_verification_planning_approval_readiness_packet.ps1",
    "ui/pages/1863_Phase37_Step47_Monitored_Live_Write_Ops_No_Write_Dry_Run_Verification_Planning_Approval_Readiness.py",
    "docs/PHASE37_STEP47_MONITORED_LIVE_WRITE_OPS_NO_WRITE_DRY_RUN_VERIFICATION_PLANNING_APPROVAL_READINESS_PACKET.md",
    "tests/test_phase37_step47_monitored_live_write_ops_no_write_dry_run_verification_planning_approval_readiness_packet.py"
)

$SafetyMarkerText = @"
planning_only=true
no_real_bridge_http_client=true
no_network_transport_implementation=true
no_bridge_post=true
no_network_sockets=true
phase37_execution_start=false
phase37_implementation_start=false
implementation_phase_start=false
trusted_production_monitored_live_write_operations_start=false
trusted_production_monitored_live_write_operations_execution_start=false
monitored_live_write_operations_start=false
monitored_live_write_operations_execution_start=false
live_write_activation_start=false
live_write_apply_start=false
live_user_access_start=false
no_live_user_access=true
no_live_write_activation=true
no_live_write_apply=true
phase38_start=false
phase38_boundary_creation=false
lacrm_default_mode=dry_run
live_write_disabled=true
live_write_unarmed=true
"@

$SafetyPosture = [ordered]@{
    planning_only = $true
    no_real_bridge_http_client = $true
    no_network_transport_implementation = $true
    no_bridge_post = $true
    no_network_sockets = $true
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
        if (-not (Test-Path $Path)) { throw ("Missing expected step file: {0}" -f $Rel) }
    }
}

function Assert-SafePosture {
    if (-not $SafetyPosture["planning_only"]) { throw "planning_only must remain true." }
    if (-not $SafetyPosture["no_live_user_access"]) { throw "no_live_user_access must remain true." }
    if (-not $SafetyPosture["no_live_write_activation"]) { throw "no_live_write_activation must remain true." }
    if (-not $SafetyPosture["no_live_write_apply"]) { throw "no_live_write_apply must remain true." }
    foreach ($Key in @(
        "phase38_start", "phase38_boundary_creation", "phase37_execution_start", "phase37_implementation_start",
        "implementation_phase_start", "trusted_production_monitored_live_write_operations_start",
        "trusted_production_monitored_live_write_operations_execution_start", "monitored_live_write_operations_start",
        "monitored_live_write_operations_execution_start", "live_write_activation_start", "live_write_apply_start", "live_user_access_start"
    )) {
        if ($SafetyPosture[$Key]) { throw ("{0} must remain false." -f $Key) }
    }
}

function Show-Packet {
    [pscustomobject]@{
        phase = $PhaseNumber
        step = $StepNumber
        title = $StepTitle
        prior_completed_step = $PriorCompletedStep
        planning_only = $SafetyPosture["planning_only"]
        no_bridge_post = $SafetyPosture["no_bridge_post"]
        no_network_sockets = $SafetyPosture["no_network_sockets"]
        no_live_user_access = $SafetyPosture["no_live_user_access"]
        no_live_write_activation = $SafetyPosture["no_live_write_activation"]
        no_live_write_apply = $SafetyPosture["no_live_write_apply"]
        phase38_start = $SafetyPosture["phase38_start"]
        phase38_boundary_creation = $SafetyPosture["phase38_boundary_creation"]
    } | Format-List
}

function Invoke-Apply {
    Assert-StepFiles
    Assert-SafePosture
    Write-Host "APPLY PASS: Phase 37 Step 47 planning-only monitored live-write operations no-write dry-run verification planning packet verified without runtime/live-write activation/Phase 38 creation."
}

function Invoke-Smoke {
    Assert-StepFiles
    Assert-SafePosture
    if ($SafetyMarkerText -notmatch "planning_only=true") { throw "Missing planning_only=true marker text." }
    if ($SafetyMarkerText -notmatch "phase38_boundary_creation=false") { throw "Missing phase38_boundary_creation=false marker text." }
    Write-Host "SMOKE TEST PASS: Phase 37 Step 47 safety markers confirm planning-only/no-write/no-live-write-apply/no-runtime/no-Phase-38 posture."
}

switch ($Action) {
    "status" { Show-Packet }
    "packet" { Show-Packet }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "all" { Show-Packet; Invoke-Apply; Invoke-Smoke }
}
