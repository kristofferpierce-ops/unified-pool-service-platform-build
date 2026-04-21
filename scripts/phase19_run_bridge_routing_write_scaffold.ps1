param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$ImplementationPlanDir = "",
    [string]$CutoverPacketDir = "",
    [string]$OutputDir = "",
    [string]$ConfirmationPhrase = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestArtifactDir {
    param(
        [string]$FolderFilter,
        [string]$JsonName
    )

    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter $FolderFilter -ErrorAction SilentlyContinue |
        Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName $JsonName)
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No $FolderFilter folder containing $JsonName found in $BackupDir."
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

if ([string]::IsNullOrWhiteSpace($ImplementationPlanDir)) {
    $ImplementationPlanDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_implementation_plan_*" -JsonName "phase19_bridge_routing_write_implementation_plan.json"
}

if ([string]::IsNullOrWhiteSpace($CutoverPacketDir)) {
    $CutoverPacketDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_cutover_packet_*" -JsonName "phase19_bridge_routing_write_cutover_packet.json"
}

$implementationPlanPath = Join-Path $ImplementationPlanDir "phase19_bridge_routing_write_implementation_plan.json"
$cutoverPacketPath = Join-Path $CutoverPacketDir "phase19_bridge_routing_write_cutover_packet.json"

if (!(Test-Path -LiteralPath $implementationPlanPath)) {
    throw "Implementation plan JSON not found: $implementationPlanPath"
}
if (!(Test-Path -LiteralPath $cutoverPacketPath)) {
    throw "Cutover packet JSON not found: $cutoverPacketPath"
}

$status = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"

$safetyErrors = @()
if ($status.bridge_post_call_implemented -ne $false) { $safetyErrors += "bridge_post_call_implemented is not false" }
if ($status.bridge_post_called -ne $false) { $safetyErrors += "bridge_post_called is not false" }
if ($status.bridge_mutation_performed -ne $false) { $safetyErrors += "bridge_mutation_performed is not false" }
if ($status.platform_db_mutation_performed -ne $false) { $safetyErrors += "platform_db_mutation_performed is not false" }
if ($status.lacrm_call_performed -ne $false) { $safetyErrors += "lacrm_call_performed is not false" }
if ($status.routing_write_endpoint_implemented -ne $false) { $safetyErrors += "routing_write_endpoint_implemented is not false" }
if ($status.execution_endpoint_available -ne $false) { $safetyErrors += "execution_endpoint_available is not false" }

$body = @{
    implementation_plan_path = $implementationPlanPath
    cutover_packet_path = $cutoverPacketPath
    dry_run = $true
    confirmation_phrase = $ConfirmationPhrase
}

$result = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-write-executor/preview" -Method "POST" -Body $body

if ($result.safety.bridge_post_called -ne $false) { $safetyErrors += "preview says bridge_post_called is not false" }
if ($result.safety.bridge_mutation_performed -ne $false) { $safetyErrors += "preview says bridge_mutation_performed is not false" }
if ($result.safety.platform_db_mutation_performed -ne $false) { $safetyErrors += "preview says platform_db_mutation_performed is not false" }
if ($result.safety.lacrm_call_performed -ne $false) { $safetyErrors += "preview says lacrm_call_performed is not false" }
if ($result.safety.bridge_post_call_implemented -ne $false) { $safetyErrors += "preview says bridge_post_call_implemented is not false" }
if ($result.blocked -ne $true) { $safetyErrors += "preview is not blocked" }
if ($result.would_call_bridge -ne $false) { $safetyErrors += "preview says would_call_bridge is not false" }

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_scaffold_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$blockerCounts = @{}
foreach ($blocker in @($result.blockers)) {
    if (!$blockerCounts.ContainsKey($blocker)) { $blockerCounts[$blocker] = 0 }
    $blockerCounts[$blocker] += 1
}

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 45"
    purpose = "Disabled-by-default bridge routing write scaffold preview"
    source_implementation_plan = $implementationPlanPath
    source_cutover_packet = $cutoverPacketPath
    platform_api = $PlatformApi
    safety = [ordered]@{
        bridge_routing_write_scaffold_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        bridge_post_call_implemented = $false
        routing_write_endpoint_implemented = $false
        live_write_enabled = $false
    }
    status = $status
    preview = $result
    safety_errors = $safetyErrors
    counts = [ordered]@{
        blocker_count = @($result.blockers).Count
        review_item_count = @($result.review_items).Count
        safety_error_count = $safetyErrors.Count
        blocker_counts = $blockerCounts
    }
    next_recommended_actions = @(
        "Review scaffold blockers before adding any real bridge HTTP client.",
        "Do not call bridge POST endpoints from Step 45.",
        "Future implementation must add audit pre-row, rollback verification, and explicit operator gates before bridge POST.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_scaffold.json"
$blockersCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_scaffold_blockers.csv"
$planItemsCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_scaffold_plan_items.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_scaffold.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

@($result.blockers) | ForEach-Object {
    [ordered]@{ blocker = $_ }
} | Export-Csv -LiteralPath $blockersCsvPath -NoTypeInformation -Encoding UTF8

@($result.plan_items_seen) | Export-Csv -LiteralPath $planItemsCsvPath -NoTypeInformation -Encoding UTF8

$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }
$blockerText = if (@($result.blockers).Count -gt 0) { (@($result.blockers) | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Bridge Routing Write Scaffold

Generated: $($report.generated_at)

Source implementation plan:

``````
$implementationPlanPath
``````

Source cutover packet:

``````
$cutoverPacketPath
``````

## Safety

- Bridge routing write scaffold only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
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
    Write-Host "PASS | bridge_routing_write_scaffold=$OutputDir | blocked=$($result.blocked) | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_write_scaffold=$OutputDir | safety_errors=$($safetyErrors.Count) | bridge_post_called=False"
}

Write-Host ""
Write-Host "Scaffold files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime

