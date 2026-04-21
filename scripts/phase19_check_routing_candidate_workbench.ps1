param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Try-GetJson {
    param([string]$Url)
    try {
        return @{ ok = $true; value = Invoke-RestMethod $Url -TimeoutSec 20; error = "" }
    } catch {
        return @{ ok = $false; value = $null; error = $_.Exception.Message }
    }
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$status = Try-GetJson "$PlatformApi/front-desk/routing/candidate-workbench/status"
$queue = Try-GetJson "$PlatformApi/front-desk/routing/candidate-workbench/queue?limit=50"

if (!$status.ok) {
    throw "Could not read routing candidate workbench status: $($status.error)"
}
if (!$queue.ok) {
    throw "Could not read routing candidate workbench queue: $($queue.error)"
}

$safetyErrors = @()
if ($status.value.read_only -ne $true) { $safetyErrors += "workbench is not reporting read_only=true" }
if ($status.value.review_write_endpoint_implemented -ne $false) { $safetyErrors += "review_write_endpoint_implemented is not false" }
if ($status.value.candidate_review_write_enabled -ne $false) { $safetyErrors += "candidate_review_write_enabled is not false" }
if ($status.value.bridge_post_enabled -ne $false) { $safetyErrors += "bridge_post_enabled is not false" }
if ($status.value.lacrm_call_enabled -ne $false) { $safetyErrors += "lacrm_call_enabled is not false" }

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_routing_candidate_workbench_check_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 32"
    purpose = "Read-only routing candidate workbench check"
    platform_api = $PlatformApi
    safety = [ordered]@{
        workbench_check_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        review_write_endpoint_implemented = $false
    }
    status = $status.value
    queue = $queue.value
    safety_errors = $safetyErrors
    counts = [ordered]@{
        total_candidates = $status.value.total_candidates
        queue_count = @($queue.value.candidates).Count
        safety_error_count = $safetyErrors.Count
    }
}

$jsonPath = Join-Path $OutputDir "phase19_routing_candidate_workbench_check.json"
$csvPath = Join-Path $OutputDir "phase19_routing_candidate_workbench_queue.csv"
$mdPath = Join-Path $OutputDir "phase19_routing_candidate_workbench_check.md"

$report | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

@($queue.value.candidates) |
    Select-Object id, preference_key, phone, proposed_mode, proposed_owner_type, risk_level, operator_decision, import_blocker, eligible_for_future_dry_run_import, write_status |
    Export-Csv -LiteralPath $csvPath -NoTypeInformation -Encoding UTF8

$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Routing Candidate Workbench Check

Generated: $($report.generated_at)

## Safety

- Workbench check only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Review write endpoint implemented: false

## Safety errors

$safetyText

## Counts

- Total candidates: $($report.counts.total_candidates)
- Queue count: $($report.counts.queue_count)
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($safetyErrors.Count -eq 0) {
    Write-Host "PASS | routing_candidate_workbench_check=$OutputDir | candidates=$($report.counts.total_candidates) | read_only=True"
} else {
    Write-Host "CHECK | routing_candidate_workbench_check=$OutputDir | safety_errors=$($safetyErrors.Count)"
}

Write-Host ""
Write-Host "Workbench check files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
