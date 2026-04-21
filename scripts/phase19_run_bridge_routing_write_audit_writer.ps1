param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$AuditPlanDir = "",
    [string]$OutputDir = "",
    [switch]$Execute,
    [string]$ConfirmationPhrase = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestAuditPlanDir {
    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter "phase19_bridge_routing_write_audit_plan_*" -ErrorAction SilentlyContinue |
        Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName "phase19_bridge_routing_write_audit_plan.json")
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No phase19_bridge_routing_write_audit_plan_* folder containing phase19_bridge_routing_write_audit_plan.json found in $BackupDir. Run Step 39 option 5 first."
    }

    return $latest.FullName
}

if ([string]::IsNullOrWhiteSpace($AuditPlanDir)) {
    $AuditPlanDir = Get-LatestAuditPlanDir
}

$planPath = Join-Path $AuditPlanDir "phase19_bridge_routing_write_audit_plan.json"
if (!(Test-Path -LiteralPath $planPath)) {
    throw "Bridge routing write audit plan JSON not found: $planPath"
}

$status = Invoke-RestMethod "$PlatformApi/front-desk/routing/bridge-write-audit-writer/status" -TimeoutSec 20
if ($status.audit_writer_endpoint_available -ne $true) {
    throw "Bridge routing audit writer endpoint is not available."
}

$dryRun = -not $Execute

$body = @{
    plan_path = $planPath
    dry_run = $dryRun
    confirmation_phrase = $ConfirmationPhrase
} | ConvertTo-Json -Depth 8

$result = Invoke-RestMethod "$PlatformApi/front-desk/routing/bridge-write-audit-writer/run" `
    -Method Post `
    -Body $body `
    -ContentType "application/json" `
    -TimeoutSec 60

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_audit_writer_run_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_audit_writer_run.json"
$csvPath = Join-Path $OutputDir "phase19_bridge_routing_write_audit_writer_run.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_audit_writer_run.md"

$result | ConvertTo-Json -Depth 60 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$rows = @()
if ($result.write_rows) { $rows = @($result.write_rows) }

$rows |
    Select-Object audit_key, action, reason, existing_audit_id |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$actionText = ""
if ($result.counts -and $result.counts.action_counts) {
    $actionText = (($result.counts.action_counts.PSObject.Properties | Sort-Object Name) | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
}

$blockerText = if ($result.blockers) { (@($result.blockers) | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Bridge Routing Write Audit Writer Run

Generated: $(Get-Date -Format o)

Source audit plan:

``````
$planPath
``````

## Safety

- Dry run: $($result.dry_run)
- Audit write performed: $($result.safety.audit_write_performed)
- Platform DB mutation performed: $($result.safety.platform_db_mutation_performed)
- Bridge mutation performed: $($result.safety.bridge_mutation_performed)
- Bridge POST called: $($result.safety.bridge_post_called)
- LACRM call performed: $($result.safety.lacrm_call_performed)
- Bridge POST call implemented: $($result.safety.bridge_post_call_implemented)

## Blockers

$blockerText

## Counts

- Plan rows: $($result.counts.plan_rows)
- Write rows: $($result.counts.write_rows)

### Action counts

$actionText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($result.safety.audit_write_performed -eq $true) {
    Write-Host "PASS | bridge_routing_write_audit_writer_run=$OutputDir | executed=True | platform_db_mutation=True | bridge_post_called=False"
} elseif ($result.blocked -eq $true) {
    Write-Host "CHECK | bridge_routing_write_audit_writer_run=$OutputDir | blocked=True | dry_run=$($result.dry_run) | bridge_post_called=False"
} else {
    Write-Host "PASS | bridge_routing_write_audit_writer_run=$OutputDir | dry_run=True | no_db_write=True | bridge_post_called=False"
}

Write-Host ""
Write-Host "Audit writer run files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
