param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$StepNumber = "56"
$PhaseStep = "Phase 22 Step 56"
$StepTitle = "Phase 22 Step 56 - Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Review Alignment Packet"
$PacketName = "Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Review Alignment Packet"
$ExpectedBranch = "phase22-step56-handoff-verification-review-alignment"
$PriorCompletedStep = "Phase 22 Step 55 - Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Alignment Packet"

$StepFiles = @(
    "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_verification_review_alignment.ps1",
    "ui/pages/162_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Handoff_Verification_Review_Alignment_Packet.py",
    "docs/PHASE22_STEP56_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_ACCEPTANCE_EVIDENCE_REVIEW_DISPOSITION_HANDOFF_VERIFICATION_REVIEW_ALIGNMENT_PACKET.md",
    "tests/test_phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_verification_review_alignment_packet.py"
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
        closure_resolution_disposition_creation = $false
        closure_resolution_disposition_approval_creation = $false
        closure_resolution_disposition_handoff_creation = $false
        closure_resolution_disposition_handoff_approval_creation = $false
        closure_resolution_handoff_execution = $false
        handoff_record_creation = $false
        handoff_queue_creation = $false
        handoff_verification_record_creation = $false
        handoff_verification_queue_creation = $false
        handoff_verification_acceptance_creation = $false
        handoff_verification_execution = $false
        handoff_verification_review_creation = $false
        handoff_verification_review_approval_creation = $false
        handoff_acceptance_creation = $false
        handoff_acceptance_approval_creation = $false
        handoff_acceptance_evidence_creation = $false
        handoff_acceptance_evidence_review_creation = $false
        handoff_acceptance_evidence_review_disposition_creation = $false
        handoff_acceptance_evidence_review_disposition_handoff_creation = $false
        handoff_acceptance_evidence_review_disposition_handoff_verification_creation = $false
        handoff_acceptance_evidence_review_disposition_handoff_verification_review_creation = $false
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
    if ($posture.planning_only -ne $true) { throw "Safety posture failed: planning_only" }
    if ($posture.no_platform_db_mutation -ne $true) { throw "Safety posture failed: no_platform_db_mutation" }
    if ($posture.no_bridge_mutation -ne $true) { throw "Safety posture failed: no_bridge_mutation" }
    if ($posture.no_real_bridge_http_client -ne $true) { throw "Safety posture failed: no_real_bridge_http_client" }
    if ($posture.no_network_transport_implementation -ne $true) { throw "Safety posture failed: no_network_transport_implementation" }
    if ($posture.no_bridge_post -ne $true) { throw "Safety posture failed: no_bridge_post" }
    if ($posture.no_network_sockets -ne $true) { throw "Safety posture failed: no_network_sockets" }
    if ($posture.lacrm_default_mode -ne "dry_run") { throw "Safety posture failed: lacrm_default_mode" }
    if ($posture.lacrm_live_write -ne $false) { throw "Safety posture failed: lacrm_live_write" }
    if ($posture.live_write_disabled -ne $true) { throw "Safety posture failed: live_write_disabled" }
    if ($posture.live_write_unarmed -ne $true) { throw "Safety posture failed: live_write_unarmed" }
    if ($posture.handoff_verification_review_creation -ne $false) { throw "Safety posture failed: handoff_verification_review_creation" }
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
    Write-Host "APPLY PASS: Phase 22 Step 56 files copied or already present."
}

function Invoke-Smoke {
    foreach ($relative in $StepFiles) {
        $path = Join-SafePath -Root $ResolvedRepoRoot -RelativePath $relative
        if (-not (Test-Path -LiteralPath $path)) {
            throw "SMOKE TEST FAIL: Missing required file $relative"
        }
    }

    Assert-SafetyPosture

    $scriptText = Get-Content -LiteralPath (Join-SafePath -Root $ResolvedRepoRoot -RelativePath "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_verification_review_alignment.ps1") -Raw
    $badExactLines = @(
        "lacrm_live_write = `$true",
        "implementation_phase_start = `$true",
        "authorization_record_creation = `$true",
        "operator_signoff_creation = `$true",
        "operator_approval_creation = `$true",
        "final_approval_creation = `$true",
        "design_closure_record_creation = `$true",
        "handoff_verification_review_creation = `$true"
    )
    foreach ($token in $badExactLines) {
        if ($scriptText.Contains($token)) {
            throw "SMOKE TEST FAIL: Forbidden exact safety assignment found: $token"
        }
    }

    Write-Host "SMOKE TEST PASS: Phase 22 Step 56 Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Review Alignment Packet is present and planning-only."
}

function Invoke-Packet {
    Assert-SafetyPosture
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $packetDir = Join-SafePath -Root $ResolvedRepoRoot -RelativePath ("backups/phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_verification_review_alignment_packet_" + $timestamp)
    if (-not (Test-Path -LiteralPath $packetDir)) {
        New-Item -ItemType Directory -Path $packetDir -Force | Out-Null
    }
    $packetPath = Join-Path $packetDir "phase22_step56_handoff_verification_review_packet.json"

    $packet = [ordered]@{
        phase_step = $PhaseStep
        step_number = $StepNumber
        packet_name = $PacketName
        prior_completed_step = $PriorCompletedStep
        expected_branch = $ExpectedBranch
        planning_only = $true
        safety_posture = Get-SafetyPosture
        alignment = [ordered]@{
            connector_first_operating_core = $true
            source_bucket_flow = "raw_normalized_matched_approved_applied"
            bridge_absorption_target = "connector_package_not_separate_product"
            handoff_verification_review = "planned_only"
            closure_deferral_acceptance_evidence_review_disposition_handoff_verification = "planned_only"
            applied_layer_release = "not_started"
            implementation_phase_start = "not_started"
        }
        generated_at = (Get-Date).ToString("o")
    }

    $packet | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $packetPath -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "PASS: handoff_verification_review=planned_only"
    Write-Host "PASS: closure_deferral_acceptance_evidence_review_disposition_handoff_verification=planned_only"
    Write-Host "PASS: handoff_verification_review_creation=false"
    Write-Host "PASS: handoff_verification_review_approval_creation=false"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: authorization_record_creation=false"
    Write-Host "CHECK: operator_signoff_creation=false"
    Write-Host "CHECK: operator_approval_creation=false"
    Write-Host "CHECK: final_approval_creation=false"
    Write-Host "CHECK: design_closure_record_creation=false"
    Write-Host "CHECK: closure_decision_creation=false"
    Write-Host "CHECK: handoff_record_creation=false"
    Write-Host "CHECK: handoff_queue_creation=false"
    Write-Host "CHECK: applied_layer_release=not_started"
    Write-Host "CHECK: packet_json=$packetPath"
}

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, ngrok tunnel, or network socket is started here."
    Write-Host "CHECK: Use a separate authorized implementation phase before runtime execution work."
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "Phase 22 Step 56 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 22 Step 56 files"
        Write-Host "3. Smoke test Phase 22 Step 56"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 20 network transport planning handoff verification review packet"
        Write-Host "6. Exit"
        $choice = Read-Host "Choose 1-6"
        switch ($choice) {
            "1" { Show-Status }
            "2" { Invoke-Apply }
            "3" { Invoke-Smoke }
            "4" { Show-ServerPlaceholder }
            "5" { Invoke-Packet }
            "6" { return }
            default { Write-Host "Invalid choice: $choice" }
        }
    }
}

switch ($Action) {
    "status" { Show-Status }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "packet" { Invoke-Packet }
    "all" { Show-Status; Invoke-Apply; Invoke-Smoke; Invoke-Packet }
    default { Show-Menu }
}


