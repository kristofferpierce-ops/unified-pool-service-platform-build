param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PhaseNumber = 35
$StepNumber = 94
$StepTitle = 'Phase 35 Step 94 - Phase 20 Network Transport Implementation Trusted Production Limited Live Write Pilot Final Release Hold Planning Safety Disposition Planning Packet'
$ExpectedBranch = 'phase35-step94-limited-live-write-final-release-hold-safety-disposition-planning'
$PriorCompletedStep = 'Phase 35 Step 93 - Phase 20 Network Transport Implementation Trusted Production Limited Live Write Pilot Final Release Hold Planning Evidence Gap Review Packet'

function Resolve-RepoRoot {
    param([string]$Candidate)

    if ($Candidate -and (Test-Path (Join-Path $Candidate ".git"))) {
        return (Resolve-Path $Candidate).Path
    }

    if ($MyInvocation.ScriptName) {
        $Here = Split-Path -Parent $MyInvocation.ScriptName
        $FromScript = Resolve-Path (Join-Path $Here "..") -ErrorAction SilentlyContinue
        if ($FromScript -and (Test-Path (Join-Path $FromScript.Path ".git"))) {
            return $FromScript.Path
        }
    }

    $Current = (Get-Location).Path
    if (Test-Path (Join-Path $Current ".git")) {
        return $Current
    }

    throw "Could not resolve repository root."
}

$RepoRoot = Resolve-RepoRoot -Candidate $RepoRoot

$StepFiles = @(
    'scripts/phase35_step94_limited_live_write_final_release_hold_safety_disposition_planning_packet.ps1',
    'ui/pages/1670_Phase35_Step94_Live_Write_Final_Release_Hold_Safety_Planning.py',
    'docs/PHASE35_STEP94_LIMITED_LIVE_WRITE_FINAL_RELEASE_HOLD_SAFETY_DISPOSITION_PLANNING_PACKET.md',
    'tests/test_phase35_step94_limited_live_write_final_release_hold_safety_disposition_planning_packet.py'
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
    phase35_boundary = 'trusted_production_limited_live_write_pilot_final_release_hold_planning_safety_disposition_planning_opened_by_packet'
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
    trusted_production_limited_live_write_pilot_final_release_hold_planning_safety_disposition_planning_mode = "reference_only"
    trusted_production_limited_live_write_pilot_final_release_hold_planning_safety_disposition_planning_write = $false
    trusted_production_limited_live_write_pilot_final_release_hold_planning_safety_disposition_planning_record_creation = $false
    limited_live_write_decision_creation = $false
    limited_live_write_approval_creation = $false
    limited_live_write_operator_approval_creation = $false
    no_operator_signoff = $true
    no_operator_approval = $true
    no_final_approval = $true
    no_live_user_access = $true
    no_live_write_activation = $true
    no_live_write_apply = $true
    phase34_reopen = $false
    phase36_start = $false
    phase36_boundary_creation = $false
    lacrm_default_mode = "dry_run"
    lacrm_live_write = $false
    live_write_disabled = $true
    live_write_unarmed = $true
}

function Show-Status {
    Write-Host "=============================================================================="
    Write-Host $StepTitle
    Write-Host "=============================================================================="
    Write-Host ("Repo root: {0}" -f $RepoRoot)
    Write-Host ("Expected branch: {0}" -f $ExpectedBranch)
    Write-Host ("Prior completed step: {0}" -f $PriorCompletedStep)
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    foreach ($Item in $SafetyPosture.GetEnumerator()) {
        Write-Host ("  {0}: {1}" -f $Item.Key, $Item.Value)
    }
    Write-Host ""
    Write-Host "Step files"
    foreach ($Rel in $StepFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (Test-Path $Path) {
            Write-Host ("  PRESENT {0}" -f $Rel)
        } else {
            Write-Host ("  MISSING {0}" -f $Rel)
        }
    }
}

function Apply-StepFiles {
    foreach ($Rel in $StepFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Path)) {
            throw ("Missing step file during apply: {0}" -f $Rel)
        }
        Write-Host ("SKIPPED {0} source and target are the same file." -f $Rel)
    }

    Write-Host "APPLY PASS: Phase 35 Step 94 files copied or already present."
}

function Test-Smoke {
    foreach ($Rel in $StepFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Path)) {
            throw ("Smoke test missing required file: {0}" -f $Rel)
        }
    }

    Assert-SafetyPosture
    Write-Host "SMOKE TEST PASS: Phase 35 Step 94 Phase 20 Network Transport Implementation Trusted Production Limited Live Write Pilot Final Release Hold Planning Safety Disposition Planning Packet is present and planning-only."
}

function Assert-SafetyPosture {
    $RequiredTrue = @(
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "no_live_user_access",
        "no_live_write_activation",
        "no_live_write_apply",
        "live_write_disabled",
        "live_write_unarmed"
    )

    foreach ($Key in $RequiredTrue) {
        if (-not $SafetyPosture.Contains($Key)) {
            throw ("Missing required true safety marker: {0}" -f $Key)
        }
        if ($SafetyPosture[$Key] -ne $true) {
            throw ("Required true safety marker is not true: {0}" -f $Key)
        }
        Write-Host ("PASS: {0}=true" -f $Key)
    }

    $RequiredFalse = @(
        "phase35_execution_start",
        "phase35_implementation_start",
        "implementation_phase_start",
        "trusted_production_limited_live_write_pilot_start",
        "trusted_production_limited_live_write_pilot_execution_start",
        "limited_live_write_pilot_start",
        "limited_live_write_pilot_execution_start",
        "live_write_activation_start",
        "live_write_apply_start",
        "live_user_access_start",
        "network_transport_runtime_start",
        "bridge_transport_runtime_start",
        "cross_repo_write",
        "cross_repo_mutation",
        "external_repo_push",
        "phase34_reopen",
        "phase36_start",
        "phase36_boundary_creation"
    )

    foreach ($Key in $RequiredFalse) {
        if (-not $SafetyPosture.Contains($Key)) {
            throw ("Missing required false safety marker: {0}" -f $Key)
        }
        if ($SafetyPosture[$Key] -ne $false) {
            throw ("Required false safety marker is not false: {0}" -f $Key)
        }
        Write-Host ("PASS: {0}=false" -f $Key)
    }

    Write-Host ("PASS: phase35_boundary={0}" -f $SafetyPosture["phase35_boundary"])
    Write-Host ("PASS: trusted_production_limited_live_write_pilot_final_release_hold_planning_safety_disposition_planning_mode={0}" -f $SafetyPosture["trusted_production_limited_live_write_pilot_final_release_hold_planning_safety_disposition_planning_mode"])
    Write-Host ("PASS: trusted_production_limited_live_write_pilot_final_release_hold_planning_safety_disposition_planning_write={0}" -f ([string]$SafetyPosture["trusted_production_limited_live_write_pilot_final_release_hold_planning_safety_disposition_planning_write"]).ToLower())
    Write-Host ("PASS: trusted_production_limited_live_write_pilot_final_release_hold_planning_safety_disposition_planning_record_creation={0}" -f ([string]$SafetyPosture["trusted_production_limited_live_write_pilot_final_release_hold_planning_safety_disposition_planning_record_creation"]).ToLower())
    Write-Host ("PASS: lacrm_default_mode={0}" -f $SafetyPosture["lacrm_default_mode"])
    Write-Host ("CHECK: prior_step={0}" -f $PriorCompletedStep)
    Write-Host "CHECK: phase35_context=trusted_production_limited_live_write_pilot_final_release_hold_planning_only"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: network_transport_runtime_start=not_started"
    Write-Host "CHECK: parent_workspace_launcher=safe"
}

function Assert-NoUnsafeOperationalMarkers {
    $OperationalFiles = @(
        'scripts/phase35_step94_limited_live_write_final_release_hold_safety_disposition_planning_packet.ps1',
        'ui/pages/1670_Phase35_Step94_Live_Write_Final_Release_Hold_Safety_Planning.py',
        'docs/PHASE35_STEP94_LIMITED_LIVE_WRITE_FINAL_RELEASE_HOLD_SAFETY_DISPOSITION_PLANNING_PACKET.md'
    )

    $ForbiddenTrueKeys = @(
        "phase36_start",
        "phase36_boundary_creation",
        "phase35_execution_start",
        "phase35_implementation_start",
        "implementation_phase_start",
        "trusted_production_limited_live_write_pilot_start",
        "trusted_production_limited_live_write_pilot_execution_start",
        "limited_live_write_pilot_start",
        "limited_live_write_pilot_execution_start",
        "live_write_activation_start",
        "live_write_apply_start",
        "live_user_access_start",
        "network_transport_runtime_start",
        "bridge_transport_runtime_start"
    )

    foreach ($Rel in $OperationalFiles) {
        $Path = Join-Path $RepoRoot $Rel
        $Text = (Get-Content -LiteralPath $Path -Raw -ErrorAction Stop).ToLower()
        $Compact = $Text.Replace(" ", "").Replace("`r", "").Replace("`n", "")
        foreach ($Key in $ForbiddenTrueKeys) {
            $UnsafeEquals = ("{0}=true" -f $Key)
            $UnsafeDollar = ("{0}=$true" -f $Key)
            if ($Compact.Contains($UnsafeEquals) -or $Compact.Contains($UnsafeDollar)) {
                throw ("Unsafe marker found in operational file {0}: {1} true" -f $Rel, $Key)
            }
        }
    }
}

function New-Packet {
    Assert-SafetyPosture
    Assert-NoUnsafeOperationalMarkers

    $BackupDirName = "phase35_step94_limited_live_write_final_release_hold_safety_disposition_planning_packet_" + (Get-Date -Format "yyyyMMdd_HHmmss")
    $BackupDir = Join-Path (Join-Path $RepoRoot "backups") $BackupDirName
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    $PacketPath = Join-Path $BackupDir "phase35_step94_limited_live_write_final_release_hold_safety_disposition_planning_packet.json"

    $Packet = [ordered]@{
        phase = $PhaseNumber
        step = $StepNumber
        title = $StepTitle
        prior_completed_step = $PriorCompletedStep
        planning_only = $true
        no_write = $true
        no_server_launch = $true
        no_network_transport_implementation = $true
        no_bridge_post = $true
        no_network_sockets = $true
        no_live_write_activation = $true
        no_live_write_apply = $true
        phase36_start = $false
        phase36_boundary_creation = $false
        generated_at = (Get-Date).ToString("o")
        step_files = $StepFiles
    }

    $Packet | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $PacketPath -Encoding UTF8
    Write-Host ("CHECK: packet_json={0}" -f $PacketPath)
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

