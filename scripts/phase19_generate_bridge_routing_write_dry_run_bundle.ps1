param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$ScaffoldDir = "",
    [string]$CutoverPacketDir = "",
    [string]$ImplementationPlanDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestArtifactDir {
    param(
        [string]$FolderFilter,
        [string]$JsonName,
        [bool]$Required = $true
    )

    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter $FolderFilter -ErrorAction SilentlyContinue |
        Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName $JsonName)
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        if ($Required) {
            throw "No $FolderFilter folder containing $JsonName found in $BackupDir."
        }
        return ""
    }

    return $latest.FullName
}

function Invoke-PlatformJson {
    param(
        [string]$Url,
        [string]$Method = "GET",
        [object]$Body = $null
    )

    if ($Method -eq "POST") {
        return Invoke-RestMethod $Url -Method Post -Body ($Body | ConvertTo-Json -Depth 100) -ContentType "application/json" -TimeoutSec 60
    }

    return Invoke-RestMethod $Url -TimeoutSec 30
}

if ([string]::IsNullOrWhiteSpace($ScaffoldDir)) {
    $ScaffoldDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_scaffold_*" -JsonName "phase19_bridge_routing_write_scaffold.json"
}

if ([string]::IsNullOrWhiteSpace($CutoverPacketDir)) {
    $CutoverPacketDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_cutover_packet_*" -JsonName "phase19_bridge_routing_write_cutover_packet.json" -Required $false
}

if ([string]::IsNullOrWhiteSpace($ImplementationPlanDir)) {
    $ImplementationPlanDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_implementation_plan_*" -JsonName "phase19_bridge_routing_write_implementation_plan.json" -Required $false
}

$scaffoldPath = Join-Path $ScaffoldDir "phase19_bridge_routing_write_scaffold.json"
$cutoverPath = if (![string]::IsNullOrWhiteSpace($CutoverPacketDir)) { Join-Path $CutoverPacketDir "phase19_bridge_routing_write_cutover_packet.json" } else { "" }
$implementationPath = if (![string]::IsNullOrWhiteSpace($ImplementationPlanDir)) { Join-Path $ImplementationPlanDir "phase19_bridge_routing_write_implementation_plan.json" } else { "" }

if (!(Test-Path -LiteralPath $scaffoldPath)) {
    throw "Scaffold report JSON not found: $scaffoldPath"
}

$status = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status"

$safetyErrors = @()
if ($status.dry_run_bundle_only -ne $true) { $safetyErrors += "status does not report dry_run_bundle_only=true" }
if ($status.bridge_http_client_implemented -ne $false) { $safetyErrors += "bridge_http_client_implemented is not false" }
if ($status.bridge_post_call_implemented -ne $false) { $safetyErrors += "bridge_post_call_implemented is not false" }
if ($status.bridge_post_called -ne $false) { $safetyErrors += "bridge_post_called is not false" }
if ($status.bridge_mutation_performed -ne $false) { $safetyErrors += "bridge_mutation_performed is not false" }
if ($status.platform_db_mutation_performed -ne $false) { $safetyErrors += "platform_db_mutation_performed is not false" }
if ($status.lacrm_call_performed -ne $false) { $safetyErrors += "lacrm_call_performed is not false" }
if ($status.routing_write_endpoint_implemented -ne $false) { $safetyErrors += "routing_write_endpoint_implemented is not false" }

$body = @{
    scaffold_report_path = $scaffoldPath
    cutover_packet_path = $cutoverPath
    implementation_plan_path = $implementationPath
}

$result = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/build-preview" -Method "POST" -Body $body

if ($result.safety.bridge_http_client_implemented -ne $false) { $safetyErrors += "bundle says bridge_http_client_implemented is not false" }
if ($result.safety.bridge_post_call_implemented -ne $false) { $safetyErrors += "bundle says bridge_post_call_implemented is not false" }
if ($result.safety.bridge_post_called -ne $false) { $safetyErrors += "bundle says bridge_post_called is not false" }
if ($result.safety.bridge_mutation_performed -ne $false) { $safetyErrors += "bundle says bridge_mutation_performed is not false" }
if ($result.safety.platform_db_mutation_performed -ne $false) { $safetyErrors += "bundle says platform_db_mutation_performed is not false" }
if ($result.safety.lacrm_call_performed -ne $false) { $safetyErrors += "bundle says lacrm_call_performed is not false" }
if ($result.dry_run_bundle_only -ne $true) { $safetyErrors += "bundle does not report dry_run_bundle_only=true" }
if ($result.blocked -ne $true) { $safetyErrors += "bundle is not blocked" }

foreach ($row in @($result.bundle_rows)) {
    if ($row.would_call_bridge -ne $false) { $safetyErrors += "a bundle row says would_call_bridge is not false" }
    if ($row.would_mutate_platform -ne $false) { $safetyErrors += "a bundle row says would_mutate_platform is not false" }
    if ($row.would_call_lacrm -ne $false) { $safetyErrors += "a bundle row says would_call_lacrm is not false" }
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_dry_run_bundle_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 46"
    purpose = "Bridge routing write dry-run request bundle"
    source_scaffold_report = $scaffoldPath
    source_cutover_packet = $cutoverPath
    source_implementation_plan = $implementationPath
    platform_api = $PlatformApi
    safety = [ordered]@{
        bridge_routing_write_dry_run_bundle_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        bridge_http_client_implemented = $false
        bridge_post_call_implemented = $false
        routing_write_endpoint_implemented = $false
        live_write_enabled = $false
    }
    status = $status
    bundle = $result
    safety_errors = $safetyErrors
    counts = [ordered]@{
        bundle_rows = @($result.bundle_rows).Count
        blocker_count = @($result.blockers).Count
        safety_error_count = $safetyErrors.Count
    }
    next_recommended_actions = @(
        "Review dry-run bundle rows before any bridge HTTP client is added.",
        "Do not call bridge POST endpoints from Step 46.",
        "Future implementation must remain dry-run by default and require audit and rollback gates.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_dry_run_bundle.json"
$rowsCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_dry_run_bundle_rows.csv"
$blockersCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_dry_run_bundle_blockers.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_dry_run_bundle.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

@($result.bundle_rows) |
    Select-Object bundle_row_type, target_bridge_endpoint, http_method, idempotency_key_template, payload_hash, would_call_bridge, would_mutate_platform, would_call_lacrm, ready_for_live_execution, reason |
    Export-Csv -LiteralPath $rowsCsvPath -NoTypeInformation -Encoding UTF8

@($result.blockers) | ForEach-Object {
    [ordered]@{ blocker = $_ }
} | Export-Csv -LiteralPath $blockersCsvPath -NoTypeInformation -Encoding UTF8

$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }
$blockerText = if (@($result.blockers).Count -gt 0) { (@($result.blockers) | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Bridge Routing Write Dry-run Bundle

Generated: $($report.generated_at)

Source scaffold report:

``````
$scaffoldPath
``````

## Safety

- Bridge routing write dry-run bundle only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Bridge HTTP client implemented: false
- Bridge POST call implemented: false
- Routing write endpoint implemented: false
- Live write enabled: false

## Safety errors

$safetyText

## Blockers

$blockerText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($safetyErrors.Count -eq 0) {
    Write-Host "PASS | bridge_routing_write_dry_run_bundle=$OutputDir | rows=$(@($result.bundle_rows).Count) | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_write_dry_run_bundle=$OutputDir | safety_errors=$($safetyErrors.Count) | bridge_post_called=False"
}

Write-Host ""
Write-Host "Dry-run bundle files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
