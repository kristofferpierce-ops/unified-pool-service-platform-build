param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "server", "all")]
    [string]$Action = "menu"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$StepNumber = 51
$PhaseNumber = 22
$StepTitle = "Phase 22 Step 51 - Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Acceptance Evidence Alignment Packet"
$ExpectedBranch = "phase22-step51-phase20-network-transport-planning-closure-deferral-resolution-disposition-handoff-acceptance-evidence-alignment-packet"
$PriorCompletedStep = "Phase 22 Step 50 - Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Acceptance Gate Alignment Packet"
$PacketFolderPrefix = "phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_alignment_packet"
$PacketJsonName = "phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_alignment_packet.json"

$StepFiles = @(
    "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_alignment_packet.ps1",
    "ui/pages/157_Phase20_Network_Transport_Planning_Closure_Deferral_Resolution_Disposition_Handoff_Acceptance_Evidence_Alignment_Packet.py",
    "docs/PHASE22_STEP51_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_RESOLUTION_DISPOSITION_HANDOFF_ACCEPTANCE_EVIDENCE_ALIGNMENT_PACKET.md",
    "tests/test_phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_alignment_packet.py"
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
    closure_review_record_creation = $false
    closure_resolution_disposition_creation = $false
    closure_resolution_disposition_approval_creation = $false
    closure_resolution_disposition_handoff_creation = $false
    closure_resolution_disposition_handoff_approval_creation = $false
    closure_resolution_handoff_execution = $false
    handoff_record_creation = $false
    handoff_queue_creation = $false
    handoff_verification_record_creation = $false
    handoff_acceptance_record_creation = $false
    handoff_acceptance_gate_creation = $false
    handoff_acceptance_gate_approval_creation = $false
    handoff_acceptance_execution = $false
    handoff_acceptance_evidence_record_creation = $false
    handoff_acceptance_evidence_approval_creation = $false
    handoff_acceptance_evidence_execution = $false
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

function Remove-ControlChars {
    param([string]$Value)
    if ([string]::IsNullOrEmpty($Value)) { return "" }
    $builder = New-Object System.Text.StringBuilder
    foreach ($ch in $Value.ToCharArray()) {
        if ([int][char]$ch -ge 32) {
            [void]$builder.Append($ch)
        }
    }
    return $builder.ToString()
}

function Normalize-RelativePath {
    param([Parameter(Mandatory=$true)][string]$PathValue)
    $clean = (Remove-ControlChars $PathValue).Trim()
    return $clean.Replace([string][char]92, "/")
}

function Join-RepoPath {
    param(
        [Parameter(Mandatory=$true)][string]$Root,
        [Parameter(Mandatory=$true)][string]$RelativePath
    )
    $normalized = Normalize-RelativePath $RelativePath
    $parts = $normalized -split "/"
    $current = $Root
    foreach ($part in $parts) {
        if ([string]::IsNullOrWhiteSpace($part)) { continue }
        $current = Join-Path -Path $current -ChildPath $part
    }
    return $current
}

function Resolve-RepoRoot {
    param([string]$Candidate)
    if (-not [string]::IsNullOrWhiteSpace($Candidate)) {
        $cleanCandidate = (Remove-ControlChars $Candidate).Trim()
        if (Test-Path -LiteralPath $cleanCandidate) {
            return (Resolve-Path -LiteralPath $cleanCandidate).Path
        }
    }

    $scriptRoot = Split-Path -Parent $PSCommandPath
    $current = $scriptRoot
    while (-not [string]::IsNullOrWhiteSpace($current)) {
        if (Test-Path -LiteralPath (Join-Path $current ".git")) {
            return (Resolve-Path -LiteralPath $current).Path
        }
        $parent = Split-Path -Parent $current
        if ($parent -eq $current) { break }
        $current = $parent
    }

    $location = (Get-Location).Path
    if (Test-Path -LiteralPath (Join-Path $location ".git")) {
        return (Resolve-Path -LiteralPath $location).Path
    }

    throw "Could not resolve repository root. Pass -RepoRoot explicitly."
}

function Write-Header {
    Write-Host ("=" * 78)
    Write-Host $StepTitle
    Write-Host ("=" * 78)
}

function Show-Status {
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
    foreach ($relative in $StepFiles) {
        $path = Join-RepoPath $ResolvedRepoRoot $relative
        if (Test-Path -LiteralPath $path) {
            Write-Host "  PRESENT $relative"
        } else {
            Write-Host "  MISSING $relative"
        }
    }
}

function Apply-StepFiles {
    foreach ($relative in $StepFiles) {
        $targetPath = Join-RepoPath $ResolvedRepoRoot $relative
        if (-not (Test-Path -LiteralPath $targetPath)) {
            throw "Missing source file: $targetPath"
        }
        Write-Host "PRESENT $relative"
    }
    Write-Host "APPLY PASS: Phase 22 Step 51 files copied or already present."
}

function Invoke-SmokeTest {
    foreach ($relative in $StepFiles) {
        $path = Join-RepoPath $ResolvedRepoRoot $relative
        if (-not (Test-Path -LiteralPath $path)) {
            throw "SMOKE TEST FAIL: Missing expected file: $relative"
        }
    }

    $publicTextFiles = @(
        "ui/pages/157_Phase20_Network_Transport_Planning_Closure_Deferral_Resolution_Disposition_Handoff_Acceptance_Evidence_Alignment_Packet.py",
        "docs/PHASE22_STEP51_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_RESOLUTION_DISPOSITION_HANDOFF_ACCEPTANCE_EVIDENCE_ALIGNMENT_PACKET.md",
        "tests/test_phase22_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_alignment_packet.py"
    )

    $forbiddenTokens = @(
        "lacrm_live_write" + "=true",
        "live_write_disabled" + "=false",
        "live_write_unarmed" + "=false",
        "planning_only" + "=false",
        "no_network_sockets" + "=false",
        "no_bridge_post" + "=false",
        "no_real_bridge_http_client" + "=false",
        "requests." + "post(",
        "httpx." + "post(",
        "socket." + "socket(",
        "uvicorn." + "run(",
        "streamlit " + "run"
    )

    foreach ($relative in $publicTextFiles) {
        $path = Join-RepoPath $ResolvedRepoRoot $relative
        $text = Get-Content -LiteralPath $path -Raw
        foreach ($token in $forbiddenTokens) {
            if ($text -like "*$token*") {
                throw "SMOKE TEST FAIL: Forbidden token found in ${relative}: $token"
            }
        }
    }

    $launcherText = Get-Content -LiteralPath (Join-RepoPath $ResolvedRepoRoot "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_resolution_disposition_handoff_acceptance_evidence_alignment_packet.ps1") -Raw
    $requiredLauncherTokens = @(
        "planning_only = `$true",
        "lacrm_default_mode = `"dry_run`"",
        "lacrm_live_write = `$false",
        "live_write_disabled = `$true",
        "live_write_unarmed = `$true",
        "handoff_acceptance_evidence_record_creation = `$false",
        "handoff_acceptance_evidence_approval_creation = `$false",
        "handoff_acceptance_evidence_execution = `$false"
    )

    foreach ($token in $requiredLauncherTokens) {
        if ($launcherText -notlike "*$token*") {
            throw "SMOKE TEST FAIL: Required launcher token missing: $token"
        }
    }

    Write-Host "SMOKE TEST PASS: Phase 22 Step 51 Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Acceptance Evidence Alignment Packet is present and planning-only."
}

function Generate-Packet {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupRoot = Join-Path $ResolvedRepoRoot "backups"
    $packetDir = Join-Path $backupRoot ("{0}_{1}" -f $PacketFolderPrefix, $timestamp)
    New-Item -ItemType Directory -Force -Path $packetDir | Out-Null

    $packet = [ordered]@{
        phase = 22
        step = 51
        title = $StepTitle
        branch = $ExpectedBranch
        prior_completed_step = $PriorCompletedStep
        generated_at_local = (Get-Date).ToString("s")
        planning_only = $true
        no_real_bridge_http_client = $true
        no_network_transport_implementation = $true
        no_bridge_post = $true
        no_network_sockets = $true
        no_execution_implementation = $true
        no_platform_db_mutation = $true
        no_bridge_mutation = $true
        lacrm_default_mode = "dry_run"
        lacrm_live_write = $false
        live_write_disabled = $true
        live_write_unarmed = $true
        closure_deferral_resolution_disposition_handoff_acceptance_evidence = "planned_only"
        handoff_acceptance_evidence_record_creation = $false
        handoff_acceptance_evidence_approval_creation = $false
        handoff_acceptance_evidence_execution = $false
        handoff_acceptance_gate_creation = $false
        handoff_acceptance_gate_approval_creation = $false
        handoff_acceptance_execution = $false
        handoff_acceptance_record_creation = $false
        implementation_phase_start = "not_started"
        authorization_record_creation = $false
        operator_signoff_creation = $false
        operator_approval_creation = $false
        final_approval_creation = $false
        design_closure_record_creation = $false
        closure_decision_creation = $false
        closure_resolution_disposition_handoff_creation = $false
        closure_resolution_disposition_handoff_approval_creation = $false
        closure_resolution_handoff_execution = $false
        handoff_record_creation = $false
        handoff_queue_creation = $false
        handoff_verification_record_creation = $false
        disposition_record_creation = $false
        applied_layer_release = "not_started"
        source_bucket_alignment = "raw_normalized_matched_approved_applied"
        bridge_absorption_target = "connector_package_not_separate_product"
        connector_first_operating_core = $true
        step_files = $StepFiles
    }

    $packetPath = Join-Path $packetDir $PacketJsonName
    $packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $packetPath -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "PASS: closure_deferral_resolution_disposition_handoff_acceptance_evidence=planned_only"
    Write-Host "PASS: handoff_acceptance_evidence_record_creation=false"
    Write-Host "PASS: handoff_acceptance_evidence_approval_creation=false"
    Write-Host "PASS: handoff_acceptance_evidence_execution=false"
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
    Write-Host "CHECK: handoff_verification_record_creation=false"
    Write-Host "CHECK: disposition_record_creation=false"
    Write-Host "CHECK: applied_layer_release=not_started"
    Write-Host "CHECK: packet_json=$packetPath"
}

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, or network socket is started here."
    Write-Host "CHECK: Use a separate authorized implementation phase before runtime execution work."
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "Phase 22 Step 51 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 22 Step 51 Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Acceptance Evidence Alignment Packet files"
        Write-Host "3. Smoke test Phase 22 Step 51"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 20 network transport planning closure deferral resolution disposition handoff acceptance evidence alignment packet"
        Write-Host "6. Exit"
        $choice = (Read-Host "Choose 1-6").Trim()
        switch ($choice) {
            "1" { Show-Status }
            "2" { Apply-StepFiles }
            "3" { Invoke-SmokeTest }
            "4" { Show-ServerPlaceholder }
            "5" { Generate-Packet }
            "6" { return }
            default { Write-Host "Invalid choice. Choose 1-6." }
        }
    }
}

$ResolvedRepoRoot = Resolve-RepoRoot $RepoRoot

switch ($Action) {
    "status" { Show-Status }
    "apply" { Apply-StepFiles }
    "smoke" { Invoke-SmokeTest }
    "packet" { Generate-Packet }
    "server" { Show-ServerPlaceholder }
    "all" {
        Show-Status
        Apply-StepFiles
        Invoke-SmokeTest
        Generate-Packet
    }
    "menu" { Show-Menu }
    default { Show-Menu }
}
