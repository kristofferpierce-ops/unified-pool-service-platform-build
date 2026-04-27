param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "server", "all")]
    [string]$Action = "menu"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$StepNumber = 53
$PhaseNumber = 22
$StepTitle = "Phase 22 Step 53 - Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Alignment Packet"
$ExpectedBranch = "phase22-step53-phase20-network-transport-planning-closure-deferral-acceptance-evidence-review-disposition-alignment-packet"
$PriorCompletedStep = "Phase 22 Step 52 - Phase 20 Network Transport Planning Closure Deferral Resolution Disposition Handoff Acceptance Evidence Review Alignment Packet"
$PacketFolderPrefix = "phase22_step53_acceptance_evidence_review_disposition_packet"
$PacketJsonName = "phase22_step53_acceptance_evidence_review_disposition_packet.json"

$StepFiles = @(
    "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_alignment_packet.ps1",
    "ui/pages/159_Phase20_Network_Transport_Planning_Closure_Deferral_Acceptance_Evidence_Review_Disposition_Alignment_Packet.py",
    "docs/PHASE22_STEP53_PHASE20_NETWORK_TRANSPORT_PLANNING_CLOSURE_DEFERRAL_ACCEPTANCE_EVIDENCE_REVIEW_DISPOSITION_ALIGNMENT_PACKET.md",
    "tests/test_phase22_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_alignment_packet.py"
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
    handoff_acceptance_evidence_review_record_creation = $false
    handoff_acceptance_evidence_review_approval_creation = $false
    handoff_acceptance_evidence_review_execution = $false
    handoff_acceptance_evidence_review_disposition_record_creation = $false
    handoff_acceptance_evidence_review_disposition_approval_creation = $false
    handoff_acceptance_evidence_review_disposition_execution = $false
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
    $clean = Normalize-RelativePath $RelativePath
    $parts = $clean -split "/"
    $current = $Root
    foreach ($part in $parts) {
        if ([string]::IsNullOrWhiteSpace($part)) { continue }
        $current = Join-Path -Path $current -ChildPath $part
    }
    return $current
}

function Resolve-RepoRoot {
    if (-not [string]::IsNullOrWhiteSpace($RepoRoot)) {
        return (Resolve-Path -LiteralPath $RepoRoot).Path
    }

    $scriptPath = $PSCommandPath
    if ([string]::IsNullOrWhiteSpace($scriptPath)) {
        $candidate = (Get-Location).Path
    } else {
        $scriptDir = Split-Path -Parent $scriptPath
        $candidate = Split-Path -Parent $scriptDir
    }

    return (Resolve-Path -LiteralPath $candidate).Path
}

$ResolvedRepoRoot = Resolve-RepoRoot

function Write-Header {
    Write-Host "=============================================================================="
    Write-Host $StepTitle
    Write-Host "=============================================================================="
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
    foreach ($rel in $StepFiles) {
        $target = Join-RepoPath -Root $ResolvedRepoRoot -RelativePath $rel
        if (Test-Path -LiteralPath $target) {
            Write-Host "  PRESENT $rel"
        } else {
            Write-Host "  MISSING $rel"
        }
    }
}

function Apply-StepFiles {
    foreach ($rel in $StepFiles) {
        $target = Join-RepoPath -Root $ResolvedRepoRoot -RelativePath $rel
        if (-not (Test-Path -LiteralPath $target)) {
            throw "Missing step file after installer write: $rel"
        }
        Write-Host "SKIPPED $rel source and target are the same file."
    }
    Write-Host "APPLY PASS: Phase 22 Step 53 files copied or already present."
}

function Get-ForbiddenTokens {
    return @(
        "requests" + ".post(",
        "httpx" + ".post(",
        "socket" + ".socket(",
        "uvicorn" + ".run(",
        "streamlit run",
        "Start-Process uvicorn",
        "bridge POST",
        "implementation_phase_start=true",
        "operator_signoff_creation=true",
        "operator_approval_creation=true",
        "final_approval_creation=true",
        "design_closure_record_creation=true",
        "closure_decision_creation=true",
        "handoff_acceptance_evidence_review_disposition_record_creation=true",
        "handoff_acceptance_evidence_review_disposition_approval_creation=true",
        "handoff_acceptance_evidence_review_disposition_execution=true",
        "lacrm_live_write=true"
    )
}

function Smoke-Test {
    foreach ($rel in $StepFiles) {
        $target = Join-RepoPath -Root $ResolvedRepoRoot -RelativePath $rel
        if (-not (Test-Path -LiteralPath $target)) {
            throw "SMOKE TEST FAIL: Missing step file: $rel"
        }
    }

    foreach ($rel in $StepFiles) {
        $target = Join-RepoPath -Root $ResolvedRepoRoot -RelativePath $rel
        $text = Get-Content -LiteralPath $target -Raw
        foreach ($token in (Get-ForbiddenTokens)) {
            if ($text.Contains($token)) {
                throw "SMOKE TEST FAIL: Forbidden token found in ${rel}: $token"
            }
        }
    }

    $scriptText = Get-Content -LiteralPath (Join-RepoPath -Root $ResolvedRepoRoot -RelativePath "scripts/phase22_generate_phase20_network_transport_planning_closure_deferral_acceptance_evidence_review_disposition_alignment_packet.ps1") -Raw
    foreach ($required in @(
        "planning_only = `$true",
        "no_platform_db_mutation = `$true",
        "no_bridge_mutation = `$true",
        "no_real_bridge_http_client = `$true",
        "no_network_transport_implementation = `$true",
        "no_bridge_post = `$true",
        "no_network_sockets = `$true",
        "lacrm_default_mode = `"dry_run`"",
        "live_write_disabled = `$true",
        "live_write_unarmed = `$true",
        "handoff_acceptance_evidence_review_disposition_record_creation = `$false",
        "handoff_acceptance_evidence_review_disposition_approval_creation = `$false",
        "handoff_acceptance_evidence_review_disposition_execution = `$false"
    )) {
        if (-not $scriptText.Contains($required)) {
            throw "SMOKE TEST FAIL: Missing required safety token: $required"
        }
    }

    Write-Host "SMOKE TEST PASS: Phase 22 Step 53 Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Alignment Packet is present and planning-only."
}

function Generate-Packet {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupRoot = Join-Path $ResolvedRepoRoot "backups"
    $packetDir = Join-Path $backupRoot "${PacketFolderPrefix}_$stamp"
    if (-not (Test-Path -LiteralPath $packetDir)) {
        New-Item -ItemType Directory -Force -Path $packetDir | Out-Null
    }

    $packetPath = Join-Path $packetDir $PacketJsonName
    $packet = [ordered]@{
        phase = $PhaseNumber
        step = $StepNumber
        step_title = $StepTitle
        prior_completed_step = $PriorCompletedStep
        planning_only = $true
        implementation_phase_start = "not_started"
        applied_layer_release = "not_started"
        closure_decision_creation = $false
        closure_deferral_acceptance_evidence_review_disposition = "planned_only"
        handoff_acceptance_evidence_review_disposition_record_creation = $false
        handoff_acceptance_evidence_review_disposition_approval_creation = $false
        handoff_acceptance_evidence_review_disposition_execution = $false
        source_bucket_alignment = "raw to normalized to matched to approved to applied"
        bridge_absorption_target = "connector_package_not_separate_product"
        safety_posture = $SafetyPosture
        step_files = $StepFiles
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
    Write-Host "PASS: closure_deferral_acceptance_evidence_review_disposition=planned_only"
    Write-Host "PASS: handoff_acceptance_evidence_review_disposition_record_creation=false"
    Write-Host "PASS: handoff_acceptance_evidence_review_disposition_approval_creation=false"
    Write-Host "PASS: handoff_acceptance_evidence_review_disposition_execution=false"
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

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, or network socket is started here."
    Write-Host "CHECK: Use a separate authorized implementation phase before any runtime execution work."
}

function Run-All {
    Show-Status
    Apply-StepFiles
    Smoke-Test
    Generate-Packet
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "Phase 22 Step 53 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 22 Step 53 Phase 20 Network Transport Planning Closure Deferral Acceptance Evidence Review Disposition Alignment Packet files"
        Write-Host "3. Smoke test Phase 22 Step 53"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 20 network transport planning closure deferral acceptance evidence review disposition packet"
        Write-Host "6. Exit"
        $choice = (Read-Host "Choose 1-6").Trim()
        switch ($choice) {
            "1" { Show-Status }
            "2" { Apply-StepFiles }
            "3" { Smoke-Test }
            "4" { Show-ServerPlaceholder }
            "5" { Generate-Packet }
            "6" { return }
            default { Write-Host "Invalid option." }
        }
    }
}

switch ($Action) {
    "status" { Show-Status }
    "apply" { Apply-StepFiles }
    "smoke" { Smoke-Test }
    "packet" { Generate-Packet }
    "server" { Show-ServerPlaceholder }
    "all" { Run-All }
    default { Show-Menu }
}
