param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$RoutingImportPlanDir = "",
    [string]$OutputDir = "",
    [switch]$Execute,
    [string]$ConfirmationPhrase = ""
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

if ([string]::IsNullOrWhiteSpace($RoutingImportPlanDir)) {
    $RoutingImportPlanDir = Get-LatestImportPlanDir
}

$planPath = Join-Path $RoutingImportPlanDir "phase19_routing_import_plan.json"
if (!(Test-Path -LiteralPath $planPath)) {
    throw "Routing import plan JSON not found: $planPath"
}

$status = Invoke-RestMethod "$PlatformApi/front-desk/routing/candidates/import/status" -TimeoutSec 20
if ($status.import_endpoint_available -ne $true) {
    throw "Routing candidate import endpoint is not available."
}

$dryRun = -not $Execute

$body = @{
    plan_path = $planPath
    dry_run = $dryRun
    confirmation_phrase = $ConfirmationPhrase
} | ConvertTo-Json -Depth 8

$result = Invoke-RestMethod "$PlatformApi/front-desk/routing/candidates/import-plan" `
    -Method Post `
    -Body $body `
    -ContentType "application/json" `
    -TimeoutSec 60

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_routing_candidate_import_run_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$jsonPath = Join-Path $OutputDir "phase19_routing_candidate_import_run.json"
$csvPath = Join-Path $OutputDir "phase19_routing_candidate_import_run.csv"
$mdPath = Join-Path $OutputDir "phase19_routing_candidate_import_run.md"

$result | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$rows = @()
if ($result.import_rows) { $rows = @($result.import_rows) }

$rows |
    Select-Object preference_key, phone, eligible_for_future_dry_run_import, action, reason, existing_candidate_id |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$actionText = ""
if ($result.counts -and $result.counts.action_counts) {
    $actionText = (($result.counts.action_counts.PSObject.Properties | Sort-Object Name) | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
}

$md = @"
# Phase 19 Routing Candidate Import Run

Generated: $(Get-Date -Format o)

Source import plan:

``````
$planPath
``````

## Safety

- Dry run: $($result.dry_run)
- Candidate import performed: $($result.safety.candidate_import_performed)
- Platform DB mutation performed: $($result.safety.platform_db_mutation_performed)
- Bridge mutation performed: $($result.safety.bridge_mutation_performed)
- Bridge POST called: $($result.safety.bridge_post_called)
- LACRM call performed: $($result.safety.lacrm_call_performed)

## Counts

- Plan rows: $($result.counts.plan_rows)
- Import rows: $($result.counts.import_rows)

### Action counts

$actionText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($result.safety.candidate_import_performed -eq $true) {
    Write-Host "PASS | routing_candidate_import_run=$OutputDir | executed=True | platform_db_mutation=True"
} elseif ($result.blocked -eq $true) {
    Write-Host "CHECK | routing_candidate_import_run=$OutputDir | blocked=True | dry_run=$($result.dry_run)"
} else {
    Write-Host "PASS | routing_candidate_import_run=$OutputDir | dry_run=True | no_db_write=True"
}

Write-Host ""
Write-Host "Run files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
