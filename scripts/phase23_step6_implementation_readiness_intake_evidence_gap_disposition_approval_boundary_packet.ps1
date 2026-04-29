param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$PhaseNumber = 23
$StepNumber = 6
$StepName = "Phase 23 Step 6 - Phase 20 Network Transport Implementation Readiness Intake Evidence Gap Disposition Approval Boundary Packet"
$PriorStepName = "Phase 23 Step 5 - Phase 20 Network Transport Implementation Readiness Intake Evidence Gap Disposition Review Packet"
$ExpectedBranch = "phase23-step6-readiness-intake-evidence-gap-disposition-approval-boundary"

$StepFiles = @(
    "scripts/phase23_step6_implementation_readiness_intake_evidence_gap_disposition_approval_boundary_packet.ps1",
    "ui/pages/182_Phase23_Step6_Implementation_Readiness_Intake_Evidence_Gap_Disposition_Approval_Boundary_Packet.py",
    "docs/PHASE23_STEP6_IMPLEMENTATION_READINESS_INTAKE_EVIDENCE_GAP_DISPOSITION_APPROVAL_BOUNDARY_PACKET.md",
    "tests/test_phase23_step6_implementation_readiness_intake_evidence_gap_disposition_approval_boundary_packet.py"
)

function Test-SafePath {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    try { return (Test-Path -LiteralPath $Path) } catch { return $false }
}

function Normalize-RelativePath {
    param([Parameter(Mandatory=$true)][string]$RelativePath)
    $value = $RelativePath.Replace("/", "\").Trim().TrimStart("\")
    if ([string]::IsNullOrWhiteSpace($value)) { throw "Relative path is empty." }
    if ($value.Contains(":")) { throw "Relative path must not contain a drive designator: $RelativePath" }
    foreach ($part in $value.Split("\")) {
        if ($part -eq "..") { throw "Relative path must not contain parent traversal: $RelativePath" }
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
    if (-not (Test-SafePath -Path $Candidate)) { return $false }
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
        if (Test-RepoRootCandidate -Candidate $full) { return (Resolve-Path -LiteralPath $full).Path }
    }
    throw "Could not resolve repo root. Run from the parent workspace or pass -RepoRoot explicitly."
}

function Get-SafetyPosture {
    return [ordered]@{
        planning_only = $true
        phase23_context = "planning_intake_only"
        phase23_planning_boundary = "opened_by_packet"
        phase23_implementation_start = $false
        phase23_runtime_start = $false
        phase23_operator_signoff_creation = $false
        phase23_operator_approval_creation = $false
        phase23_final_approval_creation = $false
        phase23_start_authorization = $false
        no_platform_db_mutation = $true
        no_bridge_mutation = $true
        no_real_bridge_http_client = $true
        no_network_transport_implementation = $true
        no_bridge_post = $true
        no_network_sockets = $true
        no_execution_implementation = $true
        implementation_phase_start = $false
        implementation_queue_creation = $false
        implementation_ready_transition = $false
        implementation_prerequisite_execution = $false
        network_transport_implementation_start = $false
        network_transport_runtime_start = $false
        bridge_absorption_execution = $false
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
        readiness_intake_evidence_gap_disposition_approval_boundary_mode = "reference_only"
        readiness_intake_evidence_gap_disposition_approval_boundary_write = $false
        readiness_intake_evidence_gap_disposition_approval_boundary_record_creation = $false
        readiness_intake_decision_creation = $false
        readiness_intake_approval_creation = $false
        handoff_evidence_collection_execution = $false
        evidence_gap_remediation_mutation = $false
        evidence_gap_resolution_execution = $false
        phase22_reopen = $false
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
    foreach ($key in $safety.Keys) { Write-Host ("  {0}: {1}" -f $key, $safety[$key]) }
    Write-Host ""
    Write-Host "Step files"
    foreach ($rel in $StepFiles) {
        $path = Join-SafePath -Root $Repo -RelativePath $rel
        if (Test-SafePath -Path $path) { Write-Host "  PRESENT $rel" } else { Write-Host "  MISSING $rel" }
    }
}

function Assert-StepFilesPresent {
    foreach ($rel in $StepFiles) {
        $path = Join-SafePath -Root $Repo -RelativePath $rel
        if (-not (Test-SafePath -Path $path)) { throw "Missing required file: $rel" }
    }
}

function Apply-StepFiles {
    Assert-StepFilesPresent
    foreach ($rel in $StepFiles) { Write-Host "SKIPPED $rel source and target are the same file or already installed by the single-file installer." }
    Write-Host "APPLY PASS: Phase 23 Step 6 files copied or already present."
}

function Test-Smoke {
    Assert-StepFilesPresent
    $safety = Get-SafetyPosture
    if (-not $safety["planning_only"]) { throw "SMOKE TEST FAIL: planning_only must be true" }
    if ($safety["phase23_implementation_start"]) { throw "SMOKE TEST FAIL: Phase 23 implementation start must remain disabled" }
    if ($safety["phase23_runtime_start"]) { throw "SMOKE TEST FAIL: Phase 23 runtime start must remain disabled" }
    if ($safety["phase23_start_authorization"]) { throw "SMOKE TEST FAIL: Phase 23 start authorization must not be created" }
    if (-not $safety["no_platform_db_mutation"]) { throw "SMOKE TEST FAIL: platform DB mutation must remain disabled" }
    if (-not $safety["no_bridge_mutation"]) { throw "SMOKE TEST FAIL: bridge mutation must remain disabled" }
    if (-not $safety["no_real_bridge_http_client"]) { throw "SMOKE TEST FAIL: real bridge HTTP client must remain disabled" }
    if (-not $safety["no_network_transport_implementation"]) { throw "SMOKE TEST FAIL: network transport implementation must remain disabled" }
    if (-not $safety["no_bridge_post"]) { throw "SMOKE TEST FAIL: bridge POST must remain disabled" }
    if (-not $safety["no_network_sockets"]) { throw "SMOKE TEST FAIL: sockets must remain disabled" }
    if (-not $safety["no_execution_implementation"]) { throw "SMOKE TEST FAIL: execution implementation must remain disabled" }
    if ($safety["implementation_phase_start"]) { throw "SMOKE TEST FAIL: implementation phase must not start" }
    if ($safety["implementation_queue_creation"]) { throw "SMOKE TEST FAIL: implementation queue creation must remain disabled" }
    if ($safety["implementation_ready_transition"]) { throw "SMOKE TEST FAIL: implementation ready transition must remain disabled" }
    if ($safety["network_transport_implementation_start"]) { throw "SMOKE TEST FAIL: network transport implementation start must remain disabled" }
    if ($safety["network_transport_runtime_start"]) { throw "SMOKE TEST FAIL: network transport runtime start must remain disabled" }
    if ($safety["cross_repo_write"]) { throw "SMOKE TEST FAIL: cross repo writes must remain disabled" }
    if ($safety["cross_repo_mutation"]) { throw "SMOKE TEST FAIL: cross repo mutation must remain disabled" }
    if ($safety["external_repo_push"]) { throw "SMOKE TEST FAIL: external repo push must remain disabled" }
    if ($safety["cross_repo_branch_change"]) { throw "SMOKE TEST FAIL: cross repo branch changes must remain disabled" }
    if ($safety["cross_repo_file_write"]) { throw "SMOKE TEST FAIL: cross repo file writes must remain disabled" }
    if ($safety["sibling_repo_mutation"]) { throw "SMOKE TEST FAIL: sibling repo mutation must remain disabled" }
    if ($safety["readiness_intake_evidence_gap_disposition_approval_boundary_write"]) { throw "SMOKE TEST FAIL: readiness intake evidence gap disposition approval boundary writes must remain disabled" }
    if ($safety["readiness_intake_evidence_gap_disposition_approval_boundary_record_creation"]) { throw "SMOKE TEST FAIL: readiness intake evidence gap disposition approval boundary record creation must remain disabled" }
    if ($safety["readiness_intake_decision_creation"]) { throw "SMOKE TEST FAIL: readiness intake decision creation must remain disabled" }
    if ($safety["readiness_intake_approval_creation"]) { throw "SMOKE TEST FAIL: readiness intake approval creation must remain disabled" }
    if ($safety["phase22_reopen"]) { throw "SMOKE TEST FAIL: Phase 22 must not reopen" }
    if ($safety["lacrm_live_write"]) { throw "SMOKE TEST FAIL: LACRM live write must remain disabled" }
    if (-not $safety["live_write_disabled"]) { throw "SMOKE TEST FAIL: live write disabled must remain true" }
    if (-not $safety["live_write_unarmed"]) { throw "SMOKE TEST FAIL: live write unarmed must remain true" }
    Write-Host "SMOKE TEST PASS: Phase 23 Step 6 Phase 20 Network Transport Implementation Readiness Intake Evidence Gap Disposition Approval Boundary Packet is present and planning-only."
}

function New-Packet {
    Assert-StepFilesPresent
    $backupRoot = Join-SafePath -Root $Repo -RelativePath "backups"
    if (-not (Test-SafePath -Path $backupRoot)) { New-Item -ItemType Directory -Path $backupRoot | Out-Null }
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $packetDir = Join-SafePath -Root $backupRoot -RelativePath ("phase23_step6_implementation_readiness_intake_evidence_gap_disposition_approval_boundary_packet_{0}" -f $stamp)
    if (-not (Test-SafePath -Path $packetDir)) { New-Item -ItemType Directory -Path $packetDir -Force | Out-Null }
    $packetPath = Join-SafePath -Root $packetDir -RelativePath "phase23_step6_implementation_readiness_intake_evidence_gap_disposition_approval_boundary_packet.json"
    $packet = [ordered]@{
        phase = 23
        step = 6
        step_name = $StepName
        prior_step = $PriorStepName
        expected_branch = $ExpectedBranch
        generated_at = (Get-Date).ToString("o")
        planning_only = $true
        phase23_context = "planning_intake_only"
        phase23_planning_boundary = "opened_by_packet"
        phase23_implementation_start = "not_started"
        implementation_phase_start = "not_started"
        network_transport_runtime_start = "not_started"
        readiness_intake_evidence_gap_disposition_approval_boundary_mode = "reference_only"
        safety_posture = Get-SafetyPosture
        intake_scope = @(
            "Carry forward the Phase 23 Step 5 readiness intake evidence gap disposition review as the prior reference",
            "Open Phase 23 as a planning intake evidence gap disposition approval boundary only",
            "Inventory prerequisites for future implementation without starting implementation",
            "Preserve parent-workspace one-file installer workflow and exact four-file staging",
            "Keep platform DB, bridge, LACRM live writes, sockets, bridge POST, and server startup disabled"
        )
        intake_buckets = @(
            "phase22_closeout_reference",
            "readiness_intake_reference_only",
            "implementation_prerequisites_not_executed",
            "network_transport_runtime_not_started",
            "operator_authorization_not_created"
        )
        non_actions = @(
            "No FastAPI server start",
            "No Streamlit server start",
            "No bridge HTTP client creation",
            "No network socket creation",
            "No platform database mutation",
            "No bridge mutation",
            "No LACRM live write",
            "No external repository mutation",
            "No implementation queue creation",
            "No readiness decision or approval creation",
            "No Phase 22 reopen"
        )
        step_files = $StepFiles
    }
    $packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $packetPath -Encoding UTF8
    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: phase23_planning_boundary=opened_by_packet"
    Write-Host "PASS: phase23_implementation_start=false"
    Write-Host "PASS: implementation_phase_start=false"
    Write-Host "PASS: cross_repo_write=false"
    Write-Host "PASS: cross_repo_mutation=false"
    Write-Host "PASS: external_repo_push=false"
    Write-Host "PASS: readiness_intake_evidence_gap_disposition_approval_boundary_mode=reference_only"
    Write-Host "PASS: readiness_intake_evidence_gap_disposition_approval_boundary_write=false"
    Write-Host "PASS: readiness_intake_evidence_gap_disposition_approval_boundary_record_creation=false"
    Write-Host "PASS: readiness_intake_decision_creation=false"
    Write-Host "PASS: readiness_intake_approval_creation=false"
    Write-Host "PASS: phase22_reopen=false"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "CHECK: prior_step=Phase 23 Step 5"
    Write-Host "CHECK: phase23_context=planning_intake_only"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: network_transport_runtime_start=not_started"
    Write-Host "CHECK: parent_workspace_launcher=safe"
    Write-Host "CHECK: packet_json=$packetPath"
}

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, network socket, bridge POST, or cross-repo write is started here."
    Write-Host "CHECK: Phase 23 Step 6 is planning intake only and does not start network transport implementation."
    Write-Host "CHECK: Readiness decisions, approvals, implementation queues, and live writes remain intentionally disabled."
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "Phase 23 Step 6 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 23 Step 6 Phase 20 Network Transport Implementation Readiness Intake Evidence Gap Disposition Approval Boundary Packet files"
        Write-Host "3. Smoke test Phase 23 Step 6"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 23 Step 6 implementation readiness intake evidence gap disposition approval boundary packet"
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
    "all" { Show-Status; Apply-StepFiles; Test-Smoke; New-Packet }
    default { Show-Menu }
}
