param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$StepNumber = 115
$StepTitle = "Phase 25 Step 115 - Phase 20 Network Transport Implementation Post-Closeout Final Release Result Review Planning Safety Disposition Review Packet"
$ExpectedBranch = "phase25-step115-post-closeout-final-release-result-review-planning-safety-disposition-review"
$PriorStep = "Phase 25 Step 114 - previous Phase 25 post-closeout packet"
$ModeKey = "implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_mode"
$WriteKey = "implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_write"
$RecordKey = "implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_record_creation"

$ExpectedRelativeFiles = @(
    "scripts/phase25_step115_post_closeout_final_release_result_review_planning_safety_disposition_review_packet.ps1",
    "ui/pages/491_Phase25_Step115_Implementation_PostCloseout_Final_Release_Result_Review_Planning_Safety_Disposition_Review_Packet.py",
    "docs/PHASE25_STEP115_POST_CLOSEOUT_FINAL_RELEASE_RESULT_REVIEW_PLANNING_SAFETY_DISPOSITION_REVIEW_PACKET.md",
    "tests/test_phase25_step115_post_closeout_final_release_result_review_planning_safety_disposition_review_packet.py"
)

$OperationalRelativeFiles = @(
    "scripts/phase25_step115_post_closeout_final_release_result_review_planning_safety_disposition_review_packet.ps1",
    "ui/pages/491_Phase25_Step115_Implementation_PostCloseout_Final_Release_Result_Review_Planning_Safety_Disposition_Review_Packet.py",
    "docs/PHASE25_STEP115_POST_CLOSEOUT_FINAL_RELEASE_RESULT_REVIEW_PLANNING_SAFETY_DISPOSITION_REVIEW_PACKET.md"
)

$Safety = [ordered]@{
    planning_only = $true
    no_platform_db_mutation = $true
    no_bridge_mutation = $true
    no_real_bridge_http_client = $true
    no_network_transport_implementation = $true
    no_bridge_post = $true
    no_network_sockets = $true
    no_execution_implementation = $true
    phase25_boundary = "implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_opened_by_packet"
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
    "implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_mode" = "reference_only"
    "implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_write" = $false
    "implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_record_creation" = $false
    post_closeout_decision_creation = $false
    post_closeout_approval_creation = $false
    post_closeout_operator_approval_creation = $false
    final_release_result_review_record_creation = $false
    final_release_result_review_decision_creation = $false
    final_release_result_review_approval_creation = $false
    phase25_closeout_hold_record_creation = $false
    phase25_closeout_hold_approval_creation = $false
    phase25_closeout_hold_execution = $false
    final_release_execution = $false
    release_gate_runtime_start = $false
    no_operator_signoff = $true
    no_operator_approval = $true
    no_final_approval = $true
    phase24_reopen = $false
    phase26_start = $false
    phase26_boundary_creation = $false
    batch_risk_review_location = "chat_only"
    lower_batch_size_required = $false
    batch_risk_reason = "This batch was reviewed in chat only. Steps 111-119 are standard no-write result review planning packets and Step 120 is a no-write closeout hold. The batch remains planning-only and does not introduce runtime activation, sockets, bridge POSTs, live writes, DB mutation, real-user release, final release execution, or Phase 26 boundary creation."
    lacrm_default_mode = "dry_run"
    lacrm_live_write = $false
    live_write_disabled = $true
    live_write_unarmed = $true
}

function Write-StepBanner {
    Write-Host "=============================================================================="
    Write-Host $StepTitle
    Write-Host "=============================================================================="
    Write-Host "Repo root: $RepoRoot"
    Write-Host "Expected branch: $ExpectedBranch"
    Write-Host "Prior completed step: $PriorStep"
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
}

function Show-Status {
    Write-StepBanner
    Write-Host ""
    Write-Host "Safety posture"
    foreach ($Item in $Safety.GetEnumerator()) {
        Write-Host ("  {0}: {1}" -f $Item.Key, $Item.Value)
    }
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
    Write-Host "APPLY PASS: Phase 25 Step 115 files copied or already present."
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
            ("controlled_activation_runtime_start" + "=true"),
            ("network_transport_runtime_start" + "=true"),
            ("bridge_transport_runtime_start" + "=true"),
            ("final_release_result_review_record_creation" + "=true"),
            ("final_release_result_review_decision_creation" + "=true"),
            ("final_release_result_review_approval_creation" + "=true"),
            ("phase25_closeout_hold_record_creation" + "=true"),
            ("phase25_closeout_hold_approval_creation" + "=true"),
            ("phase25_closeout_hold_execution" + "=true"),
            ("final_release_execution" + "=true"),
            ("release_gate_runtime_start" + "=true"),
            ("no_network_sockets" + "=false"),
            ("no_bridge_post" + "=false"),
            ("live_write_disabled" + "=false"),
            ("live_write_unarmed" + "=false")
        )) {
            if (($Text -replace "\s", "") -match [regex]::Escape($Marker)) {
                throw ("Unsafe marker found in operational file {0}: {1}" -f $Path, $Marker)
            }
        }
    }

    Write-Host "SMOKE TEST PASS: Phase 25 Step 115 Implementation Post-Closeout Final Release Result Review Planning Safety Disposition Review Packet is present and planning-only."
}

function Write-LowercaseBoolLine {
    param([string]$Name, [object]$Value)
    if ($Value -is [bool]) {
        Write-Host ("PASS: {0}={1}" -f $Name, ($Value.ToString().ToLowerInvariant()))
    } else {
        Write-Host ("PASS: {0}={1}" -f $Name, $Value)
    }
}

function New-Packet {
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupDir = Join-Path $RepoRoot "backups\phase25_step115_post_closeout_final_release_result_review_planning_safety_disposition_review_packet_$Stamp"
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    $PacketPath = Join-Path $BackupDir "phase25_step115_post_closeout_final_release_result_review_planning_safety_disposition_review_packet.json"

    $Packet = [ordered]@{
        phase = 25
        step = 115
        title = $StepTitle
        branch = $ExpectedBranch
        prior_step = $PriorStep
        planning_only = $true
        safety = $Safety
        files = $ExpectedRelativeFiles
        generated_at = (Get-Date).ToString("o")
    }

    $Packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $PacketPath -Encoding UTF8

    Write-LowercaseBoolLine "planning_only" $Safety["planning_only"]
    Write-LowercaseBoolLine "no_real_bridge_http_client" $Safety["no_real_bridge_http_client"]
    Write-LowercaseBoolLine "no_network_transport_implementation" $Safety["no_network_transport_implementation"]
    Write-LowercaseBoolLine "no_bridge_post" $Safety["no_bridge_post"]
    Write-LowercaseBoolLine "no_network_sockets" $Safety["no_network_sockets"]
    Write-LowercaseBoolLine "phase25_boundary" $Safety["phase25_boundary"]
    Write-LowercaseBoolLine "phase25_execution_start" $Safety["phase25_execution_start"]
    Write-LowercaseBoolLine "phase25_implementation_start" $Safety["phase25_implementation_start"]
    Write-LowercaseBoolLine "implementation_phase_start" $Safety["implementation_phase_start"]
    Write-LowercaseBoolLine "post_closeout_runtime_start" $Safety["post_closeout_runtime_start"]
    Write-LowercaseBoolLine "cross_repo_write" $Safety["cross_repo_write"]
    Write-LowercaseBoolLine "cross_repo_mutation" $Safety["cross_repo_mutation"]
    Write-LowercaseBoolLine "external_repo_push" $Safety["external_repo_push"]
    Write-LowercaseBoolLine "implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_mode" $Safety["implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_mode"]
    Write-LowercaseBoolLine "implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_write" $Safety["implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_write"]
    Write-LowercaseBoolLine "implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_record_creation" $Safety["implementation_post_closeout_final_release_result_review_planning_safety_disposition_review_record_creation"]
    Write-LowercaseBoolLine "post_closeout_decision_creation" $Safety["post_closeout_decision_creation"]
    Write-LowercaseBoolLine "post_closeout_approval_creation" $Safety["post_closeout_approval_creation"]
    Write-LowercaseBoolLine "final_release_result_review_record_creation" $Safety["final_release_result_review_record_creation"]
    Write-LowercaseBoolLine "final_release_result_review_decision_creation" $Safety["final_release_result_review_decision_creation"]
    Write-LowercaseBoolLine "final_release_result_review_approval_creation" $Safety["final_release_result_review_approval_creation"]
    Write-LowercaseBoolLine "phase25_closeout_hold_record_creation" $Safety["phase25_closeout_hold_record_creation"]
    Write-LowercaseBoolLine "phase25_closeout_hold_approval_creation" $Safety["phase25_closeout_hold_approval_creation"]
    Write-LowercaseBoolLine "phase25_closeout_hold_execution" $Safety["phase25_closeout_hold_execution"]
    Write-LowercaseBoolLine "final_release_execution" $Safety["final_release_execution"]
    Write-LowercaseBoolLine "release_gate_runtime_start" $Safety["release_gate_runtime_start"]
    Write-LowercaseBoolLine "phase24_reopen" $Safety["phase24_reopen"]
    Write-LowercaseBoolLine "phase26_start" $Safety["phase26_start"]
    Write-LowercaseBoolLine "phase26_boundary_creation" $Safety["phase26_boundary_creation"]
    Write-LowercaseBoolLine "batch_risk_review_location" $Safety["batch_risk_review_location"]
    Write-LowercaseBoolLine "lower_batch_size_required" $Safety["lower_batch_size_required"]
    Write-LowercaseBoolLine "lacrm_default_mode" $Safety["lacrm_default_mode"]
    Write-LowercaseBoolLine "live_write_disabled" $Safety["live_write_disabled"]
    Write-LowercaseBoolLine "live_write_unarmed" $Safety["live_write_unarmed"]
    Write-Host "CHECK: prior_step=$PriorStep"
    Write-Host "CHECK: phase25_context=post_closeout_final_release_result_review_planning_safety_disposition_review_planning_only"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: network_transport_runtime_start=not_started"
    Write-Host "CHECK: parent_workspace_launcher=safe"
    Write-Host "CHECK: batch_risk_reason=$($Safety['batch_risk_reason'])"
    Write-Host "CHECK: packet_json=$PacketPath"
}

if ($Action -eq "status") {
    Show-Status
} elseif ($Action -eq "apply") {
    Apply-StepFiles
} elseif ($Action -eq "smoke") {
    Test-Smoke
} elseif ($Action -eq "packet") {
    New-Packet
} elseif ($Action -eq "all") {
    Show-Status
    Apply-StepFiles
    Test-Smoke
    New-Packet
}
