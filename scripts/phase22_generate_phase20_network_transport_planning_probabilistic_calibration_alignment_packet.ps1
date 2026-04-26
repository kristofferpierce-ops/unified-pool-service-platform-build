param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$StepNumber = "27"
$PhaseNumber = "22"
$StepTitle = "Phase 22 Step 27 - Phase 20 Network Transport Planning Probabilistic Calibration Alignment Packet"
$ExpectedBranch = "phase22-step27-phase20-network-transport-planning-probabilistic-calibration-alignment-packet"
$PriorCompletedStep = "Phase 22 Step 26 - Phase 20 Network Transport Planning Driver Attribution Alignment Packet"

$StepFiles = @(
    "scripts/phase22_generate_phase20_network_transport_planning_probabilistic_calibration_alignment_packet.ps1",
    "ui/pages/133_Phase20_Network_Transport_Planning_Probabilistic_Calibration_Alignment_Packet.py",
    "docs/PHASE22_STEP27_PHASE20_NETWORK_TRANSPORT_PLANNING_PROBABILISTIC_CALIBRATION_ALIGNMENT_PACKET.md",
    "tests/test_phase22_phase20_network_transport_planning_probabilistic_calibration_alignment_packet.py"
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
    implementation_phase_start = $false
    authorization_record_creation = $false
    operator_signoff_creation = $false
    operator_approval_creation = $false
    final_approval_creation = $false
    design_closure_record_creation = $false
    no_operator_signoff = $true
    no_operator_approval = $true
    no_final_approval = $true
    no_design_closure_record_creation = $true
    lacrm_default_mode = "dry_run"
    lacrm_live_write = $false
    live_write_disabled = $true
    live_write_unarmed = $true
    probabilistic_calibration_writes = $false
    bayesian_update_execution = $false
    recommendation_engine_execution = $false
}

$AlignmentModel = [ordered]@{
    source_reference = "platform_rollout_logic_model.pdf"
    bridge_reference = "KPS Bridge Handoff-to-Code Traceability Report.docx"
    stage_after = "Phase 22 Step 26 driver attribution alignment"
    rollout_sequence = @(
        "rules first",
        "probabilistic calibration planning",
        "pattern detection planning",
        "recommendation engine planning"
    )
    calibration_inputs = @(
        "inputs",
        "model_version",
        "expected_outputs",
        "actual_outputs",
        "variance",
        "confidence_score",
        "likely_drivers",
        "business_result"
    )
    priors_to_plan = @(
        "account_class_priors",
        "seasonal_priors",
        "branch_priors",
        "tech_priors",
        "route_density_priors",
        "equipment_family_priors"
    )
    confidence_controls = @(
        "confidence_interval_planning_only",
        "minimum_observation_count",
        "human_review_before_application",
        "no_auto_price_change",
        "no_auto_scope_change",
        "no_live_recommendation_execution"
    )
    bridge_absorption_guardrail = "connector_package_not_separate_product"
    source_bucket_alignment = "raw_normalized_matched_approved_applied"
    implementation_state = "not_started"
}

function Write-Section([string]$Text) {
    Write-Host ""
    Write-Host "=============================================================================="
    Write-Host $Text
    Write-Host "=============================================================================="
}

function Remove-ControlCharacters([string]$Value) {
    if ($null -eq $Value) {
        return ""
    }
    return [regex]::Replace($Value, "[\x00-\x1F\x7F]", "").Trim()
}

function Test-LiteralPathSafe([string]$PathValue) {
    $Clean = Remove-ControlCharacters $PathValue
    if ([string]::IsNullOrWhiteSpace($Clean)) {
        return $false
    }
    try {
        return Test-Path -LiteralPath $Clean
    } catch {
        return $false
    }
}

function Resolve-RepoRoot([string]$RequestedRoot) {
    $CleanRequested = Remove-ControlCharacters $RequestedRoot
    $Candidates = New-Object System.Collections.Generic.List[string]

    if (-not [string]::IsNullOrWhiteSpace($CleanRequested)) {
        $Candidates.Add($CleanRequested)
    }

    $Candidates.Add((Get-Location).Path)

    if ($PSScriptRoot) {
        $Candidates.Add((Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path)
        $Candidates.Add((Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..") -ErrorAction SilentlyContinue).Path)
    }

    foreach ($Candidate in $Candidates) {
        if ([string]::IsNullOrWhiteSpace($Candidate)) {
            continue
        }
        $CleanCandidate = Remove-ControlCharacters $Candidate
        if (-not (Test-LiteralPathSafe $CleanCandidate)) {
            continue
        }
        $GitPath = Join-Path $CleanCandidate ".git"
        $ScriptsPath = Join-Path $CleanCandidate "scripts"
        $UiPath = Join-Path $CleanCandidate "ui"
        if ((Test-LiteralPathSafe $GitPath) -or ((Test-LiteralPathSafe $ScriptsPath) -and (Test-LiteralPathSafe $UiPath))) {
            return (Resolve-Path -LiteralPath $CleanCandidate).Path
        }
    }

    throw "Could not resolve repo root. Pass -RepoRoot with the unified_pool_service_platform_build repo path."
}

function Resolve-PayloadRoot() {
    if ($PSScriptRoot) {
        $Candidate = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
        return $Candidate
    }
    return (Get-Location).Path
}

function ConvertTo-DisplayBool($Value) {
    if ($Value -is [bool]) {
        if ($Value) { return "True" } else { return "False" }
    }
    return [string]$Value
}

function Show-Status([string]$Root) {
    Write-Section $StepTitle
    Write-Host "Repo root: $Root"
    Write-Host "Expected branch: $ExpectedBranch"
    Write-Host "Prior completed step: $PriorCompletedStep"
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    foreach ($Key in $SafetyPosture.Keys) {
        Write-Host ("  {0}: {1}" -f $Key, (ConvertTo-DisplayBool $SafetyPosture[$Key]))
    }
    Write-Host ""
    Write-Host "Planning alignment"
    Write-Host "  rollout stage: probabilistic calibration planning after driver attribution"
    Write-Host "  priors: account class, season, branch, tech, route density, equipment family"
    Write-Host "  controls: no automatic recommendations, no pricing change, no scope change"
    Write-Host ""
    Write-Host "Step files"
    foreach ($Rel in $StepFiles) {
        $TargetPath = Join-Path $Root $Rel
        if (Test-LiteralPathSafe $TargetPath) {
            Write-Host "  PRESENT $Rel"
        } else {
            Write-Host "  MISSING $Rel"
        }
    }
}

function Apply-StepFiles([string]$Root) {
    $PayloadRoot = Resolve-PayloadRoot
    foreach ($Rel in $StepFiles) {
        $SourcePath = Join-Path $PayloadRoot $Rel
        $TargetPath = Join-Path $Root $Rel

        if (-not (Test-LiteralPathSafe $SourcePath)) {
            Write-Host "WARN: Source file not found for $Rel"
            continue
        }

        $ResolvedSource = (Resolve-Path -LiteralPath $SourcePath).Path
        $ResolvedTarget = $null
        if (Test-LiteralPathSafe $TargetPath) {
            $ResolvedTarget = (Resolve-Path -LiteralPath $TargetPath).Path
        }

        if ($ResolvedTarget -and ([string]::Equals($ResolvedSource, $ResolvedTarget, [System.StringComparison]::OrdinalIgnoreCase))) {
            Write-Host "SKIPPED $Rel source and target are the same file."
            continue
        }

        $TargetDir = Split-Path -Parent $TargetPath
        if (-not (Test-LiteralPathSafe $TargetDir)) {
            New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
        }

        Copy-Item -LiteralPath $ResolvedSource -Destination $TargetPath -Force
        Write-Host "COPIED $Rel"
    }
    Write-Host "APPLY PASS: Phase 22 Step 27 files copied or already present."
}

function Invoke-SmokeTest([string]$Root) {
    $Missing = @()
    foreach ($Rel in $StepFiles) {
        $TargetPath = Join-Path $Root $Rel
        if (-not (Test-LiteralPathSafe $TargetPath)) {
            $Missing += $Rel
        }
    }

    if ($Missing.Count -gt 0) {
        throw "SMOKE TEST FAIL: Missing Phase 22 Step 27 files: $($Missing -join ', ')"
    }

    $ScriptText = Get-Content -LiteralPath (Join-Path $Root "scripts/phase22_generate_phase20_network_transport_planning_probabilistic_calibration_alignment_packet.ps1") -Raw
    $Forbidden = @(
        ("Invoke" + "-WebRequest"),
        ("Invoke" + "-RestMethod"),
        ("System.Net" + ".Sockets"),
        ("Tcp" + "Client"),
        ("Http" + "Client"),
        ("requests" + ".post"),
        "lacrm_live_write=true",
        "implementation_phase_start=true",
        "authorization_record_creation=true",
        "operator_signoff_creation=true",
        "final_approval_creation=true",
        "design_closure_record_creation=true",
        "recommendation_engine_execution enabled",
        "bayesian_update_execution enabled"
    )

    foreach ($Token in $Forbidden) {
        if ($ScriptText -like "*$Token*") {
            throw "SMOKE TEST FAIL: Forbidden token found in launcher: $Token"
        }
    }

    Write-Host "SMOKE TEST PASS: Phase 22 Step 27 Phase 20 Network Transport Planning Probabilistic Calibration Alignment Packet is present and planning-only."
}

function New-PlanningPacket([string]$Root) {
    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $PacketDir = Join-Path $Root "backups\phase22_phase20_network_transport_planning_probabilistic_calibration_alignment_packet_$Stamp"
    New-Item -ItemType Directory -Path $PacketDir -Force | Out-Null

    $Packet = [ordered]@{
        phase = 22
        step = 27
        name = "Phase 20 Network Transport Planning Probabilistic Calibration Alignment Packet"
        branch = $ExpectedBranch
        prior_completed_step = $PriorCompletedStep
        generated_at = (Get-Date).ToString("o")
        safety_posture = $SafetyPosture
        alignment_model = $AlignmentModel
        planning_decisions = [ordered]@{
            probabilistic_calibration_is_planning_only = $true
            bayesian_updates_are_not_executed = $true
            confidence_intervals_are_design_targets_only = $true
            no_recommendation_engine_runtime = $true
            no_auto_price_change = $true
            no_auto_scope_change = $true
            no_db_schema_change = $true
            no_platform_db_mutation = $true
            no_bridge_mutation = $true
        }
        next_planning_candidates = @(
            "pattern_detection_alignment_packet",
            "recommendation_engine_guardrail_packet",
            "implementation_backlog_exit_packet"
        )
    }

    $PacketPath = Join-Path $PacketDir "phase22_phase20_network_transport_planning_probabilistic_calibration_alignment_packet.json"
    $Packet | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $PacketPath -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "PASS: probabilistic_calibration_writes=false"
    Write-Host "PASS: bayesian_update_execution=false"
    Write-Host "PASS: recommendation_engine_execution=false"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied"
    Write-Host "CHECK: calibration_sequence=rules_first_then_probabilistic_calibration_then_pattern_detection_then_recommendations"
    Write-Host "CHECK: priors=account_class,seasonal,branch,tech,route_density,equipment_family"
    Write-Host "CHECK: packet_json=$PacketPath"
}

function Show-ServerPlaceholder() {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, or network socket is started here."
    Write-Host "CHECK: No probabilistic calibration runtime, Bayesian update execution, or recommendation engine execution starts here."
}

function Show-Menu([string]$Root) {
    while ($true) {
        Write-Host ""
        Write-Host "Phase 22 Step 27 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 22 Step 27 Phase 20 Network Transport Planning Probabilistic Calibration Alignment Packet files"
        Write-Host "3. Smoke test Phase 22 Step 27"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 20 network transport planning probabilistic calibration alignment packet"
        Write-Host "6. Run optimized all actions"
        Write-Host "7. Exit"
        $Choice = Remove-ControlCharacters (Read-Host "Choose 1-7")

        switch ($Choice) {
            "1" { Show-Status $Root }
            "2" { Apply-StepFiles $Root }
            "3" { Invoke-SmokeTest $Root }
            "4" { Show-ServerPlaceholder }
            "5" { New-PlanningPacket $Root }
            "6" { Show-Status $Root; Apply-StepFiles $Root; Invoke-SmokeTest $Root; New-PlanningPacket $Root }
            "7" { return }
            default { Write-Host "Unknown option. Choose 1-7." }
        }
    }
}

$ResolvedRepoRoot = Resolve-RepoRoot $RepoRoot

switch ($Action) {
    "status" { Show-Status $ResolvedRepoRoot }
    "apply" { Apply-StepFiles $ResolvedRepoRoot }
    "smoke" { Invoke-SmokeTest $ResolvedRepoRoot }
    "packet" { New-PlanningPacket $ResolvedRepoRoot }
    "all" { Show-Status $ResolvedRepoRoot; Apply-StepFiles $ResolvedRepoRoot; Invoke-SmokeTest $ResolvedRepoRoot; New-PlanningPacket $ResolvedRepoRoot }
    default { Show-Menu $ResolvedRepoRoot }
}
