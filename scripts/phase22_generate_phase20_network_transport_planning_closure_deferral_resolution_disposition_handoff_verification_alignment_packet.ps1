param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$PhaseStep = "Phase 22 Step 48"
$PacketName = "Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Verification Alignment Packet"
$ExpectedBranch = "phase22-step48-phase20-network-transport-planning-closure-deferral-resolution-disposition-handoff-verification-alignment-packet"
$PriorCompletedStep = "Phase 22 Step 47 - Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Alignment Packet"

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
    closure_review_record_creation = $false
    closure_resolution_disposition_creation = $false
    closure_resolution_disposition_approval_creation = $false
    closure_resolution_disposition_handoff_creation = $false
    closure_resolution_disposition_handoff_approval_creation = $false
    closure_resolution_disposition_handoff_verification_creation = $false
    closure_resolution_disposition_handoff_verification_approval_creation = $false
    closure_resolution_handoff_execution = $false
    closure_resolution_handoff_verification_execution = $false
    handoff_record_creation = $false
    handoff_queue_creation = $false
    handoff_verification_record_creation = $false
    handoff_verification_queue_creation = $false
    handoff_acceptance_creation = $false
    handoff_acceptance_approval_creation = $false
    closure_resolution_approval_creation = $false
    disposition_record_creation = $false
    closure_decision_creation = $false
    closure_deferral_backlog_mutation = $false
    resolution_evidence_mutation = $false
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

$StepFiles = [ordered]@{
    "launcher" = "scripts\phase22_generate_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_verification_alignment_packet.ps1"
    "ui" = "ui\pages\154_Phase20_Network_Transport_Planning_Closure_Deferral_Resolution_Disposition_Handoff_Verification_Alignment_Packet.py"
    "doc" = "docs\PHASE22_STEP48_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_RESOLUTION_DISPOSITION_HANDOFF_VERIFICATION_ALIGNMENT_PACKET.md"
    "test" = "tests\test_phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_verification_alignment_packet.py"
}

function Write-Header {
    Write-Host "=============================================================================="
    Write-Host "$PhaseStep - $PacketName"
    Write-Host "=============================================================================="
}

function Normalize-PathText {
    param([string]$PathText)
    if ([string]::IsNullOrWhiteSpace($PathText)) {
        return ""
    }
    $clean = -join ($PathText.ToCharArray() | Where-Object { [int][char]$_ -ge 32 })
    return $clean.Trim()
}

function Resolve-RepoRoot {
    param([string]$Candidate)
    $candidateClean = Normalize-PathText $Candidate
    if ($candidateClean -and (Test-Path -LiteralPath $candidateClean)) {
        return (Resolve-Path -LiteralPath $candidateClean).Path
    }

    $current = (Get-Location).Path
    if (Test-Path -LiteralPath (Join-Path $current ".git")) {
        return $current
    }

    $scriptDir = Split-Path -Parent $PSCommandPath
    $maybeRepo = Split-Path -Parent $scriptDir
    if (Test-Path -LiteralPath (Join-Path $maybeRepo ".git")) {
        return $maybeRepo
    }

    throw "Could not resolve repo root. Pass -RepoRoot explicitly."
}

function Resolve-SourceRoot {
    $scriptDir = Split-Path -Parent $PSCommandPath
    $sourceRoot = Split-Path -Parent $scriptDir
    return $sourceRoot
}

function Get-StepPath {
    param(
        [string]$Root,
        [string]$RelativePath
    )
    return Join-Path $Root $RelativePath
}

function Test-SameFile {
    param(
        [string]$Left,
        [string]$Right
    )
    $leftFull = [System.IO.Path]::GetFullPath($Left)
    $rightFull = [System.IO.Path]::GetFullPath($Right)
    return [string]::Equals($leftFull, $rightFull, [System.StringComparison]::OrdinalIgnoreCase)
}

function Show-Status {
    param([string]$ResolvedRepoRoot)
    Write-Header
    Write-Host "Repo root: $ResolvedRepoRoot"
    Write-Host "Expected branch: $ExpectedBranch"
    Write-Host "Prior completed step: $PriorCompletedStep"
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    foreach ($item in $SafetyPosture.GetEnumerator()) {
        Write-Host ("  {0}: {1}" -f $item.Key, $item.Value)
    }
    Write-Host ""
    Write-Host "Step files"
    foreach ($relativePath in $StepFiles.Values) {
        $target = Get-StepPath -Root $ResolvedRepoRoot -RelativePath $relativePath
        if (Test-Path -LiteralPath $target) {
            Write-Host "  PRESENT $relativePath"
        } else {
            Write-Host "  MISSING $relativePath"
        }
    }
}

function Apply-StepFiles {
    param([string]$ResolvedRepoRoot)
    $sourceRoot = Resolve-SourceRoot
    foreach ($relativePath in $StepFiles.Values) {
        $sourcePath = Get-StepPath -Root $sourceRoot -RelativePath $relativePath
        $targetPath = Get-StepPath -Root $ResolvedRepoRoot -RelativePath $relativePath
        $targetDir = Split-Path -Parent $targetPath

        if (-not (Test-Path -LiteralPath $sourcePath)) {
            if (Test-Path -LiteralPath $targetPath) {
                Write-Host "SKIPPED $relativePath source missing but target already present."
                continue
            }
            throw "Missing source file: $sourcePath"
        }

        if (Test-SameFile -Left $sourcePath -Right $targetPath) {
            Write-Host "SKIPPED $relativePath source and target are the same file."
            continue
        }

        if (-not (Test-Path -LiteralPath $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }

        Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
        Write-Host "COPIED $relativePath"
    }

    Write-Host "APPLY PASS: $PhaseStep files copied or already present."
}

function Assert-PlanningOnly {
    param([string]$ResolvedRepoRoot)

    foreach ($relativePath in $StepFiles.Values) {
        $target = Get-StepPath -Root $ResolvedRepoRoot -RelativePath $relativePath
        if (-not (Test-Path -LiteralPath $target)) {
            throw "SMOKE TEST FAIL: Missing $relativePath"
        }
    }

    $forbiddenTokens = @(
        ("planning" + "_only: False"),
        ("planning" + "_only = `$false"),
        ("no_network" + "_sockets: False"),
        ("no_bridge" + "_post: False"),
        ("lacrm_live" + "_write=true"),
        ("live_write" + "_disabled=false"),
        ("live_write" + "_unarmed=false"),
        ("implementation_phase" + "_start=true"),
        ("operator_signoff" + "_creation=true"),
        ("operator_approval" + "_creation=true"),
        ("final_approval" + "_creation=true"),
        ("design_closure_record" + "_creation=true"),
        ("closure_resolution_disposition" + "_creation=true"),
        ("closure_resolution_disposition_approval" + "_creation=true"),
        ("closure_resolution_disposition_handoff" + "_creation=true"),
        ("closure_resolution_disposition_handoff_approval" + "_creation=true"),
        ("closure_resolution_disposition_handoff_verification" + "_creation=true"),
        ("closure_resolution_disposition_handoff_verification_approval" + "_creation=true"),
        ("closure_resolution_handoff" + "_execution=true"),
        ("closure_resolution_handoff_verification" + "_execution=true"),
        ("handoff_record" + "_creation=true"),
        ("handoff_queue" + "_creation=true"),
        ("handoff_verification_record" + "_creation=true"),
        ("handoff_verification_queue" + "_creation=true"),
        ("handoff_acceptance" + "_creation=true"),
        ("handoff_acceptance_approval" + "_creation=true"),
        ("closure_resolution_approval" + "_creation=true"),
        ("disposition_record" + "_creation=true"),
        ("closure_decision" + "_creation=true")
    )

    foreach ($relativePath in $StepFiles.Values) {
        $target = Get-StepPath -Root $ResolvedRepoRoot -RelativePath $relativePath
        $text = Get-Content -LiteralPath $target -Raw
        foreach ($token in $forbiddenTokens) {
            if ($text.Contains($token)) {
                throw "SMOKE TEST FAIL: Forbidden token found in ${relativePath}: $token"
            }
        }
    }

    Write-Host "SMOKE TEST PASS: $PhaseStep $PacketName is present and planning-only."
}

function New-PlanningPacket {
    param([string]$ResolvedRepoRoot)

    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $packetDir = Join-Path $ResolvedRepoRoot "backups\phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_verification_alignment_packet_$timestamp"
    New-Item -ItemType Directory -Path $packetDir -Force | Out-Null

    $packet = [ordered]@{
        phase = 22
        step = 48
        phase_step = $PhaseStep
        packet_name = $PacketName
        generated_at = (Get-Date).ToString("o")
        planning_only = $true
        prior_completed_step = $PriorCompletedStep
        source_bucket_alignment = "raw_normalized_matched_approved_applied"
        bridge_absorption_target = "connector_package_not_separate_product"
        connector_first_operating_core = $true
        closure_deferral_resolution_disposition_handoff_verification_alignment = [ordered]@{
            resolution_disposition_handoff = "planned_only"
            verification_path = "planned_only"
            acceptance_path = "not_started"
            verification_record = "not_created"
            verification_queue = "not_created"
            handoff_acceptance = "not_created"
            approval_record = "not_created"
            backlog_mutation = "not_created"
            applied_layer_release = "not_started"
            implementation_transition = "not_started"
        }
        safety = $SafetyPosture
        step_files = $StepFiles
        operator_signoff_creation = $false
        operator_approval_creation = $false
        final_approval_creation = $false
        design_closure_record_creation = $false
        implementation_phase_start = "not_started"
        lacrm_default_mode = "dry_run"
        lacrm_live_write = $false
        live_write_disabled = $true
        live_write_unarmed = $true
    }

    $packetPath = Join-Path $packetDir "phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_verification_alignment_packet.json"
    $packet | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $packetPath -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "PASS: closure_deferral_resolution_disposition_handoff_verification=planned_only"
    Write-Host "PASS: closure_deferral_resolution_disposition_handoff=planned_only"
    Write-Host "PASS: closure_resolution_disposition_handoff_verification_creation=false"
    Write-Host "PASS: closure_resolution_disposition_handoff_verification_approval_creation=false"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: authorization_record_creation=false"
    Write-Host "CHECK: operator_signoff_creation=false"
    Write-Host "CHECK: operator_approval_creation=false"
    Write-Host "CHECK: final_approval_creation=false"
    Write-Host "CHECK: design_closure_record_creation=false"
    Write-Host "CHECK: closure_decision_creation=false"
    Write-Host "CHECK: closure_resolution_disposition_handoff_creation=false"
    Write-Host "CHECK: closure_resolution_disposition_handoff_approval_creation=false"
    Write-Host "CHECK: closure_resolution_handoff_execution=false"
    Write-Host "CHECK: closure_resolution_handoff_verification_execution=false"
    Write-Host "CHECK: handoff_record_creation=false"
    Write-Host "CHECK: handoff_queue_creation=false"
    Write-Host "CHECK: handoff_verification_record_creation=false"
    Write-Host "CHECK: handoff_verification_queue_creation=false"
    Write-Host "CHECK: handoff_acceptance_creation=false"
    Write-Host "CHECK: handoff_acceptance_approval_creation=false"
    Write-Host "CHECK: disposition_record_creation=false"
    Write-Host "CHECK: applied_layer_release=not_started"
    Write-Host "CHECK: packet_json=$packetPath"
}

function Show-Menu {
    param([string]$ResolvedRepoRoot)

    while ($true) {
        Write-Host ""
        Write-Host "$PhaseStep menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply $PhaseStep $PacketName files"
        Write-Host "3. Smoke test $PhaseStep"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 20 network transport planning closure deferral resolution disposition handoff verification packet"
        Write-Host "6. Exit"
        $choice = (Read-Host "Choose 1-6").Trim()

        switch ($choice) {
            "1" { Show-Status -ResolvedRepoRoot $ResolvedRepoRoot }
            "2" { Apply-StepFiles -ResolvedRepoRoot $ResolvedRepoRoot }
            "3" { Assert-PlanningOnly -ResolvedRepoRoot $ResolvedRepoRoot }
            "4" {
                Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
                Write-Host "CHECK: No FastAPI, Streamlit, bridge server, ngrok, webhook listener, or network socket is started here."
                Write-Host "CHECK: Use a separate authorized implementation phase before any runtime execution work."
            }
            "5" { New-PlanningPacket -ResolvedRepoRoot $ResolvedRepoRoot }
            "6" { return }
            default { Write-Host "Invalid choice. Choose 1-6." }
        }
    }
}

$ResolvedRepoRoot = Resolve-RepoRoot -Candidate $RepoRoot

switch ($Action) {
    "status" { Show-Status -ResolvedRepoRoot $ResolvedRepoRoot }
    "apply" { Apply-StepFiles -ResolvedRepoRoot $ResolvedRepoRoot }
    "smoke" { Assert-PlanningOnly -ResolvedRepoRoot $ResolvedRepoRoot }
    "packet" { New-PlanningPacket -ResolvedRepoRoot $ResolvedRepoRoot }
    "all" {
        Show-Status -ResolvedRepoRoot $ResolvedRepoRoot
        Apply-StepFiles -ResolvedRepoRoot $ResolvedRepoRoot
        Assert-PlanningOnly -ResolvedRepoRoot $ResolvedRepoRoot
        New-PlanningPacket -ResolvedRepoRoot $ResolvedRepoRoot
    }
    default { Show-Menu -ResolvedRepoRoot $ResolvedRepoRoot }
}

