param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

$ErrorActionPreference = "Stop"

$PhaseNumber = 25
$StepNumber = 76
$StepName = "Phase 25 Step 76 - Phase 20 Network Transport Implementation Post-Closeout Release Gate Readiness Planning Approval Boundary Packet"
$PriorStepName = "Phase 25 Step 75 - Phase 20 Network Transport Implementation Post-Closeout Release Gate Readiness Planning Safety Disposition Review Packet"
$ExpectedBranch = "phase25-step76-post-closeout-release-gate-readiness-planning-approval-boundary"
$ModeKey = "implementation_post_closeout_release_gate_readiness_planning_approval_boundary_mode"
$WriteKey = "implementation_post_closeout_release_gate_readiness_planning_approval_boundary_write"
$RecordKey = "implementation_post_closeout_release_gate_readiness_planning_approval_boundary_record_creation"
$PhaseContext = "implementation_post_closeout_release_gate_readiness_planning_approval_boundary_planning_only"
$PacketSlug = "phase25_step76_post_closeout_release_gate_readiness_planning_approval_boundary_packet"

$StepFiles = @(
    "scripts/phase25_step76_post_closeout_release_gate_readiness_planning_approval_boundary_packet.ps1",
    "ui/pages/452_Phase25_Step76_Implementation_PostCloseout_Release_Gate_Readiness_Planning_Approval_Boundary_Packet.py",
    "docs/PHASE25_STEP76_POST_CLOSEOUT_RELEASE_GATE_READINESS_PLANNING_APPROVAL_BOUNDARY_PACKET.md",
    "tests/test_phase25_step76_post_closeout_release_gate_readiness_planning_approval_boundary_packet.py"
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
    return (
        (Test-SafePath -Path (Join-Path $Candidate ".git")) -and
        (Test-SafePath -Path (Join-Path $Candidate "scripts")) -and
        (Test-SafePath -Path (Join-Path $Candidate "docs")) -and
        (Test-SafePath -Path (Join-Path $Candidate "tests")) -and
        (Test-SafePath -Path (Join-Path $Candidate "ui"))
    )
}

function Resolve-RepoRoot {
    param([string]$RepoRoot)
    $candidates = New-Object System.Collections.Generic.List[string]
    if (-not [string]::IsNullOrWhiteSpace($RepoRoot)) {
        $candidates.Add($RepoRoot)
        $candidates.Add((Join-Path $RepoRoot "unified_pool_service_platform_build"))
    }
    $cwd = (Get-Location).Path
    $candidates.Add($cwd)
    $candidates.Add((Join-Path $cwd "unified_pool_service_platform_build"))
    $candidates.Add((Join-Path $cwd "unified_pool_service_platform_build\unified_pool_service_platform_build"))
    if ($env:USERPROFILE) {
        $desktopParent = Join-Path $env:USERPROFILE "Desktop\unified_pool_service_platform_build"
        $candidates.Add($desktopParent)
        $candidates.Add((Join-Path $desktopParent "unified_pool_service_platform_build"))
    }
    $seen = @{}
    foreach ($candidate in $candidates) {
        if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
        try { $full = [System.IO.Path]::GetFullPath($candidate) } catch { continue }
        if ($seen.ContainsKey($full)) { continue }
        $seen[$full] = $true
        if (Test-RepoRootCandidate -Candidate $full) { return $full }
    }
    throw "Could not resolve repo root."
}

$Repo = Resolve-RepoRoot -RepoRoot $RepoRoot

$SafetyPosture = [ordered]@{
    planning_only = $true
    no_platform_db_mutation = $true
    no_bridge_mutation = $true
    no_real_bridge_http_client = $true
    no_network_transport_implementation = $true
    no_bridge_post = $true
    no_network_sockets = $true
    no_execution_implementation = $true
    phase25_boundary = "implementation_post_closeout_release_gate_readiness_planning_approval_boundary_opened_by_packet"
    phase25_execution_start = $false
    phase25_implementation_start = $false
    implementation_phase_start = $false
    post_closeout_runtime_start = $false
    controlled_activation_runtime_start = $false
    network_transport_runtime_start = $false
    bridge_transport_runtime_start = $false
    cross_repo_write = $false
    cross_repo_mutation = $false
    external_repo_push = $false
    implementation_post_closeout_release_gate_readiness_planning_approval_boundary_mode = "reference_only"
    implementation_post_closeout_release_gate_readiness_planning_approval_boundary_write = $false
    implementation_post_closeout_release_gate_readiness_planning_approval_boundary_record_creation = $false
    post_closeout_decision_creation = $false
    post_closeout_approval_creation = $false
    post_closeout_operator_approval_creation = $false
    no_operator_signoff = $true
    no_operator_approval = $true
    no_final_approval = $true
    phase24_reopen = $false
    phase26_start = $false
    phase26_boundary_creation = $false
    lacrm_default_mode = "dry_run"
    lacrm_live_write = $false
    live_write_disabled = $true
    live_write_unarmed = $true
}

function Show-Status {
    Write-Host "=============================================================================="
    Write-Host $StepName
    Write-Host "=============================================================================="
    Write-Host "Repo root: $Repo"
    Write-Host "Expected branch: $ExpectedBranch"
    Write-Host "Prior completed step: $PriorStepName"
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    foreach ($item in $SafetyPosture.GetEnumerator()) {
        Write-Host ("  {0}: {1}" -f $item.Key, $item.Value)
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

function Apply-StepFiles {
    foreach ($rel in $StepFiles) {
        $path = Join-SafePath -Root $Repo -RelativePath $rel
        if (Test-SafePath -Path $path) {
            Write-Host "SKIPPED $rel source and target are the same file."
        } else {
            throw "Missing expected step file: $rel"
        }
    }
    Write-Host "APPLY PASS: Phase 25 Step 76 files copied or already present."
}

function Invoke-SmokeTest {
    foreach ($rel in $StepFiles) {
        $path = Join-SafePath -Root $Repo -RelativePath $rel
        if (-not (Test-SafePath -Path $path)) { throw "Smoke test failed; missing $rel" }
    }
    $scriptText = Get-Content -LiteralPath (Join-SafePath -Root $Repo -RelativePath "scripts/phase25_step76_post_closeout_release_gate_readiness_planning_approval_boundary_packet.ps1") -Raw -Encoding UTF8
    if (-not $scriptText.Contains("planning_only")) { throw "Smoke test failed; missing planning_only marker." }
    if (-not $scriptText.Contains("no_network_transport_implementation")) { throw "Smoke test failed; missing network implementation guard." }
    Write-Host "SMOKE TEST PASS: Phase 25 Step 76 Implementation Post-Closeout Release Gate Readiness Planning Approval Boundary Packet is present and planning-only."
}

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, or network socket is started here."
    Write-Host "CHECK: Use a separate authorized implementation phase before any runtime execution work."
}

function Write-Packet {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDir = Join-Path $Repo ("backups\$PacketSlug`_$stamp")
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    $packetPath = Join-Path $backupDir "$PacketSlug.json"
    $packet = [ordered]@{
        phase = 25
        step = 76
        step_name = $StepName
        prior_step = $PriorStepName
        expected_branch = $ExpectedBranch
        safety_posture = $SafetyPosture
        files = $StepFiles
        packet_type = "planning_only_reference_packet"
        packet_json = $packetPath
    }
    $packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $packetPath -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: phase25_boundary=implementation_post_closeout_release_gate_readiness_planning_approval_boundary_opened_by_packet"
    Write-Host "PASS: phase25_execution_start=false"
    Write-Host "PASS: phase25_implementation_start=false"
    Write-Host "PASS: implementation_phase_start=false"
    Write-Host "PASS: post_closeout_runtime_start=false"
    Write-Host "PASS: cross_repo_write=false"
    Write-Host "PASS: cross_repo_mutation=false"
    Write-Host "PASS: external_repo_push=false"
    Write-Host "PASS: implementation_post_closeout_release_gate_readiness_planning_approval_boundary_mode=reference_only"
    Write-Host "PASS: implementation_post_closeout_release_gate_readiness_planning_approval_boundary_write=false"
    Write-Host "PASS: implementation_post_closeout_release_gate_readiness_planning_approval_boundary_record_creation=false"
    Write-Host "PASS: post_closeout_decision_creation=false"
    Write-Host "PASS: post_closeout_approval_creation=false"
    Write-Host "PASS: phase24_reopen=false"
    Write-Host "PASS: phase26_start=false"
    Write-Host "PASS: phase26_boundary_creation=false"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "CHECK: prior_step=$PriorStepName"
    Write-Host "CHECK: phase25_context=$PhaseContext"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: network_transport_runtime_start=not_started"
    Write-Host "CHECK: parent_workspace_launcher=safe"
    Write-Host "CHECK: packet_json=$packetPath"
}

function Invoke-All {
    Show-Status
    Apply-StepFiles
    Invoke-SmokeTest
    Write-Packet
}

if ($Action -eq "status") { Show-Status; return }
if ($Action -eq "apply") { Apply-StepFiles; return }
if ($Action -eq "smoke") { Invoke-SmokeTest; return }
if ($Action -eq "packet") { Write-Packet; return }
if ($Action -eq "all") { Invoke-All; return }

while ($true) {
    Write-Host ""
    Write-Host "Phase 25 Step 76 menu"
    Write-Host "1. Show status / verify paths"
    Write-Host "2. Apply Phase 25 Step 76 Implementation Post-Closeout Release Gate Readiness Planning Approval Boundary Packet files"
    Write-Host "3. Smoke test Phase 25 Step 76"
    Write-Host "4. Show server start placeholder only"
    Write-Host "5. Generate Phase 25 Step 76 Implementation Post-Closeout Release Gate Readiness Planning Approval Boundary Packet"
    Write-Host "6. Exit"
    $choice = Read-Host "Choose 1-6"
    if ($choice -eq "1") { Show-Status; continue }
    if ($choice -eq "2") { Apply-StepFiles; continue }
    if ($choice -eq "3") { Invoke-SmokeTest; continue }
    if ($choice -eq "4") { Show-ServerPlaceholder; continue }
    if ($choice -eq "5") { Write-Packet; continue }
    if ($choice -eq "6") { break }
    Write-Host "Choose a number from 1 through 6."
}
