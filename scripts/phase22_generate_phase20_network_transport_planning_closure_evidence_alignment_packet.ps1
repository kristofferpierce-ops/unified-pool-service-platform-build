param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all", "exit")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$StepNumber = 38
$PhaseNumber = 22
$StepTitle = "Phase 22 Step 38 - Phase 20 Network Transport Planning Closure Evidence Alignment Packet"
$ExpectedBranch = "phase22-step38-phase20-network-transport-planning-closure-evidence-alignment-packet"
$PriorCompletedStep = "Phase 22 Step 37 - Phase 20 Network Transport Planning Handoff Dossier Alignment Packet"
$PacketSlug = "phase22_phase20_network_transport_planning_closure_evidence_alignment_packet"

$StepFiles = @(
    "scripts\phase22_generate_phase20_network_transport_planning_closure_evidence_alignment_packet.ps1",
    "ui\pages\144_Phase20_Network_Transport_Planning_Closure_Evidence_Alignment_Packet.py",
    "docs\PHASE22_STEP38_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_EVIDENCE_ALIGNMENT_PACKET.md",
    "tests\test_phase22_phase20_network_transport_planning_closure_evidence_alignment_packet.py"
)

$PublicScanFiles = @(
    "scripts\phase22_generate_phase20_network_transport_planning_closure_evidence_alignment_packet.ps1",
    "ui\pages\144_Phase20_Network_Transport_Planning_Closure_Evidence_Alignment_Packet.py",
    "docs\PHASE22_STEP38_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_EVIDENCE_ALIGNMENT_PACKET.md"
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
    applied_layer_release_execution = $false
    deployment_execution = $false
    deployment_start = $false
    runtime_server_start = $false
    network_transport_start = $false
    deployment_recovery_execution = $false
    deployment_restore_execution = $false
    planning_exit_approval = $false
    implementation_exit_approval = $false
    planning_exit_record_creation = $false
    handoff_dossier_record_creation = $false
    implementation_handoff_execution = $false
    implementation_queue_creation = $false
    handoff_to_implementation_approval = $false
    planning_closure_record_creation = $false
    closure_evidence_record_creation = $false
    closure_evidence_approval = $false
    closure_evidence_application = $false
    closure_evidence_commitment = $false
    implementation_release_authorization = $false
    lacrm_default_mode = "dry_run"
    lacrm_live_write = $false
    live_write_disabled = $true
    live_write_unarmed = $true
    source_bucket_writes = $false
    applied_layer_writes = $false
    deployment_readiness_plan_only = $true
    planning_handoff_dossier_plan_only = $true
    planning_closure_evidence_plan_only = $true
}

$ClosureEvidenceAlignment = [ordered]@{
    closure_evidence_scope = "planning_packet_only"
    planning_lane_status = "closure_evidence_compiled_for_review_not_approved"
    prior_handoff_dossier_alignment = "Phase 22 Step 37"
    prior_exit_readiness_alignment = "Phase 22 Step 36"
    prior_deployment_readiness_checkpoint = "Phase 22 Step 35"
    rollback_recovery_prior_alignment = "Phase 22 Step 34"
    applied_layer_release_control_prior_alignment = "Phase 22 Step 33"
    approval_audit_trail_prior_alignment = "Phase 22 Step 32"
    human_review_approval_gate_prior_alignment = "Phase 22 Step 31"
    decision_boundary_governance_prior_alignment = "Phase 22 Step 30"
    source_bucket_chain = "raw_to_normalized_to_matched_to_approved_to_applied"
    connector_first_operating_core = "planned_reference_only"
    canonical_event_ledger = "planned_not_created"
    expected_actual_variance = "planned_not_executed"
    driver_attribution = "planned_not_executed"
    probabilistic_calibration = "planned_not_executed"
    pattern_detection = "planned_not_executed"
    recommendation_engine = "planned_not_executed"
    bridge_route_surface_preservation = "required"
    connector_package_absorption = "planned_not_started"
    shared_database_merge = "deferred_until_domain_model_explicit"
    handoff_dossier_record_creation = "not_created"
    planning_closure_record_creation = "not_created"
    closure_evidence_record_creation = "not_created"
    closure_evidence_approval = "not_granted"
    closure_evidence_application = "not_applied"
    implementation_queue_creation = "not_created"
    handoff_to_implementation_approval = "not_granted"
    implementation_release_authorization = "not_granted"
    runtime_server_start = "disabled"
    network_transport_start = "disabled"
    implementation_phase_start = "not_started"
    deployment_readiness_checkpoint = "documented_not_approved"
    closure_evidence_status = "evidence_alignment_only_no_closure"
}

function Remove-ControlChars {
    param([string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    return ($Value -replace '[\x00-\x1F\x7F]', '').Trim()
}

function Resolve-EffectiveRepoRoot {
    param([string]$ProvidedRepoRoot)

    $CleanProvided = Remove-ControlChars $ProvidedRepoRoot
    if ($CleanProvided -and (Test-Path -LiteralPath $CleanProvided -PathType Container)) {
        return (Resolve-Path -LiteralPath $CleanProvided).Path
    }

    $ScriptParent = Split-Path -Parent $PSScriptRoot
    if ($ScriptParent -and (Test-Path -LiteralPath (Join-Path $ScriptParent "tests") -PathType Container)) {
        return (Resolve-Path -LiteralPath $ScriptParent).Path
    }

    $Current = (Get-Location).Path
    if ($Current -and (Test-Path -LiteralPath (Join-Path $Current "tests") -PathType Container)) {
        return (Resolve-Path -LiteralPath $Current).Path
    }

    throw "Unable to resolve repository root. Pass -RepoRoot with the unified_pool_service_platform_build repo path."
}

function Join-RepoPath {
    param(
        [string]$Root,
        [string]$RelativePath
    )

    $CleanRelative = Remove-ControlChars $RelativePath
    return Join-Path $Root $CleanRelative
}

function Test-RepoFile {
    param(
        [string]$Root,
        [string]$RelativePath
    )

    $Candidate = Join-RepoPath $Root $RelativePath
    return (Test-Path -LiteralPath $Candidate -PathType Leaf)
}

function Get-FullPathSafe {
    param([string]$PathValue)

    $CleanPath = Remove-ControlChars $PathValue
    return [System.IO.Path]::GetFullPath($CleanPath)
}

function Write-Header {
    Write-Host "=============================================================================="
    Write-Host $StepTitle
    Write-Host "=============================================================================="
}

function Show-Status {
    param([string]$Root)

    Write-Header
    Write-Host "Repo root: $Root"
    Write-Host "Expected branch: $ExpectedBranch"
    Write-Host "Prior completed step: $PriorCompletedStep"
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    foreach ($Key in $SafetyPosture.Keys) {
        Write-Host ("  {0}: {1}" -f $Key, $SafetyPosture[$Key])
    }
    Write-Host ""
    Write-Host "Closure evidence alignment"
    foreach ($Key in $ClosureEvidenceAlignment.Keys) {
        Write-Host ("  {0}: {1}" -f $Key, $ClosureEvidenceAlignment[$Key])
    }
    Write-Host ""
    Write-Host "Step files"
    foreach ($RelativePath in $StepFiles) {
        if (Test-RepoFile -Root $Root -RelativePath $RelativePath) {
            Write-Host "  PRESENT $RelativePath"
        } else {
            Write-Host "  MISSING $RelativePath"
        }
    }
}

function Copy-StepFiles {
    param([string]$Root)

    $SourceRoot = Split-Path -Parent $PSScriptRoot
    if (-not (Test-Path -LiteralPath $SourceRoot -PathType Container)) {
        throw "Source root was not found: $SourceRoot"
    }

    foreach ($RelativePath in $StepFiles) {
        $SourcePath = Join-RepoPath $SourceRoot $RelativePath
        $TargetPath = Join-RepoPath $Root $RelativePath

        if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) {
            throw "Source file missing: $SourcePath"
        }

        $SourceFullPath = Get-FullPathSafe $SourcePath
        $TargetFullPath = Get-FullPathSafe $TargetPath

        if ($SourceFullPath -ieq $TargetFullPath) {
            Write-Host "SKIPPED $RelativePath source and target are the same file."
            continue
        }

        $TargetDir = Split-Path -Parent $TargetPath
        if (-not (Test-Path -LiteralPath $TargetDir -PathType Container)) {
            New-Item -ItemType Directory -Path $TargetDir | Out-Null
        }

        Copy-Item -LiteralPath $SourcePath -Destination $TargetPath -Force
        Write-Host "COPIED $RelativePath"
    }

    Write-Host "APPLY PASS: Phase 22 Step 38 files copied or already present."
}

function Test-Smoke {
    param([string]$Root)

    foreach ($RelativePath in $StepFiles) {
        if (-not (Test-RepoFile -Root $Root -RelativePath $RelativePath)) {
            throw "SMOKE TEST FAIL: Missing $RelativePath"
        }
    }

    $ForbiddenTokens = @(
        ("lacrm_live_" + "write=true"),
        ("live_write_" + "disabled=false"),
        ("live_write_" + "unarmed=false"),
        ("planning_" + "only=false"),
        ("no_network_" + "sockets=false"),
        ("no_bridge_" + "post=false"),
        ("no_real_bridge_" + "http_client=false"),
        ("implementation_phase_" + "start=true"),
        ("authorization_record_" + "creation=true"),
        ("operator_" + "signoff_creation=true"),
        ("operator_" + "approval_creation=true"),
        ("final_" + "approval_creation=true"),
        ("design_closure_record_" + "creation=true"),
        ("applied_layer_release_" + "execution=true"),
        ("deployment_" + "execution=true"),
        ("deployment_" + "start=true"),
        ("runtime_server_" + "start=true"),
        ("network_transport_" + "start=true"),
        ("rollback_" + "execution=true"),
        ("recovery_" + "execution=true"),
        ("restore_" + "execution=true"),
        ("planning_exit_" + "approval=true"),
        ("implementation_exit_" + "approval=true"),
        ("handoff_dossier_record_" + "creation=true"),
        ("implementation_handoff_" + "execution=true"),
        ("implementation_queue_" + "creation=true"),
        ("handoff_to_implementation_" + "approval=true"),
        ("planning_closure_record_" + "creation=true"),
        ("closure_evidence_record_" + "creation=true"),
        ("closure_evidence_" + "approval=true"),
        ("closure_evidence_" + "application=true"),
        ("implementation_release_" + "authorization=true")
    )

    foreach ($RelativePath in $PublicScanFiles) {
        $PathValue = Join-RepoPath $Root $RelativePath
        $Text = Get-Content -LiteralPath $PathValue -Raw
        foreach ($Token in $ForbiddenTokens) {
            if ($Text.Contains($Token)) {
                $Message = "SMOKE TEST FAIL: Forbidden token found in {0}: {1}" -f $RelativePath, $Token
                throw $Message
            }
        }
    }

    Write-Host "SMOKE TEST PASS: Phase 22 Step 38 Phase 20 Network Transport Planning Closure Evidence Alignment Packet is present and planning-only."
}

function New-PlanningPacket {
    param([string]$Root)

    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupRoot = Join-Path $Root "backups"
    $PacketDir = Join-Path $BackupRoot ("{0}_{1}" -f $PacketSlug, $Stamp)

    if (-not (Test-Path -LiteralPath $PacketDir -PathType Container)) {
        New-Item -ItemType Directory -Path $PacketDir | Out-Null
    }

    $PacketPath = Join-Path $PacketDir ($PacketSlug + ".json")

    $Packet = [ordered]@{
        phase = 22
        step = 38
        title = $StepTitle
        prior_completed_step = $PriorCompletedStep
        expected_branch = $ExpectedBranch
        generated_at = (Get-Date).ToString("o")
        planning_only = $true
        no_platform_db_mutation = $true
        no_bridge_mutation = $true
        no_real_bridge_http_client = $true
        no_network_transport_implementation = $true
        no_bridge_post = $true
        no_network_sockets = $true
        no_execution_implementation = $true
        implementation_phase_start = "not_started"
        authorization_record_creation = $false
        operator_signoff_creation = $false
        operator_approval_creation = $false
        final_approval_creation = $false
        design_closure_record_creation = $false
        applied_layer_release_execution = $false
        deployment_execution = $false
        deployment_start = $false
        runtime_server_start = $false
        network_transport_start = $false
        deployment_recovery_execution = $false
        deployment_restore_execution = $false
        planning_exit_approval = $false
        implementation_exit_approval = $false
        planning_exit_record_creation = $false
        handoff_dossier_record_creation = $false
        implementation_handoff_execution = $false
        implementation_queue_creation = $false
        handoff_to_implementation_approval = $false
        planning_closure_record_creation = $false
        closure_evidence_record_creation = $false
        closure_evidence_approval = $false
        closure_evidence_application = $false
        implementation_release_authorization = $false
        lacrm_default_mode = "dry_run"
        lacrm_live_write = $false
        live_write_disabled = $true
        live_write_unarmed = $true
        closure_evidence_alignment = $ClosureEvidenceAlignment
        safety_posture = $SafetyPosture
        step_files = $StepFiles
        future_preconditions = @(
            "future closure evidence review must not create planning closure records automatically",
            "future implementation phase must require explicit authorization outside this planning packet",
            "future handoff dossier review must not create an implementation queue automatically",
            "future deployment must require rollback recovery validation from Phase 22 Step 34",
            "future applied layer release must remain blocked until human review and audit trail gates are satisfied",
            "future bridge absorption must preserve route surface and connector package boundaries",
            "future shared database merge remains deferred until the domain model is explicit"
        )
    }

    $Packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $PacketPath -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "PASS: deployment_execution=false"
    Write-Host "PASS: deployment_start=false"
    Write-Host "PASS: runtime_server_start=false"
    Write-Host "PASS: planning_exit_approval=false"
    Write-Host "PASS: implementation_exit_approval=false"
    Write-Host "PASS: handoff_dossier_record_creation=false"
    Write-Host "PASS: implementation_handoff_execution=false"
    Write-Host "PASS: implementation_queue_creation=false"
    Write-Host "PASS: handoff_to_implementation_approval=false"
    Write-Host "PASS: planning_closure_record_creation=false"
    Write-Host "PASS: closure_evidence_record_creation=false"
    Write-Host "PASS: closure_evidence_approval=false"
    Write-Host "PASS: closure_evidence_application=false"
    Write-Host "PASS: implementation_release_authorization=false"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: authorization_record_creation=false"
    Write-Host "CHECK: applied_layer_release_execution=false"
    Write-Host "CHECK: deployment_readiness_checkpoint=documented_not_approved"
    Write-Host "CHECK: planning_lane_status=closure_evidence_compiled_for_review_not_approved"
    Write-Host "CHECK: planning_exit_record_creation=not_created"
    Write-Host "CHECK: handoff_dossier_record_creation=not_created"
    Write-Host "CHECK: planning_closure_record_creation=not_created"
    Write-Host "CHECK: closure_evidence_record_creation=not_created"
    Write-Host "CHECK: implementation_queue_creation=not_created"
    Write-Host "CHECK: implementation_release_authorization=not_granted"
    Write-Host "CHECK: packet_json=$PacketPath"
}

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, ngrok tunnel, or network socket is started here."
    Write-Host "CHECK: Closure evidence alignment is documented only and does not approve, queue, close, or start implementation."
}

function Invoke-Action {
    param(
        [string]$Root,
        [string]$SelectedAction
    )

    switch ($SelectedAction) {
        "status" { Show-Status -Root $Root }
        "apply" { Copy-StepFiles -Root $Root }
        "smoke" { Test-Smoke -Root $Root }
        "packet" { New-PlanningPacket -Root $Root }
        "all" {
            Show-Status -Root $Root
            Copy-StepFiles -Root $Root
            Test-Smoke -Root $Root
            New-PlanningPacket -Root $Root
        }
        "exit" { return }
        default { throw "Unsupported action: $SelectedAction" }
    }
}

$EffectiveRepoRoot = Resolve-EffectiveRepoRoot -ProvidedRepoRoot $RepoRoot

if ($Action -ne "menu") {
    Invoke-Action -Root $EffectiveRepoRoot -SelectedAction $Action
    exit 0
}

while ($true) {
    Write-Host ""
    Write-Host "Phase 22 Step 38 menu"
    Write-Host "1. Show status / verify paths"
    Write-Host "2. Apply Phase 22 Step 38 Phase 20 Network Transport Planning Closure Evidence Alignment Packet files"
    Write-Host "3. Smoke test Phase 22 Step 38"
    Write-Host "4. Show server start placeholder only"
    Write-Host "5. Generate Phase 20 network transport planning closure evidence alignment packet"
    Write-Host "6. Run optimized all action"
    Write-Host "7. Exit"

    $Choice = Remove-ControlChars (Read-Host "Choose 1-7")

    switch ($Choice) {
        "1" { Show-Status -Root $EffectiveRepoRoot }
        "2" { Copy-StepFiles -Root $EffectiveRepoRoot }
        "3" { Test-Smoke -Root $EffectiveRepoRoot }
        "4" { Show-ServerPlaceholder }
        "5" { New-PlanningPacket -Root $EffectiveRepoRoot }
        "6" { Invoke-Action -Root $EffectiveRepoRoot -SelectedAction "all" }
        "7" { break }
        default { Write-Host "Invalid choice. Choose 1 through 7." }
    }
}
