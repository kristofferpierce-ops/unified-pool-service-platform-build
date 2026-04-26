param(
    [string]$RepoRoot = "",
    [string]$SourceRoot = "",
    [ValidateSet("", "status", "apply", "smoke", "server-placeholder", "packet", "all")]
    [string]$Action = ""
)

$ErrorActionPreference = "Stop"

$StepNumber = 20
$StepName = "Phase 22 Step 20 - Phase 20 Network Transport Planning Implementation Containment Packet"
$PacketSlug = "phase22_phase20_network_transport_planning_implementation_containment_packet"
$BranchName = "phase22-step20-phase20-network-transport-planning-implementation-containment-packet"
$ExpectedPriorStep = "Phase 22 Step 19 - Phase 20 Network Transport Planning Implementation Isolation Packet"

$StepFiles = @(
    "scripts\phase22_generate_phase20_network_transport_planning_implementation_containment_packet.ps1",
    "ui\pages\126_Phase20_Network_Transport_Planning_Implementation_Containment_Packet.py",
    "docs\PHASE22_STEP20_PHASE20_NETWORK_TRANSPORT_PLANNING_IMPLEMENTATION_CONTAINMENT_PACKET.md",
    "tests\test_phase22_phase20_network_transport_planning_implementation_containment_packet.py"
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
    no_operator_signoff = $true
    no_operator_approval = $true
    no_final_approval = $true
    no_design_closure_record_creation = $true
    lacrm_default_mode = "dry_run"
    lacrm_live_write = $false
    live_write_disabled = $true
    live_write_unarmed = $true
}

function Remove-ControlCharacters {
    param([AllowNull()][string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ""
    }
    return ([regex]::Replace($Value, "[\x00-\x1F\x7F]", "")).Trim()
}

function Test-LiteralPathSafe {
    param([AllowNull()][string]$PathValue)
    $CleanPath = Remove-ControlCharacters -Value $PathValue
    if ([string]::IsNullOrWhiteSpace($CleanPath)) {
        return $false
    }
    try {
        return [bool](Test-Path -LiteralPath $CleanPath)
    } catch {
        return $false
    }
}

function Resolve-LiteralPathSafe {
    param([AllowNull()][string]$PathValue)
    $CleanPath = Remove-ControlCharacters -Value $PathValue
    if ([string]::IsNullOrWhiteSpace($CleanPath)) {
        return ""
    }
    try {
        return (Resolve-Path -LiteralPath $CleanPath).Path
    } catch {
        return ""
    }
}

function Test-SameLiteralPathSafe {
    param(
        [AllowNull()][string]$LeftPath,
        [AllowNull()][string]$RightPath
    )

    $LeftResolved = Resolve-LiteralPathSafe -PathValue $LeftPath
    $RightResolved = Resolve-LiteralPathSafe -PathValue $RightPath

    if ([string]::IsNullOrWhiteSpace($LeftResolved) -or [string]::IsNullOrWhiteSpace($RightResolved)) {
        return $false
    }

    return ([string]::Equals($LeftResolved, $RightResolved, [System.StringComparison]::OrdinalIgnoreCase))
}

function Test-RepoRootShape {
    param([string]$PathValue)
    if (-not (Test-LiteralPathSafe -PathValue $PathValue)) {
        return $false
    }
    $GitPath = Join-Path $PathValue ".git"
    $UiPagesPath = Join-Path $PathValue "ui\pages"
    $ScriptsPath = Join-Path $PathValue "scripts"
    $DocsPath = Join-Path $PathValue "docs"
    return ((Test-LiteralPathSafe -PathValue $GitPath) -or ((Test-LiteralPathSafe -PathValue $UiPagesPath) -and (Test-LiteralPathSafe -PathValue $ScriptsPath) -and (Test-LiteralPathSafe -PathValue $DocsPath)))
}

function Add-CandidatePath {
    param(
        [System.Collections.Generic.List[string]]$Candidates,
        [AllowNull()][string]$PathValue
    )
    $CleanPath = Remove-ControlCharacters -Value $PathValue
    if (-not [string]::IsNullOrWhiteSpace($CleanPath)) {
        [void]$Candidates.Add($CleanPath)
    }
}

function Get-CandidateRepoRoots {
    $Candidates = New-Object System.Collections.Generic.List[string]

    Add-CandidatePath -Candidates $Candidates -PathValue $RepoRoot
    Add-CandidatePath -Candidates $Candidates -PathValue ((Get-Location).Path)
    Add-CandidatePath -Candidates $Candidates -PathValue (Join-Path (Get-Location).Path "unified_pool_service_platform_build")

    if ($PSScriptRoot) {
        Add-CandidatePath -Candidates $Candidates -PathValue $PSScriptRoot
        $ScriptParent = Split-Path -Parent $PSScriptRoot
        Add-CandidatePath -Candidates $Candidates -PathValue $ScriptParent
        if ($ScriptParent) {
            $ScriptGrandParent = Split-Path -Parent $ScriptParent
            Add-CandidatePath -Candidates $Candidates -PathValue $ScriptGrandParent
        }
    }

    $CurrentParent = Split-Path -Parent (Get-Location).Path
    Add-CandidatePath -Candidates $Candidates -PathValue $CurrentParent
    if ($CurrentParent) {
        Add-CandidatePath -Candidates $Candidates -PathValue (Join-Path $CurrentParent "unified_pool_service_platform_build")
    }

    return $Candidates | Select-Object -Unique
}

function Resolve-Phase22RepoRoot {
    foreach ($Candidate in Get-CandidateRepoRoots) {
        $Resolved = Resolve-LiteralPathSafe -PathValue $Candidate
        if ($Resolved -and (Test-RepoRootShape -PathValue $Resolved)) {
            return $Resolved
        }
    }

    throw "Run this script from the unified_pool_service_platform_build repo root, from the parent workspace, or pass -RepoRoot with the repo root path."
}

function Resolve-SourceRootSafe {
    $CleanSourceRoot = Remove-ControlCharacters -Value $SourceRoot
    if (-not [string]::IsNullOrWhiteSpace($CleanSourceRoot)) {
        $ResolvedSourceRoot = Resolve-LiteralPathSafe -PathValue $CleanSourceRoot
        if ($ResolvedSourceRoot) {
            return $ResolvedSourceRoot
        }
        throw "SourceRoot was supplied but was not found: $CleanSourceRoot"
    }

    $Root = Resolve-Phase22RepoRoot
    return $Root
}

function Get-StepPath {
    param([string]$Root, [string]$RelativePath)
    return Join-Path $Root $RelativePath
}

function Test-StepFileSetPresent {
    param([string]$Root)
    $Missing = @()
    foreach ($RelativePath in $StepFiles) {
        $Path = Get-StepPath -Root $Root -RelativePath $RelativePath
        if (-not (Test-LiteralPathSafe -PathValue $Path)) {
            $Missing += $RelativePath
        }
    }
    return $Missing
}

function Show-StepStatus {
    $Root = Resolve-Phase22RepoRoot
    Write-Host "=============================================================================="
    Write-Host $StepName
    Write-Host "=============================================================================="
    Write-Host "Repo root: $Root"
    Write-Host "Expected branch: $BranchName"
    Write-Host "Prior completed step: $ExpectedPriorStep"
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    foreach ($Item in $SafetyPosture.GetEnumerator()) {
        Write-Host ("  {0}: {1}" -f $Item.Key, $Item.Value)
    }
    Write-Host ""
    Write-Host "Step files"
    foreach ($RelativePath in $StepFiles) {
        $Path = Get-StepPath -Root $Root -RelativePath $RelativePath
        if (Test-LiteralPathSafe -PathValue $Path) {
            Write-Host "  PRESENT $RelativePath"
        } else {
            Write-Host "  MISSING $RelativePath"
        }
    }
}

function Copy-Step20Files {
    $Root = Resolve-Phase22RepoRoot
    $PayloadRoot = Resolve-SourceRootSafe

    foreach ($RelativePath in $StepFiles) {
        $SourcePath = Join-Path $PayloadRoot $RelativePath
        $TargetPath = Join-Path $Root $RelativePath
        if (-not (Test-LiteralPathSafe -PathValue $SourcePath)) {
            if (Test-LiteralPathSafe -PathValue $TargetPath) {
                Write-Host "SKIPPED $RelativePath already present in repo; source payload is not separate."
                continue
            }
            throw "Missing source payload file: $SourcePath"
        }
        $TargetDir = Split-Path -Parent $TargetPath
        if (-not (Test-LiteralPathSafe -PathValue $TargetDir)) {
            New-Item -ItemType Directory -Path $TargetDir | Out-Null
        }
        if (Test-SameLiteralPathSafe -LeftPath $SourcePath -RightPath $TargetPath) {
            Write-Host "SKIPPED $RelativePath source and target are the same file."
            continue
        }
        Copy-Item -LiteralPath $SourcePath -Destination $TargetPath -Force
        Write-Host "APPLIED $RelativePath"
    }

    Write-Host "APPLY PASS: Phase 22 Step 20 files copied or already present."
}

function Test-Step20Containment {
    $Root = Resolve-Phase22RepoRoot
    $Missing = Test-StepFileSetPresent -Root $Root
    if ($Missing.Count -gt 0) {
        throw ("Missing Step 20 files: " + ($Missing -join ", "))
    }

    $Combined = ""
    foreach ($RelativePath in $StepFiles) {
        $StepPath = Get-StepPath -Root $Root -RelativePath $RelativePath
        $Combined += "`n" + (Get-Content -Raw -LiteralPath $StepPath)
    }

    $RequiredTokens = @(
        "planning_only",
        "dry_run",
        "live_write_disabled",
        "live_write_unarmed",
        "no_network_transport_implementation",
        "no_real_bridge_http_client",
        "no_bridge_post",
        "no_network_sockets",
        "no_execution_implementation",
        "implementation_phase_start",
        "authorization_record_creation",
        "operator_signoff_creation",
        "operator_approval_creation",
        "final_approval_creation",
        "design_closure_record_creation"
    )
    foreach ($Token in $RequiredTokens) {
        if ($Combined -notmatch [regex]::Escape($Token)) {
            throw "Required planning token missing: $Token"
        }
    }

    $ForbiddenTokens = @(
        ("Invoke-" + "WebRequest"),
        ("Invoke-" + "RestMethod"),
        ("requests" + ".post("),
        ("http" + "x."),
        ("socket" + ".socket"),
        ("create" + "_engine("),
        ("Session" + "("),
        (".commit" + "("),
        ("live_write_enabled" + " = True"),
        ("lacrm_live_write" + " = True")
    )
    foreach ($Token in $ForbiddenTokens) {
        if ($Combined -like "*$Token*") {
            throw "Forbidden implementation or live-write token found: $Token"
        }
    }

    Write-Host "SMOKE TEST PASS: Phase 22 Step 20 Phase 20 Network Transport Planning Implementation Containment Packet is present and planning-only."
}

function Show-ServerStartPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, or network socket is started here."
    Write-Host "CHECK: Use a separate authorized implementation phase before any runtime execution work."
}

function Write-ImplementationContainmentPacket {
    $Root = Resolve-Phase22RepoRoot
    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $PacketDir = Join-Path $Root ("backups\{0}_{1}" -f $PacketSlug, $Timestamp)
    if (-not (Test-LiteralPathSafe -PathValue $PacketDir)) {
        New-Item -ItemType Directory -Path $PacketDir | Out-Null
    }

    $Packet = [ordered]@{
        step = 19
        phase = 22
        related_phase = 20
        packet_name = $StepName
        packet_slug = $PacketSlug
        prior_completed_step = $ExpectedPriorStep
        expected_branch = $BranchName
        generated_at_local = (Get-Date).ToString("s")
        purpose = "Planning-only implementation containment packet. It records containment controls for any future implementation discussion without starting implementation, approving writes, or creating closure records."
        safety_posture = $SafetyPosture
        containment_checks = @(
            "Step 19 isolation packet is treated as the latest completed committed step.",
            "Network transport remains a planning subject only.",
            "Bridge communication remains non-executable and non-mutating.",
            "LACRM remains dry_run by default.",
            "Live write remains disabled and unarmed.",
            "No operator signoff, operator approval, final approval, or design-closure record is created.",
            "Any future implementation work must be isolated into a separately named and authorized phase after explicit direction."
        )
        step_files = $StepFiles
    }

    $JsonPath = Join-Path $PacketDir ("{0}.json" -f $PacketSlug)
    $Packet | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -LiteralPath $JsonPath

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: authorization_record_creation=false"
    Write-Host "CHECK: operator_signoff_creation=false"
    Write-Host "CHECK: operator_approval_creation=false"
    Write-Host "CHECK: final_approval_creation=false"
    Write-Host "CHECK: design_closure_record_creation=false"
    Write-Host "CHECK: packet_json=$JsonPath"
}

function Show-Menu {
    Write-Host ""
    Write-Host "Phase 22 Step 20 menu"
    Write-Host "1. Show status / verify paths"
    Write-Host "2. Apply Phase 22 Step 20 Phase 20 Network Transport Planning Implementation Containment Packet files"
    Write-Host "3. Smoke test Phase 22 Step 20"
    Write-Host "4. Show server start placeholder only"
    Write-Host "5. Generate Phase 20 network transport planning implementation containment packet"
    Write-Host "6. Exit"
}

function Invoke-Step20Action {
    param([string]$SelectedAction)
    switch ($SelectedAction) {
        "status" { Show-StepStatus }
        "apply" { Copy-Step20Files }
        "smoke" { Test-Step20Containment }
        "server-placeholder" { Show-ServerStartPlaceholder }
        "packet" { Write-ImplementationContainmentPacket }
        "all" {
            Show-StepStatus
            Copy-Step20Files
            Test-Step20Containment
            Write-ImplementationContainmentPacket
        }
        default { throw "Unsupported action: $SelectedAction" }
    }
}

$CleanAction = Remove-ControlCharacters -Value $Action
if (-not [string]::IsNullOrWhiteSpace($CleanAction)) {
    Invoke-Step20Action -SelectedAction $CleanAction
    return
}

while ($true) {
    Show-Menu
    $Choice = Remove-ControlCharacters -Value (Read-Host "Choose 1-6")
    switch ($Choice) {
        "1" { Show-StepStatus }
        "2" { Copy-Step20Files }
        "3" { Test-Step20Containment }
        "4" { Show-ServerStartPlaceholder }
        "5" { Write-ImplementationContainmentPacket }
        "6" { break }
        default { Write-Host "Unknown option. Choose 1, 2, 3, 4, 5, or 6." }
    }
}
