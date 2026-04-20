param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$RoutingImportPlanDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

$AllowedModes = @("manual", "auto")
$AllowedOwnerTypes = @("unknown", "homeowner", "property_manager")
$AllowedWriteStatus = @("import_plan_only_no_db_write")
$AllowedBlockers = @(
    "eligible_for_future_dry_run_import",
    "missing_phone",
    "operator_skipped",
    "operator_unreviewed",
    "operator_review_required",
    "high_risk_not_importable",
    "auto_attach_missing_contact",
    "decision_not_importable"
)

function Get-LatestPlanDir {
    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter "phase19_routing_import_plan_*" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No phase19_routing_import_plan_* folder found in $BackupDir. Run Step 27 option 4 first."
    }

    return $latest.FullName
}

function Normalize-String {
    param($Value)
    if ($null -eq $Value) { return "" }
    return ([string]$Value).Trim()
}

function Add-Issue {
    param(
        [System.Collections.ArrayList]$Issues,
        [string]$Severity,
        [string]$Code,
        [string]$Message,
        [string]$PreferenceKey,
        [string]$Phone,
        [string]$ProposedMode,
        [string]$ProposedOwnerType
    )

    [void]$Issues.Add([ordered]@{
        severity = $Severity
        code = $Code
        message = $Message
        preference_key = $PreferenceKey
        phone = $Phone
        proposed_mode = $ProposedMode
        proposed_owner_type = $ProposedOwnerType
    })
}

function Is-Phone-Valid {
    param([string]$Phone)
    if ([string]::IsNullOrWhiteSpace($Phone)) { return $false }
    $digits = ($Phone -replace "\D", "")
    return $digits.Length -ge 10
}

if ([string]::IsNullOrWhiteSpace($RoutingImportPlanDir)) {
    $RoutingImportPlanDir = Get-LatestPlanDir
}

if (!(Test-Path -LiteralPath $RoutingImportPlanDir)) {
    throw "Routing import plan folder not found: $RoutingImportPlanDir"
}

$planPath = Join-Path $RoutingImportPlanDir "phase19_routing_import_plan.json"
if (!(Test-Path -LiteralPath $planPath)) {
    throw "Routing import plan JSON not found: $planPath"
}

$plan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
$rows = @()
if ($plan.import_plan_rows) { $rows = @($plan.import_plan_rows) }

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_routing_import_plan_validation_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$issues = New-Object System.Collections.ArrayList
$rowReports = @()
$seenEligibleKeys = @{}
$seenAllKeys = @{}

$safety = $plan.safety
if (!$safety -or $safety.import_plan_only -ne $true) {
    Add-Issue $issues "error" "missing_import_plan_only_flag" "Import plan is missing safety.import_plan_only=true." "" "" "" ""
}
if ($safety -and $safety.platform_db_mutation_performed -eq $true) {
    Add-Issue $issues "error" "platform_mutation_flag_true" "Import plan claims platform DB mutation occurred." "" "" "" ""
}
if ($safety -and $safety.bridge_mutation_performed -eq $true) {
    Add-Issue $issues "error" "bridge_mutation_flag_true" "Import plan claims bridge mutation occurred." "" "" "" ""
}
if ($safety -and $safety.bridge_post_called -eq $true) {
    Add-Issue $issues "error" "bridge_post_called_flag_true" "Import plan claims a bridge POST was called." "" "" "" ""
}
if ($safety -and $safety.lacrm_call_performed -eq $true) {
    Add-Issue $issues "error" "lacrm_call_flag_true" "Import plan claims a LACRM call was performed." "" "" "" ""
}
if ($safety -and $safety.routing_write_endpoint_implemented -eq $true) {
    Add-Issue $issues "error" "routing_write_endpoint_flag_true" "Routing write endpoint should not exist yet in Step 28." "" "" "" ""
}

$rowNumber = 1
foreach ($row in $rows) {
    $preferenceKey = Normalize-String $row.preference_key
    $phone = Normalize-String $row.phone
    $mode = (Normalize-String $row.proposed_mode).ToLowerInvariant()
    $owner = (Normalize-String $row.proposed_owner_type).ToLowerInvariant()
    $risk = (Normalize-String $row.risk_level).ToLowerInvariant()
    $action = Normalize-String $row.proposed_action
    $decision = Normalize-String $row.operator_decision
    $eligible = [bool]$row.eligible_for_future_dry_run_import
    $blocker = Normalize-String $row.import_blocker
    $writeStatus = Normalize-String $row.write_status
    $contactCount = 0
    if ($row.default_contact_count -ne $null -and "$($row.default_contact_count)" -match "^\d+$") {
        $contactCount = [int]$row.default_contact_count
    }

    if ([string]::IsNullOrWhiteSpace($preferenceKey)) {
        Add-Issue $issues "error" "missing_preference_key" "Import plan row is missing preference_key." $preferenceKey $phone $mode $owner
    } else {
        if (!$seenAllKeys.ContainsKey($preferenceKey)) { $seenAllKeys[$preferenceKey] = 0 }
        $seenAllKeys[$preferenceKey] += 1
    }

    if (!(Is-Phone-Valid $phone)) {
        Add-Issue $issues "error" "invalid_phone" "Phone is blank or does not contain at least 10 digits." $preferenceKey $phone $mode $owner
    }

    if ($AllowedModes -notcontains $mode) {
        Add-Issue $issues "error" "invalid_proposed_mode" "Proposed mode '$mode' is not allowed." $preferenceKey $phone $mode $owner
    }

    if ($AllowedOwnerTypes -notcontains $owner) {
        Add-Issue $issues "error" "invalid_proposed_owner_type" "Proposed owner type '$owner' is not allowed." $preferenceKey $phone $mode $owner
    }

    if ($AllowedWriteStatus -notcontains $writeStatus) {
        Add-Issue $issues "error" "unexpected_write_status" "Write status '$writeStatus' is not allowed for an import plan." $preferenceKey $phone $mode $owner
    }

    if ($AllowedBlockers -notcontains $blocker) {
        Add-Issue $issues "error" "invalid_import_blocker" "Import blocker '$blocker' is not recognized." $preferenceKey $phone $mode $owner
    }

    if ($eligible -and $blocker -ne "eligible_for_future_dry_run_import") {
        Add-Issue $issues "error" "eligible_with_blocker" "Eligible row has a blocker other than eligible_for_future_dry_run_import." $preferenceKey $phone $mode $owner
    }

    if (!$eligible -and $blocker -eq "eligible_for_future_dry_run_import") {
        Add-Issue $issues "error" "blocked_without_blocker" "Blocked row has eligible_for_future_dry_run_import as the blocker." $preferenceKey $phone $mode $owner
    }

    if ($eligible -and $decision -eq "unreviewed") {
        Add-Issue $issues "error" "eligible_unreviewed" "Unreviewed row cannot be eligible for future dry-run import." $preferenceKey $phone $mode $owner
    }

    if ($eligible -and $risk -eq "high") {
        Add-Issue $issues "error" "eligible_high_risk" "High-risk row cannot be eligible for future dry-run import." $preferenceKey $phone $mode $owner
    }

    if ($eligible -and $action -eq "candidate_auto_attach_preference" -and $contactCount -lt 1) {
        Add-Issue $issues "error" "eligible_auto_attach_without_contact" "Auto-attach row cannot be eligible without a verified default contact." $preferenceKey $phone $mode $owner
    }

    if ($eligible) {
        if (!$seenEligibleKeys.ContainsKey($preferenceKey)) {
            $seenEligibleKeys[$preferenceKey] = 0
        }
        $seenEligibleKeys[$preferenceKey] += 1
    }

    $rowReports += [ordered]@{
        row_number = $rowNumber
        preference_key = $preferenceKey
        phone = $phone
        proposed_mode = $mode
        proposed_owner_type = $owner
        operator_decision = $decision
        eligible_for_future_dry_run_import = $eligible
        import_blocker = $blocker
        risk_level = $risk
        proposed_action = $action
        validation_status = "checked"
    }

    $rowNumber += 1
}

foreach ($key in $seenEligibleKeys.Keys) {
    if ($seenEligibleKeys[$key] -gt 1) {
        Add-Issue $issues "error" "duplicate_eligible_preference_key" "Eligible preference_key appears more than once." $key "" "" ""
    }
}

foreach ($key in $seenAllKeys.Keys) {
    if ($seenAllKeys[$key] -gt 1) {
        Add-Issue $issues "warning" "duplicate_plan_preference_key" "Preference key appears multiple times in the plan; verify dedupe behavior before future import." $key "" "" ""
    }
}

$errorCount = @($issues | Where-Object { $_.severity -eq "error" }).Count
$warningCount = @($issues | Where-Object { $_.severity -eq "warning" }).Count
$infoCount = @($issues | Where-Object { $_.severity -eq "info" }).Count
$eligibleCount = @($rowReports | Where-Object { $_.eligible_for_future_dry_run_import -eq $true }).Count
$blockedCount = @($rowReports | Where-Object { $_.eligible_for_future_dry_run_import -ne $true }).Count

$blockerCounts = @{}
foreach ($row in $rowReports) {
    if (!$blockerCounts.ContainsKey($row.import_blocker)) { $blockerCounts[$row.import_blocker] = 0 }
    $blockerCounts[$row.import_blocker] += 1
}

$validation = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 28"
    purpose = "Pre-persistence validation for routing import plan"
    source_routing_import_plan = $planPath
    safety = [ordered]@{
        import_plan_validation_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        live_write_enabled = $false
        routing_write_endpoint_implemented = $false
    }
    validation_gate = [ordered]@{
        errors = $errorCount
        warnings = $warningCount
        can_create_future_candidate_importer = ($errorCount -eq 0)
        can_create_platform_candidate_rows = $false
        reason = if ($errorCount -eq 0) {
            "Import plan passed pre-persistence validation. Next step may add schema only; writes remain disabled."
        } else {
            "Import plan has validation errors. Resolve before schema/import work."
        }
    }
    counts = [ordered]@{
        plan_rows = @($rows).Count
        row_reports = @($rowReports).Count
        eligible_for_future_dry_run_import = $eligibleCount
        blocked_or_review_required = $blockedCount
        errors = $errorCount
        warnings = $warningCount
        info = $infoCount
        blocker_counts = $blockerCounts
    }
    issues = @($issues)
    row_reports = $rowReports
    next_recommended_actions = @(
        "If errors exist, fix the worksheet/import plan and regenerate this validation.",
        "If errors are zero, add platform schema in the next step but keep imports disabled.",
        "Do not create RoutingPreferenceCandidate rows until a separate guarded import step exists.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_routing_import_plan_validation.json"
$issuesCsvPath = Join-Path $OutputDir "phase19_routing_import_plan_validation_issues.csv"
$rowsCsvPath = Join-Path $OutputDir "phase19_routing_import_plan_validation_rows.csv"
$mdPath = Join-Path $OutputDir "phase19_routing_import_plan_validation.md"

$validation | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8
$rowReports | Export-Csv -LiteralPath $rowsCsvPath -NoTypeInformation -Encoding UTF8

$blockerText = ($blockerCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"

$md = @"
# Phase 19 Routing Import Plan Validation

Generated: $($validation.generated_at)

Source import plan:

``````
$planPath
``````

## Safety

- Import plan validation only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Routing write endpoint implemented: false

## Gate

- Errors: $errorCount
- Warnings: $warningCount
- Can create future candidate importer: $($errorCount -eq 0)
- Can create platform candidate rows now: false

## Counts

- Plan rows: $($validation.counts.plan_rows)
- Eligible for future dry-run import: $eligibleCount
- Blocked or review required: $blockedCount

### Blocker counts

$blockerText

## Next recommended actions

$($validation.next_recommended_actions | ForEach-Object { "- $_" } | Out-String)
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($errorCount -eq 0) {
    Write-Host "PASS | routing_import_plan_validation=$OutputDir | rows=$($rows.Count) | errors=0 | validation_only=True"
} else {
    Write-Host "CHECK | routing_import_plan_validation=$OutputDir | rows=$($rows.Count) | errors=$errorCount | warnings=$warningCount"
}

Write-Host ""
Write-Host "Validation files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
