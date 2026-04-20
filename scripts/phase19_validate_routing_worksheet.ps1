param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$WorksheetCsvPath = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

$AllowedDecisions = @(
    "unreviewed",
    "candidate_keep_manual",
    "needs_contact_verification",
    "needs_scope_review",
    "block_until_reviewed",
    "approved_for_future_dry_run_only",
    "skip"
)

function Get-LatestWorksheetCsv {
    $latestDir = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter "phase19_routing_approval_worksheet_*" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latestDir) {
        throw "No phase19_routing_approval_worksheet_* folder found in $BackupDir. Run Step 25 option 4 first."
    }

    $csv = Join-Path $latestDir.FullName "phase19_routing_approval_worksheet.csv"
    if (!(Test-Path -LiteralPath $csv)) {
        throw "Worksheet CSV missing in latest worksheet folder: $csv"
    }

    return $csv
}

function Is-Blank {
    param($Value)
    return [string]::IsNullOrWhiteSpace([string]$Value)
}

function Add-Issue {
    param(
        [System.Collections.ArrayList]$Issues,
        [int]$RowNumber,
        [string]$Severity,
        [string]$Code,
        [string]$Message,
        $Row
    )

    [void]$Issues.Add([ordered]@{
        row_number = $RowNumber
        severity = $Severity
        code = $Code
        message = $Message
        phone = [string]$Row.phone
        operator_decision = [string]$Row.operator_decision
        risk_level = [string]$Row.risk_level
        proposed_action = [string]$Row.proposed_action
    })
}

if ([string]::IsNullOrWhiteSpace($WorksheetCsvPath)) {
    $WorksheetCsvPath = Get-LatestWorksheetCsv
}

if (!(Test-Path -LiteralPath $WorksheetCsvPath)) {
    throw "Worksheet CSV not found: $WorksheetCsvPath"
}

$rows = @(Import-Csv -LiteralPath $WorksheetCsvPath)

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_routing_worksheet_validation_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$issues = New-Object System.Collections.ArrayList
$validatedRows = @()
$rowNumber = 1

foreach ($row in $rows) {
    $decision = ([string]$row.operator_decision).Trim()
    $risk = ([string]$row.risk_level).Trim().ToLowerInvariant()
    $action = ([string]$row.proposed_action).Trim().ToLowerInvariant()
    $notes = [string]$row.operator_notes
    $contactCount = 0
    if ($row.default_contact_count -ne $null -and "$($row.default_contact_count)" -match "^\d+$") {
        $contactCount = [int]$row.default_contact_count
    }

    if (Is-Blank $row.phone) {
        Add-Issue $issues $rowNumber "error" "missing_phone" "Worksheet row is missing phone." $row
    }

    if ($AllowedDecisions -notcontains $decision) {
        Add-Issue $issues $rowNumber "error" "invalid_operator_decision" "Operator decision '$decision' is not allowed." $row
    }

    if ($risk -eq "high" -and $decision -eq "approved_for_future_dry_run_only") {
        Add-Issue $issues $rowNumber "error" "high_risk_approved" "High-risk routing rows cannot be approved without a future explicit override workflow." $row
    }

    if ($action -eq "candidate_auto_attach_preference" -and $contactCount -lt 1 -and $decision -eq "approved_for_future_dry_run_only") {
        Add-Issue $issues $rowNumber "error" "auto_attach_without_contact" "Auto-attach approval requires at least one verified default contact." $row
    }

    if ($decision -in @("needs_contact_verification", "needs_scope_review", "block_until_reviewed") -and [string]::IsNullOrWhiteSpace($notes)) {
        Add-Issue $issues $rowNumber "warning" "review_decision_missing_notes" "Review/block decisions should include operator notes." $row
    }

    if ($decision -eq "unreviewed") {
        Add-Issue $issues $rowNumber "info" "row_unreviewed" "Row has not been reviewed yet." $row
    }

    $validatedRows += [ordered]@{
        row_number = $rowNumber
        phone = [string]$row.phone
        risk_level = [string]$row.risk_level
        proposed_action = [string]$row.proposed_action
        operator_decision = $decision
        operator_notes_present = -not [string]::IsNullOrWhiteSpace($notes)
        default_contact_count = $contactCount
        validation_status = "checked"
    }

    $rowNumber += 1
}

$errorCount = @($issues | Where-Object { $_.severity -eq "error" }).Count
$warningCount = @($issues | Where-Object { $_.severity -eq "warning" }).Count
$infoCount = @($issues | Where-Object { $_.severity -eq "info" }).Count

$decisionCounts = @{}
foreach ($row in $rows) {
    $decision = ([string]$row.operator_decision).Trim()
    if (!$decisionCounts.ContainsKey($decision)) { $decisionCounts[$decision] = 0 }
    $decisionCounts[$decision] += 1
}

$validation = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 26"
    purpose = "Dry-run validation report for routing approval worksheet"
    source_worksheet_csv = $WorksheetCsvPath
    safety = [ordered]@{
        validation_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        live_write_enabled = $false
        routing_write_endpoint_implemented = $false
    }
    counts = [ordered]@{
        rows_checked = @($rows).Count
        errors = $errorCount
        warnings = $warningCount
        info = $infoCount
        operator_decision_counts = $decisionCounts
    }
    allowed_operator_decisions = $AllowedDecisions
    issues = @($issues)
    validated_rows = $validatedRows
    next_recommended_actions = @(
        "Resolve validation errors before any future dry-run import workflow.",
        "Add notes to review/block rows so decisions are auditable.",
        "Keep this validation report as a preflight artifact; it is not a write plan.",
        "Implement a future platform-only dry-run import checker before adding any routing preference write endpoint."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_routing_worksheet_validation.json"
$issuesCsvPath = Join-Path $OutputDir "phase19_routing_worksheet_validation_issues.csv"
$rowsCsvPath = Join-Path $OutputDir "phase19_routing_worksheet_validation_rows.csv"
$mdPath = Join-Path $OutputDir "phase19_routing_worksheet_validation.md"

$validation | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8
$validatedRows | Export-Csv -LiteralPath $rowsCsvPath -NoTypeInformation -Encoding UTF8

$decisionText = ($decisionCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"

$md = @"
# Phase 19 Routing Worksheet Validation

Generated: $($validation.generated_at)

Source worksheet:

``````
$WorksheetCsvPath
``````

## Safety

- Validation only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Routing write endpoint implemented: false

## Counts

- Rows checked: $($validation.counts.rows_checked)
- Errors: $errorCount
- Warnings: $warningCount
- Info: $infoCount

## Operator decision counts

$decisionText

## Next recommended actions

$($validation.next_recommended_actions | ForEach-Object { "- $_" } | Out-String)
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($errorCount -eq 0) {
    Write-Host "PASS | routing_worksheet_validation=$OutputDir | rows=$($rows.Count) | errors=0 | validation_only=True"
} else {
    Write-Host "CHECK | routing_worksheet_validation=$OutputDir | rows=$($rows.Count) | errors=$errorCount | warnings=$warningCount"
}

Write-Host ""
Write-Host "Validation files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
