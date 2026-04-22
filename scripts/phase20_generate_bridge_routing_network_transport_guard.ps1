param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$ReleaseCheckpointDir = "",
    [string]$OutputDir = "",
    [string]$OperatorName = "",
    [string]$TransportConfirmationPhrase = "",
    [string]$BridgeWriteConfirmationPhrase = ""
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

if ([string]::IsNullOrWhiteSpace($ReleaseCheckpointDir)) {
    $ReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_release_checkpoint_*" -JsonName "phase20_bridge_routing_http_client_release_checkpoint.json"
}

$releaseCheckpointPath = Join-Path $ReleaseCheckpointDir "phase20_bridge_routing_http_client_release_checkpoint.json"
if (!(Test-Path -LiteralPath $releaseCheckpointPath)) {
    throw "HTTP client release checkpoint JSON not found: $releaseCheckpointPath"
}

$status = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"

$safetyErrors = @()
if ($status.bridge_routing_network_transport_guard_only -ne $true) { $safetyErrors += "status does not report bridge_routing_network_transport_guard_only=true" }
if ($status.real_bridge_http_client_implemented -ne $false) { $safetyErrors += "real_bridge_http_client_implemented is not false" }
if ($status.network_transport_implemented -ne $false) { $safetyErrors += "network_transport_implemented is not false" }
if ($status.network_transport_enabled -ne $false) { $safetyErrors += "network_transport_enabled is not false" }
if ($status.network_transport_armed -ne $false) { $safetyErrors += "network_transport_armed is not false" }
if ($status.bridge_http_client_implemented -ne $false) { $safetyErrors += "bridge_http_client_implemented is not false" }
if ($status.bridge_post_call_implemented -ne $false) { $safetyErrors += "bridge_post_call_implemented is not false" }
if ($status.bridge_post_called -ne $false) { $safetyErrors += "bridge_post_called is not false" }
if ($status.bridge_mutation_performed -ne $false) { $safetyErrors += "bridge_mutation_performed is not false" }
if ($status.platform_db_mutation_performed -ne $false) { $safetyErrors += "platform_db_mutation_performed is not false" }
if ($status.lacrm_call_performed -ne $false) { $safetyErrors += "lacrm_call_performed is not false" }
if ($status.routing_write_endpoint_implemented -ne $false) { $safetyErrors += "routing_write_endpoint_implemented is not false" }

$body = @{
    release_checkpoint_path = $releaseCheckpointPath
    operator_name = $OperatorName
    transport_confirmation_phrase = $TransportConfirmationPhrase
    bridge_write_confirmation_phrase = $BridgeWriteConfirmationPhrase
}

$result = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/preview" -Method "POST" -Body $body

if ($result.safety.bridge_routing_network_transport_guard_only -ne $true) { $safetyErrors += "preview does not report bridge_routing_network_transport_guard_only=true" }
if ($result.safety.real_bridge_http_client_implemented -ne $false) { $safetyErrors += "preview says real_bridge_http_client_implemented is not false" }
if ($result.safety.network_transport_implemented -ne $false) { $safetyErrors += "preview says network_transport_implemented is not false" }
if ($result.safety.network_transport_enabled -ne $false) { $safetyErrors += "preview says network_transport_enabled is not false" }
if ($result.safety.network_transport_armed -ne $false) { $safetyErrors += "preview says network_transport_armed is not false" }
if ($result.safety.bridge_post_call_implemented -ne $false) { $safetyErrors += "preview says bridge_post_call_implemented is not false" }
if ($result.safety.bridge_post_called -ne $false) { $safetyErrors += "preview says bridge_post_called is not false" }
if ($result.safety.bridge_mutation_performed -ne $false) { $safetyErrors += "preview says bridge_mutation_performed is not false" }
if ($result.safety.platform_db_mutation_performed -ne $false) { $safetyErrors += "preview says platform_db_mutation_performed is not false" }
if ($result.safety.lacrm_call_performed -ne $false) { $safetyErrors += "preview says lacrm_call_performed is not false" }
if ($result.blocked -ne $true) { $safetyErrors += "preview is not blocked" }
if ($result.would_add_network_transport -ne $false) { $safetyErrors += "preview says would_add_network_transport is not false" }
if ($result.would_call_bridge -ne $false) { $safetyErrors += "preview says would_call_bridge is not false" }

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_guard_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 7"
    purpose = "Bridge routing network transport guard preview"
    source_release_checkpoint = $releaseCheckpointPath
    platform_api = $PlatformApi
    safety = [ordered]@{
        bridge_routing_network_transport_guard_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        real_bridge_http_client_implemented = $false
        network_transport_implemented = $false
        network_transport_enabled = $false
        network_transport_armed = $false
        bridge_http_client_implemented = $false
        bridge_post_call_implemented = $false
        routing_write_endpoint_implemented = $false
        live_write_enabled = $false
    }
    status = $status
    preview = $result
    safety_errors = $safetyErrors
    counts = [ordered]@{
        release_artifacts = @($result.release_checkpoint_artifacts).Count
        blockers = @($result.blockers).Count
        safety_errors = $safetyErrors.Count
    }
    next_recommended_actions = @(
        "Review the network transport guard before adding any real transport adapter.",
        "Do not call bridge POST endpoints from Phase 20 Step 7.",
        "Future transport adapter work must stay disabled by default and preserve dry-run behavior.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_guard.json"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_guard_artifacts.csv"
$blockersCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_guard_blockers.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_guard.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

@($result.release_checkpoint_artifacts) |
    Select-Object key, folder, json_name, json_path, sha256, last_write_time |
    Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8

@($result.blockers) | ForEach-Object {
    [ordered]@{ blocker = $_ }
} | Export-Csv -LiteralPath $blockersCsvPath -NoTypeInformation -Encoding UTF8

$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }
$blockerText = if (@($result.blockers).Count -gt 0) { (@($result.blockers) | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Guard

Generated: $($report.generated_at)

Source HTTP client release checkpoint:

``````
$releaseCheckpointPath
``````

## Safety

- Bridge routing network transport guard only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Real bridge HTTP client implemented: false
- Network transport implemented: false
- Network transport enabled: false
- Network transport armed: false
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
    Write-Host "PASS | bridge_routing_network_transport_guard=$OutputDir | blocked=$($result.blocked) | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_guard=$OutputDir | safety_errors=$($safetyErrors.Count) | bridge_post_called=False"
}

Write-Host ""
Write-Host "Network transport guard files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
