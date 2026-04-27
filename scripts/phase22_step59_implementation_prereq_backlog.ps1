param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$StepNumber = "59"
$PhaseStep = "Phase 22 Step 59"
$StepTitle = "Phase 22 Step 59 - Phase 20 Network Transport Planning Implementation Prerequisite Backlog Packet"
$PacketName = "Phase 20 Network Transport Planning Implementation Prerequisite Backlog Packet"
$ExpectedBranch = "phase22-step59-implementation-prereq-backlog"
$PriorCompletedStep = "Phase 22 Step 58 - Phase 20 Network Transport Planning Completeness Index Packet"

$StepFiles = @(
    "scripts/phase22_step59_implementation_prereq_backlog.ps1",
    "ui/pages/165_Phase22_Step59_Implementation_Prereq_Backlog.py",
    "docs/PHASE22_STEP59_IMPLEMENTATION_PREREQ_BACKLOG_PACKET.md",
    "tests/test_phase22_step59_implementation_prereq_backlog.py"
)

function Normalize-RelativePath {
    param([Parameter(Mandatory=$true)][string]$RelativePath)

    $value = $RelativePath.Replace("/", "\").Trim().TrimStart("\")
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Relative path is empty."
    }
    if ($value.Contains(":")) {
        throw "Relative path must not contain a drive designator: $RelativePath"
    }
    foreach ($part in $value.Split("\")) {
        if ($part -eq "..") {
            throw "Relative path must not contain parent traversal: $RelativePath"
        }
    }
    return $value
}

function Join-SafePath {
    param(
        [Parameter(Mandatory=$true)][string]$Root,
        [Parameter(Mandatory=$true)][string]$RelativePath
    )

    $normalized = Normalize-RelativePath -RelativePath $RelativePath
    return [System.IO.Path]::GetFullPath((Join-Path -Path $Root -ChildPath $normalized))
}

function Resolve-RepoRoot {
    param([string]$RequestedRoot)

    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($RequestedRoot)) {
        $candidates += $RequestedRoot
    }
    $candidates += (Get-Location).Path
    $scriptParent = Split-Path -Parent $PSCommandPath
    $candidates += $scriptParent
    $candidates += (Join-Path $scriptParent "..")

    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }
        $full = [System.IO.Path]::GetFullPath($candidate)
        if (Test-Path -LiteralPath (Join-Path $full ".git")) {
            return $full
        }
    }

    throw "Could not resolve repo root. Pass -RepoRoot explicitly."
}

$ResolvedRepoRoot = Resolve-RepoRoot -RequestedRoot $RepoRoot

function Write-Header {
    Write-Host "=============================================================================="
    Write-Host $StepTitle
    Write-Host "=============================================================================="
}

function Get-SafetyPosture {
    [ordered]@{
        planning_only = $true
        no_platform_db_mutation = $true
        no_bridge_mutation = $true
        no_real_bridge_http_client = $true
        no_network_transport_implementation = $true
        no_bridge_post = $true
        no_network_sockets = $true
        no_execution_implementation = $true
        implementation_phase_start = $false
        authorization_record_creation = $false
        operator_signoff_creation = $false
        operator_approval_creation = $false
        final_approval_creation = $false
        design_closure_record_creation = $false
        closure_review_record_creation = $false
        closure_decision_creation = $false
        closure_resolution_disposition_creation = $false
        closure_resolution_disposition_approval_creation = $false
        handoff_record_creation = $false
        handoff_queue_creation = $false
        handoff_verification_record_creation = $false
        handoff_verification_review_creation = $false
        handoff_verification_review_disposition_creation = $false
        planning_completeness_index_record_creation = $false
        planning_completeness_index_approval_creation = $false
        implementation_prerequisite_backlog_record_creation = $false
        implementation_prerequisite_backlog_queue_creation = $false
        implementation_prerequisite_backlog_approval_creation = $false
        implementation_prerequisite_backlog_mutation = $false
        implementation_prerequisite_queue_creation = $false
        implementation_prerequisite_execution = $false
        implementation_ready_transition = $false
        phase22_closeout_creation = $false
        phase23_start_boundary_creation = $false
        no_operator_signoff = $true
        no_operator_approval = $true
        no_final_approval = $true
        no_design_closure_record_creation = $true
        lacrm_default_mode = "dry_run"
        lacrm_live_write = $false
        live_write_disabled = $true
        live_write_unarmed = $true
        source_bucket_writes = $false
        applied_layer_mutation = $false
        review_gate_mutation = $false
    }
}

function Assert-SafetyPosture {
    $posture = Get-SafetyPosture

    $trueGuards = @(
        "planning_only",
        "no_platform_db_mutation",
        "no_bridge_mutation",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "no_execution_implementation",
        "no_operator_signoff",
        "no_operator_approval",
        "no_final_approval",
        "no_design_closure_record_creation",
        "live_write_disabled",
        "live_write_unarmed"
    )
    foreach ($key in $trueGuards) {
        if ($posture[$key] -ne $true) {
            throw "Safety posture failed: $key"
        }
    }

    $falseGuards = @(
        "implementation_phase_start",
        "authorization_record_creation",
        "operator_signoff_creation",
        "operator_approval_creation",
        "final_approval_creation",
        "design_closure_record_creation",
        "closure_review_record_creation",
        "closure_decision_creation",
        "closure_resolution_disposition_creation",
        "closure_resolution_disposition_approval_creation",
        "handoff_record_creation",
        "handoff_queue_creation",
        "handoff_verification_record_creation",
        "handoff_verification_review_creation",
        "handoff_verification_review_disposition_creation",
        "planning_completeness_index_record_creation",
        "planning_completeness_index_approval_creation",
        "implementation_prerequisite_backlog_record_creation",
        "implementation_prerequisite_backlog_queue_creation",
        "implementation_prerequisite_backlog_approval_creation",
        "implementation_prerequisite_backlog_mutation",
        "implementation_prerequisite_queue_creation",
        "implementation_prerequisite_execution",
        "implementation_ready_transition",
        "phase22_closeout_creation",
        "phase23_start_boundary_creation",
        "lacrm_live_write",
        "source_bucket_writes",
        "applied_layer_mutation",
        "review_gate_mutation"
    )
    foreach ($key in $falseGuards) {
        if ($posture[$key] -ne $false) {
            throw "Safety posture failed: $key"
        }
    }

    if ($posture.lacrm_default_mode -ne "dry_run") {
        throw "Safety posture failed: lacrm_default_mode"
    }
}

function Show-Status {
    Write-Header
    Write-Host "Repo root: $ResolvedRepoRoot"
    Write-Host "Expected branch: $ExpectedBranch"
    Write-Host "Prior completed step: $PriorCompletedStep"
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    $posture = Get-SafetyPosture
    foreach ($key in $posture.Keys) {
        Write-Host ("  {0}: {1}" -f $key, $posture[$key])
    }
    Write-Host ""
    Write-Host "Step files"
    foreach ($relative in $StepFiles) {
        $path = Join-SafePath -Root $ResolvedRepoRoot -RelativePath $relative
        if (Test-Path -LiteralPath $path) {
            Write-Host "  PRESENT $relative"
        } else {
            Write-Host "  MISSING $relative"
        }
    }
}

function Invoke-Apply {
    foreach ($relative in $StepFiles) {
        $sourcePath = Join-SafePath -Root $ResolvedRepoRoot -RelativePath $relative
        $targetPath = Join-SafePath -Root $ResolvedRepoRoot -RelativePath $relative
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            throw "Missing source file: $sourcePath"
        }
        if ([System.IO.Path]::GetFullPath($sourcePath) -eq [System.IO.Path]::GetFullPath($targetPath)) {
            Write-Host "SKIPPED $relative source and target are the same file."
            continue
        }
        $targetDir = Split-Path -Parent $targetPath
        if (-not (Test-Path -LiteralPath $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
        Write-Host "COPIED $relative"
    }
    Write-Host "APPLY PASS: Phase 22 Step 59 files copied or already present."
}

function Invoke-Smoke {
    foreach ($relative in $StepFiles) {
        $path = Join-SafePath -Root $ResolvedRepoRoot -RelativePath $relative
        if (-not (Test-Path -LiteralPath $path)) {
            throw "SMOKE TEST FAIL: Missing required file $relative"
        }
    }

    Assert-SafetyPosture

    Write-Host "SMOKE TEST PASS: Phase 22 Step 59 Phase 20 Network Transport Planning Implementation Prerequisite Backlog Packet is present and planning-only."
}

function Invoke-Packet {
    Assert-SafetyPosture
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $packetDir = Join-SafePath -Root $ResolvedRepoRoot -RelativePath ("backups/phase22_step59_implementation_prereq_backlog_packet_" + $timestamp)
    if (-not (Test-Path -LiteralPath $packetDir)) {
        New-Item -ItemType Directory -Path $packetDir -Force | Out-Null
    }
    $packetPath = Join-Path $packetDir "phase22_step59_implementation_prereq_backlog_packet.json"

    $packet = [ordered]@{
        phase_step = $PhaseStep
        step_number = $StepNumber
        packet_name = $PacketName
        prior_completed_step = $PriorCompletedStep
        planning_only = $true
        source_bucket_alignment = "raw_normalized_matched_approved_applied"
        connector_first_operating_core = $true
        bridge_absorption_target = "connector_package_not_separate_product"
        completeness_index_reference = "Phase 22 Step 58"
        implementation_prerequisite_backlog = "planned_only"
        implementation_prerequisite_backlog_record_creation = $false
        implementation_prerequisite_backlog_queue_creation = $false
        implementation_prerequisite_execution = $false
        implementation_ready_transition = $false
        phase22_closeout_creation = $false
        phase23_start_boundary_creation = $false
        safety_posture = Get-SafetyPosture
        step_files = $StepFiles
    }

    $packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $packetPath -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "PASS: implementation_prerequisite_backlog=planned_only"
    Write-Host "CHECK: implementation_prerequisite_backlog_record_creation=false"
    Write-Host "CHECK: implementation_prerequisite_backlog_queue_creation=false"
    Write-Host "CHECK: implementation_prerequisite_execution=false"
    Write-Host "CHECK: implementation_ready_transition=false"
    Write-Host "CHECK: phase22_closeout_creation=false"
    Write-Host "CHECK: phase23_start_boundary_creation=false"
    Write-Host "CHECK: packet_json=$packetPath"
}

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, or network socket is started here."
    Write-Host "CHECK: Implementation prerequisite backlog work remains planned-only here."
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "Phase 22 Step 59 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 22 Step 59 Implementation Prerequisite Backlog Packet files"
        Write-Host "3. Smoke test Phase 22 Step 59"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 20 network transport planning implementation prerequisite backlog packet"
        Write-Host "6. Exit"
        $choice = Read-Host "Choose 1-6"
        switch ($choice.Trim()) {
            "1" { Show-Status }
            "2" { Invoke-Apply }
            "3" { Invoke-Smoke }
            "4" { Show-ServerPlaceholder }
            "5" { Invoke-Packet }
            "6" { return }
            default { Write-Host "Invalid choice." }
        }
    }
}

switch ($Action) {
    "status" { Show-Status }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "packet" { Invoke-Packet }
    "all" {
        Show-Status
        Invoke-Apply
        Invoke-Smoke
        Invoke-Packet
    }
    default { Show-Menu }
}

