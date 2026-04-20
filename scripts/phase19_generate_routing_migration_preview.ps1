param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$RoutingSnapshotPath = "",
    [string]$OutputPath = "",
    [string]$MarkdownPath = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestRoutingSnapshot {
    $latest = Get-ChildItem -LiteralPath $BackupDir -File -Filter "phase19_routing_rules_snapshot_*.json" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No phase19_routing_rules_snapshot_*.json found in $BackupDir. Run Step 22 option 4 first."
    }

    return $latest.FullName
}

function Normalize-Mode {
    param([string]$Mode)
    if ([string]::IsNullOrWhiteSpace($Mode)) { return "manual" }
    $m = $Mode.Trim().ToLowerInvariant()
    if ($m -in @("auto", "automatic", "auto_attach")) { return "auto" }
    if ($m -in @("manual", "manual_review", "review")) { return "manual" }
    return $m
}

function Normalize-OwnerType {
    param([string]$OwnerType)
    if ([string]::IsNullOrWhiteSpace($OwnerType)) { return "unknown" }
    return $OwnerType.Trim().ToLowerInvariant()
}

function Risk-Level {
    param($Rule)
    $mode = Normalize-Mode ([string]$Rule.mode)
    $ownerType = Normalize-OwnerType ([string]$Rule.owner_type)
    $defaultContactCount = 0
    if ($Rule.default_contact_count -ne $null) { $defaultContactCount = [int]$Rule.default_contact_count }

    if ($mode -eq "auto" -and $defaultContactCount -lt 1) { return "high" }
    if ($mode -eq "auto" -and $ownerType -eq "unknown") { return "high" }
    if ($mode -eq "auto") { return "medium" }
    if ($ownerType -eq "property_manager") { return "medium" }
    return "low"
}

function Proposed-Action {
    param($Rule)
    $mode = Normalize-Mode ([string]$Rule.mode)
    $ownerType = Normalize-OwnerType ([string]$Rule.owner_type)
    $risk = Risk-Level $Rule

    if ($risk -eq "high") { return "manual_review_required" }
    if ($mode -eq "auto") { return "candidate_auto_attach_preference" }
    if ($ownerType -eq "property_manager") { return "candidate_property_manager_preference" }
    return "manual_review_preference"
}

if ([string]::IsNullOrWhiteSpace($RoutingSnapshotPath)) {
    $RoutingSnapshotPath = Get-LatestRoutingSnapshot
}

if (!(Test-Path -LiteralPath $RoutingSnapshotPath)) {
    throw "Routing snapshot not found: $RoutingSnapshotPath"
}

$snapshot = Get-Content -LiteralPath $RoutingSnapshotPath -Raw | ConvertFrom-Json
$rules = @()
if ($snapshot.routing_rules -and $snapshot.routing_rules.rules_preview) {
    $rules = @($snapshot.routing_rules.rules_preview)
}

$previewRows = @()
foreach ($rule in $rules) {
    $phone = [string]$rule.phone
    if ([string]::IsNullOrWhiteSpace($phone)) { continue }

    $risk = Risk-Level $rule
    $mode = Normalize-Mode ([string]$rule.mode)
    $ownerType = Normalize-OwnerType ([string]$rule.owner_type)
    $action = Proposed-Action $rule

    $previewRows += [ordered]@{
        phone = $phone
        source_mode = [string]$rule.mode
        proposed_mode = $mode
        source_owner_type = [string]$rule.owner_type
        proposed_owner_type = $ownerType
        source_label = [string]$rule.label
        default_contact_count = if ($rule.default_contact_count -ne $null) { [int]$rule.default_contact_count } else { 0 }
        batch_count = if ($rule.batch_count -ne $null) { [int]$rule.batch_count } else { 0 }
        risk_level = $risk
        proposed_action = $action
        migration_status = "preview_only"
        reason = if ($risk -eq "high") {
            "Auto/unknown routing cannot be migrated without operator approval and contact verification."
        } elseif ($mode -eq "auto") {
            "Auto rule candidate; requires approval before any platform preference write."
        } elseif ($ownerType -eq "property_manager") {
            "Property manager rule candidate; keep manual unless operator confirms PM property behavior."
        } else {
            "Manual-review routing preference candidate."
        }
        sample_batch_ids = $rule.sample_batch_ids
    }
}

$riskCounts = @{}
$actionCounts = @{}
foreach ($row in $previewRows) {
    if (!$riskCounts.ContainsKey($row.risk_level)) { $riskCounts[$row.risk_level] = 0 }
    if (!$actionCounts.ContainsKey($row.proposed_action)) { $actionCounts[$row.proposed_action] = 0 }
    $riskCounts[$row.risk_level] += 1
    $actionCounts[$row.proposed_action] += 1
}

$preview = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 23"
    purpose = "Dry-run bridge routing-rule migration preview"
    source_routing_snapshot = $RoutingSnapshotPath
    safety = [ordered]@{
        preview_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        live_write_enabled = $false
    }
    counts = [ordered]@{
        source_unique_rules = @($rules).Count
        preview_rows = @($previewRows).Count
        risk_counts = $riskCounts
        proposed_action_counts = $actionCounts
    }
    proposed_schema = [ordered]@{
        platform_entity = "RoutingPreference"
        key_fields = @("phone", "proposed_mode", "proposed_owner_type")
        approval_required = $true
        write_path = "not implemented in Step 23"
    }
    preview_rows = $previewRows
    next_recommended_actions = @(
        "Review high-risk and auto routing rows before implementing any platform write endpoint.",
        "Add a guarded platform-only approval table for RoutingPreference candidates.",
        "Add dry-run diff view comparing bridge routing rows to approved platform preferences.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputPath = Join-Path $BackupDir "phase19_routing_migration_preview_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownPath)) {
    $MarkdownPath = [System.IO.Path]::ChangeExtension($OutputPath, ".md")
}

$preview | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

$riskText = ($riskCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
$actionText = ($actionCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"

$md = @"
# Phase 19 Routing Migration Preview

Generated: $($preview.generated_at)

Source routing snapshot:

``````
$RoutingSnapshotPath
``````

## Safety

- Preview only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false

## Counts

- Source unique rules: $($preview.counts.source_unique_rules)
- Preview rows: $($preview.counts.preview_rows)

### Risk counts

$riskText

### Proposed action counts

$actionText

## Next recommended actions

$($preview.next_recommended_actions | ForEach-Object { "- $_" } | Out-String)
"@

$md | Set-Content -LiteralPath $MarkdownPath -Encoding UTF8

if ($previewRows.Count -ge 1) {
    Write-Host "PASS | routing_migration_preview=$OutputPath | rows=$($previewRows.Count) | preview_only=True"
} else {
    Write-Host "CHECK | routing_migration_preview=$OutputPath | rows=0 | source=$RoutingSnapshotPath"
}
