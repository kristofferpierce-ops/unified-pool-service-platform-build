param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PhaseNumber = 38
$StepNumber = 32
$StepTitle = "Phase 38 Step 32 - Phase 20 Network Transport Implementation Trusted Production Sustained Live Write Operations No-Write Dry Run Readiness Evidence Index Packet"
$PriorCompletedStep = "Phase 37 Step 120 - Phase 37 Final No-Write Closeout Hold Packet"

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
    "scripts/phase38_step32_sustained_live_write_ops_no_write_dry_run_readiness_evidence_index_packet.ps1",
    "ui/pages/1968_Phase38_Step32_Sustained_Live_Write_Ops_No_Write_Dry_Run_Readiness_Evidence_Index.py",
    "docs/PHASE38_STEP32_SUSTAINED_LIVE_WRITE_OPS_NO_WRITE_DRY_RUN_READINESS_EVIDENCE_INDEX_PACKET.md",
    "tests/test_phase38_step32_sustained_live_write_ops_no_write_dry_run_readiness_evidence_index_packet.py"
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
    phase38_boundary = "trusted_production_sustained_live_write_operations_no_write_dry_run_readiness_packet"
    phase38_execution_start = $false
    phase38_implementation_start = $false
    implementation_phase_start = $false
    trusted_production_sustained_live_write_operations_start = $false
    trusted_production_sustained_live_write_operations_execution_start = $false
    sustained_live_write_operations_start = $false
    sustained_live_write_operations_execution_start = $false
    live_write_activation_start = $false
    live_write_apply_start = $false
    live_user_access_start = $false
    no_live_user_access = $true
    no_live_write_activation = $true
    no_live_write_apply = $true
    phase39_start = $false
    phase39_boundary_creation = $false
    lacrm_default_mode = "dry_run"
    live_write_disabled = $true
    live_write_unarmed = $true
}

function Show-Packet {
    Write-Host $StepTitle
    Write-Host ("RepoRoot={0}" -f $RepoRoot)
    Write-Host "Safety posture: planning-only/no-write/no-server/no-network-transport/no-live-write-activation/no-live-write-apply/no-phase39"
    Write-Host "planning_only=true"
    Write-Host "no_real_bridge_http_client=true"
    Write-Host "no_network_transport_implementation=true"
    Write-Host "no_bridge_post=true"
    Write-Host "no_network_sockets=true"
    Write-Host "phase38_execution_start=false"
    Write-Host "phase38_implementation_start=false"
    Write-Host "implementation_phase_start=false"
    Write-Host "trusted_production_sustained_live_write_operations_start=false"
    Write-Host "trusted_production_sustained_live_write_operations_execution_start=false"
    Write-Host "sustained_live_write_operations_start=false"
    Write-Host "sustained_live_write_operations_execution_start=false"
    Write-Host "live_write_activation_start=false"
    Write-Host "live_write_apply_start=false"
    Write-Host "live_user_access_start=false"
    Write-Host "no_live_user_access=true"
    Write-Host "no_live_write_activation=true"
    Write-Host "no_live_write_apply=true"
    Write-Host "phase39_start=false"
    Write-Host "phase39_boundary_creation=false"
    Write-Host "lacrm_default_mode=dry_run"
    Write-Host "live_write_disabled=true"
    Write-Host "live_write_unarmed=true"
}

function Assert-StepFilesPresent {
    foreach ($Rel in $StepFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Path)) {
            throw ("Missing required step file: {0}" -f $Rel)
        }
    }
}

function Invoke-Apply {
    Assert-StepFilesPresent
    if (-not $SafetyPosture.planning_only) { throw "planning_only must remain enabled." }
    if (-not $SafetyPosture.no_live_user_access) { throw "no_live_user_access must remain enabled." }
    if (-not $SafetyPosture.no_live_write_activation) { throw "no_live_write_activation must remain enabled." }
    if (-not $SafetyPosture.no_live_write_apply) { throw "no_live_write_apply must remain enabled." }
    if ($SafetyPosture.phase39_start) { throw "Next phase start must remain false." }
    if ($SafetyPosture.phase39_boundary_creation) { throw "Next phase boundary creation must remain false." }
    if ($SafetyPosture.live_write_activation_start) { throw "live_write_activation_start must remain false." }
    if ($SafetyPosture.live_write_apply_start) { throw "live_write_apply_start must remain false." }
    if ($SafetyPosture.live_user_access_start) { throw "live_user_access_start must remain false." }
    Write-Host "APPLY PASS"
}

function Invoke-Smoke {
    Assert-StepFilesPresent
    if ($SafetyPosture.phase38_execution_start) { throw "phase38_execution_start must remain false." }
    if ($SafetyPosture.phase38_implementation_start) { throw "phase38_implementation_start must remain false." }
    if ($SafetyPosture.implementation_phase_start) { throw "implementation_phase_start must remain false." }
    if ($SafetyPosture.trusted_production_sustained_live_write_operations_start) { throw "trusted_production_sustained_live_write_operations_start must remain false." }
    if ($SafetyPosture.trusted_production_sustained_live_write_operations_execution_start) { throw "trusted_production_sustained_live_write_operations_execution_start must remain false." }
    if ($SafetyPosture.sustained_live_write_operations_start) { throw "sustained_live_write_operations_start must remain false." }
    if ($SafetyPosture.sustained_live_write_operations_execution_start) { throw "sustained_live_write_operations_execution_start must remain false." }
    if ($SafetyPosture.live_write_activation_start) { throw "live_write_activation_start must remain false." }
    if ($SafetyPosture.live_write_apply_start) { throw "live_write_apply_start must remain false." }
    if ($SafetyPosture.live_user_access_start) { throw "live_user_access_start must remain false." }
    Write-Host "SMOKE TEST PASS"
}

switch ($Action) {
    "status" { Show-Packet }
    "packet" { Show-Packet }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "all" { Show-Packet; Invoke-Apply; Invoke-Smoke }
}
