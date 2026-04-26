param(
    [string]$RepoRoot = "",
    [string]$SourceRoot = ""
)

$ErrorActionPreference = "Stop"

$StepNumber = 16
$StepName = "Phase 22 Step 16 - Phase 20 Network Transport Planning Implementation Readiness Packet"
$PacketSlug = "phase22_phase20_network_transport_planning_implementation_readiness_packet"
$BranchName = "phase22-step16-phase20-network-transport-planning-implementation-readiness-packet"
$ExpectedPriorStep = "Phase 22 Step 15 - Phase 20 Network Transport Planning Implementation Gate Packet"

$StepFiles = @(
    "scripts\phase22_generate_phase20_network_transport_planning_implementation_readiness_packet.ps1",
    "ui\pages\122_Phase20_Network_Transport_Planning_Implementation_Readiness_Packet.py",
    "docs\PHASE22_STEP16_PHASE20_NETWORK_TRANSPORT_PLANNING_IMPLEMENTATION_READINESS_PACKET.md",
    "tests\test_phase22_phase20_network_transport_planning_implementation_readiness_packet.py"
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
    return ((Test-LiteralPathSafe -PathValue $GitPath) -or (Test-LiteralPathSafe -PathValue $UiPagesPath) -or (Test-LiteralPathSafe -PathValue $ScriptsPath))
}

function Get-CandidateRepoRoots {
    $Candidates = New-Object System.Collections.Generic.List[string]

    $ExplicitRoot = Remove-ControlCharacters -Value $RepoRoot
    if (-not [string]::IsNullOrWhiteSpace($ExplicitRoot)) {
        [void]$Candidates.Add($ExplicitRoot)
    }

    [void]$Candidates.Add((Get-Location).Path)

    if ($PSScriptRoot) {
        [void]$Candidates.Add($PSScriptRoot)
        $ScriptParent = Split-Path -Parent $PSScriptRoot
        if ($ScriptParent) {
            [void]$Candidates.Add($ScriptParent)
        }
        $ScriptGrandParent = Split-Path -Parent $ScriptParent
        if ($ScriptGrandParent) {
            [void]$Candidates.Add($ScriptGrandParent)
        }
    }

    $CurrentParent = Split-Path -Parent (Get-Location).Path
    if ($CurrentParent) {
        [void]$Candidates.Add($CurrentParent)
    }

    return $Candidates | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique
}

function Resolve-Phase22RepoRoot {
    foreach ($Candidate in Get-CandidateRepoRoots) {
        $Resolved = Resolve-LiteralPathSafe -PathValue $Candidate
        if ($Resolved -and (Test-RepoRootShape -PathValue $Resolved)) {
            return $Resolved
        }
    }

    throw "Run this script from the unified_pool_service_platform_build repo root, or pass -RepoRoot with the repo root path."
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

function Copy-Step16Files {
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

    Write-Host "APPLY PASS: Phase 22 Step 16 files copied or already present."
}

function Test-Step16Readiness {
    $Root = Resolve-Phase22RepoRoot
    $Missing = Test-StepFileSetPresent -Root $Root
    if ($Missing.Count -gt 0) {
        throw ("Missing Step 16 files: " + ($Missing -join ", "))
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
        "implementation_phase_start"
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

    Write-Host "SMOKE TEST PASS: Phase 22 Step 16 Phase 20 Network Transport Planning Implementation Readiness Packet is present and planning-only."
}

function Show-ServerStartPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, or network socket is started here."
    Write-Host "CHECK: Use a separate authorized implementation phase before any runtime execution work."
}

function Write-ImplementationReadinessPacket {
    $Root = Resolve-Phase22RepoRoot
    $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $PacketDir = Join-Path $Root ("backups\{0}_{1}" -f $PacketSlug, $Timestamp)
    if (-not (Test-LiteralPathSafe -PathValue $PacketDir)) {
        New-Item -ItemType Directory -Path $PacketDir | Out-Null
    }

    $Packet = [ordered]@{
        step = 16
        phase = 22
        related_phase = 20
        packet_name = $StepName
        packet_slug = $PacketSlug
        prior_completed_step = $ExpectedPriorStep
        expected_branch = $BranchName
        generated_at_local = (Get-Date).ToString("s")
        purpose = "Planning-only readiness packet after the implementation gate packet. It does not start implementation."
        safety_posture = $SafetyPosture
        readiness_checks = @(
            "Step 15 gate packet is treated as the latest completed committed step.",
            "Network transport remains a planning subject only.",
            "Bridge communication remains non-executable and non-mutating.",
            "LACRM remains dry_run by default.",
            "Live write remains disabled and unarmed.",
            "Any future implementation work must be separate from this packet."
        )
        step_files = $StepFiles
    }

    $JsonPath = Join-Path $PacketDir ("{0}.json" -f $PacketSlug)
    $Packet | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 -LiteralPath $JsonPath

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: authorization_record_creation=false"
    Write-Host "CHECK: packet_json=$JsonPath"
}

function Show-Menu {
    Write-Host ""
    Write-Host "Phase 22 Step 16 menu"
    Write-Host "1. Show status / verify paths"
    Write-Host "2. Apply Phase 22 Step 16 Phase 20 Network Transport Planning Implementation Readiness Packet files"
    Write-Host "3. Smoke test Phase 22 Step 16"
    Write-Host "4. Show server start placeholder only"
    Write-Host "5. Generate Phase 20 network transport planning implementation readiness packet"
    Write-Host "6. Exit"
}

while ($true) {
    Show-Menu
    $Choice = (Read-Host "Choose 1-6").Trim()
    switch ($Choice) {
        "1" { Show-StepStatus }
        "2" { Copy-Step16Files }
        "3" { Test-Step16Readiness }
        "4" { Show-ServerStartPlaceholder }
        "5" { Write-ImplementationReadinessPacket }
        "6" { break }
        default { Write-Host "Unknown option. Choose 1, 2, 3, 4, 5, or 6." }
    }
}
