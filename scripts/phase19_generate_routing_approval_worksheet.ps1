param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$RoutingApprovalPacketDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestPacketDir {
    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter "phase19_routing_approval_packet_*" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No phase19_routing_approval_packet_* folder found in $BackupDir. Run Step 24 option 4 first."
    }

    return $latest.FullName
}

function Default-Decision {
    param($Row)

    $recommendation = ([string]$Row.approval_recommendation).ToLowerInvariant()
    $risk = ([string]$Row.risk_level).ToLowerInvariant()

    if ($recommendation -like "block_*" -or $risk -eq "high") {
        return "block_until_reviewed"
    }
    if ($recommendation -eq "review_before_auto_attach") {
        return "needs_contact_verification"
    }
    if ($recommendation -eq "review_property_manager_scope") {
        return "needs_scope_review"
    }
    return "candidate_keep_manual"
}

function Decision-Reason {
    param($Row)

    $decision = Default-Decision $Row
    if ($decision -eq "block_until_reviewed") {
        return "High-risk or incomplete routing candidate. Do not migrate without operator verification."
    }
    if ($decision -eq "needs_contact_verification") {
        return "Auto-attach candidate requires verified contact/property before any preference write."
    }
    if ($decision -eq "needs_scope_review") {
        return "Property-manager routing may affect multiple properties; scope must be reviewed."
    }
    return "Manual routing can remain manual until an explicit platform preference write workflow exists."
}

if ([string]::IsNullOrWhiteSpace($RoutingApprovalPacketDir)) {
    $RoutingApprovalPacketDir = Get-LatestPacketDir
}

if (!(Test-Path -LiteralPath $RoutingApprovalPacketDir)) {
    throw "Routing approval packet folder not found: $RoutingApprovalPacketDir"
}

$packetPath = Join-Path $RoutingApprovalPacketDir "phase19_routing_approval_packet.json"
if (!(Test-Path -LiteralPath $packetPath)) {
    throw "Routing approval packet JSON not found: $packetPath"
}

$packet = Get-Content -LiteralPath $packetPath -Raw | ConvertFrom-Json
$rows = @()
if ($packet.packet_rows) { $rows = @($packet.packet_rows) }

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_routing_approval_worksheet_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$worksheetRows = @()
foreach ($row in $rows) {
    $worksheetRows += [ordered]@{
        phone = [string]$row.phone
        proposed_mode = [string]$row.proposed_mode
        proposed_owner_type = [string]$row.proposed_owner_type
        source_label = [string]$row.source_label
        risk_level = [string]$row.risk_level
        proposed_action = [string]$row.proposed_action
        approval_recommendation = [string]$row.approval_recommendation
        default_decision = Default-Decision $row
        operator_decision = "unreviewed"
        operator_notes = ""
        decision_reason = Decision-Reason $row
        default_contact_count = if ($row.default_contact_count -ne $null) { [int]$row.default_contact_count } else { 0 }
        batch_count = if ($row.batch_count -ne $null) { [int]$row.batch_count } else { 0 }
        write_status = "worksheet_only_no_write_path"
        sample_batch_ids = $row.sample_batch_ids
    }
}

$decisionCounts = @{}
$riskCounts = @{}
foreach ($row in $worksheetRows) {
    if (!$decisionCounts.ContainsKey($row.default_decision)) { $decisionCounts[$row.default_decision] = 0 }
    if (!$riskCounts.ContainsKey($row.risk_level)) { $riskCounts[$row.risk_level] = 0 }
    $decisionCounts[$row.default_decision] += 1
    $riskCounts[$row.risk_level] += 1
}

$worksheet = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 25"
    purpose = "Editable operator worksheet for routing approval packet review"
    source_routing_approval_packet = $packetPath
    safety = [ordered]@{
        worksheet_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        live_write_enabled = $false
        routing_write_endpoint_implemented = $false
    }
    allowed_operator_decisions = @(
        "unreviewed",
        "candidate_keep_manual",
        "needs_contact_verification",
        "needs_scope_review",
        "block_until_reviewed",
        "approved_for_future_dry_run_only",
        "skip"
    )
    counts = [ordered]@{
        source_packet_rows = @($rows).Count
        worksheet_rows = @($worksheetRows).Count
        default_decision_counts = $decisionCounts
        risk_counts = $riskCounts
    }
    worksheet_rows = $worksheetRows
    next_recommended_actions = @(
        "Review the worksheet manually before any platform DB model is introduced.",
        "Use the CSV as the operator handoff artifact; do not import it as live preferences yet.",
        "Add a future dry-run-only import checker before creating any RoutingPreference table rows.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_routing_approval_worksheet.json"
$csvPath = Join-Path $OutputDir "phase19_routing_approval_worksheet.csv"
$mdPath = Join-Path $OutputDir "phase19_routing_approval_worksheet.md"

$worksheet | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$worksheetRows |
    Select-Object phone, proposed_mode, proposed_owner_type, risk_level, proposed_action, approval_recommendation, default_decision, operator_decision, operator_notes, batch_count, default_contact_count, write_status, decision_reason |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$decisionText = ($decisionCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
$riskText = ($riskCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"

$md = @"
# Phase 19 Routing Approval Worksheet

Generated: $($worksheet.generated_at)

Source packet:

``````
$packetPath
``````

## Safety

- Worksheet only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Routing write endpoint implemented: false

## Counts

- Source packet rows: $($worksheet.counts.source_packet_rows)
- Worksheet rows: $($worksheet.counts.worksheet_rows)

### Default decision counts

$decisionText

### Risk counts

$riskText

## Allowed operator decisions

$($worksheet.allowed_operator_decisions | ForEach-Object { "- $_" } | Out-String)

## Next recommended actions

$($worksheet.next_recommended_actions | ForEach-Object { "- $_" } | Out-String)
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($worksheetRows.Count -ge 1) {
    Write-Host "PASS | routing_approval_worksheet=$OutputDir | rows=$($worksheetRows.Count) | worksheet_only=True"
} else {
    Write-Host "CHECK | routing_approval_worksheet=$OutputDir | rows=0 | source=$packetPath"
}

Write-Host ""
Write-Host "Worksheet files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
