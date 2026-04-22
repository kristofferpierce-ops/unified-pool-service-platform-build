param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$StubReportDir = "",
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

if ([string]::IsNullOrWhiteSpace($StubReportDir)) {
    $StubReportDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_http_client_stub_*" -JsonName "phase20_bridge_routing_http_client_stub.json"
}

$stubReportPath = Join-Path $StubReportDir "phase20_bridge_routing_http_client_stub.json"
if (!(Test-Path -LiteralPath $stubReportPath)) {
    throw "HTTP client stub JSON not found: $stubReportPath"
}

$status = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"

$safetyErrors = @()
if ($status.bridge_routing_http_client_dry_run_only -ne $true) { $safetyErrors += "status does not report bridge_routing_http_client_dry_run_only=true" }
if ($status.real_bridge_http_client_implemented -ne $false) { $safetyErrors += "real_bridge_http_client_implemented is not false" }
if ($status.network_transport_implemented -ne $false) { $safetyErrors += "network_transport_implemented is not false" }
if ($status.bridge_http_client_implemented -ne $false) { $safetyErrors += "bridge_http_client_implemented is not false" }
if ($status.bridge_post_call_implemented -ne $false) { $safetyErrors += "bridge_post_call_implemented is not false" }
if ($status.bridge_post_called -ne $false) { $safetyErrors += "bridge_post_called is not false" }
if ($status.bridge_mutation_performed -ne $false) { $safetyErrors += "bridge_mutation_performed is not false" }
if ($status.platform_db_mutation_performed -ne $false) { $safetyErrors += "platform_db_mutation_performed is not false" }
if ($status.lacrm_call_performed -ne $false) { $safetyErrors += "lacrm_call_performed is not false" }
if ($status.routing_write_endpoint_implemented -ne $false) { $safetyErrors += "routing_write_endpoint_implemented is not false" }

$body = @{
    stub_report_path = $stubReportPath
    operator_name = $OperatorName
    confirmation_phrase = $ConfirmationPhrase
}

$result = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/simulate" -Method "POST" -Body $body

if ($result.safety.bridge_routing_http_client_dry_run_only -ne $true) { $safetyErrors += "simulation does not report bridge_routing_http_client_dry_run_only=true" }
if ($result.safety.real_bridge_http_client_implemented -ne $false) { $safetyErrors += "simulation says real_bridge_http_client_implemented is not false" }
if ($result.safety.network_transport_implemented -ne $false) { $safetyErrors += "simulation says network_transport_implemented is not false" }
if ($result.safety.bridge_post_call_implemented -ne $false) { $safetyErrors += "simulation says bridge_post_call_implemented is not false" }
if ($result.safety.bridge_post_called -ne $false) { $safetyErrors += "simulation says bridge_post_called is not false" }
if ($result.safety.bridge_mutation_performed -ne $false) { $safetyErrors += "simulation says bridge_mutation_performed is not false" }
if ($result.safety.platform_db_mutation_performed -ne $false) { $safetyErrors += "simulation says platform_db_mutation_performed is not false" }
if ($result.safety.lacrm_call_performed -ne $false) { $safetyErrors += "simulation says lacrm_call_performed is not false" }
if ($result.blocked -ne $true) { $safetyErrors += "simulation is not blocked" }
if ($result.would_call_bridge -ne $false) { $safetyErrors += "simulation says would_call_bridge is not false" }
if ($result.simulated_response.would_send -ne $false) { $safetyErrors += "simulated_response says would_send is not false" }

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_http_client_dry_run_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 2"
    purpose = "Bridge routing HTTP client dry-run transport simulation"
    source_stub_report = $stubReportPath
    platform_api = $PlatformApi
    safety = [ordered]@{
        bridge_routing_http_client_dry_run_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        real_bridge_http_client_implemented = $false
        network_transport_implemented = $false
        bridge_http_client_implemented = $false
        bridge_post_call_implemented = $false
        routing_write_endpoint_implemented = $false
        live_write_enabled = $false
    }
    status = $status
    simulation = $result
    safety_errors = $safetyErrors
    counts = [ordered]@{
        blockers = @($result.blockers).Count
        safety_errors = $safetyErrors.Count
        simulated_requests = 1
    }
    next_recommended_actions = @(
        "Review the dry-run transport simulation before adding any real network transport.",
        "Do not call bridge POST endpoints from Phase 20 Step 2.",
        "Future HTTP client work must keep dry-run as the safe default.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_dry_run.json"
$requestCsvPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_dry_run_request.csv"
$blockersCsvPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_dry_run_blockers.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_http_client_dry_run.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

@(
    [ordered]@{
        request_id = $result.simulated_request.request_id
        target_bridge_base_url = $result.simulated_request.target_bridge_base_url
        target_bridge_endpoint = $result.simulated_request.target_bridge_endpoint
        http_method = $result.simulated_request.http_method
        payload_hash = $result.simulated_request.payload_hash
        transport = $result.simulated_request.transport
        would_send = $result.simulated_response.would_send
        would_call_bridge = $result.simulated_response.would_call_bridge
        would_mutate_bridge = $result.simulated_response.would_mutate_bridge
    }
) | Export-Csv -LiteralPath $requestCsvPath -NoTypeInformation -Encoding UTF8

@($result.blockers) | ForEach-Object {
    [ordered]@{ blocker = $_ }
} | Export-Csv -LiteralPath $blockersCsvPath -NoTypeInformation -Encoding UTF8

$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }
$blockerText = if (@($result.blockers).Count -gt 0) { (@($result.blockers) | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing HTTP Client Dry-run Transport

Generated: $($report.generated_at)

Source HTTP client stub report:

``````
$stubReportPath
``````

## Safety

- Bridge routing HTTP client dry-run only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Real bridge HTTP client implemented: false
- Network transport implemented: false
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
    Write-Host "PASS | bridge_routing_http_client_dry_run=$OutputDir | blocked=$($result.blocked) | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_http_client_dry_run=$OutputDir | safety_errors=$($safetyErrors.Count) | bridge_post_called=False"
}

Write-Host ""
Write-Host "HTTP client dry-run files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
