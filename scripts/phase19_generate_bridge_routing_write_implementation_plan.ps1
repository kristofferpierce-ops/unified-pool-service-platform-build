param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$CutoverPacketDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestArtifact {
    param(
        [string]$FolderFilter,
        [string]$JsonName,
        [bool]$Required = $true
    )

    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter $FolderFilter -ErrorAction SilentlyContinue |
        Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName $JsonName)
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        if ($Required) {
            throw "No $FolderFilter folder containing $JsonName found in $BackupDir."
        }
        return $null
    }

    return [ordered]@{
        folder = $latest.FullName
        json_path = Join-Path $latest.FullName $JsonName
        json_name = $JsonName
        folder_name = $latest.Name
        last_write_time = $latest.LastWriteTime.ToString("o")
    }
}

function Try-GetJson {
    param([string]$Url)
    try {
        return @{ ok = $true; value = Invoke-RestMethod $Url -TimeoutSec 30; error = "" }
    } catch {
        return @{ ok = $false; value = $null; error = $_.Exception.Message }
    }
}

function Read-JsonFile {
    param([string]$Path)
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Add-PlanItem {
    param(
        [System.Collections.ArrayList]$Items,
        [string]$Category,
        [string]$Name,
        [string]$Status,
        [string]$Reason,
        [string]$FutureFile = "",
        [string]$SafetyGate = ""
    )

    [void]$Items.Add([ordered]@{
        category = $Category
        name = $Name
        status = $Status
        reason = $Reason
        future_file = $FutureFile
        safety_gate = $SafetyGate
    })
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($CutoverPacketDir)) {
    $cutoverArtifact = Get-LatestArtifact -FolderFilter "phase19_bridge_routing_write_cutover_packet_*" -JsonName "phase19_bridge_routing_write_cutover_packet.json" -Required $true
} else {
    $cutoverJson = Join-Path $CutoverPacketDir "phase19_bridge_routing_write_cutover_packet.json"
    if (!(Test-Path -LiteralPath $cutoverJson)) {
        throw "Cutover packet JSON not found: $cutoverJson"
    }
    $cutoverArtifact = [ordered]@{
        folder = $CutoverPacketDir
        json_path = $cutoverJson
        json_name = "phase19_bridge_routing_write_cutover_packet.json"
        folder_name = Split-Path -Leaf $CutoverPacketDir
        last_write_time = (Get-Item -LiteralPath $cutoverJson).LastWriteTime.ToString("o")
    }
}

$readinessArtifact = Get-LatestArtifact -FolderFilter "phase19_bridge_routing_write_readiness_*" -JsonName "phase19_bridge_routing_write_readiness.json" -Required $false
$contractArtifact = Get-LatestArtifact -FolderFilter "phase19_bridge_routing_write_contract_*" -JsonName "phase19_bridge_routing_write_contract.json" -Required $false
$rollbackArtifact = Get-LatestArtifact -FolderFilter "phase19_bridge_routing_rollback_snapshot_*" -JsonName "phase19_bridge_routing_rollback_snapshot.json" -Required $false
$auditWriterArtifact = Get-LatestArtifact -FolderFilter "phase19_bridge_routing_write_audit_writer_run_*" -JsonName "phase19_bridge_routing_write_audit_writer_run.json" -Required $false

$cutover = Read-JsonFile $cutoverArtifact.json_path
$readiness = if ($readinessArtifact) { Read-JsonFile $readinessArtifact.json_path } else { $null }
$contract = if ($contractArtifact) { Read-JsonFile $contractArtifact.json_path } else { $null }
$rollback = if ($rollbackArtifact) { Read-JsonFile $rollbackArtifact.json_path } else { $null }
$auditWriter = if ($auditWriterArtifact) { Read-JsonFile $auditWriterArtifact.json_path } else { $null }

$platformRehearsalStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-rehearsal/status"
$platformAuditStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-audit/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$planItems = New-Object System.Collections.ArrayList

Add-PlanItem $planItems "future_service" "Bridge routing HTTP client module" "not_implemented_in_step44" "Future step may add a client wrapper, but Step 44 does not add requests/httpx or bridge POST code." "app/services/routing_bridge_write_client.py" "PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED"
Add-PlanItem $planItems "future_service" "Bridge routing guarded writer service" "not_implemented_in_step44" "Future service must require cutover packet approval, audit pre-row, rollback snapshot, idempotency key, and typed confirmation." "app/services/routing_bridge_write_executor.py" "PLATFORM_BRIDGE_ROUTING_WRITE_ARMED"
Add-PlanItem $planItems "future_api" "Bridge routing write endpoint" "not_implemented_in_step44" "Future API must default to dry_run and refuse live writes unless every gate is true." "app/api/routes/routing_bridge_write_executor.py" "WRITE BRIDGE ROUTING"
Add-PlanItem $planItems "future_audit" "Pre-write audit capture" "required_before_future_write" "Future implementation must write platform-local audit row before any bridge POST attempt." "app/services/routing_bridge_write_audit_writer.py" "PLATFORM_BRIDGE_ROUTING_AUDIT_WRITE_ENABLED"
Add-PlanItem $planItems "future_audit" "Post-write audit update" "required_before_future_write" "Future implementation must record response payload, bridge_post_called flag, and bridge mutation result." "app/services/routing_bridge_write_audit_writer.py" "PLATFORM_BRIDGE_ROUTING_AUDIT_WRITE_ARMED"
Add-PlanItem $planItems "future_rollback" "Rollback restore payload capture" "required_before_future_write" "Future implementation must require rollback_snapshot_available for each target row." "scripts/phase19_capture_bridge_routing_rollback_snapshot.ps1" "rollback snapshot review"
Add-PlanItem $planItems "future_test" "No-live-write regression tests" "required_before_future_write" "Future tests must prove missing gates block writes and do not call bridge POST." "tests/test_phase19_bridge_routing_write_executor.py" "test safety gates"
Add-PlanItem $planItems "future_ui" "Operator bridge write review UI" "not_implemented_in_step44" "Future UI must show blocked/dry-run/live states and never default to live." "ui/pages/46_or_later_Bridge_Routing_Write_Executor.py" "operator signoff"

$blockers = New-Object System.Collections.ArrayList

function Add-Blocker {
    param([string]$Code, [string]$Message, [string]$Severity = "blocker", [string]$Source = "")
    [void]$blockers.Add([ordered]@{
        severity = $Severity
        code = $Code
        source = $Source
        message = $Message
    })
}

if ($cutover.safety.bridge_post_called -ne $false) {
    Add-Blocker "cutover_bridge_post_called" "Cutover packet indicates bridge_post_called was not false." "blocker" "cutover"
}
if ($cutover.safety.bridge_write_implementation_added -ne $false) {
    Add-Blocker "cutover_write_implementation_added" "Cutover packet indicates a bridge write implementation was already added." "blocker" "cutover"
}
if ($cutover.cutover_packet.can_execute_bridge_write_now -ne $false) {
    Add-Blocker "cutover_can_execute_now" "Cutover packet does not explicitly block immediate bridge write execution." "blocker" "cutover"
}
if ($cutover.cutover_packet.required_failures -gt 0) {
    Add-Blocker "cutover_required_failures" "Cutover packet has required failures." "blocker" "cutover"
}
if ($cutover.cutover_packet.recommended_failures -gt 0) {
    Add-Blocker "cutover_recommended_failures" "Cutover packet has recommended failures requiring operator review." "review" "cutover"
}
if ($cutover.cutover_packet.safety_blockers -gt 0) {
    Add-Blocker "cutover_safety_blockers" "Cutover packet has safety blockers." "blocker" "cutover"
}

if ($readiness) {
    if ($readiness.safety.bridge_post_called -ne $false) {
        Add-Blocker "readiness_bridge_post_called" "Readiness report indicates bridge_post_called was not false." "blocker" "readiness"
    }
    if ($readiness.readiness.can_execute_bridge_write_now -ne $false) {
        Add-Blocker "readiness_can_execute_now" "Readiness report does not explicitly block immediate bridge write execution." "blocker" "readiness"
    }
} else {
    Add-Blocker "missing_readiness" "Readiness report artifact is missing." "blocker" "readiness"
}

if ($contract) {
    if ($contract.safety.bridge_post_called -ne $false) {
        Add-Blocker "contract_bridge_post_called" "Contract report indicates bridge_post_called was not false." "blocker" "contract"
    }
} else {
    Add-Blocker "missing_contract" "Bridge routing write contract artifact is missing." "blocker" "contract"
}

if ($rollback) {
    if ($rollback.safety.bridge_get_only -ne $true) {
        Add-Blocker "rollback_not_get_only" "Rollback snapshot is not marked bridge_get_only." "blocker" "rollback"
    }
    if ($rollback.safety.bridge_post_called -ne $false) {
        Add-Blocker "rollback_bridge_post_called" "Rollback snapshot indicates bridge_post_called was not false." "blocker" "rollback"
    }
} else {
    Add-Blocker "missing_rollback_snapshot" "Rollback snapshot artifact is missing." "blocker" "rollback"
}

if ($auditWriter) {
    if ($auditWriter.safety.bridge_post_called -ne $false) {
        Add-Blocker "audit_writer_bridge_post_called" "Audit writer run indicates bridge_post_called was not false." "blocker" "audit_writer"
    }
} else {
    Add-Blocker "missing_audit_writer_run" "Audit writer run artifact is missing." "blocker" "audit_writer"
}

if ($platformRehearsalStatus.ok) {
    if ($platformRehearsalStatus.value.bridge_post_call_implemented -ne $false) {
        Add-Blocker "rehearsal_post_implemented" "Platform rehearsal status says bridge_post_call_implemented is not false." "blocker" "platform"
    }
} else {
    Add-Blocker "rehearsal_status_unreadable" "Could not read platform bridge-write-rehearsal status: $($platformRehearsalStatus.error)" "review" "platform"
}

if ($platformAuditStatus.ok) {
    if ($platformAuditStatus.value.bridge_post_enabled -ne $false) {
        Add-Blocker "audit_bridge_post_enabled" "Platform audit status says bridge_post_enabled is not false." "blocker" "platform"
    }
} else {
    Add-Blocker "audit_status_unreadable" "Could not read platform bridge-write-audit status: $($platformAuditStatus.error)" "review" "platform"
}

$requiredBlockers = @($blockers | Where-Object { $_.severity -eq "blocker" })
$reviewItems = @($blockers | Where-Object { $_.severity -eq "review" })

$implementationPlanStatus = if ($requiredBlockers.Count -eq 0 -and $reviewItems.Count -eq 0) {
    "ready_for_guarded_implementation_scaffold_design"
} elseif ($requiredBlockers.Count -eq 0) {
    "operator_review_required_before_scaffold_design"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_implementation_plan_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$artifactRows = @(
    [ordered]@{ key="cutover_packet"; json_path=$cutoverArtifact.json_path; folder=$cutoverArtifact.folder },
    [ordered]@{ key="readiness"; json_path=if ($readinessArtifact) { $readinessArtifact.json_path } else { "" }; folder=if ($readinessArtifact) { $readinessArtifact.folder } else { "" } },
    [ordered]@{ key="contract"; json_path=if ($contractArtifact) { $contractArtifact.json_path } else { "" }; folder=if ($contractArtifact) { $contractArtifact.folder } else { "" } },
    [ordered]@{ key="rollback_snapshot"; json_path=if ($rollbackArtifact) { $rollbackArtifact.json_path } else { "" }; folder=if ($rollbackArtifact) { $rollbackArtifact.folder } else { "" } },
    [ordered]@{ key="audit_writer_run"; json_path=if ($auditWriterArtifact) { $auditWriterArtifact.json_path } else { "" }; folder=if ($auditWriterArtifact) { $auditWriterArtifact.folder } else { "" } }
)

$plan = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 44"
    purpose = "Bridge routing write guarded implementation plan"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_write_implementation_plan_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        live_write_enabled = $false
        routing_write_endpoint_implemented = $false
        bridge_write_implementation_added = $false
    }
    implementation_plan = [ordered]@{
        status = $implementationPlanStatus
        required_blockers = $requiredBlockers.Count
        review_items = $reviewItems.Count
        can_add_guarded_write_scaffold_next = ($requiredBlockers.Count -eq 0)
        can_execute_bridge_write_now = $false
        next_step_recommendation = if ($requiredBlockers.Count -eq 0) {
            "Add a disabled-by-default bridge write scaffold that still has no live default and is blocked without all gates."
        } else {
            "Resolve blockers before adding any bridge write scaffold."
        }
        required_future_gates = @(
            "PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED=true",
            "PLATFORM_BRIDGE_ROUTING_WRITE_ARMED=true",
            "PLATFORM_BRIDGE_ADMIN_TOKEN configured if required",
            "operator confirmation phrase WRITE BRIDGE ROUTING",
            "cutover packet approved for future design only",
            "rollback snapshot available for each row",
            "audit pre-row created before bridge POST",
            "idempotency key included on every future request"
        )
    }
    artifacts = $artifactRows
    plan_items = @($planItems)
    blockers = @($blockers)
    runtime_status = [ordered]@{
        platform_rehearsal_status_ok = $platformRehearsalStatus.ok
        platform_rehearsal_status = if ($platformRehearsalStatus.ok) { $platformRehearsalStatus.value } else { $null }
        platform_audit_status_ok = $platformAuditStatus.ok
        platform_audit_status = if ($platformAuditStatus.ok) { $platformAuditStatus.value } else { $null }
        bridge_health_ok = $bridgeHealth.ok
        bridge_health = if ($bridgeHealth.ok) { $bridgeHealth.value } else { $null }
        bridge_health_error = $bridgeHealth.error
    }
    next_recommended_actions = @(
        "Review this plan before adding any bridge write scaffold.",
        "Do not add bridge POST code until the scaffold design is accepted.",
        "Keep bridge routing controls as the operational write path until explicit cutover.",
        "Keep LACRM live writes disabled unless a separate LACRM-specific signoff is completed."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_implementation_plan.json"
$itemsCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_implementation_plan_items.csv"
$blockersCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_implementation_plan_blockers.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_implementation_plan_artifacts.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_implementation_plan.md"

$plan | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$planItems | Export-Csv -LiteralPath $itemsCsvPath -NoTypeInformation -Encoding UTF8
$blockers | Export-Csv -LiteralPath $blockersCsvPath -NoTypeInformation -Encoding UTF8
$artifactRows | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8

$itemText = (@($planItems) | ForEach-Object { "- [$($_.category)] $($_.name): $($_.status) - $($_.reason)" }) -join "`n"
$blockerText = if (@($blockers).Count -gt 0) { (@($blockers) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }
$artifactText = ($artifactRows | ForEach-Object { "- $($_.key): $($_.json_path)" }) -join "`n"
$gateText = ($plan.implementation_plan.required_future_gates | ForEach-Object { "- $_" }) -join "`n"

$md = @"
# Phase 19 Bridge Routing Write Implementation Plan

Generated: $($plan.generated_at)

## Safety

- Bridge routing write implementation plan only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Routing write endpoint implemented: false
- Bridge write implementation added: false

## Implementation plan status

- Status: $implementationPlanStatus
- Required blockers: $($requiredBlockers.Count)
- Review items: $($reviewItems.Count)
- Can execute bridge write now: false

## Artifacts

$artifactText

## Future plan items

$itemText

## Blockers / review items

$blockerText

## Required future gates

$gateText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($implementationPlanStatus -eq "blocked") {
    Write-Host "CHECK | bridge_routing_write_implementation_plan=$OutputDir | status=$implementationPlanStatus | blockers=$($requiredBlockers.Count) | bridge_post_called=False"
} else {
    Write-Host "PASS | bridge_routing_write_implementation_plan=$OutputDir | status=$implementationPlanStatus | bridge_post_called=False"
}

Write-Host ""
Write-Host "Implementation plan files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
