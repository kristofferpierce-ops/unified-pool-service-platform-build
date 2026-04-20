param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$OutputPath = "",
    [string]$MarkdownPath = ""
)

$ErrorActionPreference = "Stop"

$PlatformDir = Join-Path $Workspace "unified_pool_service_platform_build"
$BridgeLiveDir = Join-Path $Workspace "front_desk_bridge"
$BackupDir = Join-Path $Workspace "backups"

function Try-GetJson {
    param([string]$Url)
    try {
        return @{ ok = $true; value = Invoke-RestMethod $Url -TimeoutSec 15; error = "" }
    } catch {
        return @{ ok = $false; value = $null; error = $_.Exception.Message }
    }
}

function Try-GetText {
    param([string]$Url)
    try {
        return @{ ok = $true; value = (Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 15).Content; error = "" }
    } catch {
        return @{ ok = $false; value = ""; error = $_.Exception.Message }
    }
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

function Count-Items {
    param($Value, [string]$Property)
    if (!$Value) { return 0 }
    if ($Property -and $Value.$Property) { return @($Value.$Property).Count }
    if ($Value -is [System.Array]) { return @($Value).Count }
    return 0
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$bridgeHtml = Try-GetText $BridgeUrl
$bridgeHealth = Try-GetJson "$BridgeUrl/health"
$bridgeSms = Try-GetJson "$BridgeUrl/api/sms/batches?view=active"
$bridgeOutbox = Try-GetJson "$BridgeUrl/api/admin/platform_outbox/status"

$platformHealth = Try-GetJson "$PlatformApi/health"
$platformIngestion = Try-GetJson "$PlatformApi/connectors/ringcentral/ingestion-status"
$platformReview = Try-GetJson "$PlatformApi/front-desk/bridge-review-summary"
$platformThreads = Try-GetJson "$PlatformApi/front-desk/sms-threads?limit=50"
$lacrmSafety = Try-GetJson "$PlatformApi/front-desk/lacrm-apply/status"
$liveReadiness = Try-GetJson "$PlatformApi/front-desk/lacrm-apply/live-readiness"
$textQuality = Try-GetJson "$PlatformApi/front-desk/text-quality/summary?sample_limit=5"

$bridgeMarkers = [ordered]@{
    data_hub_title = $bridgeHtml.ok -and $bridgeHtml.value -match "Keys Pool Service Data Hub"
    incoming_hud = $bridgeHtml.ok -and $bridgeHtml.value -match "incomingHud"
    text_summaries_tab = $bridgeHtml.ok -and $bridgeHtml.value -match "Text summaries"
    lacrm_search = $bridgeHtml.ok -and $bridgeHtml.value -match "Search LACRM"
    task_modal = $bridgeHtml.ok -and $bridgeHtml.value -match "taskModal"
    eod_batch_button = $bridgeHtml.ok -and $bridgeHtml.value -match "runEodBtn"
}

$platformFeatureChecks = [ordered]@{
    bridge_review_summary_endpoint = $platformReview.ok
    sms_threads_endpoint = $platformThreads.ok
    lacrm_safety_endpoint = $lacrmSafety.ok
    live_readiness_endpoint = $liveReadiness.ok
    text_quality_endpoint = $textQuality.ok
    ingestion_diagnostics_endpoint = $platformIngestion.ok
}

$bridgeActiveSmsCount = 0
if ($bridgeSms.ok) {
    if ($bridgeSms.value -is [System.Array]) { $bridgeActiveSmsCount = @($bridgeSms.value).Count }
    elseif ($bridgeSms.value.items) { $bridgeActiveSmsCount = @($bridgeSms.value.items).Count }
    elseif ($bridgeSms.value.batches) { $bridgeActiveSmsCount = @($bridgeSms.value.batches).Count }
}

$platformSmsMessages = 0
$platformSmsThreads = 0
if ($platformIngestion.ok -and $platformIngestion.value) {
    if ($platformIngestion.value.sms_messages_total) { $platformSmsMessages = [int]$platformIngestion.value.sms_messages_total }
    if ($platformIngestion.value.sms_threads_total) { $platformSmsThreads = [int]$platformIngestion.value.sms_threads_total }
}

$platformReviewThreads = 0
if ($platformThreads.ok -and $platformThreads.value) {
    if ($platformThreads.value.sms_threads) { $platformReviewThreads = @($platformThreads.value.sms_threads).Count }
    elseif ($platformThreads.value.threads) { $platformReviewThreads = @($platformThreads.value.threads).Count }
}

$liveWriteEnabled = $false
$liveWriteArmed = $false
if ($lacrmSafety.ok -and $lacrmSafety.value) {
    $liveWriteEnabled = [bool]$lacrmSafety.value.live_write_enabled
    $liveWriteArmed = [bool]$lacrmSafety.value.live_write_armed
}

$matrix = @(
    [ordered]@{ capability = "Original bridge/Data Hub UI"; source = "Bridge"; status = if ($bridgeMarkers.data_hub_title) { "present" } else { "check" }; target = "Keep on 8000 until explicit parity replacement"; evidence = "Keys Pool Service Data Hub marker" },
    [ordered]@{ capability = "Incoming call HUD"; source = "Bridge"; status = if ($bridgeMarkers.incoming_hud) { "bridge_only" } else { "missing" }; target = "Later platform parity slice"; evidence = "incomingHud marker" },
    [ordered]@{ capability = "RingCentral SMS ingestion"; source = "Bridge -> Platform"; status = if ($bridgeOutbox.ok -and $platformSmsMessages -ge 1) { "integrated" } else { "check" }; target = "Continue event outbox path"; evidence = "platform sms_messages_total=$platformSmsMessages" },
    [ordered]@{ capability = "Platform bridge SMS review"; source = "Platform"; status = if ($platformThreads.ok) { "present" } else { "check" }; target = "Streamlit Bridge Review page"; evidence = "/front-desk/sms-threads" },
    [ordered]@{ capability = "LACRM candidate search/import"; source = "Platform"; status = if ($platformFeatureChecks.lacrm_safety_endpoint) { "present" } else { "check" }; target = "Keep dry-run until live cutover"; evidence = "LACRM safety endpoint" },
    [ordered]@{ capability = "Guarded LACRM apply"; source = "Platform"; status = if (!$liveWriteEnabled -and !$liveWriteArmed) { "safe_dry_run" } else { "review" }; target = "Live writes remain disabled"; evidence = "enabled=$liveWriteEnabled armed=$liveWriteArmed" },
    [ordered]@{ capability = "Apply audit"; source = "Platform"; status = if ($lacrmSafety.ok) { "present" } else { "check" }; target = "Continue audit-first workflow"; evidence = "/front-desk/lacrm-apply/status" },
    [ordered]@{ capability = "Text quality diagnostics"; source = "Platform"; status = if ($textQuality.ok) { "present" } else { "check" }; target = "Display-only cleanup"; evidence = "/front-desk/text-quality/summary" },
    [ordered]@{ capability = "Evidence pack"; source = "Extractor"; status = "external_verified_by_step16_17"; target = "Keep extractor as evidence/governance subsystem"; evidence = "See evidence index/manifest" },
    [ordered]@{ capability = "End-of-day text batch"; source = "Bridge"; status = if ($bridgeMarkers.eod_batch_button) { "bridge_only" } else { "check" }; target = "Later platform parity slice"; evidence = "runEodBtn marker" },
    [ordered]@{ capability = "Bridge CRM task modal"; source = "Bridge"; status = if ($bridgeMarkers.task_modal) { "bridge_only" } else { "check" }; target = "Platform has local tasks; live CRM writes guarded"; evidence = "taskModal marker" }
)

$summary = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 19"
    app_map = [ordered]@{
        streamlit_dashboard = "http://127.0.0.1:8501"
        fastapi_backend = $PlatformApi
        original_bridge_data_hub = $BridgeUrl
    }
    runtime = [ordered]@{
        fastapi_ok = $platformHealth.ok -and $platformHealth.value.status -eq "ok"
        bridge_ok = $bridgeHealth.ok
        streamlit_port_listening = Test-Port 8501
        bridge_original_markers = $bridgeMarkers
    }
    counts = [ordered]@{
        bridge_active_sms_batches_visible = $bridgeActiveSmsCount
        platform_sms_threads_total = $platformSmsThreads
        platform_sms_messages_total = $platformSmsMessages
        platform_review_threads_returned = $platformReviewThreads
    }
    safety = [ordered]@{
        live_write_enabled = $liveWriteEnabled
        live_write_armed = $liveWriteArmed
        live_apply_ready = if ($liveReadiness.ok -and $liveReadiness.value) { [bool]$liveReadiness.value.ready_for_live_apply } else { $false }
    }
    parity_matrix = $matrix
    next_recommended_slices = @(
        "Incoming call HUD parity/read-only call context in Streamlit",
        "Bridge end-of-day text batch parity or controlled platform equivalent",
        "Bridge routing rule migration review",
        "Operator task parity and CRM write cutover rehearsal"
    )
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputPath = Join-Path $BackupDir "phase19_bridge_parity_matrix_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownPath)) {
    $MarkdownPath = [System.IO.Path]::ChangeExtension($OutputPath, ".md")
}

$summary | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

$rows = $matrix | ForEach-Object {
    "| $($_.capability) | $($_.source) | $($_.status) | $($_.target) |"
}
$md = @"
# Phase 19 Bridge Parity Matrix

Generated: $($summary.generated_at)

## App map

- Streamlit dashboard: http://127.0.0.1:8501
- FastAPI backend/API: $PlatformApi
- Original bridge/Data Hub: $BridgeUrl

## Counts

- Bridge active SMS batches visible: $bridgeActiveSmsCount
- Platform SMS threads: $platformSmsThreads
- Platform SMS messages: $platformSmsMessages

## Safety

- Live write enabled: $liveWriteEnabled
- Live write armed: $liveWriteArmed

## Matrix

| Capability | Source | Status | Target |
|---|---|---|---|
$($rows -join "`n")

## Next recommended slices

$($summary.next_recommended_slices | ForEach-Object { "- $_" } | Out-String)
"@
$md | Set-Content -LiteralPath $MarkdownPath -Encoding UTF8

if (($platformHealth.ok) -and ($bridgeHealth.ok) -and $bridgeMarkers.data_hub_title -and ($platformSmsMessages -ge 1) -and !$liveWriteEnabled -and !$liveWriteArmed) {
    Write-Host "PASS | parity=$OutputPath | bridge_original=True | platform_sms=$platformSmsMessages | live_writes_off=True"
} else {
    Write-Host "CHECK | parity=$OutputPath | fastapi=$($platformHealth.ok) | bridge=$($bridgeHealth.ok) | bridgeOriginal=$($bridgeMarkers.data_hub_title) | platform_sms=$platformSmsMessages | liveEnabled=$liveWriteEnabled | armed=$liveWriteArmed"
}
