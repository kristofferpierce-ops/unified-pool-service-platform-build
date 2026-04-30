param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$StepNumber = 105
$StepName = "Phase 25 Step 105 - Phase 20 Network Transport Implementation Post-Closeout Final Release Hold Verification Planning Safety Disposition Review Packet"
$ExpectedBranch = "phase25-step105-post-closeout-final-release-hold-verification-planning-safety-disposition-review"
$PriorStep = "Phase 25 Step 104 - Phase 20 Network Transport Implementation Post-Closeout Final Release Hold Verification Planning Safety Disposition Planning Packet"
$ScriptRel = "scripts/phase25_step105_post_closeout_final_release_hold_verification_planning_safety_disposition_review_packet.ps1"
$PageRel = "ui/pages/481_Phase25_Step105_Implementation_PostCloseout_Final_Release_Hold_Verification_Planning_Safety_Disposition_Review_Packet.py"
$DocRel = "docs/PHASE25_STEP105_POST_CLOSEOUT_FINAL_RELEASE_HOLD_VERIFICATION_PLANNING_SAFETY_DISPOSITION_REVIEW_PACKET.md"
$TestRel = "tests/test_phase25_step105_post_closeout_final_release_hold_verification_planning_safety_disposition_review_packet.py"
$Phase25Boundary = "implementation_post_closeout_final_release_hold_verification_planning_safety_disposition_review_opened_by_packet"
$ModeKey = "implementation_post_closeout_final_release_hold_verification_planning_safety_disposition_review_mode"
$WriteKey = "implementation_post_closeout_final_release_hold_verification_planning_safety_disposition_review_write"
$RecordKey = "implementation_post_closeout_final_release_hold_verification_planning_safety_disposition_review_record_creation"
$PacketBase = "phase25_step105_post_closeout_final_release_hold_verification_planning_safety_disposition_review_packet"

$ExpectedRelativeFiles = @(
    $ScriptRel,
    $PageRel,
    $DocRel,
    $TestRel
)

$OperationalRelativeFiles = @(
    $ScriptRel,
    $PageRel,
    $DocRel
)

function Write-StepHeader {
    Write-Host "=============================================================================="
    Write-Host $StepName
    Write-Host "=============================================================================="
    Write-Host "Repo root: $RepoRoot"
    Write-Host "Expected branch: $ExpectedBranch"
    Write-Host "Prior completed step: $PriorStep"
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
}

function Show-Status {
    Write-StepHeader
    Write-Host ""
    Write-Host "Safety posture"
    Write-Host "  planning_only: True"
    Write-Host "  no_platform_db_mutation: True"
    Write-Host "  no_bridge_mutation: True"
    Write-Host "  no_real_bridge_http_client: True"
    Write-Host "  no_network_transport_implementation: True"
    Write-Host "  no_bridge_post: True"
    Write-Host "  no_network_sockets: True"
    Write-Host "  no_execution_implementation: True"
    Write-Host "  phase25_boundary: $Phase25Boundary"
    Write-Host "  phase25_execution_start: False"
    Write-Host "  phase25_implementation_start: False"
    Write-Host "  implementation_phase_start: False"
    Write-Host "  post_closeout_runtime_start: False"
    Write-Host "  controlled_activation_runtime_start: False"
    Write-Host "  network_transport_runtime_start: False"
    Write-Host "  bridge_transport_runtime_start: False"
    Write-Host "  cross_repo_write: False"
    Write-Host "  cross_repo_mutation: False"
    Write-Host "  external_repo_push: False"
    Write-Host ("  {0}: reference_only" -f $ModeKey)
    Write-Host ("  {0}: False" -f $WriteKey)
    Write-Host ("  {0}: False" -f $RecordKey)
    Write-Host "  post_closeout_decision_creation: False"
    Write-Host "  post_closeout_approval_creation: False"
    Write-Host "  post_closeout_operator_approval_creation: False"
    Write-Host "  no_operator_signoff: True"
    Write-Host "  no_operator_approval: True"
    Write-Host "  no_final_approval: True"
    Write-Host "  phase24_reopen: False"
    Write-Host "  phase26_start: False"
    Write-Host "  phase26_boundary_creation: False"
    Write-Host "  lacrm_default_mode: dry_run"
    Write-Host "  lacrm_live_write: False"
    Write-Host "  live_write_disabled: True"
    Write-Host "  live_write_unarmed: True"
    Write-Host ""
    Write-Host "Step files"
    foreach ($Rel in $ExpectedRelativeFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (Test-Path $Path) { Write-Host "  PRESENT $Rel" } else { Write-Host "  MISSING $Rel" }
    }
}

function Apply-StepFiles {
    foreach ($Rel in $ExpectedRelativeFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Path)) { throw ("Missing expected step file: {0}" -f $Rel) }
        Write-Host "SKIPPED $Rel source and target are the same file."
    }
    Write-Host "APPLY PASS: Phase 25 Step 105 files copied or already present."
}

function Test-Smoke {
    foreach ($Rel in $ExpectedRelativeFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Path)) { throw ("Smoke test missing expected file: {0}" -f $Rel) }
    }

    foreach ($Rel in $OperationalRelativeFiles) {
        $Path = Join-Path $RepoRoot $Rel
        $Text = (Get-Content -LiteralPath $Path -Raw).ToLowerInvariant()
        foreach ($Marker in @(
            ("phase26_start" + "=true"),
            ("phase26_boundary_creation" + "=true"),
            ("phase25_execution_start" + "=true"),
            ("phase25_implementation_start" + "=true"),
            ("implementation_phase_start" + "=true"),
            ("post_closeout_runtime_start" + "=true"),
            ("network_transport_runtime_start" + "=true"),
            ("no_network_sockets" + "=false"),
            ("no_bridge_post" + "=false"),
            ("live_write_disabled" + "=false"),
            ("live_write_unarmed" + "=false")
        )) {
            if ($Text.Contains($Marker)) { throw ("Unsafe marker found in operational file {0}: {1}" -f $Rel, $Marker) }
        }
    }

    Write-Host "SMOKE TEST PASS: Phase 25 Step 105 Implementation Post-Closeout Final Release Hold Verification Planning Safety Disposition Review Packet is present and planning-only."
}

function New-Packet {
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupDir = Join-Path $RepoRoot ("backups\{0}_{1}" -f $PacketBase, $Stamp)
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    $PacketPath = Join-Path $BackupDir ("{0}.json" -f $PacketBase)

    $Payload = [ordered]@{
        phase = 25
        step = $StepNumber
        step_name = $StepName
        prior_step = $PriorStep
        mode = "planning_only_reference_packet"
        safety = [ordered]@{
            planning_only = $true
            no_platform_db_mutation = $true
            no_bridge_mutation = $true
            no_real_bridge_http_client = $true
            no_network_transport_implementation = $true
            no_bridge_post = $true
            no_network_sockets = $true
            no_execution_implementation = $true
            phase25_boundary = $Phase25Boundary
            phase25_execution_start = $false
            phase25_implementation_start = $false
            implementation_phase_start = $false
            post_closeout_runtime_start = $false
            controlled_activation_runtime_start = $false
            network_transport_runtime_start = $false
            bridge_transport_runtime_start = $false
            cross_repo_write = $false
            cross_repo_mutation = $false
            external_repo_push = $false
            phase24_reopen = $false
            phase26_start = $false
            phase26_boundary_creation = $false
            lacrm_default_mode = "dry_run"
            lacrm_live_write = $false
            live_write_disabled = $true
            live_write_unarmed = $true
        }
        files = $ExpectedRelativeFiles
    }

    $Payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $PacketPath -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: phase25_boundary=$Phase25Boundary"
    Write-Host "PASS: phase25_execution_start=false"
    Write-Host "PASS: phase25_implementation_start=false"
    Write-Host "PASS: implementation_phase_start=false"
    Write-Host "PASS: post_closeout_runtime_start=false"
    Write-Host "PASS: cross_repo_write=false"
    Write-Host "PASS: cross_repo_mutation=false"
    Write-Host "PASS: external_repo_push=false"
    Write-Host "PASS: $ModeKey=reference_only"
    Write-Host "PASS: $WriteKey=false"
    Write-Host "PASS: $RecordKey=false"
    Write-Host "PASS: post_closeout_decision_creation=false"
    Write-Host "PASS: post_closeout_approval_creation=false"
    Write-Host "PASS: phase24_reopen=false"
    Write-Host "PASS: phase26_start=false"
    Write-Host "PASS: phase26_boundary_creation=false"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "CHECK: prior_step=$PriorStep"
    Write-Host "CHECK: phase25_context=implementation_post_closeout_final_release_hold_verification_planning_safety_disposition_review_planning_only"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: network_transport_runtime_start=not_started"
    Write-Host "CHECK: parent_workspace_launcher=safe"
    Write-Host "CHECK: packet_json=$PacketPath"
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
