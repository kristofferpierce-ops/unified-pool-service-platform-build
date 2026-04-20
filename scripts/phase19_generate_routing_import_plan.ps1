param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$ValidationDir = "",
    [string]$WorksheetCsvPath = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

$AllowedImportDecisions = @(
    "candidate_keep_manual",
    "approved_for_future_dry_run_only",
    "skip"
)

function Get-LatestValidationDir {
    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter "phase19_routing_worksheet_validation_*" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No phase19_routing_worksheet_validation_* folder found in $BackupDir. Run Step 26 option 4 first."
    }

    return $latest.FullName
}

function Get-LatestWorksheetCsv {
    $latestDir = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter "phase19_routing_approval_worksheet_*" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latestDir) {
        throw "No phase19_routing_approval_worksheet_* folder found in $BackupDir. Run Step 25 option 4 first."
    }

    $csv = Join-Path $latestDir.FullName "phase19_routing_approval_worksheet.csv"
    if (!(Test-Path -LiteralPath $csv)) {
        throw "Worksheet CSV missing: $csv"
    }

    return $csv
}

function Normalize-Decision {
    param([string]$Decision)
    if ([string]::IsNullOrWhiteSpace($Decision)) { return "unreviewed" }
    return $Decision.Trim()
}

function Normalize-Phone {
    param([string]$Phone)
    if ([string]::IsNullOrWhiteSpace($Phone)) { return "" }
    return ($Phone -replace "[^\d+]", "").Trim()
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

function Import-Eligibility {
    param($Row)

    $decision = Normalize-Decision ([string]$Row.operator_decision)
    $risk = ([string]$Row.risk_level).Trim().ToLowerInvariant()
    $phone = Normalize-Phone ([string]$Row.phone)
    $contactCount = 0
    if ($Row.default_contact_count -ne $null -and "$($Row.default_contact_count)" -match "^\d+$") {
        $contactCount = [int]$Row.default_contact_count
    }

    if ([string]::IsNullOrWhiteSpace($phone)) {
        return @{ eligible = $false; reason = "missing_phone" }
    }

    if ($decision -eq "skip") {
        return @{ eligible = $false; reason = "operator_skipped" }
    }

    if ($decision -eq "unreviewed") {
        return @{ eligible = $false; reason = "operator_unreviewed" }
    }

    if ($decision -in @("needs_contact_verification", "needs_scope_review", "block_until_reviewed")) {
        return @{ eligible = $false; reason = "operator_review_required" }
    }

    if ($risk -eq "high" -and $decision -eq "approved_for_future_dry_run_only") {
        return @{ eligible = $false; reason = "high_risk_not_importable" }
    }

    if ($decision -eq "approved_for_future_dry_run_only" -and $Row.proposed_action -eq "candidate_auto_attach_preference" -and $contactCount -lt 1) {
        return @{ eligible = $false; reason = "auto_attach_missing_contact" }
    }

    if ($AllowedImportDecisions -notcontains $decision) {
        return @{ eligible = $false; reason = "decision_not_importable" }
    }

    return @{ eligible = $true; reason = "eligible_for_future_dry_run_import" }
}

if ([string]::IsNullOrWhiteSpace($ValidationDir)) {
    $ValidationDir = Get-LatestValidationDir
}

if (!(Test-Path -LiteralPath $ValidationDir)) {
    throw "Validation folder not found: $ValidationDir"
}

$validationPath = Join-Path $ValidationDir "phase19_routing_worksheet_validation.json"
if (!(Test-Path -LiteralPath $validationPath)) {
    throw "Validation JSON not found: $validationPath"
}

if ([string]::IsNullOrWhiteSpace($WorksheetCsvPath)) {
    $WorksheetCsvPath = Get-LatestWorksheetCsv
}

if (!(Test-Path -LiteralPath $WorksheetCsvPath)) {
    throw "Worksheet CSV not found: $WorksheetCsvPath"
}

$validation = Get-Content -LiteralPath $validationPath -Raw | ConvertFrom-Json
$worksheetRows = @(Import-Csv -LiteralPath $WorksheetCsvPath)

$errorCount = 0
if ($validation.counts -and $validation.counts.errors -ne $null) {
    $errorCount = [int]$validation.counts.errors
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_routing_import_plan_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$planRows = @()
foreach ($row in $worksheetRows) {
    $decision = Normalize-Decision ([string]$row.operator_decision)
    $eligibility = Import-Eligibility $row
    $phone = Normalize-Phone ([string]$row.phone)
    $proposedMode = Normalize-Mode ([string]$row.proposed_mode)
    $proposedOwner = Normalize-OwnerType ([string]$row.proposed_owner_type)
    $preferenceKey = "$phone|$proposedMode|$proposedOwner"

    $planRows += [ordered]@{
        preference_key = $preferenceKey
        phone = $phone
        proposed_mode = $proposedMode
        proposed_owner_type = $proposedOwner
        risk_level = [string]$row.risk_level
        proposed_action = [string]$row.proposed_action
        operator_decision = $decision
        operator_notes_present = -not [string]::IsNullOrWhiteSpace([string]$row.operator_notes)
        eligible_for_future_dry_run_import = [bool]$eligibility.eligible
        import_blocker = [string]$eligibility.reason
        write_status = "import_plan_only_no_db_write"
        source_batch_count = if ($row.batch_count -ne $null -and "$($row.batch_count)" -match "^\d+$") { [int]$row.batch_count } else { 0 }
        default_contact_count = if ($row.default_contact_count -ne $null -and "$($row.default_contact_count)" -match "^\d+$") { [int]$row.default_contact_count } else { 0 }
    }
}

$eligibleCount = @($planRows | Where-Object { $_.eligible_for_future_dry_run_import -eq $true }).Count
$blockedCount = @($planRows | Where-Object { $_.eligible_for_future_dry_run_import -ne $true }).Count

$blockerCounts = @{}
$decisionCounts = @{}
foreach ($row in $planRows) {
    if (!$blockerCounts.ContainsKey($row.import_blocker)) { $blockerCounts[$row.import_blocker] = 0 }
    if (!$decisionCounts.ContainsKey($row.operator_decision)) { $decisionCounts[$row.operator_decision] = 0 }
    $blockerCounts[$row.import_blocker] += 1
    $decisionCounts[$row.operator_decision] += 1
}

$plan = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 27"
    purpose = "Dry-run routing preference import plan from validated operator worksheet"
    source_validation_report = $validationPath
    source_worksheet_csv = $WorksheetCsvPath
    safety = [ordered]@{
        import_plan_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        live_write_enabled = $false
        routing_write_endpoint_implemented = $false
    }
    validation_gate = [ordered]@{
        validation_errors = $errorCount
        can_continue_to_future_import_checker = ($errorCount -eq 0)
        import_plan_generated_even_if_blocked = $true
    }
    counts = [ordered]@{
        worksheet_rows = @($worksheetRows).Count
        import_plan_rows = @($planRows).Count
        eligible_for_future_dry_run_import = $eligibleCount
        blocked_or_review_required = $blockedCount
        blocker_counts = $blockerCounts
        operator_decision_counts = $decisionCounts
    }
    proposed_schema = [ordered]@{
        entity = "RoutingPreferenceCandidate"
        write_table = "not implemented in Step 27"
        unique_key = "phone + proposed_mode + proposed_owner_type"
        requires_operator_approval = $true
    }
    import_plan_rows = $planRows
    next_recommended_actions = @(
        "Resolve all validation errors and review import blockers before any future import checker.",
        "Add a platform-only RoutingPreferenceCandidate table only after this import plan is reviewed.",
        "Keep the first candidate import as dry-run-only and reversible.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_routing_import_plan.json"
$csvPath = Join-Path $OutputDir "phase19_routing_import_plan.csv"
$mdPath = Join-Path $OutputDir "phase19_routing_import_plan.md"

$plan | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$planRows |
    Select-Object preference_key, phone, proposed_mode, proposed_owner_type, risk_level, proposed_action, operator_decision, eligible_for_future_dry_run_import, import_blocker, write_status, source_batch_count, default_contact_count |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$blockerText = ($blockerCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
$decisionText = ($decisionCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"

$md = @"
# Phase 19 Routing Import Plan

Generated: $($plan.generated_at)

Source validation:

``````
$validationPath
``````

Source worksheet:

``````
$WorksheetCsvPath
``````

## Safety

- Import plan only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Routing write endpoint implemented: false

## Validation gate

- Validation errors: $errorCount
- Can continue to future import checker: $($errorCount -eq 0)

## Counts

- Worksheet rows: $($plan.counts.worksheet_rows)
- Import plan rows: $($plan.counts.import_plan_rows)
- Eligible for future dry-run import: $eligibleCount
- Blocked or review required: $blockedCount

### Blocker counts

$blockerText

### Operator decision counts

$decisionText

## Next recommended actions

$($plan.next_recommended_actions | ForEach-Object { "- $_" } | Out-String)
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($errorCount -eq 0) {
    Write-Host "PASS | routing_import_plan=$OutputDir | rows=$($planRows.Count) | eligible=$eligibleCount | import_plan_only=True"
} else {
    Write-Host "CHECK | routing_import_plan=$OutputDir | rows=$($planRows.Count) | eligible=$eligibleCount | validation_errors=$errorCount"
}

Write-Host ""
Write-Host "Import plan files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
