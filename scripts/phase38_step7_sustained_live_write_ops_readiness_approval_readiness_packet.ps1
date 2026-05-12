param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PhaseNumber = 38
$StepNumber = 7
$StepTitle = "Phase 38 Step 7 - Phase 20 Network Transport Implementation Trusted Production Sustained Live Write Operations Readiness Approval Readiness Packet"
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
    "scripts/phase38_step7_sustained_live_write_ops_readiness_approval_readiness_packet.ps1",
    "ui/pages/1943_Phase38_Step7_Sustained_Live_Write_Ops_Readiness_Approval_Readiness.py",
    "docs/PHASE38_STEP7_SUSTAINED_LIVE_WRITE_OPS_READINESS_APPROVAL_READINESS_PACKET.md",
    "tests/test_phase38_step7_sustained_live_write_ops_readiness_approval_readiness_packet.py"
)

$SafetyPosture = [ordered]@{
    planning_only = $true
    no_real_bridge_http_client = $true
    no_network_transport_implementation = $true
    no_bridge_post = $true
    no_network_sockets = $true
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

function Convert-SafetyValue {
    param([object]$Value)
    if ($Value -is [bool]) { return $Value.ToString().ToLowerInvariant() }
    return [string]$Value
}

function Show-Packet {
    Write-Host $StepTitle
    Write-Host ("RepoRoot={0}" -f $RepoRoot)
    Write-Host "Safety posture: planning-only/no-write/no-server/no-network-transport/no-live-write-activation/no-live-write-apply/no-phase39"
    foreach ($Item in $SafetyPosture.GetEnumerator()) {
        Write-Host ("{0}={1}" -f $Item.Key, (Convert-SafetyValue -Value $Item.Value))
    }
}

function Assert-StepFilesPresent {
    foreach ($Rel in $StepFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Path)) {
            throw ("Missing required step file: {0}" -f $Rel)
        }
    }
}

function Assert-NoNextPhaseFiles {
    $Folders = @("scripts", "docs", "tests", "ui/pages")
    foreach ($Folder in $Folders) {
        $Root = Join-Path $RepoRoot $Folder
        if (Test-Path $Root) {
            $Hits = @(Get-ChildItem -Path $Root -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Name.ToLowerInvariant().Contains("phase39") })
            if ($Hits.Count -gt 0) {
                throw ("Phase 39 file detected before boundary approval: {0}" -f $Hits[0].FullName)
            }
        }
    }
}

function Invoke-Apply {
    Assert-StepFilesPresent
    Assert-NoNextPhaseFiles
    Write-Host "APPLY PASS"
}

function Invoke-Smoke {
    Assert-StepFilesPresent
    if (-not $SafetyPosture.planning_only) { throw "planning_only must remain true." }
    if (-not $SafetyPosture.no_live_user_access) { throw "no_live_user_access must remain true." }
    if (-not $SafetyPosture.no_live_write_activation) { throw "no_live_write_activation must remain true." }
    if (-not $SafetyPosture.no_live_write_apply) { throw "no_live_write_apply must remain true." }
    if ($SafetyPosture.phase39_start) { throw "phase39_start must remain false." }
    if ($SafetyPosture.phase39_boundary_creation) { throw "phase39_boundary_creation must remain false." }
    if ($SafetyPosture.phase38_execution_start) { throw "phase38_execution_start must remain false." }
    if ($SafetyPosture.phase38_implementation_start) { throw "phase38_implementation_start must remain false." }
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
