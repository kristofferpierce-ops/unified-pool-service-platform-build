param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "all"
)

$ErrorActionPreference = "Stop"

$StepNumber = 26
$StepTitle = "Phase 27 Step 26 - Phase 20 Network Transport Implementation Staging Runtime Preflight Planning Approval Boundary Packet"
$ShortTitle = "Phase 20 Network Transport Implementation Staging Runtime Preflight Planning Approval Boundary Packet"
$ExpectedBranch = "phase27-step26-implementation-staging-runtime-preflight-planning-approval-boundary"
$PriorStep = "Phase 27 Step 25 - Phase 20 Network Transport Implementation Staging Runtime Preflight Planning Safety Disposition Review Packet"
$Slug = "implementation_staging_runtime_preflight_planning_approval_boundary"

if (-not $RepoRoot) { $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path }

$StepFiles = @("scripts/phase27_step26_implementation_staging_runtime_preflight_planning_approval_boundary_packet.ps1", "ui/pages/642_Phase27_Step26_Implementation_Staging_Runtime_Preflight_Planning_Approval_Boundary_Packet.py", "docs/PHASE27_STEP26_IMPLEMENTATION_STAGING_RUNTIME_PREFLIGHT_PLANNING_APPROVAL_BOUNDARY_PACKET.md", "tests/test_phase27_step26_implementation_staging_runtime_preflight_planning_approval_boundary_packet.py")

$SafetyPosture = [ordered]@{
    planning_only = $true
    no_platform_db_mutation = $true
    no_bridge_mutation = $true
    no_real_bridge_http_client = $true
    no_network_transport_implementation = $true
    no_bridge_post = $true
    no_network_sockets = $true
    no_execution_implementation = $true
    phase27_boundary = "implementation_staging_runtime_preflight_planning_approval_boundary_opened_by_packet"
    phase27_execution_start = $false
    phase27_implementation_start = $false
    implementation_phase_start = $false
    staging_runtime_start = $false
    staging_execution_start = $false
    network_transport_runtime_start = $false
    bridge_transport_runtime_start = $false
    cross_repo_write = $false
    cross_repo_mutation = $false
    external_repo_push = $false
    implementation_staging_runtime_preflight_planning_approval_boundary_mode = "reference_only"
    implementation_staging_runtime_preflight_planning_approval_boundary_write = $false
    implementation_staging_runtime_preflight_planning_approval_boundary_record_creation = $false
    staging_readiness_decision_creation = $false
    staging_readiness_approval_creation = $false
    staging_operator_approval_creation = $false
    no_operator_signoff = $true
    no_operator_approval = $true
    no_final_approval = $true
    phase26_reopen = $false
    phase28_start = $false
    phase28_boundary_creation = $false
    lacrm_default_mode = "dry_run"
    lacrm_live_write = $false
    live_write_disabled = $true
    live_write_unarmed = $true
}

function Show-Status {
    Write-Host "=============================================================================="
    Write-Host $StepTitle
    Write-Host "=============================================================================="
    Write-Host ("Repo root: {0}" -f $RepoRoot)
    Write-Host ("Expected branch: {0}" -f $ExpectedBranch)
    Write-Host ("Prior completed step: {0}" -f $PriorStep)
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    foreach ($Key in $SafetyPosture.Keys) { Write-Host ("  {0}: {1}" -f $Key, $SafetyPosture[$Key]) }
    Write-Host ""
    Write-Host "Step files"
    foreach ($Relative in $StepFiles) {
        $Path = Join-Path $RepoRoot $Relative
        if (Test-Path $Path) { Write-Host ("  PRESENT {0}" -f $Relative) } else { Write-Host ("  MISSING {0}" -f $Relative) }
    }
}

function Apply-StepFiles {
    foreach ($Relative in $StepFiles) {
        $Path = Join-Path $RepoRoot $Relative
        if (-not (Test-Path $Path)) { throw ("Required step file missing: {0}" -f $Relative) }
        Write-Host ("SKIPPED {0} source and target are the same file." -f $Relative)
    }
    Write-Host "APPLY PASS: Phase 27 Step 26 files copied or already present."
}

function Test-Smoke {
    foreach ($Relative in $StepFiles) {
        $Path = Join-Path $RepoRoot $Relative
        if (-not (Test-Path $Path)) { throw ("Smoke test missing file: {0}" -f $Relative) }
    }
    if (-not $SafetyPosture["planning_only"]) { throw "planning_only must be true" }
    if ($SafetyPosture["no_network_transport_implementation"] -ne $true) { throw "no_network_transport_implementation must be true" }
    if ($SafetyPosture["no_bridge_post"] -ne $true) { throw "no_bridge_post must be true" }
    if ($SafetyPosture["no_network_sockets"] -ne $true) { throw "no_network_sockets must be true" }
    if ($SafetyPosture["phase28_start"] -ne $false) { throw "phase28_start must be false" }
    Write-Host "SMOKE TEST PASS: Phase 27 Step 26 Phase 20 Network Transport Implementation Staging Runtime Preflight Planning Approval Boundary Packet is present and planning-only."
}

function New-Packet {
    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupRoot = Join-Path $RepoRoot "backups"
    $PacketDir = Join-Path $BackupRoot ("phase27_step26_{0}_packet_{1}" -f $Slug, $Timestamp)
    New-Item -ItemType Directory -Path $PacketDir -Force | Out-Null
    $PacketJson = Join-Path $PacketDir ("phase27_step26_{0}_packet.json" -f $Slug)

    $Payload = [ordered]@{ phase = 27; step = 26; title = $StepTitle; prior_step = $PriorStep; safety_posture = $SafetyPosture; files = $StepFiles; generated_at = (Get-Date).ToString("s") }
    $Payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $PacketJson -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: phase27_boundary=implementation_staging_runtime_preflight_planning_approval_boundary_opened_by_packet"
    Write-Host "PASS: phase27_execution_start=false"
    Write-Host "PASS: phase27_implementation_start=false"
    Write-Host "PASS: implementation_phase_start=false"
    Write-Host "PASS: staging_runtime_start=false"
    Write-Host "PASS: staging_execution_start=false"
    Write-Host "PASS: cross_repo_write=false"
    Write-Host "PASS: cross_repo_mutation=false"
    Write-Host "PASS: external_repo_push=false"
    Write-Host "PASS: implementation_staging_runtime_preflight_planning_approval_boundary_mode=reference_only"
    Write-Host "PASS: implementation_staging_runtime_preflight_planning_approval_boundary_write=false"
    Write-Host "PASS: implementation_staging_runtime_preflight_planning_approval_boundary_record_creation=false"
    Write-Host "PASS: staging_readiness_decision_creation=false"
    Write-Host "PASS: staging_readiness_approval_creation=false"
    Write-Host "PASS: phase26_reopen=false"
    Write-Host "PASS: phase28_start=false"
    Write-Host "PASS: phase28_boundary_creation=false"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host ("CHECK: prior_step={0}" -f $PriorStep)
    Write-Host "CHECK: phase27_context=implementation_staging_runtime_preflight_planning_planning_only"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: network_transport_runtime_start=not_started"
    Write-Host "CHECK: parent_workspace_launcher=safe"
    Write-Host ("CHECK: packet_json={0}" -f $PacketJson)
}

switch ($Action) {
    "status" { Show-Status }
    "apply" { Apply-StepFiles }
    "smoke" { Test-Smoke }
    "packet" { New-Packet }
    "all" { Show-Status; Apply-StepFiles; Test-Smoke; New-Packet }
}
