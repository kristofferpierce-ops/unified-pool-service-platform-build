param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$Phase = 22
$Step = 29
$StepTitle = "Phase 22 Step 29 - Phase 20 Network Transport Planning Recommendation Engine Alignment Packet"
$ExpectedBranch = "phase22-step29-phase20-network-transport-planning-recommendation-engine-alignment-packet"
$PriorCompletedStep = "Phase 22 Step 28 - Phase 20 Network Transport Planning Pattern Detection Alignment Packet"

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
    source_bucket_writes = $false
    canonical_event_ledger_writes = $false
    expected_actual_engine_runtime = $false
    driver_attribution_runtime = $false
    probabilistic_calibration_runtime = $false
    pattern_detection_runtime = $false
    anomaly_detection_runtime = $false
    recommendation_engine_runtime = $false
    recommendation_decision_application = $false
    recommendation_writeback_runtime = $false
}

$StepFiles = @(
    [ordered]@{
        relative_path = "scripts\phase22_generate_phase20_network_transport_planning_recommendation_engine_alignment_packet.ps1"
        description = "Phase 22 Step 29 path-safe planning launcher"
    },
    [ordered]@{
        relative_path = "ui\pages\135_Phase20_Network_Transport_Planning_Recommendation_Engine_Alignment_Packet.py"
        description = "Streamlit planning page for recommendation engine alignment"
    },
    [ordered]@{
        relative_path = "docs\PHASE22_STEP29_PHASE20_NETWORK_TRANSPORT_PLANNING_RECOMMENDATION_ENGINE_ALIGNMENT_PACKET.md"
        description = "Planning documentation for recommendation engine alignment"
    },
    [ordered]@{
        relative_path = "tests\test_phase22_phase20_network_transport_planning_recommendation_engine_alignment_packet.py"
        description = "Planning-only pytest coverage for Phase 22 Step 29"
    }
)

function Remove-ControlCharacters {
    param([string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    return -join ($Value.ToCharArray() | Where-Object {
        $code = [int][char]$_
        ($code -eq 9) -or ($code -eq 10) -or ($code -eq 13) -or ($code -ge 32)
    })
}

function Test-LiteralPathSafe {
    param([string]$PathValue)

    $Clean = Remove-ControlCharacters $PathValue
    if ([string]::IsNullOrWhiteSpace($Clean)) {
        return $false
    }

    try {
        return Test-Path -LiteralPath $Clean
    }
    catch {
        return $false
    }
}

function Get-FullPathSafe {
    param([string]$PathValue)

    $Clean = Remove-ControlCharacters $PathValue
    return [System.IO.Path]::GetFullPath($Clean)
}

function Join-PathSafe {
    param(
        [string]$BasePath,
        [string]$ChildPath
    )

    $CleanBase = Remove-ControlCharacters $BasePath
    $CleanChild = Remove-ControlCharacters $ChildPath
    return Join-Path -Path $CleanBase -ChildPath $CleanChild
}

function Resolve-RepoRoot {
    param([string]$RequestedRoot)

    $Candidates = New-Object System.Collections.Generic.List[string]

    if (-not [string]::IsNullOrWhiteSpace($RequestedRoot)) {
        [void]$Candidates.Add((Remove-ControlCharacters $RequestedRoot))
    }

    [void]$Candidates.Add((Get-Location).Path)

    if ($PSScriptRoot) {
        [void]$Candidates.Add((Resolve-Path -LiteralPath (Join-PathSafe $PSScriptRoot "..")).Path)
    }

    foreach ($Candidate in $Candidates) {
        if ([string]::IsNullOrWhiteSpace($Candidate)) {
            continue
        }

        $Full = Get-FullPathSafe $Candidate
        $GitPath = Join-PathSafe $Full ".git"
        if (Test-LiteralPathSafe $GitPath) {
            return $Full
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($RequestedRoot)) {
        $RequestedFull = Get-FullPathSafe $RequestedRoot
        if (Test-LiteralPathSafe $RequestedFull) {
            return $RequestedFull
        }
    }

    return (Get-Location).Path
}

function Resolve-SourceRoot {
    param([string]$ResolvedRepoRoot)

    if ($PSScriptRoot) {
        $ScriptParent = (Resolve-Path -LiteralPath (Join-PathSafe $PSScriptRoot "..")).Path
        $DocPath = Join-PathSafe $ScriptParent "docs\PHASE22_STEP29_PHASE20_NETWORK_TRANSPORT_PLANNING_RECOMMENDATION_ENGINE_ALIGNMENT_PACKET.md"
        if (Test-LiteralPathSafe $DocPath) {
            return $ScriptParent
        }
    }

    $RepoDocPath = Join-PathSafe $ResolvedRepoRoot "docs\PHASE22_STEP29_PHASE20_NETWORK_TRANSPORT_PLANNING_RECOMMENDATION_ENGINE_ALIGNMENT_PACKET.md"
    if (Test-LiteralPathSafe $RepoDocPath) {
        return $ResolvedRepoRoot
    }

    return $ResolvedRepoRoot
}

function Write-StepHeader {
    Write-Host ("=" * 78)
    Write-Host $StepTitle
    Write-Host ("=" * 78)
}

function Show-Status {
    param([string]$ResolvedRepoRoot)

    Write-StepHeader
    Write-Host "Repo root: $ResolvedRepoRoot"
    Write-Host "Expected branch: $ExpectedBranch"
    Write-Host "Prior completed step: $PriorCompletedStep"
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    foreach ($Key in $SafetyPosture.Keys) {
        Write-Host ("  {0}: {1}" -f $Key, $SafetyPosture[$Key])
    }

    Write-Host ""
    Write-Host "Step files"
    foreach ($File in $StepFiles) {
        $TargetPath = Join-PathSafe $ResolvedRepoRoot $File.relative_path
        if (Test-LiteralPathSafe $TargetPath) {
            Write-Host ("  PRESENT {0}" -f $File.relative_path)
        }
        else {
            Write-Host ("  MISSING {0}" -f $File.relative_path)
        }
    }
}

function Copy-StepFiles {
    param(
        [string]$ResolvedRepoRoot,
        [string]$SourceRoot
    )

    foreach ($File in $StepFiles) {
        $SourcePath = Join-PathSafe $SourceRoot $File.relative_path
        $TargetPath = Join-PathSafe $ResolvedRepoRoot $File.relative_path

        if (-not (Test-LiteralPathSafe $SourcePath)) {
            if (Test-LiteralPathSafe $TargetPath) {
                Write-Host ("SKIPPED {0} source missing but target already present." -f $File.relative_path)
                continue
            }

            throw "APPLY FAIL: Missing source file $SourcePath"
        }

        $SourceFull = Get-FullPathSafe $SourcePath
        $TargetFull = Get-FullPathSafe $TargetPath

        if ([string]::Equals($SourceFull, $TargetFull, [System.StringComparison]::OrdinalIgnoreCase)) {
            Write-Host ("SKIPPED {0} source and target are the same file." -f $File.relative_path)
            continue
        }

        $TargetDirectory = Split-Path -Parent $TargetFull
        if (-not (Test-LiteralPathSafe $TargetDirectory)) {
            New-Item -ItemType Directory -Path $TargetDirectory -Force | Out-Null
        }

        Copy-Item -LiteralPath $SourceFull -Destination $TargetFull -Force
        Write-Host ("COPIED {0}" -f $File.relative_path)
    }

    Write-Host "APPLY PASS: Phase 22 Step 29 files copied or already present."
}

function Test-StepSmoke {
    param([string]$ResolvedRepoRoot)

    foreach ($File in $StepFiles) {
        $TargetPath = Join-PathSafe $ResolvedRepoRoot $File.relative_path
        if (-not (Test-LiteralPathSafe $TargetPath)) {
            throw "SMOKE TEST FAIL: Missing $($File.relative_path)"
        }
    }

    $ForbiddenTokenParts = @(
        @("planning", "_", "only", "=", "false"),
        @("lacrm", "_", "live", "_", "write", "=", "true"),
        @("live", "_", "write", "_", "disabled", "=", "false"),
        @("live", "_", "write", "_", "unarmed", "=", "false"),
        @("implementation", "_", "phase", "_", "start", "=", "true"),
        @("authorization", "_", "record", "_", "creation", "=", "true"),
        @("operator", "_", "signoff", "_", "creation", "=", "true"),
        @("operator", "_", "approval", "_", "creation", "=", "true"),
        @("final", "_", "approval", "_", "creation", "=", "true"),
        @("design", "_", "closure", "_", "record", "_", "creation", "=", "true"),
        @("requests", ".", "post"),
        @("urllib", ".", "request"),
        @("http", ".", "client"),
        @("socket", ".", "create", "_", "connection"),
        @("Fast", "API", "("),
        @("uvicorn", ".", "run")
    )

    foreach ($File in $StepFiles) {
        $TargetPath = Join-PathSafe $ResolvedRepoRoot $File.relative_path
        $Text = Get-Content -LiteralPath $TargetPath -Raw
        $LowerText = $Text.ToLowerInvariant()

        foreach ($Parts in $ForbiddenTokenParts) {
            $Token = (($Parts -join "")).ToLowerInvariant()
            if ($LowerText.Contains($Token)) {
                throw "SMOKE TEST FAIL: Forbidden token found in $($File.relative_path): $Token"
            }
        }
    }

    Write-Host "SMOKE TEST PASS: Phase 22 Step 29 Phase 20 Network Transport Planning Recommendation Engine Alignment Packet is present and planning-only."
}

function New-StepPacket {
    param([string]$ResolvedRepoRoot)

    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $OutputDirectory = Join-PathSafe $ResolvedRepoRoot "backups\phase22_phase20_network_transport_planning_recommendation_engine_alignment_packet_$Timestamp"
    if (-not (Test-LiteralPathSafe $OutputDirectory)) {
        New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    }

    $PacketPath = Join-PathSafe $OutputDirectory "phase22_phase20_network_transport_planning_recommendation_engine_alignment_packet.json"

    $Packet = [ordered]@{
        packet_id = "phase22_step29_phase20_network_transport_planning_recommendation_engine_alignment_packet"
        phase = 22
        step = 29
        title = $StepTitle
        prior_completed_step = $PriorCompletedStep
        expected_branch = $ExpectedBranch
        generated_at = (Get-Date).ToString("o")
        safety_posture = $SafetyPosture
        planning_alignment = [ordered]@{
            connector_first_operating_core = $true
            source_bucket_alignment = "raw_normalized_matched_approved_applied"
            canonical_event_ledger_dependency = "planned_reference_only"
            expected_actual_variance_dependency = "planned_reference_only"
            driver_attribution_dependency = "planned_reference_only"
            probabilistic_calibration_dependency = "planned_reference_only"
            pattern_detection_dependency = "planned_reference_only"
            recommendation_engine_stage = "planning_alignment_only"
            recommendation_engine_runtime = $false
            recommendation_decision_application = $false
            recommendation_writeback_runtime = $false
            manual_approval_required = $true
            branch_overlay_required = $true
            source_provenance_required = $true
            bridge_absorption_target = "connector_package_not_separate_product"
            bridge_route_surface_preserved = $true
            shared_database_merge_authorized = $false
            runtime_execution_authorized = $false
            implementation_phase_start = "not_started"
        }
        recommendation_engine_scope = [ordered]@{
            price_adjustment_candidates = "planned_only"
            scope_reduction_candidates = "planned_only"
            route_density_recommendations = "planned_only"
            vendor_change_candidates = "planned_only"
            branch_expansion_signals = "planned_only"
            retreat_signals = "planned_only"
            account_scoring = "planned_only"
            route_scoring = "planned_only"
            quote_model_calibration_feedback = "planned_only"
            service_line_guidance = "planned_only"
        }
        non_actions = @(
            "no platform DB mutation",
            "no bridge DB mutation",
            "no bridge POST",
            "no network sockets",
            "no real bridge HTTP client",
            "no LACRM live write",
            "no source bucket writes",
            "no event ledger writes",
            "no anomaly detection runtime",
            "no recommendation engine runtime",
            "no recommendation writeback runtime",
            "no recommendation decision application",
            "no implementation phase start",
            "no operator signoff creation",
            "no operator approval creation",
            "no final approval creation",
            "no design closure record creation"
        )
        files = $StepFiles
    }

    $Packet | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $PacketPath -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "PASS: recommendation_engine_runtime=false"
    Write-Host "PASS: recommendation_writeback_runtime=false"
    Write-Host "PASS: recommendation_decision_application=false"
    Write-Host "CHECK: recommendation_engine_stage=planning_alignment_only"
    Write-Host "CHECK: manual_approval_required=true"
    Write-Host "CHECK: branch_overlay_required=true"
    Write-Host "CHECK: source_provenance_required=true"
    Write-Host "CHECK: pattern_detection_dependency=planned_reference_only"
    Write-Host "CHECK: connector_first_operating_core=true"
    Write-Host "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied"
    Write-Host "CHECK: bridge_absorption_target=connector_package_not_separate_product"
    Write-Host "CHECK: packet_json=$PacketPath"
}

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, ngrok tunnel, or network socket is started here."
    Write-Host "CHECK: Recommendation-engine execution, writeback, and decision application remain disabled."
}

function Invoke-Action {
    param(
        [string]$RequestedAction,
        [string]$ResolvedRepoRoot,
        [string]$SourceRoot
    )

    switch ($RequestedAction) {
        "status" { Show-Status -ResolvedRepoRoot $ResolvedRepoRoot }
        "apply" { Copy-StepFiles -ResolvedRepoRoot $ResolvedRepoRoot -SourceRoot $SourceRoot }
        "smoke" { Test-StepSmoke -ResolvedRepoRoot $ResolvedRepoRoot }
        "packet" { New-StepPacket -ResolvedRepoRoot $ResolvedRepoRoot }
        "all" {
            Show-Status -ResolvedRepoRoot $ResolvedRepoRoot
            Copy-StepFiles -ResolvedRepoRoot $ResolvedRepoRoot -SourceRoot $SourceRoot
            Test-StepSmoke -ResolvedRepoRoot $ResolvedRepoRoot
            New-StepPacket -ResolvedRepoRoot $ResolvedRepoRoot
        }
        default { throw "Unsupported action: $RequestedAction" }
    }
}

function Show-Menu {
    param(
        [string]$ResolvedRepoRoot,
        [string]$SourceRoot
    )

    while ($true) {
        Write-Host ""
        Write-Host "Phase 22 Step 29 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 22 Step 29 Phase 20 Network Transport Planning Recommendation Engine Alignment Packet files"
        Write-Host "3. Smoke test Phase 22 Step 29"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 20 network transport planning recommendation engine alignment packet"
        Write-Host "6. Exit"

        $ChoiceRaw = Read-Host "Choose 1-6"
        $Choice = (Remove-ControlCharacters $ChoiceRaw).Trim()

        switch ($Choice) {
            "1" { Show-Status -ResolvedRepoRoot $ResolvedRepoRoot }
            "2" { Copy-StepFiles -ResolvedRepoRoot $ResolvedRepoRoot -SourceRoot $SourceRoot }
            "3" { Test-StepSmoke -ResolvedRepoRoot $ResolvedRepoRoot }
            "4" { Show-ServerPlaceholder }
            "5" { New-StepPacket -ResolvedRepoRoot $ResolvedRepoRoot }
            "6" { return }
            default { Write-Host "Please choose a number from 1 through 6." }
        }
    }
}

$ResolvedRepoRoot = Resolve-RepoRoot -RequestedRoot $RepoRoot
$SourceRoot = Resolve-SourceRoot -ResolvedRepoRoot $ResolvedRepoRoot

if ($Action -eq "menu") {
    Show-Menu -ResolvedRepoRoot $ResolvedRepoRoot -SourceRoot $SourceRoot
}
else {
    Invoke-Action -RequestedAction $Action -ResolvedRepoRoot $ResolvedRepoRoot -SourceRoot $SourceRoot
}
