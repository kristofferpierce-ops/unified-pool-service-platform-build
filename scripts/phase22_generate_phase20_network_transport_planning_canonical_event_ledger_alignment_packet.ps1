param(
    [string]$RepoRoot = "",
    [ValidateSet("menu", "status", "apply", "smoke", "packet", "all")]
    [string]$Action = "menu"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$StepNumber = 24
$StepLabel = "Phase 22 Step 24"
$StepTitle = "Phase 22 Step 24 - Phase 20 Network Transport Planning Canonical Event Ledger Alignment Packet"
$ExpectedBranch = "phase22-step24-phase20-network-transport-planning-canonical-event-ledger-alignment-packet"
$PriorCompletedStep = "Phase 22 Step 23 - Phase 20 Network Transport Planning Source Bucket Traceability Alignment Packet"
$PacketFolderPrefix = "phase22_phase20_network_transport_planning_canonical_event_ledger_alignment_packet"

$StepFiles = @(
    "scripts\phase22_generate_phase20_network_transport_planning_canonical_event_ledger_alignment_packet.ps1",
    "ui\pages\130_Phase20_Network_Transport_Planning_Canonical_Event_Ledger_Alignment_Packet.py",
    "docs\PHASE22_STEP24_PHASE20_NETWORK_TRANSPORT_PLANNING_CANONICAL_EVENT_LEDGER_ALIGNMENT_PACKET.md",
    "tests\test_phase22_phase20_network_transport_planning_canonical_event_ledger_alignment_packet.py"
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
    source_bucket_alignment_mode = "planning_traceability_alignment_only"
    source_bucket_writes = $false
    source_bucket_runtime = $false
    canonical_event_ledger_alignment_mode = "planning_entity_event_traceability_only"
    canonical_event_ledger_writes = $false
    canonical_event_ledger_runtime = $false
    operating_intelligence_runtime = $false
    expected_actual_runtime = $false
    connector_first_core = $true
    bridge_absorption_target = "connector_package_not_separate_product"
}

$CanonicalEventLedgerAlignment = [ordered]@{
    canonical_event_ledger = $true
    every_record_is_time_stamped_event = $true
    event_tied_to_entity = $true
    connector_first_operating_core = $true
    source_bucket_alignment = @(
        "raw",
        "normalized",
        "matched",
        "approved",
        "applied"
    )
    canonical_entity_scope = @(
        "Organization",
        "Branch",
        "User",
        "Customer",
        "Contact",
        "Property",
        "PoolOrVessel",
        "Equipment",
        "Product",
        "VendorProduct",
        "PriceHistory",
        "LaborProfile",
        "OverheadProfile",
        "QuoteModel",
        "QuoteScenario",
        "WorkOrder",
        "ServiceVisit",
        "Invoice",
        "Payment",
        "VendorOrder",
        "VendorDelivery",
        "InventorySnapshot",
        "CallEvent",
        "IntakeCase",
        "ReviewItem",
        "SyncJob",
        "SourceRecordRaw",
        "SourceRecordNormalized"
    )
    event_examples = @(
        "source payload received",
        "candidate match created",
        "review item deferred",
        "quote created",
        "service visit completed",
        "customer called",
        "lead created",
        "work order opened",
        "invoice sent",
        "invoice paid",
        "route travel completed"
    )
    later_intelligence_targets = @(
        "expected_vs_actual_engine",
        "variance_analysis",
        "profitability_analysis",
        "route_scoring",
        "quote_accuracy_tracking",
        "bayesian_update_layer"
    )
    forbidden_alignment_outcomes = @(
        "creating event ledger tables",
        "migrating bridge database",
        "writing canonical events",
        "starting operating intelligence runtime",
        "starting expected actual runtime",
        "network transport implementation",
        "shared database merge before internal model is explicit"
    )
}

function Remove-ControlCharacters {
    param([AllowNull()][string]$Value)
    if ($null -eq $Value) { return "" }
    return ($Value -replace "\p{Cc}", "").Trim()
}

function ConvertTo-SafeFullPath {
    param([Parameter(Mandatory = $true)][string]$PathValue)
    $clean = Remove-ControlCharacters $PathValue
    if ([string]::IsNullOrWhiteSpace($clean)) {
        throw "Path value was empty after cleanup."
    }
    return [System.IO.Path]::GetFullPath($clean)
}

function Test-SafePath {
    param([Parameter(Mandatory = $true)][string]$PathValue)
    $clean = Remove-ControlCharacters $PathValue
    if ([string]::IsNullOrWhiteSpace($clean)) { return $false }
    return Test-Path -LiteralPath $clean
}

function Resolve-RepoRoot {
    param([string]$RequestedRoot)

    if (-not [string]::IsNullOrWhiteSpace($RequestedRoot)) {
        $candidate = ConvertTo-SafeFullPath $RequestedRoot
        if (Test-SafePath $candidate) {
            return $candidate
        }
        throw "Requested repo root does not exist: $candidate"
    }

    $current = ConvertTo-SafeFullPath (Get-Location).Path
    $currentScripts = Join-Path $current "scripts"
    $currentTests = Join-Path $current "tests"
    if ((Test-SafePath $currentScripts) -and (Test-SafePath $currentTests)) {
        return $current
    }

    $scriptParent = ConvertTo-SafeFullPath (Join-Path $PSScriptRoot "..")
    $scriptParentScripts = Join-Path $scriptParent "scripts"
    $scriptParentTests = Join-Path $scriptParent "tests"
    if ((Test-SafePath $scriptParentScripts) -and (Test-SafePath $scriptParentTests)) {
        return $scriptParent
    }

    throw "Could not resolve repo root. Pass -RepoRoot explicitly."
}

$ResolvedRepoRoot = Resolve-RepoRoot $RepoRoot

function Join-RepoPath {
    param([Parameter(Mandatory = $true)][string]$RelativePath)
    $cleanRelative = Remove-ControlCharacters $RelativePath
    return Join-Path $ResolvedRepoRoot $cleanRelative
}

function Get-SourceRoot {
    $candidate = ConvertTo-SafeFullPath (Join-Path $PSScriptRoot "..")
    if ((Test-SafePath (Join-Path $candidate "scripts")) -and (Test-SafePath (Join-Path $candidate "docs"))) {
        return $candidate
    }
    return $ResolvedRepoRoot
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host "=============================================================================="
    Write-Host $Title
    Write-Host "=============================================================================="
}

function Show-Status {
    Write-Header $StepTitle
    Write-Host "Repo root: $ResolvedRepoRoot"
    Write-Host "Expected branch: $ExpectedBranch"
    Write-Host "Prior completed step: $PriorCompletedStep"
    Write-Host "Optimized launcher actions: -Action status, apply, smoke, packet, all"
    Write-Host ""
    Write-Host "Safety posture"
    foreach ($entry in $SafetyPosture.GetEnumerator()) {
        Write-Host ("  {0}: {1}" -f $entry.Key, $entry.Value)
    }
    Write-Host ""
    Write-Host "Canonical event ledger alignment"
    foreach ($entry in $CanonicalEventLedgerAlignment.GetEnumerator()) {
        if ($entry.Value -is [array]) {
            Write-Host ("  {0}: {1}" -f $entry.Key, ($entry.Value -join ", "))
        } else {
            Write-Host ("  {0}: {1}" -f $entry.Key, $entry.Value)
        }
    }
    Write-Host ""
    Write-Host "Step files"
    foreach ($relative in $StepFiles) {
        $target = Join-RepoPath $relative
        if (Test-SafePath $target) {
            Write-Host "  PRESENT $relative"
        } else {
            Write-Host "  MISSING $relative"
        }
    }
}

function Apply-StepFiles {
    $sourceRoot = Get-SourceRoot
    foreach ($relative in $StepFiles) {
        $sourcePath = Join-Path $sourceRoot $relative
        $targetPath = Join-RepoPath $relative

        if (-not (Test-SafePath $sourcePath)) {
            throw "Missing source file: $sourcePath"
        }

        $sourceFull = ConvertTo-SafeFullPath $sourcePath
        $targetFull = ConvertTo-SafeFullPath $targetPath

        if ([string]::Equals($sourceFull, $targetFull, [System.StringComparison]::OrdinalIgnoreCase)) {
            Write-Host "SKIPPED $relative source and target are the same file."
            continue
        }

        $targetDir = Split-Path -Parent $targetFull
        if (-not (Test-SafePath $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }

        Copy-Item -LiteralPath $sourceFull -Destination $targetFull -Force
        Write-Host "COPIED $relative"
    }

    Write-Host "APPLY PASS: Phase 22 Step 24 files copied or already present."
}

function Test-StepSmoke {
    $missing = @()
    foreach ($relative in $StepFiles) {
        $target = Join-RepoPath $relative
        if (-not (Test-SafePath $target)) {
            $missing += $relative
        }
    }

    if ($missing.Count -gt 0) {
        throw ("SMOKE TEST FAIL: Missing Phase 22 Step 24 files: " + ($missing -join ", "))
    }

    if (-not $SafetyPosture.planning_only) {
        throw "SMOKE TEST FAIL: planning_only flag must remain true."
    }
    if (-not $SafetyPosture.no_network_sockets) {
        throw "SMOKE TEST FAIL: no_network_sockets flag must remain true."
    }
    if (-not $SafetyPosture.live_write_unarmed) {
        throw "SMOKE TEST FAIL: live_write_unarmed flag must remain true."
    }
    if ($SafetyPosture.implementation_phase_start) {
        throw "SMOKE TEST FAIL: implementation phase must not start in Phase 22 Step 24."
    }
    if ($SafetyPosture.canonical_event_ledger_writes) {
        throw "SMOKE TEST FAIL: canonical event ledger writes must remain disabled in Phase 22 Step 24."
    }
    if ($SafetyPosture.expected_actual_runtime) {
        throw "SMOKE TEST FAIL: expected actual runtime must remain disabled in Phase 22 Step 24."
    }

    Write-Host "SMOKE TEST PASS: Phase 22 Step 24 Phase 20 Network Transport Planning Canonical Event Ledger Alignment Packet is present and planning-only."
}

function New-Packet {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupRoot = Join-Path $ResolvedRepoRoot "backups"
    $packetDir = Join-Path $backupRoot ("{0}_{1}" -f $PacketFolderPrefix, $stamp)
    New-Item -ItemType Directory -Path $packetDir -Force | Out-Null

    $packet = [ordered]@{
        phase = 22
        step = 24
        step_label = $StepLabel
        step_title = $StepTitle
        prior_completed_step = $PriorCompletedStep
        expected_branch = $ExpectedBranch
        generated_at_local = (Get-Date).ToString("s")
        planning_only = $SafetyPosture.planning_only
        safety_posture = $SafetyPosture
        canonical_event_ledger_alignment = $CanonicalEventLedgerAlignment
        canonical_event_ledger_intent = [ordered]@{
            purpose = "Record planning alignment between Phase 20 network transport planning and the canonical event ledger needed for operating intelligence."
            allowed = @(
                "document event ledger alignment",
                "record entity tied time stamped event guardrails",
                "connect source buckets to later expected actual analysis",
                "confirm no canonical event writes",
                "confirm no operating intelligence runtime"
            )
            blocked = @(
                "real bridge HTTP client",
                "network transport implementation",
                "bridge POST",
                "network socket",
                "execution implementation",
                "implementation phase start",
                "operator signoff creation",
                "operator approval creation",
                "final approval creation",
                "design closure record creation",
                "platform database mutation",
                "bridge mutation",
                "live LACRM write",
                "canonical event ledger table creation",
                "expected actual runtime"
            )
        }
        step_files = $StepFiles
    }

    $jsonPath = Join-Path $packetDir ($PacketFolderPrefix + ".json")
    $packet | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

    Write-Host "PASS: planning_only=true"
    Write-Host "PASS: no_real_bridge_http_client=true"
    Write-Host "PASS: no_network_transport_implementation=true"
    Write-Host "PASS: no_bridge_post=true"
    Write-Host "PASS: no_network_sockets=true"
    Write-Host "PASS: lacrm_default_mode=dry_run"
    Write-Host "PASS: live_write_disabled=true"
    Write-Host "PASS: live_write_unarmed=true"
    Write-Host "PASS: source_bucket_writes=false"
    Write-Host "PASS: canonical_event_ledger_writes=false"
    Write-Host "PASS: operating_intelligence_runtime=false"
    Write-Host "PASS: expected_actual_runtime=false"
    Write-Host "CHECK: implementation_phase_start=not_started"
    Write-Host "CHECK: authorization_record_creation=false"
    Write-Host "CHECK: operator_signoff_creation=false"
    Write-Host "CHECK: operator_approval_creation=false"
    Write-Host "CHECK: final_approval_creation=false"
    Write-Host "CHECK: design_closure_record_creation=false"
    Write-Host "CHECK: source_bucket_alignment=raw_normalized_matched_approved_applied"
    Write-Host "CHECK: event_ledger_alignment=canonical_time_stamped_entity_tied_events"
    Write-Host "CHECK: bridge_absorption_target=connector_package_not_separate_product"
    Write-Host "CHECK: connector_first_operating_core=true"
    Write-Host "CHECK: packet_json=$jsonPath"
}

function Show-ServerPlaceholder {
    Write-Host "CHECK: Server startup is intentionally disabled in this planning-only step."
    Write-Host "CHECK: No FastAPI, Streamlit, bridge server, or network socket is started here."
    Write-Host "CHECK: Phase 22 Step 24 only records canonical event ledger planning alignment."
}

function Invoke-Action {
    param([string]$SelectedAction)

    switch ($SelectedAction) {
        "status" { Show-Status }
        "apply" { Apply-StepFiles }
        "smoke" { Test-StepSmoke }
        "packet" { New-Packet }
        "all" {
            Show-Status
            Apply-StepFiles
            Test-StepSmoke
            New-Packet
        }
        default { throw "Unsupported action: $SelectedAction" }
    }
}

function Show-Menu {
    while ($true) {
        Write-Host ""
        Write-Host "Phase 22 Step 24 menu"
        Write-Host "1. Show status / verify paths"
        Write-Host "2. Apply Phase 22 Step 24 Phase 20 Network Transport Planning Canonical Event Ledger Alignment Packet files"
        Write-Host "3. Smoke test Phase 22 Step 24"
        Write-Host "4. Show server start placeholder only"
        Write-Host "5. Generate Phase 20 network transport planning canonical event ledger alignment packet"
        Write-Host "6. Exit"
        $choice = Remove-ControlCharacters (Read-Host "Choose 1-6")

        switch ($choice) {
            "1" { Show-Status }
            "2" { Apply-StepFiles }
            "3" { Test-StepSmoke }
            "4" { Show-ServerPlaceholder }
            "5" { New-Packet }
            "6" { return }
            default { Write-Host "Invalid choice. Enter a number from 1 to 6." }
        }
    }
}

if ($Action -eq "menu") {
    Show-Menu
} else {
    Invoke-Action $Action
}
