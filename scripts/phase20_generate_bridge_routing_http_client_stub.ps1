param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$ReleaseCheckpointDir = "",
    [string]$OutputDir = "",
    [string]$OperatorName = "",
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

if ([string]::IsNullOrWhiteSpace($ReleaseCheckpointDir)) {
    $ReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase19_bridge_routing_write_release_checkpoint_*" -JsonName "phase19_bridge_routing_write_release_checkpoint.json"
}

$releaseCheckpointPath = Join-Path $ReleaseCheckpointDir "phase19_bridge_routing_write_release_checkpoint.json"
if (!(Test-Path -LiteralPath $releaseCheckpointPath)) {
    throw "Release checkpoint JSON not found: $releaseCheckpointPath"
}

$status = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-http-client-stub/status"

$safetyErrors = @()
if ($status.bridge_routing_http_client_stub_only -ne $true) { $safetyErrors += "status does not report bridge_routing_http_client_stub_only=true" }
if ($status.real_bridge_http_client_implemented -ne $false) { $safetyErrors += "real_bridge_http_client_implemented is not false" }
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
    confirmation_phrase = $ConfirmationPhrase
}

$result = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-http-client-stub/preview" -Method "POST" -Body $body

if ($result.safety.bridge_routing_http_client_stub_only -ne $true) { $safetyErrors += "preview does not report bridge_routing_http_client_stub_only=true" }
if ($result.safety.real_bridge_http_client_implemented -ne $false) { $safetyErrors += "preview says real_bridge_http_client_implemented is not false" }
if ($result.safety.bridge_http_client_implemented -ne $false) { $safetyErrors += "preview says bridge_http_client_implemented is not false" }
if ($result.safety.bridge_post_call_implemented -ne $false) { $safetyErrors += "preview says bridge_post_call_implemented is not false" }
if ($result.safety.bridge_post_called -ne $false) { $safetyErrors += "preview says bridge_post_called is not false" }
if ($result.safety.bridge_mutation_performed -ne $false) { $safetyErrors += "preview says bridge_mutation_performed is not false" }
if ($result.safety.platform_db_mutation_performed -ne $false) { $safetyErrors += "preview says platform_db_mutation_performed is not false" }
if ($result.safety.lacrm_call_performed -ne $false) { $safetyErrors += "preview says lacrm_call_performed is not false" }
if ($result.blocked -ne $true) { $safetyErrors += "preview is not blocked" }
if ($result.would_call_bridge -ne $false) { $safetyErrors += "preview says would_call_bridge is not false" }

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_http_client_stub_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 1"
    purpose = "Bridge routing HTTP client stub preview"
    source_release_checkpoint = $releaseCheckpointPath
    platform_api = $PlatformApi
    safety = [ordered]@{
        bridge_routing_http_client_stub_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        real_bridge_http_client_implemented = $false
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
        "Review the stub preview before adding any real bridge HTTP client.",
        "Do not call bridge POST endpoints from Phase 20 Step 1.",
        "Future HTTP client work must remain disabled by default and preserve dry-run behavior.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_stub.json"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_stub_artifacts.csv"
$blockersCsvPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_stub_blockers.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_stub.md"

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
# Phase 20 Bridge Routing HTTP Client Stub

Generated: $($report.generated_at)

Source release checkpoint:

``````
$releaseCheckpointPath
``````

## Safety

- Bridge routing HTTP client stub only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Real bridge HTTP client implemented: false
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
    Write-Host "PASS | bridge_routing_http_client_stub=$OutputDir | blocked=$($result.blocked) | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_http_client_stub=$OutputDir | safety_errors=$($safetyErrors.Count) | bridge_post_called=False"
}

Write-Host ""
Write-Host "HTTP client stub files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
