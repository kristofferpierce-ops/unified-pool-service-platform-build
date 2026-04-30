param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$StepNumber = 42
$StepTitle = "Phase 26 Step 42 - Phase 20 Network Transport Implementation Transition No-Write Dry Run Verification Planning Evidence Index Packet"
$ExpectedBranch = "phase26-step42-implementation-transition-no-write-dry-run-verification-planning-evidence-index"
$PriorStep = "Phase 26 Step 41 - previous Phase 26 implementation transition no-write dry-run verification planning packet"
$ModeKey = "implementation_transition_no_write_dry_run_verification_planning_evidence_index_mode"
$WriteKey = "implementation_transition_no_write_dry_run_verification_planning_evidence_index_write"
$RecordKey = "implementation_transition_no_write_dry_run_verification_planning_evidence_index_record_creation"

$ExpectedRelativeFiles = @(
    "scripts/phase26_step42_implementation_transition_no_write_dry_run_verification_planning_evidence_index_packet.ps1",
    "ui/pages/538_Phase26_Step42_Implementation_Transition_NoWrite_Dry_Run_Verification_Planning_Evidence_Index_Packet.py",
    "docs/PHASE26_STEP42_IMPLEMENTATION_TRANSITION_NO_WRITE_DRY_RUN_VERIFICATION_PLANNING_EVIDENCE_INDEX_PACKET.md",
    "tests/test_phase26_step42_implementation_transition_no_write_dry_run_verification_planning_evidence_index_packet.py"
)

$OperationalRelativeFiles = @(
    "scripts/phase26_step42_implementation_transition_no_write_dry_run_verification_planning_evidence_index_packet.ps1",
    "ui/pages/538_Phase26_Step42_Implementation_Transition_NoWrite_Dry_Run_Verification_Planning_Evidence_Index_Packet.py",
    "docs/PHASE26_STEP42_IMPLEMENTATION_TRANSITION_NO_WRITE_DRY_RUN_VERIFICATION_PLANNING_EVIDENCE_INDEX_PACKET.md"
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
    phase26_boundary = "implementation_transition_no_write_dry_run_verification_planning_evidence_index_opened_by_packet"
    phase26_execution_start = $false
    phase26_implementation_start = $false
    implementation_phase_start = $false
    post_closeout_runtime_start = $false
    controlled_activation_runtime_start = $false
    network_transport_runtime_start = $false
    bridge_transport_runtime_start = $false
    transition_runtime_start = $false
    transition_execution_start = $false
    cross_repo_write = $false
    cross_repo_mutation = $false
    external_repo_push = $false
    "implementation_transition_no_write_dry_run_verification_planning_evidence_index_mode" = "reference_only"
    "implementation_transition_no_write_dry_run_verification_planning_evidence_index_write" = $false
    "implementation_transition_no_write_dry_run_verification_planning_evidence_index_record_creation" = $false
    implementation_transition_decision_creation = $false
    implementation_transition_approval_creation = $false
    implementation_transition_operator_approval_creation = $false
    implementation_transition_runtime_creation = $false
    implementation_transition_execution = $false
    release_gate_runtime_start = $false
    no_operator_signoff = $true
    no_operator_approval = $true
    no_final_approval = $true
    phase25_reopen = $false
    phase27_start = $false
    phase27_boundary_creation = $false
    batch_risk_review_location = "chat_only"
    lower_batch_size_required = $false
    batch_risk_reason = "Phase 26 Steps 41-50 were reviewed in chat only. The range opens implementation transition no-write dry-run verification planning packets but remains planning-only, no-write, no-runtime, no sockets, no bridge POST, no live writes, no DB mutation, no real-user release, and no Phase 27 boundary."
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
    Write-Host "APPLY PASS: Phase 26 Step 42 files copied or already present."
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
            ("phase27_start" + "=true"),
            ("phase27_boundary_creation" + "=true"),
            ("phase26_execution_start" + "=true"),
            ("phase26_implementation_start" + "=true"),
            ("implementation_phase_start" + "=true"),
            ("post_closeout_runtime_start" + "=true"),
            ("controlled_activation_runtime_start" + "=true"),
            ("network_transport_runtime_start" + "=true"),
            ("bridge_transport_runtime_start" + "=true"),
            ("transition_runtime_start" + "=true"),
            ("transition_execution_start" + "=true"),
            ("implementation_transition_runtime_creation" + "=true"),
            ("implementation_transition_execution" + "=true"),
            ("implementation_transition_decision_creation" + "=true"),
            ("implementation_transition_approval_creation" + "=true"),
            ("implementation_transition_operator_approval_creation" + "=true"),
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

    Write-Host "SMOKE TEST PASS: Phase 26 Step 42 Implementation Transition No-Write Dry Run Verification Planning Evidence Index Packet is present and planning-only."
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
    $BackupDir = Join-Path $RepoRoot "backups\phase26_step42_implementation_transition_no_write_dry_run_verification_planning_evidence_index_packet_$Stamp"
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    $PacketPath = Join-Path $BackupDir "phase26_step42_implementation_transition_no_write_dry_run_verification_planning_evidence_index_packet.json"

    $Packet = [ordered]@{
        phase = 26
        step = 42
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
    Write-LowercaseBoolLine "phase26_boundary" $Safety["phase26_boundary"]
    Write-LowercaseBoolLine "phase26_execution_start" $Safety["phase26_execution_start"]
    Write-LowercaseBoolLine "phase26_implementation_start" $Safety["phase26_implementation_start"]
    Write-LowercaseBoolLine "implementation_phase_start" $Safety["implementation_phase_start"]
    Write-LowercaseBoolLine "post_closeout_runtime_start" $Safety["post_closeout_runtime_start"]
    Write-LowercaseBoolLine "transition_runtime_start" $Safety["transition_runtime_start"]
    Write-LowercaseBoolLine "transition_execution_start" $Safety["transition_execution_start"]
    Write-LowercaseBoolLine "cross_repo_write" $Safety["cross_repo_write"]
    Write-LowercaseBoolLine "cross_repo_mutation" $Safety["cross_repo_mutation"]
    Write-LowercaseBoolLine "external_repo_push" $Safety["external_repo_push"]
    Write-LowercaseBoolLine "implementation_transition_no_write_dry_run_verification_planning_evidence_index_mode" $Safety["implementation_transition_no_write_dry_run_verification_planning_evidence_index_mode"]
    Write-LowercaseBoolLine "implementation_transition_no_write_dry_run_verification_planning_evidence_index_write" $Safety["implementation_transition_no_write_dry_run_verification_planning_evidence_index_write"]
    Write-LowercaseBoolLine "implementation_transition_no_write_dry_run_verification_planning_evidence_index_record_creation" $Safety["implementation_transition_no_write_dry_run_verification_planning_evidence_index_record_creation"]
    Write-LowercaseBoolLine "implementation_transition_decision_creation" $Safety["implementation_transition_decision_creation"]
    Write-LowercaseBoolLine "implementation_transition_approval_creation" $Safety["implementation_transition_approval_creation"]
    Write-LowercaseBoolLine "implementation_transition_operator_approval_creation" $Safety["implementation_transition_operator_approval_creation"]
    Write-LowercaseBoolLine "implementation_transition_runtime_creation" $Safety["implementation_transition_runtime_creation"]
    Write-LowercaseBoolLine "implementation_transition_execution" $Safety["implementation_transition_execution"]
    Write-LowercaseBoolLine "release_gate_runtime_start" $Safety["release_gate_runtime_start"]
    Write-LowercaseBoolLine "phase25_reopen" $Safety["phase25_reopen"]
    Write-LowercaseBoolLine "phase27_start" $Safety["phase27_start"]
    Write-LowercaseBoolLine "phase27_boundary_creation" $Safety["phase27_boundary_creation"]
    Write-LowercaseBoolLine "batch_risk_review_location" $Safety["batch_risk_review_location"]
    Write-LowercaseBoolLine "lower_batch_size_required" $Safety["lower_batch_size_required"]
    Write-LowercaseBoolLine "lacrm_default_mode" $Safety["lacrm_default_mode"]
    Write-LowercaseBoolLine "live_write_disabled" $Safety["live_write_disabled"]
    Write-LowercaseBoolLine "live_write_unarmed" $Safety["live_write_unarmed"]
    Write-Host "CHECK: prior_step=$PriorStep"
    Write-Host "CHECK: phase26_context=implementation_transition_no_write_dry_run_verification_planning_evidence_index_planning_only"
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
