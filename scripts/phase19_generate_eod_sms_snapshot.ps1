param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$OutputPath = "",
    [string]$MarkdownPath = ""
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

function Try-GetText {
    param([string]$Url)
    try {
        return @{ ok = $true; value = (Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 20).Content; error = "" }
    } catch {
        return @{ ok = $false; value = ""; error = $_.Exception.Message }
    }
}

function Count-Items {
    param($Value)
    if (!$Value) { return 0 }
    if ($Value -is [System.Array]) { return @($Value).Count }
    foreach ($key in @("items", "batches", "results", "queue", "sms_batches")) {
        if ($Value.$key -is [System.Array]) { return @($Value.$key).Count }
    }
    return 0
}

function Preview-Batches {
    param($Value, [int]$Limit = 20)
    $items = @()
    if ($Value -is [System.Array]) { $items = @($Value) }
    elseif ($Value) {
        foreach ($key in @("items", "batches", "results", "queue", "sms_batches")) {
            if ($Value.$key -is [System.Array]) {
                $items = @($Value.$key)
                break
            }
        }
    }

    $preview = @()
    foreach ($item in ($items | Select-Object -First $Limit)) {
        $preview += [ordered]@{
            id = $item.id
            batch_date = $item.batch_date
            external_phone = $item.external_phone
            internal_phone = $item.internal_phone
            latest_message_at = $item.latest_message_at
            status = $item.status
            has_summary = -not [string]::IsNullOrWhiteSpace([string]$item.summary)
            has_next_steps = -not [string]::IsNullOrWhiteSpace([string]$item.next_steps)
            auto_attached = $item.auto_attached
        }
    }
    return $preview
}

function Test-Port {
    param([int]$Port)
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
        return $null -ne $conn
    } catch {
        return $false
    }
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$bridgeHtml = Try-GetText $BridgeUrl
$bridgeHealth = Try-GetJson "$BridgeUrl/health"
$activeBatches = Try-GetJson "$BridgeUrl/api/sms/batches?view=active"
$processedBatches = Try-GetJson "$BridgeUrl/api/sms/batches?view=processed"
$platformHealth = Try-GetJson "$PlatformApi/health"
$platformReview = Try-GetJson "$PlatformApi/front-desk/bridge-review-summary"
$platformThreads = Try-GetJson "$PlatformApi/front-desk/sms-threads?limit=50"
$textQuality = Try-GetJson "$PlatformApi/front-desk/text-quality/summary?sample_limit=5"
$lacrmSafety = Try-GetJson "$PlatformApi/front-desk/lacrm-apply/status"

$markers = [ordered]@{
    data_hub_title = $bridgeHtml.ok -and $bridgeHtml.value -match "Keys Pool Service Data Hub"
    run_eod_button = $bridgeHtml.ok -and $bridgeHtml.value -match "runEodBtn"
    text_summaries_tab = $bridgeHtml.ok -and $bridgeHtml.value -match "Text summaries"
    force_batch_button = $bridgeHtml.ok -and $bridgeHtml.value -match "forceBatchBtn"
    sms_summary_text = $bridgeHtml.ok -and $bridgeHtml.value -match "smsSummaryText"
    sms_next_steps_text = $bridgeHtml.ok -and $bridgeHtml.value -match "smsNextStepsText"
}

$activeCount = if ($activeBatches.ok) { Count-Items $activeBatches.value } else { 0 }
$processedCount = if ($processedBatches.ok) { Count-Items $processedBatches.value } else { 0 }

$platformThreadCount = 0
if ($platformThreads.ok -and $platformThreads.value) {
    if ($platformThreads.value.sms_threads -is [System.Array]) { $platformThreadCount = @($platformThreads.value.sms_threads).Count }
    elseif ($platformThreads.value.threads -is [System.Array]) { $platformThreadCount = @($platformThreads.value.threads).Count }
}

$liveEnabled = $false
$liveArmed = $false
if ($lacrmSafety.ok -and $lacrmSafety.value) {
    $liveEnabled = [bool]$lacrmSafety.value.live_write_enabled
    $liveArmed = [bool]$lacrmSafety.value.live_write_armed
}

$snapshot = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 21"
    purpose = "Read-only end-of-day SMS batch parity snapshot"
    app_map = [ordered]@{
        streamlit_dashboard = "http://127.0.0.1:8501"
        fastapi_backend = $PlatformApi
        original_bridge_data_hub = $BridgeUrl
    }
    runtime = [ordered]@{
        fastapi_ok = $platformHealth.ok -and $platformHealth.value.status -eq "ok"
        bridge_ok = $bridgeHealth.ok
        streamlit_port_listening = Test-Port 8501
        bridge_port_listening = Test-Port 8000
        fastapi_port_listening = Test-Port 8010
    }
    bridge_ui_markers = $markers
    bridge_sms_batches = [ordered]@{
        active_count = $activeCount
        processed_count = $processedCount
        active_preview = if ($activeBatches.ok) { Preview-Batches $activeBatches.value 25 } else { @() }
        processed_preview = if ($processedBatches.ok) { Preview-Batches $processedBatches.value 25 } else { @() }
    }
    platform_context = [ordered]@{
        bridge_review_summary_ok = $platformReview.ok
        bridge_review_summary = if ($platformReview.ok) { $platformReview.value } else { $null }
        platform_sms_thread_preview_count = $platformThreadCount
        text_quality_ok = $textQuality.ok
        text_quality_summary = if ($textQuality.ok) { $textQuality.value } else { $null }
    }
    lacrm_safety = [ordered]@{
        status_endpoint_ok = $lacrmSafety.ok
        live_write_enabled = $liveEnabled
        live_write_armed = $liveArmed
        default_mode = if ($lacrmSafety.ok -and $lacrmSafety.value) { $lacrmSafety.value.default_mode } else { "" }
    }
    parity_status = [ordered]@{
        original_eod_button_present_on_bridge = [bool]$markers.run_eod_button
        original_text_summary_ui_present_on_bridge = [bool]$markers.text_summaries_tab
        platform_eod_snapshot_page_added = $true
        read_only_only = $true
        bridge_batch_mutation_performed = $false
        bridge_force_batch_called = $false
        bridge_run_eod_called = $false
        lacrm_call_performed = $false
    }
    next_recommended_actions = @(
        "Add platform-side read-only grouping of EOD SMS batches by date/status.",
        "Design a dry-run-only platform EOD rebuild preview before any bridge mutation.",
        "Map bridge summary/next_steps fields into platform review events with provenance.",
        "Keep bridge runEodBtn as the operational write path until explicit parity cutover."
    )
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputPath = Join-Path $BackupDir "phase19_eod_sms_snapshot_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownPath)) {
    $MarkdownPath = [System.IO.Path]::ChangeExtension($OutputPath, ".md")
}

$snapshot | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

$md = @"
# Phase 19 EOD SMS Snapshot

Generated: $($snapshot.generated_at)

## Runtime

- FastAPI OK: $($snapshot.runtime.fastapi_ok)
- Bridge OK: $($snapshot.runtime.bridge_ok)
- Bridge EOD button present: $($snapshot.bridge_ui_markers.run_eod_button)
- Bridge text summaries tab present: $($snapshot.bridge_ui_markers.text_summaries_tab)

## Counts

- Active bridge SMS batches: $activeCount
- Processed bridge SMS batches: $processedCount
- Platform SMS thread preview count: $platformThreadCount

## Safety

- Read-only only: true
- Bridge batch mutation performed: false
- Bridge force batch called: false
- Bridge run EOD called: false
- LACRM call performed: false
- Live write enabled: $liveEnabled
- Live write armed: $liveArmed

## Next recommended actions

$($snapshot.next_recommended_actions | ForEach-Object { "- $_" } | Out-String)
"@

$md | Set-Content -LiteralPath $MarkdownPath -Encoding UTF8

if ($bridgeHealth.ok -and $markers.run_eod_button -and $markers.text_summaries_tab -and !$liveEnabled -and !$liveArmed) {
    Write-Host "PASS | eod_sms_snapshot=$OutputPath | bridge_eod=True | active_batches=$activeCount | live_writes_off=True"
} else {
    Write-Host "CHECK | eod_sms_snapshot=$OutputPath | bridge_ok=$($bridgeHealth.ok) | eod=$($markers.run_eod_button) | textTab=$($markers.text_summaries_tab) | active_batches=$activeCount | liveEnabled=$liveEnabled | armed=$liveArmed"
}
