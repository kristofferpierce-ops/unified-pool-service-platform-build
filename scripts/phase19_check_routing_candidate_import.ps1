param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$RoutingImportPlanDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestImportPlanDir {
    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter "phase19_routing_import_plan_*" -ErrorAction SilentlyContinue |
        Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName "phase19_routing_import_plan.json")
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No phase19_routing_import_plan_* folder containing phase19_routing_import_plan.json found in $BackupDir. Run Step 27 option 4 first."
    }

    return $latest.FullName
}
function Try-GetJson {
    param([string]$Url)
    try {
        return @{ ok = $true; value = Invoke-RestMethod $Url -TimeoutSec 20; error = "" }
    } catch {
        return @{ ok = $false; value = $null; error = $_.Exception.Message }
    }
}

function Normalize-String {
    param($Value)
    if ($null -eq $Value) { return "" }
    return ([string]$Value).Trim()
}

function Build-CandidateKeyMap {
    param($Candidates)
    $map = @{}
    foreach ($candidate in @($Candidates)) {
        $key = Normalize-String $candidate.preference_key
        if (![string]::IsNullOrWhiteSpace($key)) {
            $map[$key] = $candidate
        }
    }
    return $map
}

function Compare-Row-To-Candidate {
    param($PlanRow, $Candidate)

    $diffs = @()

    foreach ($field in @("phone", "proposed_mode", "proposed_owner_type", "risk_level", "proposed_action", "operator_decision", "import_blocker")) {
        $planValue = Normalize-String $PlanRow.$field
        $candidateValue = Normalize-String $Candidate.$field
        if ($planValue -ne $candidateValue) {
            $diffs += [ordered]@{
                field = $field
                plan_value = $planValue
                candidate_value = $candidateValue
            }
        }
    }

    $planEligible = [bool]$PlanRow.eligible_for_future_dry_run_import
    $candidateEligible = [bool]$Candidate.eligible_for_future_dry_run_import
    if ($planEligible -ne $candidateEligible) {
        $diffs += [ordered]@{
            field = "eligible_for_future_dry_run_import"
            plan_value = $planEligible
            candidate_value = $candidateEligible
        }
    }

    return @($diffs)
}

if ([string]::IsNullOrWhiteSpace($RoutingImportPlanDir)) {
    $RoutingImportPlanDir = Get-LatestImportPlanDir
}

if (!(Test-Path -LiteralPath $RoutingImportPlanDir)) {
    throw "Routing import plan folder not found: $RoutingImportPlanDir"
}

$planPath = Join-Path $RoutingImportPlanDir "phase19_routing_import_plan.json"
if (!(Test-Path -LiteralPath $planPath)) {
    throw "Routing import plan JSON not found: $planPath"
}

$plan = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
$planRows = @()
if ($plan.import_plan_rows) { $planRows = @($plan.import_plan_rows) }

$status = Try-GetJson "$PlatformApi/front-desk/routing/candidates/status"
$candidates = Try-GetJson "$PlatformApi/front-desk/routing/candidates?limit=500&offset=0"

if (!$status.ok) {
    throw "Could not read routing candidate status from platform: $($status.error)"
}
if (!$candidates.ok) {
    throw "Could not read routing candidates from platform: $($candidates.error)"
}

$safetyErrors = @()
if ($status.value.read_only -ne $true) { $safetyErrors += "routing candidate API is not reporting read_only=true" }
if ($status.value.candidate_import_enabled -ne $false) { $safetyErrors += "candidate_import_enabled is not false" }
if ($status.value.routing_write_endpoint_implemented -ne $false) { $safetyErrors += "routing_write_endpoint_implemented is not false" }
if ($status.value.bridge_post_enabled -ne $false) { $safetyErrors += "bridge_post_enabled is not false" }
if ($status.value.lacrm_call_enabled -ne $false) { $safetyErrors += "lacrm_call_enabled is not false" }

$candidateRows = @()
if ($candidates.value.candidates) { $candidateRows = @($candidates.value.candidates) }
$candidateByKey = Build-CandidateKeyMap $candidateRows

$checkRows = @()
foreach ($row in $planRows) {
    $key = Normalize-String $row.preference_key
    $eligible = [bool]$row.eligible_for_future_dry_run_import
    $existing = $null
    if ($candidateByKey.ContainsKey($key)) {
        $existing = $candidateByKey[$key]
    }

    $action = "would_block"
    $reason = Normalize-String $row.import_blocker
    $diffs = @()

    if ($safetyErrors.Count -gt 0) {
        $action = "blocked_by_api_safety_flags"
        $reason = "routing candidate API safety flags are not read-only"
    } elseif (!$eligible) {
        $action = "would_block"
        if ([string]::IsNullOrWhiteSpace($reason)) { $reason = "not eligible for future dry-run import" }
    } elseif ($null -eq $existing) {
        $action = "would_create"
        $reason = "eligible row does not exist in platform candidate table"
    } else {
        $diffs = Compare-Row-To-Candidate $row $existing
        if ($diffs.Count -gt 0) {
            $action = "would_update"
            $reason = "eligible row exists but differs from import plan"
        } else {
            $action = "would_skip_existing"
            $reason = "eligible row already matches import plan"
        }
    }

    $checkRows += [ordered]@{
        preference_key = $key
        phone = Normalize-String $row.phone
        proposed_mode = Normalize-String $row.proposed_mode
        proposed_owner_type = Normalize-String $row.proposed_owner_type
        operator_decision = Normalize-String $row.operator_decision
        eligible_for_future_dry_run_import = $eligible
        existing_candidate_id = if ($existing) { $existing.id } else { $null }
        dry_run_action = $action
        reason = $reason
        diff_count = @($diffs).Count
        diffs = @($diffs)
    }
}

$actionCounts = @{}
foreach ($row in $checkRows) {
    if (!$actionCounts.ContainsKey($row.dry_run_action)) { $actionCounts[$row.dry_run_action] = 0 }
    $actionCounts[$row.dry_run_action] += 1
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_routing_candidate_import_check_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 30"
    purpose = "Dry-run routing candidate import checker"
    source_routing_import_plan = $planPath
    platform_api = $PlatformApi
    safety = [ordered]@{
        dry_run_check_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        live_write_enabled = $false
        candidate_import_performed = $false
        candidate_import_enabled = $false
        routing_write_endpoint_implemented = $false
    }
    api_status = $status.value
    api_safety_errors = $safetyErrors
    counts = [ordered]@{
        plan_rows = @($planRows).Count
        existing_candidates = @($candidateRows).Count
        check_rows = @($checkRows).Count
        action_counts = $actionCounts
    }
    check_rows = $checkRows
    next_recommended_actions = @(
        "Review would_create and would_update rows before enabling any importer.",
        "If API safety flags fail, stop and fix the routing candidate API before continuing.",
        "Next step may add a disabled-by-default importer, but it must default to dry-run and no writes.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_routing_candidate_import_check.json"
$csvPath = Join-Path $OutputDir "phase19_routing_candidate_import_check.csv"
$mdPath = Join-Path $OutputDir "phase19_routing_candidate_import_check.md"

$report | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$checkRows |
    Select-Object preference_key, phone, proposed_mode, proposed_owner_type, operator_decision, eligible_for_future_dry_run_import, existing_candidate_id, dry_run_action, reason, diff_count |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$actionText = ($actionCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Routing Candidate Import Check

Generated: $($report.generated_at)

Source import plan:

``````
$planPath
``````

## Safety

- Dry-run check only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Candidate import performed: false

## API safety errors

$safetyText

## Counts

- Plan rows: $($report.counts.plan_rows)
- Existing candidates: $($report.counts.existing_candidates)
- Check rows: $($report.counts.check_rows)

### Dry-run action counts

$actionText

## Next recommended actions

$($report.next_recommended_actions | ForEach-Object { "- $_" } | Out-String)
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($safetyErrors.Count -eq 0) {
    Write-Host "PASS | routing_candidate_import_check=$OutputDir | rows=$($checkRows.Count) | dry_run_check_only=True"
} else {
    Write-Host "CHECK | routing_candidate_import_check=$OutputDir | rows=$($checkRows.Count) | api_safety_errors=$($safetyErrors.Count)"
}

Write-Host ""
Write-Host "Import check files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime

