param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PhaseNumber = 38
$StepNumber = 48
$StepTitle = "Phase 38 Step 48 - Phase 20 Network Transport Implementation Trusted Production Sustained Live Write Operations No-Write Dry Run Verification Planning Operator Hold Point Packet"
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
    "scripts/phase38_step48_sustained_live_write_ops_dry_run_verification_operator_hold_packet.ps1",
    "ui/pages/1984_Phase38_Step48_Sustained_Live_Write_Ops_Dry_Run_Verification_Operator_Hold.py",
    "docs/PHASE38_STEP48_SUSTAINED_LIVE_WRITE_OPS_DRY_RUN_VERIFICATION_OPERATOR_HOLD_PACKET.md",
    "tests/test_phase38_step48_sustained_live_write_ops_dry_run_verification_operator_hold_packet.py"
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
    phase38_boundary = "trusted_production_sustained_live_write_operations_no_write_dry_run_verification_planning_packet"
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

function Get-SafetyMarkerText {
    $Lines = New-Object System.Collections.Generic.List[string]
    foreach ($Key in $SafetyPosture.Keys) {
        $Value = $SafetyPosture[$Key]
        if ($Value -is [bool]) { $Value = $Value.ToString().ToLowerInvariant() }
        $Lines.Add(("{0}={1}" -f $Key, $Value))
    }
    return ($Lines -join "`n")
}

function Assert-PlanningOnlySafety {
    $SafetyMarkerText = (Get-SafetyMarkerText).Replace(" ", "").ToLowerInvariant()
    $ForbiddenMarkers = @(
        ("phase39_start" + "=true"),
        ("phase39_boundary_creation" + "=true"),
        ("phase38_execution_start" + "=true"),
        ("phase38_implementation_start" + "=true"),
        ("implementation_phase_start" + "=true"),
        ("trusted_production_sustained_live_write_operations_start" + "=true"),
        ("trusted_production_sustained_live_write_operations_execution_start" + "=true"),
        ("sustained_live_write_operations_start" + "=true"),
        ("sustained_live_write_operations_execution_start" + "=true"),
        ("live_write_activation_start" + "=true"),
        ("live_write_apply_start" + "=true"),
        ("live_user_access_start" + "=true"),
        ("no_live_user_access" + "=false"),
        ("no_live_write_activation" + "=false"),
        ("no_live_write_apply" + "=false")
    )

    foreach ($Marker in $ForbiddenMarkers) {
        if ($SafetyMarkerText.Contains($Marker)) {
            throw ("Forbidden runtime marker detected: {0}" -f $Marker)
        }
    }

    if (-not $SafetyMarkerText.Contains("planning_only=true")) { throw "Missing planning_only=true marker." }
    if (-not $SafetyMarkerText.Contains("no_live_write_activation=true")) { throw "Missing no_live_write_activation=true marker." }
    if (-not $SafetyMarkerText.Contains("no_live_write_apply=true")) { throw "Missing no_live_write_apply=true marker." }
    if (-not $SafetyMarkerText.Contains("lacrm_default_mode=dry_run")) { throw "Missing lacrm_default_mode=dry_run marker." }
}

function Assert-StepFilesPresent {
    foreach ($Rel in $StepFiles) {
        $Full = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Full)) {
            throw ("Missing required step file: {0}" -f $Rel)
        }
    }
}

function Assert-NoNextPhaseFiles {
    $Folders = @("scripts", "docs", "tests", "ui/pages")
    foreach ($Folder in $Folders) {
        $Full = Join-Path $RepoRoot $Folder
        if (Test-Path $Full) {
            $Hit = Get-ChildItem -Path $Full -File -Recurse -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "(?i)phase39" } | Select-Object -First 1
            if ($Hit) { throw ("Unexpected Phase 39 file detected before boundary creation: {0}" -f $Hit.FullName) }
        }
    }
}

function Show-Packet {
    Write-Host "=============================================================================="
    Write-Host $StepTitle
    Write-Host "=============================================================================="
    Write-Host ("RepoRoot={0}" -f $RepoRoot)
    Write-Host "Safety posture: planning-only/no-write/no-server/no-network-transport/no-live-write-activation/no-live-write-apply/no-phase39"
    Write-Host (Get-SafetyMarkerText)
}

function Invoke-Apply {
    Assert-PlanningOnlySafety
    Assert-StepFilesPresent
    Assert-NoNextPhaseFiles
    Write-Host "APPLY PASS"
}

function Invoke-Smoke {
    Assert-PlanningOnlySafety
    Assert-NoNextPhaseFiles
    Write-Host "SMOKE TEST PASS"
}

switch ($Action) {
    "status" { Show-Packet }
    "packet" { Show-Packet }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "all" { Show-Packet; Invoke-Apply; Invoke-Smoke }
}