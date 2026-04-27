param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all", "exit")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$StepNumber = 35
$PhaseNumber = 22
$StepTitle = "Phase 22 Step 35 - Phase 20 Network Transport Planning Deployment Readiness Checkpoint Alignment Packet"
$ExpectedBranch = "phase22-step35-phase20-network-transport-planning-deployment-readiness-checkpoint-alignment-packet"
$PriorCompletedStep = "Phase 22 Step 34 - Phase 20 Network Transport Planning Rollback Recovery Alignment Packet"
$PacketSlug = "phase22_phase20_network_transport_planning_deployment_readiness_checkpoint_alignment_packet"

$StepFiles = @(
    "scripts\phase22_generate_phase20_network_transport_planning_deployment_readiness_checkpoint_alignment_packet.ps1",
    "ui\pages\141_Phase20_Network_Transport_Planning_Deployment_Readiness_Checkpoint_Alignment_Packet.py",
    "docs\PHASE22_STEP35_PHASE20_NETWORK_TRANSPORT_PLANNING_DEPLOYMENT_READINESS_CHECKPOINT_ALIGNMENT_PACKET.md",
    "tests\test_phase22_phase20_network_transport_planning_deployment_readiness_checkpoint_alignment_packet.py"
)

$PublicScanFiles = @(
    "scripts\phase22_generate_phase20_network_transport_planning_deployment_readiness_checkpoint_alignment_packet.ps1",
    "ui\pages\141_Phase20_Network_Transport_Planning_Deployment_Readiness_Checkpoint_Alignment_Packet.py",
    "docs\PHASE22_STEP35_PHASE20_NETWORK_TRANSPORT_PLANNING_DEPLOYMENT_READINESS_CHECKPOINT_ALIGNMENT_PACKET.md"
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
    network_transport_start = $false
    runtime_server_start = $false
    deployment_start = $false
    deployment_recovery_execution = $false
    deployment_restore_execution = $false
    lacrm_default_mode = "dry_run"
    lacrm_live_write = $false
    live_write_disabled = $true
    live_write_unarmed = $true
    source_bucket_writes = $false
    applied_layer_writes = $false
    deployment_readiness_plan_only = $true
    deployment_checkpoint_plan_only = $true
}

$RollbackRecoveryAlignment = [ordered]@{
    rollback_scope = "planning_packet_only"
    recovery_scope = "planning_packet_only"
    preflight_snapshot_requirement = "required_before_future_deployment"
    rollback_validation_requirement = "required_before_future_deployment"
    applied_layer_release_control_prior_step = "Phase 22 Step 33"
    source_bucket_chain = "raw_to_normalized_to_matched_to_approved_to_applied"
    bridge_route_surface_preservation = "required"
    connector_package_absorption = "planned_not_started"
    shared_database_merge = "deferred_until_domain_model_explicit"
    runtime_server_start = "disabled"
    network_transport_start = "disabled"
    implementation_phase_start = "not_started"
    deployment_readiness_checkpoint = "documented_not_approved"
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
    Write-Host "Deployment readiness checkpoint alignment"
    foreach ($Key in $RollbackRecoveryAlignment.Keys) {
        Write-Host ("  {0}: {1}" -f $Key, $RollbackRecoveryAlignment[$Key])
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

    Write-Host "APPLY PASS: Phase 22 Step 35 files copied or already present."
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
        ("rollback_" + "execution=true"),
        ("recovery_" + "execution=true"),
        ("restore_" + "execution=true")
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

    Write-Host "SMOKE TEST PASS: Phase 22 Step 35 Phase 20 Network Transport Planning Deployment Readiness Checkpoint Alignment Packet is present and planning-only."
}

function New-PlanningPacket {
    param([string]$Root)

    $Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupRoot = Join-Path $Root "backups"
    $PacketDir = Join-Path $BackupRoot ("0_1" -f $PacketSlug, $Stamp)

    if (-not (Test-Path -LiteralPath $PacketDir -PathType Container)) {
        New-Item -ItemType Directory -Path $PacketDir | Out-Null
    }

    $PacketPath = Join-Path $PacketDir ($PacketSlug + ".json")

    $Packet = [ordered]@{
        phase = 22
        step = 35
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
        deployment_recovery_execution = $false
        deployment_restore_execution = $false
        lacrm_default_mode = "dry_run"
        lacrm_live_write = $false
        live_write_disabled = $true
        live_write_unarmed = $true
        deployment_readiness_checkpoint_alignment = $RollbackRecoveryAlignment
        safety_posture = $SafetyPosture
        step_files = $StepFiles
        future_preconditions = @(
            "future implementation must snapshot platform DB before any mutation",
            "future bridge integration must preserve route surface before migration",
            "future rollback must be validated before any applied layer release",
            "future recovery must not depend on live connector writes",
            "future restore checks must remain separate from approval creation"
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
    Write-Host "PASS: deployment_recovery_execution=false"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: authorization_record_creation=false"
    Write-Host "CHECK: applied_layer_release_execution=false"
    Write-Host "CHECK: preflight_snapshot_requirement=required_before_future_deployment"
    Write-Host "CHECK: rollback_validation_requirement=required_before_future_deployment"
    Write-Host "CHECK: deployment_readiness_checkpoint=documented_not_approved"
    Write-Host "CHECK: packet_json=$PacketPath"
}

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, ngrok tunnel, or network socket is started here."
    Write-Host "CHECK: Deployment readiness is documented only and does not start runtime deployment."
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
    Write-Host "Phase 22 Step 35 menu"
    Write-Host "1. Show status / verify paths"
    Write-Host "2. Apply Phase 22 Step 35 Phase 20 Network Transport Planning Deployment Readiness Checkpoint Alignment Packet files"
    Write-Host "3. Smoke test Phase 22 Step 35"
    Write-Host "4. Show server start placeholder only"
    Write-Host "5. Generate Phase 20 network transport planning deployment readiness checkpoint alignment packet"
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
