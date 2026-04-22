param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$InterfaceScaffoldReleaseCheckpointDir = "",
    [string]$OutputDir = "",
    [string]$OperatorName = "",
    [string]$TransportConfirmationPhrase = ""
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

if ([string]::IsNullOrWhiteSpace($InterfaceScaffoldReleaseCheckpointDir)) {
    $InterfaceScaffoldReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint.json"
}

$checkpointPath = Join-Path $InterfaceScaffoldReleaseCheckpointDir "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint.json"
if (!(Test-Path -LiteralPath $checkpointPath)) {
    throw "Interface scaffold release checkpoint JSON not found: $checkpointPath"
}

$status = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"

$safetyErrors = @()
if ($status.bridge_routing_network_transport_dry_run_invocation_path_only -ne $true) { $safetyErrors += "status does not report bridge_routing_network_transport_dry_run_invocation_path_only=true" }
if ($status.real_bridge_http_client_implemented -ne $false) { $safetyErrors += "real_bridge_http_client_implemented is not false" }
if ($status.network_transport_implemented -ne $false) { $safetyErrors += "network_transport_implemented is not false" }
if ($status.network_transport_enabled -ne $false) { $safetyErrors += "network_transport_enabled is not false" }
if ($status.network_transport_armed -ne $false) { $safetyErrors += "network_transport_armed is not false" }
if ($status.network_socket_opened -ne $false) { $safetyErrors += "network_socket_opened is not false" }
if ($status.bridge_http_client_implemented -ne $false) { $safetyErrors += "bridge_http_client_implemented is not false" }
if ($status.bridge_post_call_implemented -ne $false) { $safetyErrors += "bridge_post_call_implemented is not false" }
if ($status.bridge_post_called -ne $false) { $safetyErrors += "bridge_post_called is not false" }
if ($status.bridge_mutation_performed -ne $false) { $safetyErrors += "bridge_mutation_performed is not false" }
if ($status.platform_db_mutation_performed -ne $false) { $safetyErrors += "platform_db_mutation_performed is not false" }
if ($status.lacrm_call_performed -ne $false) { $safetyErrors += "lacrm_call_performed is not false" }
if ($status.routing_write_endpoint_implemented -ne $false) { $safetyErrors += "routing_write_endpoint_implemented is not false" }

$body = @{
    interface_scaffold_release_checkpoint_path = $checkpointPath
    operator_name = $OperatorName
    transport_confirmation_phrase = $TransportConfirmationPhrase
}

$result = Invoke-PlatformJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/preview" -Method "POST" -Body $body

if ($result.safety.bridge_routing_network_transport_dry_run_invocation_path_only -ne $true) { $safetyErrors += "preview does not report bridge_routing_network_transport_dry_run_invocation_path_only=true" }
if ($result.safety.real_bridge_http_client_implemented -ne $false) { $safetyErrors += "preview says real_bridge_http_client_implemented is not false" }
if ($result.safety.network_transport_implemented -ne $false) { $safetyErrors += "preview says network_transport_implemented is not false" }
if ($result.safety.network_transport_enabled -ne $false) { $safetyErrors += "preview says network_transport_enabled is not false" }
if ($result.safety.network_transport_armed -ne $false) { $safetyErrors += "preview says network_transport_armed is not false" }
if ($result.safety.network_socket_opened -ne $false) { $safetyErrors += "preview says network_socket_opened is not false" }
if ($result.safety.bridge_post_call_implemented -ne $false) { $safetyErrors += "preview says bridge_post_call_implemented is not false" }
if ($result.safety.bridge_post_called -ne $false) { $safetyErrors += "preview says bridge_post_called is not false" }
if ($result.safety.bridge_mutation_performed -ne $false) { $safetyErrors += "preview says bridge_mutation_performed is not false" }
if ($result.safety.platform_db_mutation_performed -ne $false) { $safetyErrors += "preview says platform_db_mutation_performed is not false" }
if ($result.safety.lacrm_call_performed -ne $false) { $safetyErrors += "preview says lacrm_call_performed is not false" }
if ($result.blocked -ne $true) { $safetyErrors += "preview is not blocked" }
if ($result.would_add_network_transport -ne $false) { $safetyErrors += "preview says would_add_network_transport is not false" }
if ($result.would_open_socket -ne $false) { $safetyErrors += "preview says would_open_socket is not false" }
if ($result.would_send_http_request -ne $false) { $safetyErrors += "preview says would_send_http_request is not false" }
if ($result.would_call_bridge -ne $false) { $safetyErrors += "preview says would_call_bridge is not false" }

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 19"
    purpose = "Bridge routing network transport dry-run invocation path"
    source_interface_scaffold_release_checkpoint = $checkpointPath
    platform_api = $PlatformApi
    safety = [ordered]@{
        bridge_routing_network_transport_dry_run_invocation_path_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        real_bridge_http_client_implemented = $false
        network_transport_implemented = $false
        network_transport_enabled = $false
        network_transport_armed = $false
        network_socket_opened = $false
        bridge_http_client_implemented = $false
        bridge_post_call_implemented = $false
        routing_write_endpoint_implemented = $false
        live_write_enabled = $false
    }
    status = $status
    preview = $result
    safety_errors = $safetyErrors
    counts = [ordered]@{
        blockers = @($result.blockers).Count
        safety_errors = $safetyErrors.Count
        request_fields = @($result.invocation_path_contract.request_shape).Count
        result_fields = @($result.invocation_path_contract.result_shape).Count
    }
    next_recommended_actions = @(
        "Review the dry-run invocation path before adding any real transport adapter.",
        "Do not call bridge POST endpoints from Phase 20 Step 19.",
        "Do not add requests/httpx bridge calls or open sockets in this step.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path.json"
$contractCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_contract.csv"
$blockersCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_blockers.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_dry_run_invocation_path.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

@(
    [ordered]@{
        invocation_path_name = $result.invocation_path_contract.invocation_path_name
        implementation_kind = $result.invocation_path_contract.implementation_kind
        source_interface = $result.invocation_path_contract.source_interface
        transport_mode = $result.invocation_path_contract.transport_mode
        execution_behavior = $result.invocation_path_contract.execution_behavior
        network_transport_implemented = $result.invocation_path_contract.network_transport_implemented
        network_socket_opened = $result.invocation_path_contract.network_socket_opened
        would_open_socket = $result.invocation_path_contract.would_open_socket
        would_send_http_request = $result.invocation_path_contract.would_send_http_request
        would_call_bridge = $result.invocation_path_contract.would_call_bridge
        bridge_post_called = $false
        contract_hash = $result.invocation_path_contract_hash
    }
) | Export-Csv -LiteralPath $contractCsvPath -NoTypeInformation -Encoding UTF8

@($result.blockers) | ForEach-Object {
    [ordered]@{ blocker = $_ }
} | Export-Csv -LiteralPath $blockersCsvPath -NoTypeInformation -Encoding UTF8

$safetyText = if ($safetyErrors.Count -gt 0) { ($safetyErrors | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }
$blockerText = if (@($result.blockers).Count -gt 0) { (@($result.blockers) | ForEach-Object { "- $_" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Dry-run Invocation Path

Generated: $($report.generated_at)

Source interface scaffold release checkpoint:

``````
$checkpointPath
``````

## Safety

- Bridge routing network transport dry-run invocation path only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Real bridge HTTP client implemented: false
- Network transport implemented: false
- Network transport enabled: false
- Network transport armed: false
- Network socket opened: false
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
    Write-Host "PASS | bridge_routing_network_transport_dry_run_invocation_path=$OutputDir | blocked=$($result.blocked) | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_dry_run_invocation_path=$OutputDir | safety_errors=$($safetyErrors.Count) | bridge_post_called=False"
}

Write-Host ""
Write-Host "Network transport dry-run invocation path files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
