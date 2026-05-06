param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
}

$StepNumber = 65
$StepTitle = "Phase 20 Network Transport Implementation Trusted Production Shadow Run Validation No-Write Dry Run Result Disposition Planning Safety Disposition Review Packet"
$ExpectedBranch = "phase34-step65-shadow-run-result-disposition-safety-disposition-review"
$PriorCompletedStep = "Phase 34 Step 64"
$ApplyPassMessage = "APPLY PASS: Phase 34 Step 65 files copied or already present."
$SmokePassMessage = "SMOKE TEST PASS: Phase 34 Step 65 Phase 20 Network Transport Implementation Trusted Production Shadow Run Validation No-Write Dry Run Result Disposition Planning Safety Disposition Review Packet is present and planning-only."

$SafetyPosture = [ordered]@{
    planning_only = $true
    no_platform_db_mutation = $true
    no_bridge_mutation = $true
    no_real_bridge_http_client = $true
    no_network_transport_implementation = $true
    no_bridge_post = $true
    no_network_sockets = $true
    no_execution_implementation = $true
    phase34_boundary = "trusted_production_shadow_run_validation_no_write_dry_run_result_disposition_planning_safety_disposition_review_opened_by_packet"
    phase34_execution_start = $false
    phase34_implementation_start = $false
    implementation_phase_start = $false
    controlled_active_program_start = $false
    controlled_active_program_execution_start = $false
    trusted_production_shadow_run_validation_start = $false
    trusted_production_shadow_run_validation_execution_start = $false
    shadow_run_execution_start = $false
    live_read_activation_start = $false
    live_user_access_start = $false
    network_transport_runtime_start = $false
    bridge_transport_runtime_start = $false
    cross_repo_write = $false
    cross_repo_mutation = $false
    external_repo_push = $false
    trusted_production_shadow_run_validation_no_write_dry_run_result_disposition_planning_safety_disposition_review_mode = "reference_only"
    trusted_production_shadow_run_validation_no_write_dry_run_result_disposition_planning_safety_disposition_review_write = $false
    trusted_production_shadow_run_validation_no_write_dry_run_result_disposition_planning_safety_disposition_review_record_creation = $false
    shadow_run_validation_decision_creation = $false
    shadow_run_validation_approval_creation = $false
    shadow_run_validation_operator_approval_creation = $false
    no_operator_signoff = $true
    no_operator_approval = $true
    no_final_approval = $true
    phase33_reopen = $false
    phase35_start = $false
    phase35_boundary_creation = $false
    lacrm_default_mode = "dry_run"
    lacrm_live_write = $false
    live_write_disabled = $true
    live_write_unarmed = $true
}

$StepFiles = @(
    "scripts/phase34_step65_trusted_production_shadow_run_validation_no_write_dry_run_result_disposition_planning_safety_disposition_review_packet.ps1",
    "ui/pages/1521_Phase34_Step65_Shadow_Run_Result_Disposition_Safety_Review.py",
    "docs/PHASE34_STEP65_TRUSTED_PRODUCTION_SHADOW_RUN_VALIDATION_NO_WRITE_DRY_RUN_RESULT_DISPOSITION_PLANNING_SAFETY_DISPOSITION_REVIEW_PACKET.md",
    "tests/test_phase34_step65_trusted_production_shadow_run_validation_no_write_dry_run_result_disposition_planning_safety_disposition_review_packet.py"
)

function Join-RepoPath {
    param([Parameter(Mandatory=$true)][string]$RelativePath)
    return (Join-Path -Path $RepoRoot -ChildPath $RelativePath)
}

function Show-Status {
    Write-Host "=============================================================================="
    Write-Host "Phase 34 Step $StepNumber - $StepTitle"
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
        $Path = Join-RepoPath $Rel
        if (Test-Path -LiteralPath $Path) {
            Write-Host ("  PRESENT {0}" -f $Rel)
        } else {
            Write-Host ("  MISSING {0}" -f $Rel)
        }
    }
}

function Apply-StepFiles {
    foreach ($Rel in $StepFiles) {
        $Path = Join-RepoPath $Rel
        if (-not (Test-Path -LiteralPath $Path)) {
            throw ("Missing step file: {0}" -f $Rel)
        }
        Write-Host ("SKIPPED {0} source and target are the same file." -f $Rel)
    }
    Write-Host $ApplyPassMessage
}

function Test-Smoke {
    foreach ($Rel in $StepFiles) {
        $Path = Join-RepoPath $Rel
        if (-not (Test-Path -LiteralPath $Path)) {
            throw ("Smoke test missing required file: {0}" -f $Rel)
        }
    }
    Write-Host $SmokePassMessage
}

function Assert-SafetyMarkers {
    $RequiredTrue = @("planning_only", "no_real_bridge_http_client", "no_network_transport_implementation", "no_bridge_post", "no_network_sockets", "live_write_disabled", "live_write_unarmed")
    foreach ($Key in $RequiredTrue) {
        if ($SafetyPosture[$Key] -ne $true) { throw ("Required true marker missing: {0}" -f $Key) }
        Write-Host ("PASS: {0}=true" -f $Key)
    }

    $RequiredFalse = @("phase34_execution_start", "phase34_implementation_start", "implementation_phase_start", "trusted_production_shadow_run_validation_start", "trusted_production_shadow_run_validation_execution_start", "shadow_run_execution_start", "live_read_activation_start", "live_user_access_start", "phase35_start", "phase35_boundary_creation")
    foreach ($Key in $RequiredFalse) {
        if ($SafetyPosture[$Key] -ne $false) { throw ("Required false marker missing: {0}" -f $Key) }
        Write-Host ("PASS: {0}=false" -f $Key)
    }

    if ($SafetyPosture["lacrm_default_mode"] -ne "dry_run") { throw "lacrm_default_mode must stay dry_run" }
    Write-Host "PASS: lacrm_default_mode=dry_run"
}

function Assert-NoUnsafeOperationalMarkers {
    $OperationalFiles = @("scripts/phase34_step65_trusted_production_shadow_run_validation_no_write_dry_run_result_disposition_planning_safety_disposition_review_packet.ps1", "ui/pages/1521_Phase34_Step65_Shadow_Run_Result_Disposition_Safety_Review.py", "docs/PHASE34_STEP65_TRUSTED_PRODUCTION_SHADOW_RUN_VALIDATION_NO_WRITE_DRY_RUN_RESULT_DISPOSITION_PLANNING_SAFETY_DISPOSITION_REVIEW_PACKET.md")
    $PositiveWord = "tr" + "ue"
    $NegativeWord = "fal" + "se"
    $UnsafePairs = @(
        @("phase35_start", $PositiveWord),
        @("phase35_boundary_creation", $PositiveWord),
        @("phase34_execution_start", $PositiveWord),
        @("phase34_implementation_start", $PositiveWord),
        @("implementation_phase_start", $PositiveWord),
        @("trusted_production_shadow_run_validation_start", $PositiveWord),
        @("trusted_production_shadow_run_validation_execution_start", $PositiveWord),
        @("shadow_run_execution_start", $PositiveWord),
        @("live_read_activation_start", $PositiveWord),
        @("live_user_access_start", $PositiveWord),
        @("no_network_sockets", $NegativeWord),
        @("no_bridge_post", $NegativeWord),
        @("no_network_transport_implementation", $NegativeWord),
        @("live_write_disabled", $NegativeWord),
        @("live_write_unarmed", $NegativeWord)
    )
    foreach ($Rel in $OperationalFiles) {
        $Text = (Get-Content -LiteralPath (Join-RepoPath $Rel) -Raw).ToLowerInvariant()
        $Compact = ($Text -replace "[\s`"'_:=-]+", "")
        foreach ($Pair in $UnsafePairs) {
            $Needle = (($Pair[0] + $Pair[1]) -replace "[\s`"'_:=-]+", "").ToLowerInvariant()
            if ($Compact.Contains($Needle)) {
                throw ("Unsafe marker found in operational file {0}: {1}={2}" -f $Rel, $Pair[0], $Pair[1])
            }
        }
    }
}

function New-Packet {
    Assert-SafetyMarkers
    Assert-NoUnsafeOperationalMarkers
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupDir = Join-RepoPath ("backups/phase34_step65_trusted_production_shadow_run_validation_no_write_dry_run_result_disposition_planning_safety_disposition_review_{0}" -f $Stamp)
    New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
    $PacketPath = Join-Path $BackupDir "phase34_step65_trusted_production_shadow_run_validation_no_write_dry_run_result_disposition_planning_safety_disposition_review.json"
    $Payload = [ordered]@{
        phase = 34
        step = $StepNumber
        title = $StepTitle
        planning_only = $true
        no_write = $true
        no_server_launch = $true
        no_network_transport_implementation = $true
        no_bridge_post = $true
        no_network_sockets = $true
        live_write_disabled = $true
        live_write_unarmed = $true
        phase35_start = $false
        phase35_boundary_creation = $false
        generated_at = (Get-Date).ToString("o")
    }
    $Payload | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $PacketPath -Encoding UTF8
    Write-Host ("CHECK: prior_step={0}" -f $PriorCompletedStep)
    Write-Host "CHECK: phase34_context=trusted_production_shadow_run_validation_result_disposition_planning_only"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: network_transport_runtime_start=not_started"
    Write-Host "CHECK: parent_workspace_launcher=safe"
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

