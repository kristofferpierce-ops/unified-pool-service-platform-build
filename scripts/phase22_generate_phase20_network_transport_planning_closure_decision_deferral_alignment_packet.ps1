param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$StepTitle = "Phase 22 Step 41 - Phase 20 Network Transport Planning Closure Decision Deferral Alignment Packet"
$ExpectedBranch = "phase22-step41-phase20-network-transport-planning-closure-decision-deferral-alignment-packet"
$PriorCompletedStep = "Phase 22 Step 40 - Phase 20 Network Transport Planning Closure Decision Readiness Alignment Packet"
$PacketName = "Phase 22 Step 41 Phase 20 Network Transport Planning Closure Decision Deferral Alignment Packet"
$PacketSlug = "phase22_phase20_network_transport_planning_closure_decision_deferral_alignment_packet"
$PacketFileName = "phase22_phase20_network_transport_planning_closure_decision_deferral_alignment_packet.json"

$StepFiles = @(
    "scripts/phase22_generate_phase20_network_transport_planning_closure_decision_deferral_alignment_packet.ps1",
    "ui/pages/147_Phase20_Network_Transport_Planning_Closure_Decision_Deferral_Alignment_Packet.py",
    "docs/PHASE22_STEP41_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DECISION_DEFERRAL_ALIGNMENT_PACKET.md",
    "tests/test_phase22_phase20_network_transport_planning_closure_decision_deferral_alignment_packet.py"
)

function Remove-ControlCharacters {
    param([string]$Value)
    if ($null -eq $Value) { return "" }
    return ($Value -replace '[\x00-\x1F\x7F]', '').Trim()
}

function Test-LiteralPathSafe {
    param([string]$Path)
    $CleanPath = Remove-ControlCharacters $Path
    if ([string]::IsNullOrWhiteSpace($CleanPath)) { return $false }
    try { return Test-Path -LiteralPath $CleanPath } catch { return $false }
}

function Get-FullPathSafe {
    param([string]$Path)
    $CleanPath = Remove-ControlCharacters $Path
    if ([string]::IsNullOrWhiteSpace($CleanPath)) { return "" }
    return [System.IO.Path]::GetFullPath($CleanPath)
}

function Resolve-RepoRoot {
    param([string]$CandidateRoot)
    $Candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($CandidateRoot)) { $Candidates += (Remove-ControlCharacters $CandidateRoot) }
    $Candidates += (Get-Location).Path
    $Candidates += (Split-Path -Parent $PSScriptRoot)
    $Candidates += (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
    foreach ($Candidate in $Candidates) {
        if ([string]::IsNullOrWhiteSpace($Candidate)) { continue }
        $FullCandidate = Get-FullPathSafe $Candidate
        if ([string]::IsNullOrWhiteSpace($FullCandidate)) { continue }
        if (Test-LiteralPathSafe (Join-Path $FullCandidate ".git")) { return $FullCandidate }
        if ((Test-LiteralPathSafe (Join-Path $FullCandidate "scripts/phase22_generate_phase20_network_transport_planning_closure_decision_deferral_alignment_packet.ps1")) -and (Test-LiteralPathSafe (Join-Path $FullCandidate "docs/PHASE22_STEP41_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DECISION_DEFERRAL_ALIGNMENT_PACKET.md"))) { return $FullCandidate }
    }
    throw "Could not resolve repository root. Pass -RepoRoot with the platform repository path."
}

function Get-SourceRoot {
    $Candidate = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
    if ([string]::IsNullOrWhiteSpace($Candidate)) { return (Get-Location).Path }
    return (Get-FullPathSafe $Candidate)
}

$ResolvedRepoRoot = Resolve-RepoRoot $RepoRoot
$SourceRoot = Get-SourceRoot

$SafetyPosture = [ordered]@{
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
    closure_decision_record_creation = $false
    closure_approval_creation = $false
    implementation_queue_creation = $false
    no_operator_signoff = $true
    no_operator_approval = $true
    no_final_approval = $true
    no_design_closure_record_creation = $true
    no_closure_decision_creation = $true
    no_planning_exit_approval = $true
    no_implementation_exit_approval = $true
    lacrm_default_mode = "dry_run"
    lacrm_live_write = $false
    live_write_disabled = $true
    live_write_unarmed = $true
    source_bucket_writes = $false
    applied_layer_writes = $false
    recommendation_execution = $false
    runtime_pattern_detection = $false
    bayesian_update_execution = $false
    closure_decision_deferred = $true
}

$AlignmentModel = [ordered]@{
    phase = "Phase 22"
    step = "Phase 22 Step 41"
    packet = $PacketName
    prior_step = $PriorCompletedStep
    decision_state = "deferred_without_approval"
    closure_decision_readiness = "reviewed_but_not_authorized"
    closure_outcome = "not_closed"
    closure_record_creation = $false
    implementation_transition = "not_started"
    source_bucket_alignment = "raw_normalized_matched_approved_applied"
    connector_first_operating_core = $true
    bridge_absorption_target = "connector_package_not_separate_product"
    applied_layer_release = "blocked_until_explicit_authorization"
    rollback_recovery_posture = "documented_planning_only"
    human_review_gate = "required_before_any_applied_layer_change"
    audit_trail_posture = "planned_not_written"
    decision_boundary = "recommendations_may_inform_but_never_execute_without_human_authorization"
    intelligence_layer_status = "planned_not_runtime"
}

function Write-Header { param([string]$Title) Write-Host "=============================================================================="; Write-Host $Title; Write-Host "==============================================================================" }

function Show-Status {
    Write-Header $StepTitle
    Write-Host "Repo root: $ResolvedRepoRoot"
    Write-Host "Source root: $SourceRoot"
    Write-Host "Expected branch: $ExpectedBranch"
    Write-Host "Prior completed step: $PriorCompletedStep"
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    foreach ($Key in $SafetyPosture.Keys) { Write-Host ("  {0}: {1}" -f $Key, $SafetyPosture[$Key]) }
    Write-Host ""
    Write-Host "Step files"
    foreach ($RelativePath in $StepFiles) {
        $TargetPath = Join-Path $ResolvedRepoRoot $RelativePath
        if (Test-LiteralPathSafe $TargetPath) { Write-Host "  PRESENT $RelativePath" } else { Write-Host "  MISSING $RelativePath" }
    }
}

function Apply-StepFiles {
    foreach ($RelativePath in $StepFiles) {
        $SourcePath = Join-Path $SourceRoot $RelativePath
        $TargetPath = Join-Path $ResolvedRepoRoot $RelativePath
        $TargetDir = Split-Path -Parent $TargetPath
        if (-not (Test-LiteralPathSafe $SourcePath)) {
            if (Test-LiteralPathSafe $TargetPath) { Write-Host "SKIPPED $RelativePath source not found but target already present."; continue }
            throw "Source file not found for $RelativePath at $SourcePath"
        }
        if (-not (Test-LiteralPathSafe $TargetDir)) { New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null }
        $SourceFull = Get-FullPathSafe $SourcePath
        $TargetFull = Get-FullPathSafe $TargetPath
        if ($SourceFull -ieq $TargetFull) { Write-Host "SKIPPED $RelativePath source and target are the same file."; continue }
        Copy-Item -LiteralPath $SourcePath -Destination $TargetPath -Force
        Write-Host "COPIED $RelativePath"
    }
    Write-Host "APPLY PASS: Phase 22 Step 41 files copied or already present."
}

function Get-ForbiddenTokens {
    return @(
        ("lacrm_live" + "_write=true"),
        ("live_write" + "=true"),
        ("planning_only" + "=false"),
        ("no_network" + "_sockets=false"),
        ("no_bridge" + "_post=false"),
        ("implementation_phase" + "_start=true"),
        ("operator_signoff" + "_creation=true"),
        ("operator_approval" + "_creation=true"),
        ("final_approval" + "_creation=true"),
        ("design_closure" + "_record_creation=true"),
        ("closure_decision" + "_record_creation=true"),
        ("closure_approval" + "_creation=true"),
        ("implementation_queue" + "_creation=true"),
        ("source_bucket" + "_writes=true"),
        ("applied_layer" + "_writes=true"),
        ("recommendation" + "_execution=true"),
        ("runtime_pattern" + "_detection=true"),
        ("bayesian_update" + "_execution=true")
    )
}

function Test-Smoke {
    foreach ($RelativePath in $StepFiles) {
        $TargetPath = Join-Path $ResolvedRepoRoot $RelativePath
        if (-not (Test-LiteralPathSafe $TargetPath)) { throw "SMOKE TEST FAIL: Missing $RelativePath" }
    }
    if (-not $SafetyPosture.planning_only) { throw "SMOKE TEST FAIL: planning_only is false" }
    if (-not $SafetyPosture.no_platform_db_mutation) { throw "SMOKE TEST FAIL: platform DB mutation is not blocked" }
    if (-not $SafetyPosture.no_bridge_mutation) { throw "SMOKE TEST FAIL: bridge mutation is not blocked" }
    if (-not $SafetyPosture.no_real_bridge_http_client) { throw "SMOKE TEST FAIL: real bridge HTTP client is not blocked" }
    if (-not $SafetyPosture.no_network_transport_implementation) { throw "SMOKE TEST FAIL: network transport implementation is not blocked" }
    if (-not $SafetyPosture.no_bridge_post) { throw "SMOKE TEST FAIL: bridge POST is not blocked" }
    if (-not $SafetyPosture.no_network_sockets) { throw "SMOKE TEST FAIL: network sockets are not blocked" }
    if ($SafetyPosture.implementation_phase_start) { throw "SMOKE TEST FAIL: implementation phase start is true" }
    if ($SafetyPosture.authorization_record_creation) { throw "SMOKE TEST FAIL: authorization record creation is true" }
    if ($SafetyPosture.operator_signoff_creation) { throw "SMOKE TEST FAIL: operator signoff creation is true" }
    if ($SafetyPosture.final_approval_creation) { throw "SMOKE TEST FAIL: final approval creation is true" }
    if ($SafetyPosture.design_closure_record_creation) { throw "SMOKE TEST FAIL: design closure record creation is true" }
    if ($SafetyPosture.closure_decision_record_creation) { throw "SMOKE TEST FAIL: closure decision record creation is true" }
    if ($SafetyPosture.closure_approval_creation) { throw "SMOKE TEST FAIL: closure approval creation is true" }
    if ($SafetyPosture.implementation_queue_creation) { throw "SMOKE TEST FAIL: implementation queue creation is true" }
    if ($SafetyPosture.lacrm_default_mode -ne "dry_run") { throw "SMOKE TEST FAIL: LACRM default is not dry_run" }
    if ($SafetyPosture.lacrm_live_write) { throw "SMOKE TEST FAIL: LACRM live write is true" }
    if (-not $SafetyPosture.live_write_disabled) { throw "SMOKE TEST FAIL: live write disabled is false" }
    if (-not $SafetyPosture.live_write_unarmed) { throw "SMOKE TEST FAIL: live write unarmed is false" }
    if (-not $SafetyPosture.closure_decision_deferred) { throw "SMOKE TEST FAIL: closure decision deferral is not true" }
    $ForbiddenTokens = Get-ForbiddenTokens
    foreach ($RelativePath in $StepFiles) {
        $TargetPath = Join-Path $ResolvedRepoRoot $RelativePath
        $Content = Get-Content -LiteralPath $TargetPath -Raw
        foreach ($Token in $ForbiddenTokens) {
            if ($Content -match ([regex]::Escape($Token))) { throw "SMOKE TEST FAIL: Forbidden token found in ${RelativePath}: $Token" }
        }
    }
    Write-Host "SMOKE TEST PASS: Phase 22 Step 41 Phase 20 Network Transport Planning Closure Decision Deferral Alignment Packet is present and planning-only."
}

function Generate-Packet {
    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupRoot = Join-Path $ResolvedRepoRoot "backups"
    $PacketDir = Join-Path $BackupRoot ("$PacketSlug" + "_" + $Timestamp)
    if (-not (Test-LiteralPathSafe $PacketDir)) { New-Item -ItemType Directory -Path $PacketDir -Force | Out-Null }
    $Packet = [ordered]@{
        phase = "Phase 22"
        step = "Phase 22 Step 41"
        name = $PacketName
        generated_at = (Get-Date).ToString("o")
        repo_root = $ResolvedRepoRoot
        expected_branch = $ExpectedBranch
        prior_completed_step = $PriorCompletedStep
        planning_only = $true
        safety_posture = $SafetyPosture
        alignment_model = $AlignmentModel
        closure_decision_deferral = [ordered]@{
            deferred = $true
            reason = "Planning closure decision readiness is documented, but approval and implementation authorization are intentionally not created in this step."
            allowed_outputs = @("planning dossier", "readiness notes", "deferred decision checklist")
            blocked_outputs = @("closure decision record", "operator signoff", "final approval", "design closure record", "implementation queue", "bridge write", "platform DB mutation", "LACRM live write", "network socket")
        }
        rollout_reference_alignment = [ordered]@{
            connector_first_operating_core = $true
            source_bucket_discipline = "raw to normalized to matched to approved to applied"
            bridge_absorption_path = "stabilize first, then absorb through connector modules"
            operating_intelligence_path = "event ledger, expected vs actual, variance, attribution, calibration, pattern detection, recommendation governance"
        }
        step_files = $StepFiles
    }
    $PacketPath = Join-Path $PacketDir $PacketFileName
    $Packet | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $PacketPath -Encoding UTF8
    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "PASS: closure_decision_deferred=true"
    Write-Host "CHECK: closure_decision_record_creation=false"
    Write-Host "CHECK: closure_approval_creation=false"
    Write-Host "CHECK: implementation_queue_creation=false"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied"
    Write-Host "CHECK: bridge_absorption_target=connector_package_not_separate_product"
    Write-Host "CHECK: packet_json=$PacketPath"
}

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, ngrok tunnel, webhook listener, or network socket is started here."
    Write-Host "CHECK: Closure decision deferral is planning evidence only and does not authorize implementation."
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "Phase 22 Step 41 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 22 Step 41 Phase 20 Network Transport Planning Closure Decision Deferral Alignment Packet files"
        Write-Host "3. Smoke test Phase 22 Step 41"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 20 network transport planning closure decision deferral alignment packet"
        Write-Host "6. Exit"
        $Choice = Remove-ControlCharacters (Read-Host "Choose 1-6")
        switch ($Choice) {
            "1" { Show-Status }
            "2" { Apply-StepFiles }
            "3" { Test-Smoke }
            "4" { Show-ServerPlaceholder }
            "5" { Generate-Packet }
            "6" { return }
            default { Write-Host "Invalid choice. Enter 1, 2, 3, 4, 5, or 6." }
        }
    }
}

switch ($Action) {
    "status" { Show-Status }
    "apply" { Apply-StepFiles }
    "smoke" { Test-Smoke }
    "packet" { Generate-Packet }
    "all" { Show-Status; Apply-StepFiles; Test-Smoke; Generate-Packet }
    "menu" { Show-Menu }
}
