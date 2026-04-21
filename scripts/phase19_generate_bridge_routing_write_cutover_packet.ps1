param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$ReadinessDir = "",
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

function Add-ChecklistItem {
    param(
        [System.Collections.ArrayList]$Items,
        [string]$Category,
        [string]$Item,
        [bool]$Passed,
        [string]$Evidence = "",
        [string]$RequiredForFutureWrite = "yes"
    )

    [void]$Items.Add([ordered]@{
        category = $Category
        item = $Item
        passed = $Passed
        evidence = $Evidence
        required_for_future_write = $RequiredForFutureWrite
    })
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($ReadinessDir)) {
    $readinessArtifact = Get-LatestArtifact -FolderFilter "phase19_bridge_routing_write_readiness_*" -JsonName "phase19_bridge_routing_write_readiness.json" -Required $true
} else {
    $readinessJson = Join-Path $ReadinessDir "phase19_bridge_routing_write_readiness.json"
    if (!(Test-Path -LiteralPath $readinessJson)) {
        throw "Readiness JSON not found: $readinessJson"
    }
    $readinessArtifact = [ordered]@{
        folder = $ReadinessDir
        json_path = $readinessJson
        json_name = "phase19_bridge_routing_write_readiness.json"
        folder_name = Split-Path -Leaf $ReadinessDir
        last_write_time = (Get-Item -LiteralPath $readinessJson).LastWriteTime.ToString("o")
    }
}

$artifactSpecs = @(
    @{ key="readiness"; artifact=$readinessArtifact },
    @{ key="contract"; artifact=(Get-LatestArtifact -FolderFilter "phase19_bridge_routing_write_contract_*" -JsonName "phase19_bridge_routing_write_contract.json" -Required $false) },
    @{ key="apply_preview"; artifact=(Get-LatestArtifact -FolderFilter "phase19_routing_bridge_apply_preview_*" -JsonName "phase19_routing_bridge_apply_preview.json" -Required $false) },
    @{ key="rehearsal"; artifact=(Get-LatestArtifact -FolderFilter "phase19_bridge_routing_write_rehearsal_*" -JsonName "phase19_bridge_routing_write_rehearsal.json" -Required $false) },
    @{ key="audit_plan"; artifact=(Get-LatestArtifact -FolderFilter "phase19_bridge_routing_write_audit_plan_*" -JsonName "phase19_bridge_routing_write_audit_plan.json" -Required $false) },
    @{ key="audit_writer_run"; artifact=(Get-LatestArtifact -FolderFilter "phase19_bridge_routing_write_audit_writer_run_*" -JsonName "phase19_bridge_routing_write_audit_writer_run.json" -Required $false) },
    @{ key="rollback_snapshot"; artifact=(Get-LatestArtifact -FolderFilter "phase19_bridge_routing_rollback_snapshot_*" -JsonName "phase19_bridge_routing_rollback_snapshot.json" -Required $false) }
)

$artifacts = [ordered]@{}
$artifactData = [ordered]@{}

foreach ($spec in $artifactSpecs) {
    if ($null -ne $spec.artifact) {
        $artifacts[$spec.key] = $spec.artifact
        $artifactData[$spec.key] = Read-JsonFile $spec.artifact.json_path
    }
}

$platformAuditStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-audit/status"
$platformRehearsalStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-rehearsal/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$readiness = $artifactData.readiness
$readinessGate = $readiness.readiness

$checklist = New-Object System.Collections.ArrayList

Add-ChecklistItem $checklist "artifact" "Readiness report exists" $artifacts.Contains("readiness") $readinessArtifact.json_path
Add-ChecklistItem $checklist "artifact" "Bridge routing write contract exists" $artifacts.Contains("contract") $(if ($artifacts.Contains("contract")) { $artifacts.contract.json_path } else { "" })
Add-ChecklistItem $checklist "artifact" "Bridge apply preview exists" $artifacts.Contains("apply_preview") $(if ($artifacts.Contains("apply_preview")) { $artifacts.apply_preview.json_path } else { "" })
Add-ChecklistItem $checklist "artifact" "Bridge write rehearsal exists" $artifacts.Contains("rehearsal") $(if ($artifacts.Contains("rehearsal")) { $artifacts.rehearsal.json_path } else { "" })
Add-ChecklistItem $checklist "artifact" "Audit plan exists" $artifacts.Contains("audit_plan") $(if ($artifacts.Contains("audit_plan")) { $artifacts.audit_plan.json_path } else { "" })
Add-ChecklistItem $checklist "artifact" "Audit writer dry-run exists" $artifacts.Contains("audit_writer_run") $(if ($artifacts.Contains("audit_writer_run")) { $artifacts.audit_writer_run.json_path } else { "" })
Add-ChecklistItem $checklist "artifact" "Rollback snapshot exists" $artifacts.Contains("rollback_snapshot") $(if ($artifacts.Contains("rollback_snapshot")) { $artifacts.rollback_snapshot.json_path } else { "" })

Add-ChecklistItem $checklist "readiness" "No readiness blockers" ([int]$readinessGate.blocker_count -eq 0) "blocker_count=$($readinessGate.blocker_count)"
Add-ChecklistItem $checklist "readiness" "No readiness review items" ([int]$readinessGate.review_count -eq 0) "review_count=$($readinessGate.review_count)" "recommended"
Add-ChecklistItem $checklist "readiness" "Readiness report says bridge write cannot execute now" ($readinessGate.can_execute_bridge_write_now -eq $false) "can_execute_bridge_write_now=$($readinessGate.can_execute_bridge_write_now)"
Add-ChecklistItem $checklist "safety" "Readiness artifact reports no bridge POST" ($readiness.safety.bridge_post_called -eq $false) "bridge_post_called=$($readiness.safety.bridge_post_called)"
Add-ChecklistItem $checklist "safety" "Readiness artifact reports no platform DB mutation" ($readiness.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($readiness.safety.platform_db_mutation_performed)"
Add-ChecklistItem $checklist "safety" "Readiness artifact reports no LACRM call" ($readiness.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($readiness.safety.lacrm_call_performed)"

if ($platformAuditStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Platform audit status read successfully" $true "$PlatformApi/front-desk/routing/bridge-write-audit/status"
    Add-ChecklistItem $checklist "runtime" "Platform audit API remains read-only" ($platformAuditStatus.value.read_only -eq $true) "read_only=$($platformAuditStatus.value.read_only)"
    Add-ChecklistItem $checklist "runtime" "Platform audit API reports bridge POST disabled" ($platformAuditStatus.value.bridge_post_enabled -eq $false) "bridge_post_enabled=$($platformAuditStatus.value.bridge_post_enabled)"
} else {
    Add-ChecklistItem $checklist "runtime" "Platform audit status read successfully" $false $platformAuditStatus.error
}

if ($platformRehearsalStatus.ok) {
    Add-ChecklistItem $checklist "runtime" "Platform rehearsal status read successfully" $true "$PlatformApi/front-desk/routing/bridge-write-rehearsal/status"
    Add-ChecklistItem $checklist "runtime" "Bridge POST implementation remains absent" ($platformRehearsalStatus.value.bridge_post_call_implemented -eq $false) "bridge_post_call_implemented=$($platformRehearsalStatus.value.bridge_post_call_implemented)"
} else {
    Add-ChecklistItem $checklist "runtime" "Platform rehearsal status read successfully" $false $platformRehearsalStatus.error
}

Add-ChecklistItem $checklist "runtime" "Bridge health reachable for operator verification" $bridgeHealth.ok $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "recommended"

$requiredFailures = @($checklist | Where-Object { $_.required_for_future_write -eq "yes" -and $_.passed -ne $true })
$recommendedFailures = @($checklist | Where-Object { $_.required_for_future_write -eq "recommended" -and $_.passed -ne $true })

$packetStatus = if (@($requiredFailures).Count -eq 0 -and @($recommendedFailures).Count -eq 0) {
    "ready_for_operator_design_review"
} elseif (@($requiredFailures).Count -eq 0) {
    "operator_review_required"
} else {
    "blocked"
}

$safetyBlockers = @()
foreach ($dataKey in $artifactData.Keys) {
    $data = $artifactData[$dataKey]
    if ($data.safety) {
        if ($data.safety.bridge_post_called -eq $true) {
            $safetyBlockers += "$dataKey reports bridge_post_called=true"
        }
        if ($data.safety.bridge_mutation_performed -eq $true) {
            $safetyBlockers += "$dataKey reports bridge_mutation_performed=true"
        }
        if ($data.safety.lacrm_call_performed -eq $true) {
            $safetyBlockers += "$dataKey reports lacrm_call_performed=true"
        }
    }
}

if ($safetyBlockers.Count -gt 0) {
    $packetStatus = "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_cutover_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$packet = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 43"
    purpose = "Operator cutover packet for future guarded bridge routing write design"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_write_cutover_packet_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        live_write_enabled = $false
        routing_write_endpoint_implemented = $false
        bridge_write_implementation_added = $false
    }
    cutover_packet = [ordered]@{
        status = $packetStatus
        required_failures = @($requiredFailures).Count
        recommended_failures = @($recommendedFailures).Count
        safety_blockers = @($safetyBlockers).Count
        can_design_future_guarded_write = (@($requiredFailures).Count -eq 0 -and $safetyBlockers.Count -eq 0)
        can_execute_bridge_write_now = $false
        operator_signoff_required = $true
        future_confirmation_phrase = "WRITE BRIDGE ROUTING"
        future_required_gates = @(
            "PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED=true",
            "PLATFORM_BRIDGE_ROUTING_WRITE_ARMED=true",
            "PLATFORM_BRIDGE_ADMIN_TOKEN configured if bridge requires it",
            "readiness packet reviewed",
            "rollback snapshots available for every row to be written",
            "audit writer run completed before any bridge POST",
            "operator signs cutover packet"
        )
    }
    artifacts = $artifacts
    checklist = @($checklist)
    safety_blockers = $safetyBlockers
    readiness = $readiness
    runtime_status = [ordered]@{
        platform_audit_status_ok = $platformAuditStatus.ok
        platform_audit_status = if ($platformAuditStatus.ok) { $platformAuditStatus.value } else { $null }
        platform_rehearsal_status_ok = $platformRehearsalStatus.ok
        platform_rehearsal_status = if ($platformRehearsalStatus.ok) { $platformRehearsalStatus.value } else { $null }
        bridge_health_ok = $bridgeHealth.ok
        bridge_health = if ($bridgeHealth.ok) { $bridgeHealth.value } else { $null }
        bridge_health_error = $bridgeHealth.error
    }
    operator_signoff = [ordered]@{
        operator_name = ""
        reviewed_at = ""
        approved_for_future_design_only = $false
        approved_for_live_bridge_write = $false
        notes = ""
    }
    next_recommended_actions = @(
        "Resolve any required failures before adding a guarded bridge write implementation.",
        "Use this packet as the operator review artifact for future design only.",
        "Do not execute bridge writes from Step 43; no bridge write endpoint is implemented.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_cutover_packet.json"
$checklistCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_cutover_packet_checklist.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_cutover_packet_artifacts.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_cutover_packet.md"

$packet | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$checklist | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8

$artifactRows = @()
foreach ($key in $artifacts.Keys) {
    $artifactRows += [ordered]@{
        key = $key
        folder = $artifacts[$key].folder
        json_path = $artifacts[$key].json_path
        last_write_time = $artifacts[$key].last_write_time
    }
}
$artifactRows | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8

$checklistText = (@($checklist) | ForEach-Object { ("- [{0}] {1}: {2} - {3}" -f $_.category, $_.item, $_.passed, $_.evidence) }) -join "`n"
$artifactText = ($artifactRows | ForEach-Object { "- $($_.key): $($_.json_path)" }) -join "`n"
$safetyBlockerText = if ($safetyBlockers.Count -gt 0) { ($safetyBlockers | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }
$gateText = ($packet.cutover_packet.future_required_gates | ForEach-Object { "- $_" }) -join "`n"

$md = @"
# Phase 19 Bridge Routing Write Cutover Packet

Generated: $($packet.generated_at)

## Safety

- Bridge routing write cutover packet only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Routing write endpoint implemented: false
- Bridge write implementation added: false

## Packet status

- Status: $packetStatus
- Required failures: $(@($requiredFailures).Count)
- Recommended failures: $(@($recommendedFailures).Count)
- Safety blockers: $($safetyBlockers.Count)
- Can execute bridge write now: false

## Artifacts

$artifactText

## Checklist

$checklistText

## Safety blockers

$safetyBlockerText

## Future required gates

$gateText

## Operator signoff

- Operator name:
- Reviewed at:
- Approved for future design only: false
- Approved for live bridge write: false
- Notes:
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($packetStatus -eq "blocked") {
    Write-Host "CHECK | bridge_routing_write_cutover_packet=$OutputDir | status=$packetStatus | required_failures=$(@($requiredFailures).Count) | bridge_post_called=False"
} else {
    Write-Host "PASS | bridge_routing_write_cutover_packet=$OutputDir | status=$packetStatus | bridge_post_called=False"
}

Write-Host ""
Write-Host "Cutover packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
