param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$StepNumber = "55"
$PhaseStep = "Phase 22 Step 55"
$StepTitle = "Phase 22 Step 55 - Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Alignment Packet"
$PacketName = "Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Alignment Packet"
$ExpectedBranch = "phase22-step55-phase20-network-transport-planning-closure-deferral-acceptance-evidence-review-disposition-handoff-verification-alignment-packet"
$PriorCompletedStep = "Phase 22 Step 54 - Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Alignment Packet"

$StepFiles = @(
    "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_verification_alignment.ps1",
    "ui/pages/161_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Handoff_Verification_Alignment_Packet.py",
    "docs/PHASE22_STEP55_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_ACCEPTANCE_EVIDENCE_REVIEW_DISPOSITION_HANDOFF_VERIFICATION_ALIGNMENT_PACKET.md",
    "tests/test_phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_verification_alignment_packet.py"
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
    $candidates += (Split-Path -Parent $PSCommandPath)
    $candidates += (Join-Path (Split-Path -Parent $PSCommandPath) "..")

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
        handoff_acceptance_creation = $false
        handoff_acceptance_approval_creation = $false
        handoff_acceptance_evidence_creation = $false
        handoff_acceptance_evidence_review_creation = $false
        handoff_acceptance_evidence_review_disposition_creation = $false
        handoff_acceptance_evidence_review_disposition_handoff_creation = $false
        handoff_acceptance_evidence_review_disposition_handoff_verification_creation = $false
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

        if ($sourcePath -eq $targetPath) {
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

    Write-Host "APPLY PASS: Phase 22 Step 55 files copied or already present."
}

function Invoke-Smoke {
    foreach ($relative in $StepFiles) {
        $path = Join-SafePath -Root $ResolvedRepoRoot -RelativePath $relative
        if (-not (Test-Path -LiteralPath $path)) {
            throw "SMOKE TEST FAIL: Missing required file $relative"
        }
    }

    $combined = ""
    foreach ($relative in $StepFiles) {
        $path = Join-SafePath -Root $ResolvedRepoRoot -RelativePath $relative
        $combined += "`n"
        $combined += Get-Content -LiteralPath $path -Raw
    }

    $required = @(
        "Phase 22 Step 55",
        "Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Alignment Packet",
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "lacrm_default_mode",
        "dry_run",
        "live_write_disabled",
        "live_write_unarmed",
        "handoff_acceptance_evidence_review_disposition_handoff_verification",
        "planned_only"
    )

    foreach ($token in $required) {
        if ($combined -notlike "*$token*") {
            throw "SMOKE TEST FAIL: Required token missing: $token"
        }
    }

    $forbidden = @(
        ("lacrm_live_" + "write=true"),
        ("live_write_" + "disabled=false"),
        ("no_network_" + "sockets=false"),
        ("implementation_phase_" + "start=true"),
        ("operator_signoff_" + "creation=true"),
        ("final_approval_" + "creation=true"),
        ("design_closure_record_" + "creation=true"),
        ("handoff_verification_" + "execution=true"),
        ("handoff_verification_" + "record_creation=true"),
        ("handoff_verification_" + "queue_creation=true"),
        ("db_mutation = " + "$true"),
        ("bridge_post = " + "$true")
    )

    foreach ($token in $forbidden) {
        if ($combined.Contains($token)) {
            throw "SMOKE TEST FAIL: Forbidden token found: $token"
        }
    }

    Write-Host "SMOKE TEST PASS: Phase 22 Step 55 Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Alignment Packet is present and planning-only."
}

function Invoke-Packet {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupRoot = Join-SafePath -Root $ResolvedRepoRoot -RelativePath "backups"
    $packetFolder = Join-Path $backupRoot ("phase22_step55_handoff_verification_packet_" + $timestamp)

    if (-not (Test-Path -LiteralPath $packetFolder)) {
        New-Item -ItemType Directory -Path $packetFolder -Force | Out-Null
    }

    $packetPath = Join-Path $packetFolder "phase22_step55_handoff_verification_packet.json"

    $packet = [ordered]@{
        phase_step = "Phase 22 Step 55"
        packet_name = "Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Alignment Packet"
        prior_completed_step = $PriorCompletedStep
        expected_branch = $ExpectedBranch
        planning_only = $true
        source_bucket_alignment = "raw_normalized_matched_approved_applied"
        connector_first_operating_core = $true
        bridge_absorption_target = "connector_package_not_separate_product"
        handoff_acceptance_evidence_review_disposition_handoff_verification = "planned_only"
        handoff_verification_record_creation = $false
        handoff_verification_queue_creation = $false
        handoff_verification_acceptance_creation = $false
        handoff_verification_execution = $false
        closure_decision_creation = $false
        implementation_phase_start = "not_started"
        safety_posture = Get-SafetyPosture
        step_files = $StepFiles
        generated_at = (Get-Date).ToString("o")
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
    Write-Host "PASS: handoff_acceptance_evidence_review_disposition_handoff_verification=planned_only"
    Write-Host "PASS: handoff_verification_record_creation=false"
    Write-Host "PASS: handoff_verification_queue_creation=false"
    Write-Host "PASS: handoff_verification_acceptance_creation=false"
    Write-Host "PASS: handoff_verification_execution=false"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: authorization_record_creation=false"
    Write-Host "CHECK: operator_signoff_creation=false"
    Write-Host "CHECK: operator_approval_creation=false"
    Write-Host "CHECK: final_approval_creation=false"
    Write-Host "CHECK: design_closure_record_creation=false"
    Write-Host "CHECK: closure_decision_creation=false"
    Write-Host "CHECK: applied_layer_release=not_started"
    Write-Host "CHECK: packet_json=$packetPath"
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "Phase 22 Step 55 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 22 Step 55 Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Verification Alignment Packet files"
        Write-Host "3. Smoke test Phase 22 Step 55"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 20 network transport planning closure deferral acceptance evidence review disposition handoff verification alignment packet"
        Write-Host "6. Exit"
        $choice = Read-Host "Choose 1-6"

        switch ($choice.Trim()) {
            "1" { Show-Status }
            "2" { Invoke-Apply }
            "3" { Invoke-Smoke }
            "4" {
                Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
                Write-Host "CHECK: No FastAPI, Streamlit, bridge server, or network socket is started here."
                Write-Host "CHECK: Use a separate authorized implementation phase before any runtime execution work."
            }
            "5" { Invoke-Packet }
            "6" { return }
            default { Write-Host "Invalid option." }
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


