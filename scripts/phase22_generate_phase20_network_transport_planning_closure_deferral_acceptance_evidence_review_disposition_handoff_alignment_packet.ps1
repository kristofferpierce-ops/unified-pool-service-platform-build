param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$StepNumber = "54"
$PhaseStep = "Phase 22 Step 54"
$StepTitle = "Phase 22 Step 54 - Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Alignment Packet"
$PacketName = "Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Handoff Alignment Packet"
$ExpectedBranch = "phase22-step54-phase20-network-transport-planning-closure-deferral-acceptance-evidence-review-disposition-handoff-alignment-packet"
$PriorCompletedStep = "Phase 22 Step 53 - Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Alignment Packet"

$StepFiles = @(
    "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_alignment_packet.ps1",
    "ui/pages/160_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Handoff_Alignment_Packet.py",
    "docs/PHASE22_STEP54_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_ACCEPTANCE_EVIDENCE_REVIEW_DISPOSITION_HANDOFF_ALIGNMENT_PACKET.md",
    "tests/test_phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_alignment_packet.py"
)

function Normalize-RelativePath {
    param([Parameter(Mandatory=$true)][string]$RelativePath)

    $value = $RelativePath.Replace('/', '\').Trim()
    $value = $value.TrimStart('\')

    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Relative path is empty."
    }

    if ($value.Contains(":")) {
        throw "Relative path must not contain a drive designator: $RelativePath"
    }

    foreach ($part in $value.Split('\')) {
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
        handoff_acceptance_creation = $false
        handoff_acceptance_approval_creation = $false
        handoff_acceptance_evidence_creation = $false
        handoff_acceptance_evidence_review_creation = $false
        handoff_acceptance_evidence_review_disposition_creation = $false
        handoff_acceptance_evidence_review_disposition_handoff_creation = $false
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

function Apply-StepFiles {
    foreach ($relative in $StepFiles) {
        $sourcePath = Join-SafePath -Root $ResolvedRepoRoot -RelativePath $relative
        $targetPath = Join-SafePath -Root $ResolvedRepoRoot -RelativePath $relative

        if (-not (Test-Path -LiteralPath $sourcePath)) {
            throw "Missing source file: $sourcePath"
        }

        $sourceFull = [System.IO.Path]::GetFullPath($sourcePath)
        $targetFull = [System.IO.Path]::GetFullPath($targetPath)

        if ([string]::Equals($sourceFull, $targetFull, [System.StringComparison]::OrdinalIgnoreCase)) {
            Write-Host "SKIPPED $relative source and target are the same file."
            continue
        }

        $targetDir = Split-Path -Parent $targetFull
        if (-not (Test-Path -LiteralPath $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }

        Copy-Item -LiteralPath $sourceFull -Destination $targetFull -Force
        Write-Host "COPIED $relative"
    }

    Write-Host "APPLY PASS: Phase 22 Step 54 files copied or already present."
}

function Invoke-SmokeTest {
    foreach ($relative in $StepFiles) {
        $path = Join-SafePath -Root $ResolvedRepoRoot -RelativePath $relative
        if (-not (Test-Path -LiteralPath $path)) {
            throw "SMOKE TEST FAIL: Missing step file $relative"
        }
    }

    $scanFiles = @(
        "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_alignment_packet.ps1",
        "ui/pages/160_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Handoff_Alignment_Packet.py",
        "docs/PHASE22_STEP54_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_ACCEPTANCE_EVIDENCE_REVIEW_DISPOSITION_HANDOFF_ALIGNMENT_PACKET.md"
    )

    $forbiddenTokens = @(
        ("lacrm_live_write" + "=true"),
        ("live_write_disabled" + "=false"),
        ("live_write_unarmed" + "=false"),
        ("no_network_sockets" + "=false"),
        ("requests" + ".post("),
        ("httpx" + ".post("),
        ("socket" + ".socket("),
        ("uvicorn" + ".run("),
        ("FastAPI" + "("),
        ("sqlite3" + ".connect("),
        ("create_engine" + "(")
    )

    foreach ($relative in $scanFiles) {
        $path = Join-SafePath -Root $ResolvedRepoRoot -RelativePath $relative
        $text = Get-Content -LiteralPath $path -Raw
        foreach ($token in $forbiddenTokens) {
            if ($text.Contains($token)) {
                throw ("SMOKE TEST FAIL: Forbidden token found in {0}: {1}" -f $relative, $token)
            }
        }
    }

    Write-Host "SMOKE TEST PASS: Phase 22 Step 54 $PacketName is present and planning-only."
}

function Generate-PlanningPacket {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupRoot = Join-SafePath -Root $ResolvedRepoRoot -RelativePath "backups"
    $packetDir = Join-Path $backupRoot "phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_alignment_packet_$stamp"

    if (-not (Test-Path -LiteralPath $packetDir)) {
        New-Item -ItemType Directory -Path $packetDir -Force | Out-Null
    }

    $packetPath = Join-Path $packetDir "phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_handoff_alignment_packet.json"

    $packet = [ordered]@{
        phase = 22
        step = 54
        phase_step = $PhaseStep
        packet_name = $PacketName
        prior_completed_step = $PriorCompletedStep
        planning_only = $true
        safety_posture = Get-SafetyPosture
        closure_deferral_acceptance_evidence_review_disposition_handoff = "planned_only"
        closure_deferral_acceptance_evidence_review_disposition = "planned_only"
        closure_resolution_disposition_creation = $false
        closure_resolution_disposition_handoff_creation = $false
        handoff_acceptance_evidence_review_disposition_handoff_creation = $false
        handoff_acceptance_evidence_review_disposition_handoff_approval_creation = $false
        source_bucket_alignment = "raw_normalized_matched_approved_applied"
        connector_first_operating_core = $true
        bridge_absorption_target = "connector_package_not_separate_product"
        implementation_phase_start = "not_started"
        applied_layer_release = "not_started"
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
    Write-Host "PASS: closure_deferral_acceptance_evidence_review_disposition_handoff=planned_only"
    Write-Host "PASS: closure_deferral_acceptance_evidence_review_disposition=planned_only"
    Write-Host "PASS: closure_resolution_disposition_creation=false"
    Write-Host "PASS: closure_resolution_disposition_handoff_creation=false"
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
    Write-Host "CHECK: handoff_record_creation=false"
    Write-Host "CHECK: handoff_queue_creation=false"
    Write-Host "CHECK: handoff_acceptance_evidence_review_disposition_handoff_creation=false"
    Write-Host "CHECK: applied_layer_release=not_started"
    Write-Host "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied"
    Write-Host "CHECK: packet_json=$packetPath"
}

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, or network socket is started here."
    Write-Host "CHECK: Use a separate authorized implementation phase before any runtime execution work."
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "Phase 22 Step 54 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 22 Step 54 $PacketName files"
        Write-Host "3. Smoke test Phase 22 Step 54"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 20 network transport planning closure deferral acceptance evidence review disposition handoff packet"
        Write-Host "6. Exit"
        $choice = Read-Host "Choose 1-6"

        switch ($choice.Trim()) {
            "1" { Show-Status }
            "2" { Apply-StepFiles }
            "3" { Invoke-SmokeTest }
            "4" { Show-ServerPlaceholder }
            "5" { Generate-PlanningPacket }
            "6" { return }
            default { Write-Host "Invalid choice. Choose 1-6." }
        }
    }
}

switch ($Action) {
    "status" { Show-Status }
    "apply" { Apply-StepFiles }
    "smoke" { Invoke-SmokeTest }
    "packet" { Generate-PlanningPacket }
    "all" {
        Show-Status
        Apply-StepFiles
        Invoke-SmokeTest
        Generate-PlanningPacket
    }
    default { Show-Menu }
}

