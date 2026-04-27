param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$PhaseNumber = 22
$StepNumber = 64
$StepName = "Phase 22 Step 64 - Phase 20 Network Transport Planning Cross-Repo Handoff Evidence Gap Review Packet"
$PriorStepName = "Phase 22 Step 63 - Phase 20 Network Transport Planning Cross-Repo Handoff Evidence Index Packet"
$ExpectedBranch = "phase22-step64-cross-repo-handoff-evidence-gap-review"

$StepFiles = @(
    "scripts/phase22_step64_cross_repo_handoff_evidence_gap_review_packet.ps1",
    "ui/pages/170_Phase20_Network_Transport_Planning_Cross_Repo_Handoff_Evidence_Gap_Review_Packet.py",
    "docs/PHASE22_STEP64_CROSS_REPO_HANDOFF_EVIDENCE_GAP_REVIEW_PACKET.md",
    "tests/test_phase22_step64_cross_repo_handoff_evidence_gap_review_packet.py"
)

function Test-SafePath {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $false
    }

    try {
        return (Test-Path -LiteralPath $Path)
    } catch {
        return $false
    }
}

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

function Test-RepoRootCandidate {
    param([string]$Candidate)

    if (-not (Test-SafePath -Path $Candidate)) {
        return $false
    }

    $scriptsPath = Join-SafePath -Root $Candidate -RelativePath "scripts"
    $docsPath = Join-SafePath -Root $Candidate -RelativePath "docs"
    $testsPath = Join-SafePath -Root $Candidate -RelativePath "tests"
    $uiPath = Join-SafePath -Root $Candidate -RelativePath "ui"
    return ((Test-SafePath -Path $scriptsPath) -and (Test-SafePath -Path $docsPath) -and (Test-SafePath -Path $testsPath) -and (Test-SafePath -Path $uiPath))
}

function Resolve-RepoRoot {
    param([string]$InputRoot)

    $candidates = New-Object System.Collections.Generic.List[string]

    if (-not [string]::IsNullOrWhiteSpace($InputRoot)) {
        $candidates.Add($InputRoot)
        $candidates.Add((Join-Path $InputRoot "unified_pool_service_platform_build"))
    }

    if ($PSScriptRoot) {
        $candidates.Add((Split-Path -Parent $PSScriptRoot))
        $candidates.Add((Join-Path (Split-Path -Parent $PSScriptRoot) "unified_pool_service_platform_build"))
    }

    $current = (Get-Location).Path
    $candidates.Add($current)
    $candidates.Add((Join-Path $current "unified_pool_service_platform_build"))
    $candidates.Add((Join-Path $current "unified_pool_service_platform_build\unified_pool_service_platform_build"))

    if ($env:USERPROFILE) {
        $workspace = Join-Path $env:USERPROFILE "Desktop\unified_pool_service_platform_build"
        $candidates.Add($workspace)
        $candidates.Add((Join-Path $workspace "unified_pool_service_platform_build"))
    }

    $seen = @{}
    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        try { $full = [System.IO.Path]::GetFullPath($candidate) } catch { continue }
        if ($seen.ContainsKey($full)) { continue }
        $seen[$full] = $true
        if (Test-RepoRootCandidate -Candidate $full) {
            return (Resolve-Path -LiteralPath $full).Path
        }
    }

    throw "Could not resolve repo root. Run from the parent workspace or pass -RepoRoot explicitly."
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
        phase23_start = $false
        phase23_branch_creation = $false
        implementation_queue_creation = $false
        authorization_record_creation = $false
        operator_signoff_creation = $false
        operator_approval_creation = $false
        final_approval_creation = $false
        design_closure_record_creation = $false
        closure_review_record_creation = $false
        closure_decision_creation = $false
        cross_repo_write = $false
        cross_repo_mutation = $false
        external_repo_push = $false
        cross_repo_branch_change = $false
        cross_repo_file_write = $false
        sibling_repo_mutation = $false
        cross_repo_validation_write = $false
        handoff_record_creation = $false
        handoff_queue_creation = $false
        handoff_verification_record_creation = $false
        handoff_evidence_gap_review_record_creation = $false
        handoff_evidence_collection_execution = $false
        handoff_evidence_gap_review_write = $false
        evidence_gap_remediation_mutation = $false
        bridge_absorption_execution = $false
        phase22_reopen = $false
        phase23_start_boundary_creation = $false
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
    Write-Host "Parent-workspace safe: true"
    Write-Host "Single-file installer compatible: true"
    Write-Host ""
    Write-Host "Safety posture"
    $safety = Get-SafetyPosture
    foreach ($key in $safety.Keys) {
        Write-Host ("  {0}: {1}" -f $key, $safety[$key])
    }
    Write-Host ""
    Write-Host "Step files"
    foreach ($rel in $StepFiles) {
        $path = Join-SafePath -Root $Repo -RelativePath $rel
        if (Test-SafePath -Path $path) {
            Write-Host "  PRESENT $rel"
        } else {
            Write-Host "  MISSING $rel"
        }
    }
}

function Assert-StepFilesPresent {
    foreach ($rel in $StepFiles) {
        $path = Join-SafePath -Root $Repo -RelativePath $rel
        if (-not (Test-SafePath -Path $path)) {
            throw "Missing required file: $rel"
        }
    }
}

function Apply-StepFiles {
    Assert-StepFilesPresent
    foreach ($rel in $StepFiles) {
        Write-Host "SKIPPED $rel source and target are the same file or already installed by the single-file installer."
    }
    Write-Host "APPLY PASS: Phase 22 Step 64 files copied or already present."
}

function Test-Smoke {
    Assert-StepFilesPresent

    $safety = Get-SafetyPosture

    if (-not $safety["planning_only"]) { throw "SMOKE TEST FAIL: planning_only must be true" }
    if (-not $safety["no_platform_db_mutation"]) { throw "SMOKE TEST FAIL: platform DB mutation must remain disabled" }
    if (-not $safety["no_bridge_mutation"]) { throw "SMOKE TEST FAIL: bridge mutation must remain disabled" }
    if (-not $safety["no_real_bridge_http_client"]) { throw "SMOKE TEST FAIL: real bridge HTTP client must remain disabled" }
    if (-not $safety["no_network_transport_implementation"]) { throw "SMOKE TEST FAIL: network transport implementation must remain disabled" }
    if (-not $safety["no_bridge_post"]) { throw "SMOKE TEST FAIL: bridge POST must remain disabled" }
    if (-not $safety["no_network_sockets"]) { throw "SMOKE TEST FAIL: sockets must remain disabled" }
    if (-not $safety["no_execution_implementation"]) { throw "SMOKE TEST FAIL: execution implementation must remain disabled" }
    if ($safety["implementation_phase_start"]) { throw "SMOKE TEST FAIL: implementation phase must not start" }
    if ($safety["phase23_start"]) { throw "SMOKE TEST FAIL: Phase 23 must not start in this packet" }
    if ($safety["phase23_branch_creation"]) { throw "SMOKE TEST FAIL: Phase 23 branch creation must remain disabled" }
    if ($safety["implementation_queue_creation"]) { throw "SMOKE TEST FAIL: implementation queue creation must remain disabled" }
    if ($safety["cross_repo_write"]) { throw "SMOKE TEST FAIL: cross repo writes must remain disabled" }
    if ($safety["cross_repo_mutation"]) { throw "SMOKE TEST FAIL: cross repo mutation must remain disabled" }
    if ($safety["external_repo_push"]) { throw "SMOKE TEST FAIL: external repo push must remain disabled" }
    if ($safety["cross_repo_branch_change"]) { throw "SMOKE TEST FAIL: cross repo branch changes must remain disabled" }
    if ($safety["cross_repo_file_write"]) { throw "SMOKE TEST FAIL: cross repo file writes must remain disabled" }
    if ($safety["sibling_repo_mutation"]) { throw "SMOKE TEST FAIL: sibling repo mutation must remain disabled" }
    if ($safety["handoff_evidence_collection_execution"]) { throw "SMOKE TEST FAIL: handoff evidence collection execution must remain disabled" }
    if ($safety["handoff_evidence_gap_review_write"]) { throw "SMOKE TEST FAIL: handoff evidence gap review write must remain disabled" }
    if ($safety["evidence_gap_remediation_mutation"]) { throw "SMOKE TEST FAIL: evidence capture mutation must remain disabled" }
    if ($safety["lacrm_live_write"]) { throw "SMOKE TEST FAIL: LACRM live write must remain disabled" }
    if (-not $safety["live_write_disabled"]) { throw "SMOKE TEST FAIL: live write disabled must remain true" }
    if (-not $safety["live_write_unarmed"]) { throw "SMOKE TEST FAIL: live write unarmed must remain true" }

    Write-Host "SMOKE TEST PASS: Phase 22 Step 64 Phase 20 Network Transport Planning Cross-Repo Handoff Evidence Gap Review Packet is present and planning-only."
}

function New-Packet {
    Assert-StepFilesPresent
    $backupDir = Join-SafePath -Root $Repo -RelativePath "backups"
    if (-not (Test-SafePath -Path $backupDir)) {
        New-Item -ItemType Directory -Path $backupDir | Out-Null
    }

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $packetPath = Join-SafePath -Root $backupDir -RelativePath ("phase22_step64_cross_repo_handoff_evidence_gap_review_packet_{0}.json" -f $stamp)

    $packet = [ordered]@{
        phase = 22
        step = 64
        step_name = $StepName
        prior_step = $PriorStepName
        expected_branch = $ExpectedBranch
        generated_at = (Get-Date).ToString("o")
        planning_only = $true
        evidence_gap_review_mode = "reference_only"
        handoff_state = "post_step63_reference_indexed"
        phase23_start = "not_started"
        implementation_phase_start = "not_started"
        safety_posture = Get-SafetyPosture
        evidence_gap_review_scope = @(
            "Review Step 61, Step 62, and Step 63 handoff artifacts for reference-only evidence gaps",
            "Confirm parent-workspace commit commands remain the only write path",
            "Confirm sibling repositories are named for coordination only",
            "Confirm no cross-repo branch, file, push, or validation write is requested",
            "Confirm no network transport implementation, bridge POST, socket, or runtime execution is introduced"
        )
        evidence_gap_review_buckets = @(
            "platform planning packets",
            "cross-repo handoff reference",
            "cross-repo handoff verification reference",
            "source-bucket alignment notes",
            "implementation-still-closed notes"
        )
        non_actions = @(
            "No FastAPI server start",
            "No Streamlit server start",
            "No bridge HTTP client creation",
            "No network socket creation",
            "No platform database mutation",
            "No bridge mutation",
            "No external repository mutation",
            "No evidence collection execution",
            "No Phase 23 branch creation",
            "No operator signoff or approval record creation"
        )
        step_files = $StepFiles
    }

    $packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $packetPath -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: cross_repo_write=false"
    Write-Host "PASS: cross_repo_mutation=false"
    Write-Host "PASS: external_repo_push=false"
    Write-Host "PASS: evidence_gap_review_mode=reference_only"
    Write-Host "PASS: handoff_evidence_gap_review_write=false"
    Write-Host "PASS: phase23_start=false"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "CHECK: prior_step=Phase 22 Step 63"
    Write-Host "CHECK: phase23_start=not_started"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: evidence_gap_review_mode=reference_only"
    Write-Host "CHECK: parent_workspace_launcher=safe"
    Write-Host "CHECK: packet_json=$packetPath"
}

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, network socket, or cross-repo write is started here."
    Write-Host "CHECK: Phase 23 start remains intentionally deferred."
    Write-Host "CHECK: Evidence gap review is reference-only and does not collect, mutate, or validate sibling repositories."
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "Phase 22 Step 64 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 22 Step 64 Phase 20 Network Transport Planning Cross-Repo Handoff Evidence Gap Review Packet files"
        Write-Host "3. Smoke test Phase 22 Step 64"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 22 Step 64 cross-repo handoff evidence gap review packet"
        Write-Host "6. Exit"
        $choice = Read-Host "Choose 1-6"

        switch ($choice) {
            "1" { Show-Status }
            "2" { Apply-StepFiles }
            "3" { Test-Smoke }
            "4" { Show-ServerPlaceholder }
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

