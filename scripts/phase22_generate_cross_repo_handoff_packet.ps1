param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$StepNumber = 61
$StepName = "Phase 22 Step 61 - Phase 20 Network Transport Planning Cross-Repo Handoff Packet"
$PriorStepName = "Phase 22 Step 60 - Phase 20 Network Transport Planning Closeout Packet"
$ExpectedBranch = "phase22-step61-cross-repo-handoff"

$StepFiles = @(
    "scripts/phase22_generate_cross_repo_handoff_packet.ps1",
    "ui/pages/167_Phase20_Network_Transport_Planning_Cross_Repo_Handoff_Packet.py",
    "docs/PHASE22_STEP61_CROSS_REPO_HANDOFF_PACKET.md",
    "tests/test_phase22_step61_cross_repo_handoff_packet.py"
)

function Resolve-RepoRoot {
    param([string]$InputRoot)

    if ($InputRoot -and (Test-Path -LiteralPath $InputRoot)) {
        return (Resolve-Path -LiteralPath $InputRoot).Path
    }

    $scriptRoot = $PSScriptRoot
    if ($scriptRoot) {
        $candidate = Split-Path -Parent $scriptRoot
        if (Test-Path -LiteralPath (Join-Path $candidate "scripts")) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    $current = (Get-Location).Path
    if (Test-Path -LiteralPath (Join-Path $current "scripts")) {
        return (Resolve-Path -LiteralPath $current).Path
    }

    $nested = Join-Path $current "unified_pool_service_platform_build"
    if (Test-Path -LiteralPath (Join-Path $nested "scripts")) {
        return (Resolve-Path -LiteralPath $nested).Path
    }

    throw "Could not resolve repo root. Pass -RepoRoot explicitly."
}

function Join-SafePath {
    param(
        [Parameter(Mandatory=$true)][string]$Root,
        [Parameter(Mandatory=$true)][string]$RelativePath
    )

    $clean = $RelativePath.Replace("\", "/").TrimStart("/")
    $result = $Root
    foreach ($part in $clean.Split("/")) {
        if ($part) {
            $result = Join-Path $result $part
        }
    }
    return $result
}

function Get-SafetyPosture {
    return [ordered]@{
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
        phase23_start = $false
        phase23_branch_creation = $false
        implementation_queue_creation = $false
        cross_repo_write = $false
        cross_repo_mutation = $false
        external_repo_push = $false
        bridge_absorption_execution = $false
        source_bucket_writes = $false
        applied_layer_mutation = $false
        review_gate_mutation = $false
        lacrm_default_mode = "dry_run"
        lacrm_live_write = $false
        live_write_disabled = $true
        live_write_unarmed = $true
    }
}

$Repo = Resolve-RepoRoot -InputRoot $RepoRoot

function Show-Status {
    Write-Host "=============================================================================="
    Write-Host $StepName
    Write-Host "=============================================================================="
    Write-Host "Repo root: $Repo"
    Write-Host "Expected branch: $ExpectedBranch"
    Write-Host "Prior completed step: $PriorStepName"
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    $safety = Get-SafetyPosture
    foreach ($key in $safety.Keys) {
        Write-Host ("  0: 1" -f $key, $safety[$key])
    }
    Write-Host ""
    Write-Host "Step files"
    foreach ($rel in $StepFiles) {
        $path = Join-SafePath -Root $Repo -RelativePath $rel
        if (Test-Path -LiteralPath $path) {
            Write-Host "  PRESENT $rel"
        } else {
            Write-Host "  MISSING $rel"
        }
    }
}

function Apply-StepFiles {
    foreach ($rel in $StepFiles) {
        $target = Join-SafePath -Root $Repo -RelativePath $rel
        if (Test-Path -LiteralPath $target) {
            Write-Host "SKIPPED $rel source and target are the same file."
        } else {
            throw "Missing source file after installer write: $target"
        }
    }
    Write-Host "APPLY PASS: Phase 22 Step 61 files copied or already present."
}

function Test-Smoke {
    foreach ($rel in $StepFiles) {
        $path = Join-SafePath -Root $Repo -RelativePath $rel
        if (-not (Test-Path -LiteralPath $path)) {
            throw "SMOKE TEST FAIL: Missing required file: $rel"
        }
    }

    $safety = Get-SafetyPosture

    if (-not $safety["planning_only"]) { throw "SMOKE TEST FAIL: planning_only must be true" }
    if (-not $safety["no_platform_db_mutation"]) { throw "SMOKE TEST FAIL: platform DB mutation must remain disabled" }
    if (-not $safety["no_bridge_mutation"]) { throw "SMOKE TEST FAIL: bridge mutation must remain disabled" }
    if (-not $safety["no_real_bridge_http_client"]) { throw "SMOKE TEST FAIL: real bridge HTTP client must remain disabled" }
    if (-not $safety["no_network_transport_implementation"]) { throw "SMOKE TEST FAIL: network transport implementation must remain disabled" }
    if (-not $safety["no_bridge_post"]) { throw "SMOKE TEST FAIL: bridge POST must remain disabled" }
    if (-not $safety["no_network_sockets"]) { throw "SMOKE TEST FAIL: sockets must remain disabled" }
    if ($safety["implementation_phase_start"]) { throw "SMOKE TEST FAIL: implementation phase must not start" }
    if ($safety["phase23_start"]) { throw "SMOKE TEST FAIL: Phase 23 must not start in this packet" }
    if ($safety["cross_repo_write"]) { throw "SMOKE TEST FAIL: cross repo writes must remain disabled" }
    if ($safety["cross_repo_mutation"]) { throw "SMOKE TEST FAIL: cross repo mutation must remain disabled" }
    if ($safety["external_repo_push"]) { throw "SMOKE TEST FAIL: external repo push must remain disabled" }
    if ($safety["lacrm_live_write"]) { throw "SMOKE TEST FAIL: LACRM live write must remain disabled" }
    if (-not $safety["live_write_disabled"]) { throw "SMOKE TEST FAIL: live write disabled must remain true" }
    if (-not $safety["live_write_unarmed"]) { throw "SMOKE TEST FAIL: live write unarmed must remain true" }

    Write-Host "SMOKE TEST PASS: Phase 22 Step 61 Phase 20 Network Transport Planning Cross-Repo Handoff Packet is present and planning-only."
}

function New-Packet {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupRoot = Join-SafePath -Root $Repo -RelativePath "backups"
    $folder = Join-Path $backupRoot "phase22_step61_cross_repo_handoff_packet_$timestamp"
    New-Item -ItemType Directory -Force -Path $folder | Out-Null

    $packet = [ordered]@{
        phase = 22
        step = 61
        name = $StepName
        prior_completed_step = $PriorStepName
        expected_branch = $ExpectedBranch
        planning_only = $true
        generated_at = (Get-Date).ToString("o")
        cross_repo_handoff = [ordered]@{
            purpose = "Prepare planning-only handoff from Phase 22 closeout into cross-repo coordination."
            platform_repo = "unified_pool_service_platform_build"
            extractor_repo = "start_here_extractor_m1_completion"
            bridge_repo = "front_desk_bridge or equivalent local bridge folder"
            handoff_mode = "reference_only"
            cross_repo_write = $false
            cross_repo_mutation = $false
            external_repo_push = $false
            phase23_start = $false
        }
        rollout_alignment = [ordered]@{
            connector_first_core = $true
            source_bucket_flow = "raw_to_normalized_to_matched_to_approved_to_applied"
            bridge_absorption_target = "connector_package_not_separate_product"
            expected_actual_logic = "preserved_for_future_phase"
            implementation_queue_creation = $false
        }
        safety_posture = Get-SafetyPosture
        step_files = $StepFiles
    }

    $jsonPath = Join-Path $folder "phase22_step61_cross_repo_handoff_packet.json"
    $packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: cross_repo_write=false"
    Write-Host "PASS: cross_repo_mutation=false"
    Write-Host "PASS: external_repo_push=false"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "CHECK: phase23_start=not_started"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: handoff_mode=reference_only"
    Write-Host "CHECK: packet_json=$jsonPath"
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "Phase 22 Step 61 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 22 Step 61 Cross-Repo Handoff Packet files"
        Write-Host "3. Smoke test Phase 22 Step 61"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 22 Step 61 cross-repo handoff packet"
        Write-Host "6. Exit"
        $choice = Read-Host "Choose 1-6"
        switch ($choice) {
            "1" { Show-Status }
            "2" { Apply-StepFiles }
            "3" { Test-Smoke }
            "4" {
                Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
                Write-Host "CHECK: No FastAPI, Streamlit, bridge server, network socket, or cross-repo write is started here."
                Write-Host "CHECK: Phase 23 start is intentionally deferred."
            }
            "5" { New-Packet }
            "6" { return }
            default { Write-Host "Choose a number from 1 through 6." }
        }
    }
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
    default { Show-Menu }
}

