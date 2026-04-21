param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
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

function Add-Blocker {
    param(
        [System.Collections.ArrayList]$Blockers,
        [string]$Code,
        [string]$Message,
        [string]$Severity = "blocker",
        [string]$Source = ""
    )

    [void]$Blockers.Add([ordered]@{
        severity = $Severity
        code = $Code
        source = $Source
        message = $Message
    })
}

function Count-Rows {
    param($Value, [string[]]$Keys)
    if ($null -eq $Value) { return 0 }
    if ($Value -is [System.Array]) { return @($Value).Count }
    foreach ($key in $Keys) {
        if ($Value.$key -is [System.Array]) {
            return @($Value.$key).Count
        }
    }
    return 0
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$artifactSpecs = @(
    @{ key="contract"; filter="phase19_bridge_routing_write_contract_*"; json="phase19_bridge_routing_write_contract.json" },
    @{ key="apply_preview"; filter="phase19_routing_bridge_apply_preview_*"; json="phase19_routing_bridge_apply_preview.json" },
    @{ key="rehearsal"; filter="phase19_bridge_routing_write_rehearsal_*"; json="phase19_bridge_routing_write_rehearsal.json" },
    @{ key="audit_plan"; filter="phase19_bridge_routing_write_audit_plan_*"; json="phase19_bridge_routing_write_audit_plan.json" },
    @{ key="audit_writer_run"; filter="phase19_bridge_routing_write_audit_writer_run_*"; json="phase19_bridge_routing_write_audit_writer_run.json" },
    @{ key="rollback_snapshot"; filter="phase19_bridge_routing_rollback_snapshot_*"; json="phase19_bridge_routing_rollback_snapshot.json" }
)

$artifacts = [ordered]@{}
$artifactData = [ordered]@{}
$blockers = New-Object System.Collections.ArrayList

foreach ($spec in $artifactSpecs) {
    try {
        $artifact = Get-LatestArtifact -FolderFilter $spec.filter -JsonName $spec.json -Required $true
        $artifacts[$spec.key] = $artifact
        $artifactData[$spec.key] = Read-JsonFile $artifact.json_path
    } catch {
        Add-Blocker $blockers "missing_artifact" $_.Exception.Message "blocker" $spec.key
    }
}

$platformAuditStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-audit/status"
$platformRehearsalStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-rehearsal/status"
$platformApplyPreviewStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-apply-preview/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

if (!$platformAuditStatus.ok) {
    Add-Blocker $blockers "platform_audit_status_unreadable" "Could not read platform bridge-write-audit status: $($platformAuditStatus.error)" "blocker" "platform"
} else {
    if ($platformAuditStatus.value.read_only -ne $true) {
        Add-Blocker $blockers "platform_audit_not_read_only" "Bridge write audit API is not reporting read_only=true." "blocker" "platform"
    }
    if ($platformAuditStatus.value.bridge_post_enabled -ne $false) {
        Add-Blocker $blockers "platform_audit_bridge_post_enabled" "Bridge write audit API reports bridge_post_enabled not false." "blocker" "platform"
    }
    if ([int]$platformAuditStatus.value.bridge_post_called_rows -ne 0) {
        Add-Blocker $blockers "bridge_post_called_rows_exist" "Audit status reports bridge_post_called rows." "blocker" "platform"
    }
}

if (!$platformRehearsalStatus.ok) {
    Add-Blocker $blockers "platform_rehearsal_status_unreadable" "Could not read platform bridge-write-rehearsal status: $($platformRehearsalStatus.error)" "blocker" "platform"
} else {
    if ($platformRehearsalStatus.value.rehearsal_only -ne $true) {
        Add-Blocker $blockers "rehearsal_not_marked_rehearsal_only" "Bridge write rehearsal API is not reporting rehearsal_only=true." "blocker" "platform"
    }
    if ($platformRehearsalStatus.value.bridge_post_call_implemented -ne $false) {
        Add-Blocker $blockers "bridge_post_call_implemented" "Bridge write rehearsal API reports bridge_post_call_implemented not false." "blocker" "platform"
    }
    if ($platformRehearsalStatus.value.bridge_post_called -ne $false) {
        Add-Blocker $blockers "bridge_post_called" "Bridge write rehearsal API reports bridge_post_called not false." "blocker" "platform"
    }
}

if (!$platformApplyPreviewStatus.ok) {
    Add-Blocker $blockers "platform_apply_preview_status_unreadable" "Could not read platform bridge-apply-preview status: $($platformApplyPreviewStatus.error)" "review" "platform"
} else {
    if ($platformApplyPreviewStatus.value.preview_only -ne $true) {
        Add-Blocker $blockers "apply_preview_not_preview_only" "Bridge apply preview status is not reporting preview_only=true." "blocker" "platform"
    }
    if ($platformApplyPreviewStatus.value.bridge_post_called -ne $false) {
        Add-Blocker $blockers "apply_preview_bridge_post_called" "Bridge apply preview status reports bridge_post_called not false." "blocker" "platform"
    }
}

if (!$bridgeHealth.ok) {
    Add-Blocker $blockers "bridge_health_unreadable" "Could not read bridge health: $($bridgeHealth.error)" "review" "bridge"
}

if ($artifactData.Contains("contract")) {
    $contract = $artifactData.contract
    if ($contract.safety.bridge_routing_write_contract_only -ne $true) {
        Add-Blocker $blockers "contract_not_contract_only" "Step 36 contract safety flag is not contract-only." "blocker" "contract"
    }
    if ($contract.safety.bridge_post_called -ne $false) {
        Add-Blocker $blockers "contract_bridge_post_called" "Step 36 contract reports bridge_post_called not false." "blocker" "contract"
    }
}

if ($artifactData.Contains("apply_preview")) {
    $preview = $artifactData.apply_preview
    if ($preview.safety.bridge_apply_preview_only -ne $true) {
        Add-Blocker $blockers "apply_preview_not_preview_only_artifact" "Step 35 preview report is not preview-only." "blocker" "apply_preview"
    }
    if ($preview.safety.bridge_post_called -ne $false) {
        Add-Blocker $blockers "apply_preview_artifact_bridge_post_called" "Step 35 preview report says bridge_post_called not false." "blocker" "apply_preview"
    }
}

if ($artifactData.Contains("rehearsal")) {
    $rehearsal = $artifactData.rehearsal
    if ($rehearsal.safety.bridge_routing_write_rehearsal_only -ne $true) {
        Add-Blocker $blockers "rehearsal_not_rehearsal_only_artifact" "Step 37 rehearsal report is not rehearsal-only." "blocker" "rehearsal"
    }
    if ($rehearsal.safety.bridge_post_called -ne $false) {
        Add-Blocker $blockers "rehearsal_bridge_post_called" "Step 37 rehearsal report says bridge_post_called not false." "blocker" "rehearsal"
    }
    foreach ($item in @($rehearsal.safety_errors)) {
        Add-Blocker $blockers "rehearsal_safety_error" "$item" "blocker" "rehearsal"
    }
}

if ($artifactData.Contains("audit_plan")) {
    $auditPlan = $artifactData.audit_plan
    if ($auditPlan.safety.bridge_routing_write_audit_plan_only -ne $true) {
        Add-Blocker $blockers "audit_plan_not_plan_only" "Step 39 audit plan report is not audit-plan-only." "blocker" "audit_plan"
    }
    if ($auditPlan.safety.bridge_post_called -ne $false) {
        Add-Blocker $blockers "audit_plan_bridge_post_called" "Step 39 audit plan report says bridge_post_called not false." "blocker" "audit_plan"
    }
    foreach ($item in @($auditPlan.safety_errors)) {
        Add-Blocker $blockers "audit_plan_safety_error" "$item" "blocker" "audit_plan"
    }
}

if ($artifactData.Contains("audit_writer_run")) {
    $writerRun = $artifactData.audit_writer_run
    if ($writerRun.safety.bridge_post_called -ne $false) {
        Add-Blocker $blockers "audit_writer_bridge_post_called" "Step 40 audit writer run says bridge_post_called not false." "blocker" "audit_writer_run"
    }
    if ($writerRun.safety.bridge_mutation_performed -ne $false) {
        Add-Blocker $blockers "audit_writer_bridge_mutation" "Step 40 audit writer run says bridge_mutation_performed not false." "blocker" "audit_writer_run"
    }
    if ($writerRun.dry_run -ne $true -and $writerRun.safety.audit_write_performed -ne $true) {
        Add-Blocker $blockers "audit_writer_unknown_execution_state" "Step 40 audit writer run is neither dry-run nor recorded audit-write execution." "review" "audit_writer_run"
    }
}

if ($artifactData.Contains("rollback_snapshot")) {
    $rollback = $artifactData.rollback_snapshot
    if ($rollback.safety.bridge_routing_rollback_snapshot_only -ne $true) {
        Add-Blocker $blockers "rollback_not_snapshot_only" "Step 41 rollback report is not rollback-snapshot-only." "blocker" "rollback_snapshot"
    }
    if ($rollback.safety.bridge_get_only -ne $true) {
        Add-Blocker $blockers "rollback_not_get_only" "Step 41 rollback report is not bridge GET only." "blocker" "rollback_snapshot"
    }
    if ($rollback.safety.bridge_post_called -ne $false) {
        Add-Blocker $blockers "rollback_bridge_post_called" "Step 41 rollback report says bridge_post_called not false." "blocker" "rollback_snapshot"
    }
    foreach ($item in @($rollback.safety_errors)) {
        Add-Blocker $blockers "rollback_safety_error" "$item" "blocker" "rollback_snapshot"
    }

    $statusCounts = $rollback.counts.status_counts
    if ($statusCounts -and $statusCounts.rollback_snapshot_not_available -gt 0) {
        Add-Blocker $blockers "rollback_snapshots_missing" "Some rollback snapshot rows are not available." "review" "rollback_snapshot"
    }
}

$artifactSummary = @()
foreach ($key in $artifacts.Keys) {
    $data = $artifactData[$key]
    $artifactSummary += [ordered]@{
        key = $key
        folder = $artifacts[$key].folder
        json_path = $artifacts[$key].json_path
        generated_at = if ($data.generated_at) { $data.generated_at } else { "" }
        safety = if ($data.safety) { $data.safety } else { @{} }
    }
}

$blockerCount = @($blockers | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($blockers | Where-Object { $_.severity -eq "review" }).Count
$goNoGo = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "ready_for_future_guarded_write_design"
} elseif ($blockerCount -eq 0) {
    "review_required_before_future_write_design"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_readiness_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 42"
    purpose = "Bridge routing write readiness go/no-go gate"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_write_readiness_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        live_write_enabled = $false
        routing_write_endpoint_implemented = $false
    }
    readiness = [ordered]@{
        go_no_go = $goNoGo
        blocker_count = $blockerCount
        review_count = $reviewCount
        can_design_future_guarded_write = ($blockerCount -eq 0)
        can_execute_bridge_write_now = $false
        reason = if ($blockerCount -eq 0) {
            "Readiness artifacts are present enough for future design review. Step 42 still implements no bridge write."
        } else {
            "Readiness is blocked. Resolve blockers before adding any bridge write implementation."
        }
    }
    artifacts = $artifactSummary
    platform_status = [ordered]@{
        audit_status_ok = $platformAuditStatus.ok
        audit_status = if ($platformAuditStatus.ok) { $platformAuditStatus.value } else { $null }
        rehearsal_status_ok = $platformRehearsalStatus.ok
        rehearsal_status = if ($platformRehearsalStatus.ok) { $platformRehearsalStatus.value } else { $null }
        apply_preview_status_ok = $platformApplyPreviewStatus.ok
        apply_preview_status = if ($platformApplyPreviewStatus.ok) { $platformApplyPreviewStatus.value } else { $null }
    }
    bridge_status = [ordered]@{
        health_ok = $bridgeHealth.ok
        health = if ($bridgeHealth.ok) { $bridgeHealth.value } else { $null }
        error = $bridgeHealth.error
    }
    blockers = @($blockers)
    counts = [ordered]@{
        artifacts_found = $artifacts.Count
        blockers = $blockerCount
        reviews = $reviewCount
        apply_preview_rows = if ($artifactData.Contains("apply_preview")) { Count-Rows $artifactData.apply_preview.preview.preview_rows @("preview_rows") } else { 0 }
        rehearsal_rows = if ($artifactData.Contains("rehearsal")) { Count-Rows $artifactData.rehearsal.rehearsals @("rehearsals") } else { 0 }
        audit_plan_rows = if ($artifactData.Contains("audit_plan")) { Count-Rows $artifactData.audit_plan.plan_rows @("plan_rows") } else { 0 }
        rollback_rows = if ($artifactData.Contains("rollback_snapshot")) { Count-Rows $artifactData.rollback_snapshot.rollback_rows @("rollback_rows") } else { 0 }
    }
    next_recommended_actions = @(
        "Resolve blockers before adding any bridge routing write implementation.",
        "If only review items remain, review them manually before future write design.",
        "Keep bridge routing controls as the operational write path until explicit cutover.",
        "Do not call bridge POST endpoints until a separate guarded write implementation step exists."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_readiness.json"
$csvPath = Join-Path $OutputDir "phase19_bridge_routing_write_readiness_blockers.csv"
$artifactCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_readiness_artifacts.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_readiness.md"

$report | ConvertTo-Json -Depth 80 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$blockers | Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8
$artifactSummary | Select-Object key, folder, json_path, generated_at | Export-Csv -LiteralPath $artifactCsvPath -NoTypeInformation -Encoding UTF8

$blockerText = if (@($blockers).Count -gt 0) { (@($blockers) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }
$artifactText = ($artifactSummary | ForEach-Object { "- $($_.key): $($_.json_path)" }) -join "`n"

$md = @"
# Phase 19 Bridge Routing Write Readiness

Generated: $($report.generated_at)

## Safety

- Bridge routing write readiness only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Routing write endpoint implemented: false

## Readiness

- Go/no-go: $goNoGo
- Blockers: $blockerCount
- Review items: $reviewCount
- Can execute bridge write now: false

## Artifacts

$artifactText

## Blockers / review items

$blockerText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_write_readiness=$OutputDir | go_no_go=$goNoGo | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_write_readiness=$OutputDir | go_no_go=$goNoGo | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Readiness files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
