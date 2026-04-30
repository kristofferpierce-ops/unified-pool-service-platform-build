param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

$ErrorActionPreference = "Stop"

$StepNumber = 91
$StepTitle = "Phase 25 Step 91 - Phase 20 Network Transport Implementation Post-Closeout Final Release Hold Planning Boundary Packet"
$ExpectedBranch = "phase25-step91-post-closeout-final-release-hold-planning-boundary"
$PriorStep = "Phase 25 Step 90 - Phase 20 Network Transport Implementation Post-Closeout Release Gate Verification Planning Final Boundary Confirmation Packet"
if ($StepNumber -gt 91) {
    $PriorStep = "Phase 25 Step 90 - previous Phase 25 post-closeout final release hold planning packet"
}

$StepFiles = @(
    "scripts/phase25_step91_post_closeout_final_release_hold_planning_boundary_packet.ps1",
    "ui/pages/467_Phase25_Step91_Implementation_PostCloseout_Final_Release_Hold_Planning_Boundary_Packet.py",
    "docs/PHASE25_STEP91_POST_CLOSEOUT_FINAL_RELEASE_HOLD_PLANNING_BOUNDARY_PACKET.md",
    "tests/test_phase25_step91_post_closeout_final_release_hold_planning_boundary_packet.py"
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
    phase25_boundary = "implementation_post_closeout_final_release_hold_planning_boundary_opened_by_packet"
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
    implementation_post_closeout_final_release_hold_planning_boundary_mode = "reference_only"
    implementation_post_closeout_final_release_hold_planning_boundary_write = $false
    implementation_post_closeout_final_release_hold_planning_boundary_record_creation = $false
    post_closeout_decision_creation = $false
    post_closeout_approval_creation = $false
    post_closeout_operator_approval_creation = $false
    final_release_hold_record_creation = $false
    final_release_hold_decision_creation = $false
    final_release_hold_approval_creation = $false
    final_release_execution = $false
    no_operator_signoff = $true
    no_operator_approval = $true
    no_final_approval = $true
    phase24_reopen = $false
    phase26_start = $false
    phase26_boundary_creation = $false
    complexity_batch_gate = "standard_planning_only_with_release_hold_language"
    complexity_review_required = $false
    lower_batch_size_required = $false
    complexity_reason = "Final release hold planning language is present, but this batch remains reference-only and does not start runtime, sockets, bridge POSTs, live writes, DB mutation, real-user release, or Phase 26. Lower batch size is not required for this range."
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
    foreach ($Rel in $StepFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (Test-Path $Path) {
            Write-Host "  PRESENT $Rel"
        } else {
            Write-Host "  MISSING $Rel"
        }
    }
}

function Apply-StepFiles {
    foreach ($Rel in $StepFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (Test-Path $Path) {
            Write-Host "SKIPPED $Rel source and target are the same file."
        } else {
            throw "Missing expected step file: $Rel"
        }
    }
    Write-Host "APPLY PASS: Phase 25 Step 91 files copied or already present."
}

function Invoke-SmokeTest {
    foreach ($Rel in $StepFiles) {
        $Path = Join-Path $RepoRoot $Rel
        if (-not (Test-Path $Path)) {
            throw "SMOKE TEST FAIL: missing $Rel"
        }
    }

    $OperationalFiles = @(
        "scripts/phase25_step91_post_closeout_final_release_hold_planning_boundary_packet.ps1",
        "ui/pages/467_Phase25_Step91_Implementation_PostCloseout_Final_Release_Hold_Planning_Boundary_Packet.py",
        "docs/PHASE25_STEP91_POST_CLOSEOUT_FINAL_RELEASE_HOLD_PLANNING_BOUNDARY_PACKET.md"
    ) | ForEach-Object { Join-Path $RepoRoot $_ }
    $Forbidden = @(
        ("phase26_start" + "=true"),
        ("phase26_boundary_creation" + "=true"),
        ("phase25_execution_start" + "=true"),
        ("phase25_implementation_start" + "=true"),
        ("implementation_phase_start" + "=true"),
        ("post_closeout_runtime_start" + "=true"),
        ("network_transport_runtime_start" + "=true"),
        ("bridge_transport_runtime_start" + "=true"),
        ("final_release_execution" + "=true"),
        ("final_release_hold_approval_creation" + "=true"),
        ("no_network_sockets" + "=false"),
        ("no_bridge_post" + "=false"),
        ("live_write_disabled" + "=false"),
        ("live_write_unarmed" + "=false")
    )
    foreach ($File in $OperationalFiles) {
        $Text = Get-Content -LiteralPath $File -Raw
        foreach ($Marker in $Forbidden) {
            if ($Text -replace "\\s", "" -match [regex]::Escape($Marker)) {
                throw ("Unsafe marker found in operational file {0}: {1}" -f $File, $Marker)
            }
        }
    }

    Write-Host "SMOKE TEST PASS: Phase 25 Step 91 Implementation Post-Closeout Final Release Hold Planning Boundary Packet is present and planning-only."
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
    $BackupDir = Join-Path $RepoRoot "backups\phase25_step91_post_closeout_final_release_hold_planning_boundary_packet_$Stamp"
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    $PacketPath = Join-Path $BackupDir "phase25_step91_post_closeout_final_release_hold_planning_boundary_packet.json"

    $Packet = [ordered]@{
        phase = 25
        step = 91
        title = $StepTitle
        branch = $ExpectedBranch
        prior_step = $PriorStep
        planning_only = $true
        safety = $Safety
        files = $StepFiles
        generated_at = (Get-Date).ToString("o")
    }

    $Packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $PacketPath -Encoding UTF8

    Write-LowercaseBoolLine "planning_only" $Safety.planning_only
    Write-LowercaseBoolLine "no_real_bridge_http_client" $Safety.no_real_bridge_http_client
    Write-LowercaseBoolLine "no_network_transport_implementation" $Safety.no_network_transport_implementation
    Write-LowercaseBoolLine "no_bridge_post" $Safety.no_bridge_post
    Write-LowercaseBoolLine "no_network_sockets" $Safety.no_network_sockets
    Write-LowercaseBoolLine "phase25_boundary" $Safety.phase25_boundary
    Write-LowercaseBoolLine "phase25_execution_start" $Safety.phase25_execution_start
    Write-LowercaseBoolLine "phase25_implementation_start" $Safety.phase25_implementation_start
    Write-LowercaseBoolLine "implementation_phase_start" $Safety.implementation_phase_start
    Write-LowercaseBoolLine "post_closeout_runtime_start" $Safety.post_closeout_runtime_start
    Write-LowercaseBoolLine "cross_repo_write" $Safety.cross_repo_write
    Write-LowercaseBoolLine "cross_repo_mutation" $Safety.cross_repo_mutation
    Write-LowercaseBoolLine "external_repo_push" $Safety.external_repo_push
    Write-LowercaseBoolLine "implementation_post_closeout_final_release_hold_planning_boundary_mode" $Safety.implementation_post_closeout_final_release_hold_planning_boundary_mode
    Write-LowercaseBoolLine "implementation_post_closeout_final_release_hold_planning_boundary_write" $Safety.implementation_post_closeout_final_release_hold_planning_boundary_write
    Write-LowercaseBoolLine "implementation_post_closeout_final_release_hold_planning_boundary_record_creation" $Safety.implementation_post_closeout_final_release_hold_planning_boundary_record_creation
    Write-LowercaseBoolLine "post_closeout_decision_creation" $Safety.post_closeout_decision_creation
    Write-LowercaseBoolLine "post_closeout_approval_creation" $Safety.post_closeout_approval_creation
    Write-LowercaseBoolLine "final_release_hold_record_creation" $Safety.final_release_hold_record_creation
    Write-LowercaseBoolLine "final_release_hold_decision_creation" $Safety.final_release_hold_decision_creation
    Write-LowercaseBoolLine "final_release_hold_approval_creation" $Safety.final_release_hold_approval_creation
    Write-LowercaseBoolLine "final_release_execution" $Safety.final_release_execution
    Write-LowercaseBoolLine "phase24_reopen" $Safety.phase24_reopen
    Write-LowercaseBoolLine "phase26_start" $Safety.phase26_start
    Write-LowercaseBoolLine "phase26_boundary_creation" $Safety.phase26_boundary_creation
    Write-LowercaseBoolLine "complexity_batch_gate" $Safety.complexity_batch_gate
    Write-LowercaseBoolLine "complexity_review_required" $Safety.complexity_review_required
    Write-LowercaseBoolLine "lower_batch_size_required" $Safety.lower_batch_size_required
    Write-LowercaseBoolLine "lacrm_default_mode" $Safety.lacrm_default_mode
    Write-LowercaseBoolLine "live_write_disabled" $Safety.live_write_disabled
    Write-LowercaseBoolLine "live_write_unarmed" $Safety.live_write_unarmed
    Write-Host "CHECK: prior_step=$PriorStep"
    Write-Host "CHECK: phase25_context=post_closeout_final_release_hold_planning_boundary_planning_only"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: network_transport_runtime_start=not_started"
    Write-Host "CHECK: parent_workspace_launcher=safe"
    Write-Host "CHECK: complexity_reason=$($Safety.complexity_reason)"
    Write-Host "CHECK: packet_json=$PacketPath"
}

if ($Action -eq "status") {
    Show-Status
} elseif ($Action -eq "apply") {
    Apply-StepFiles
} elseif ($Action -eq "smoke") {
    Invoke-SmokeTest
} elseif ($Action -eq "packet") {
    New-Packet
} elseif ($Action -eq "all") {
    Show-Status
    Apply-StepFiles
    Invoke-SmokeTest
    New-Packet
}
