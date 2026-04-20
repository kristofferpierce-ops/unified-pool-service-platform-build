param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$RoutingMigrationPreviewPath = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestPreview {
    $latest = Get-ChildItem -LiteralPath $BackupDir -File -Filter "phase19_routing_migration_preview_*.json" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No phase19_routing_migration_preview_*.json found in $BackupDir. Run Step 23 option 4 first."
    }

    return $latest.FullName
}

function Approval-Recommendation {
    param($Row)

    $risk = ([string]$Row.risk_level).ToLowerInvariant()
    $action = ([string]$Row.proposed_action).ToLowerInvariant()
    $contactCount = 0
    if ($Row.default_contact_count -ne $null) { $contactCount = [int]$Row.default_contact_count }

    if ($risk -eq "high") { return "block_until_operator_verifies_contact" }
    if ($action -eq "candidate_auto_attach_preference" -and $contactCount -lt 1) { return "block_until_contact_is_selected" }
    if ($action -eq "candidate_auto_attach_preference") { return "review_before_auto_attach" }
    if ($action -eq "candidate_property_manager_preference") { return "review_property_manager_scope" }
    return "eligible_for_manual_preference"
}

function Approval-Risk-Reason {
    param($Row)

    $risk = ([string]$Row.risk_level).ToLowerInvariant()
    $mode = ([string]$Row.proposed_mode).ToLowerInvariant()
    $owner = ([string]$Row.proposed_owner_type).ToLowerInvariant()
    $contactCount = 0
    if ($Row.default_contact_count -ne $null) { $contactCount = [int]$Row.default_contact_count }

    if ($risk -eq "high") {
        return "High-risk row must not be migrated until an operator verifies the target contact/property."
    }
    if ($mode -eq "auto" -and $contactCount -lt 1) {
        return "Auto routing without a default contact cannot become an auto-attach preference."
    }
    if ($owner -eq "property_manager") {
        return "Property-manager routing can affect multiple properties; scope must be reviewed."
    }
    return "Manual routing preference candidate; low operational risk."
}

if ([string]::IsNullOrWhiteSpace($RoutingMigrationPreviewPath)) {
    $RoutingMigrationPreviewPath = Get-LatestPreview
}

if (!(Test-Path -LiteralPath $RoutingMigrationPreviewPath)) {
    throw "Routing migration preview not found: $RoutingMigrationPreviewPath"
}

$preview = Get-Content -LiteralPath $RoutingMigrationPreviewPath -Raw | ConvertFrom-Json
$rows = @()
if ($preview.preview_rows) { $rows = @($preview.preview_rows) }

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_routing_approval_packet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$packetRows = @()
foreach ($row in $rows) {
    $packetRows += [ordered]@{
        phone = [string]$row.phone
        source_mode = [string]$row.source_mode
        proposed_mode = [string]$row.proposed_mode
        source_owner_type = [string]$row.source_owner_type
        proposed_owner_type = [string]$row.proposed_owner_type
        source_label = [string]$row.source_label
        default_contact_count = if ($row.default_contact_count -ne $null) { [int]$row.default_contact_count } else { 0 }
        batch_count = if ($row.batch_count -ne $null) { [int]$row.batch_count } else { 0 }
        risk_level = [string]$row.risk_level
        proposed_action = [string]$row.proposed_action
        approval_recommendation = Approval-Recommendation $row
        approval_reason = Approval-Risk-Reason $row
        operator_decision = "unreviewed"
        operator_notes = ""
        write_status = "not_implemented_preview_only"
        sample_batch_ids = $row.sample_batch_ids
    }
}

$riskCounts = @{}
$recommendationCounts = @{}
foreach ($row in $packetRows) {
    if (!$riskCounts.ContainsKey($row.risk_level)) { $riskCounts[$row.risk_level] = 0 }
    if (!$recommendationCounts.ContainsKey($row.approval_recommendation)) { $recommendationCounts[$row.approval_recommendation] = 0 }
    $riskCounts[$row.risk_level] += 1
    $recommendationCounts[$row.approval_recommendation] += 1
}

$packet = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 24"
    purpose = "Operator review packet for dry-run bridge routing migration candidates"
    source_routing_migration_preview = $RoutingMigrationPreviewPath
    safety = [ordered]@{
        packet_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        live_write_enabled = $false
        routing_write_endpoint_implemented = $false
    }
    counts = [ordered]@{
        source_preview_rows = @($rows).Count
        packet_rows = @($packetRows).Count
        risk_counts = $riskCounts
        approval_recommendation_counts = $recommendationCounts
    }
    review_instructions = @(
        "Review high-risk rows first.",
        "Do not approve auto-attach rows without a verified target contact/property.",
        "Keep property-manager rows manual until the scope of managed properties is known.",
        "This packet is not a write plan; it is a review artifact only."
    )
    packet_rows = $packetRows
}

$jsonPath = Join-Path $OutputDir "phase19_routing_approval_packet.json"
$csvPath = Join-Path $OutputDir "phase19_routing_approval_packet.csv"
$mdPath = Join-Path $OutputDir "phase19_routing_approval_packet.md"

$packet | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$packetRows |
    Select-Object phone, proposed_mode, proposed_owner_type, risk_level, proposed_action, approval_recommendation, operator_decision, batch_count, default_contact_count, approval_reason |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$riskText = ($riskCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
$recommendationText = ($recommendationCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"

$md = @"
# Phase 19 Routing Approval Packet

Generated: $($packet.generated_at)

Source preview:

``````
$RoutingMigrationPreviewPath
``````

## Safety

- Packet only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Routing write endpoint implemented: false

## Counts

- Source preview rows: $($packet.counts.source_preview_rows)
- Packet rows: $($packet.counts.packet_rows)

### Risk counts

$riskText

### Approval recommendation counts

$recommendationText

## Review instructions

$($packet.review_instructions | ForEach-Object { "- $_" } | Out-String)
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($packetRows.Count -ge 1) {
    Write-Host "PASS | routing_approval_packet=$OutputDir | rows=$($packetRows.Count) | packet_only=True"
} else {
    Write-Host "CHECK | routing_approval_packet=$OutputDir | rows=0 | source=$RoutingMigrationPreviewPath"
}

Write-Host ""
Write-Host "Packet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
