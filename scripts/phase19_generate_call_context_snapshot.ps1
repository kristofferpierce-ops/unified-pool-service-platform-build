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

function Count-BridgeItems {
    param($Value)
    if (!$Value) { return 0 }
    if ($Value -is [System.Array]) { return @($Value).Count }
    if ($Value.items) { return @($Value.items).Count }
    if ($Value.calls) { return @($Value.calls).Count }
    if ($Value.queue) { return @($Value.queue).Count }
    return 0
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$bridgeHtml = Try-GetText $BridgeUrl
$bridgeHealth = Try-GetJson "$BridgeUrl/health"
$bridgeActiveCalls = Try-GetJson "$BridgeUrl/api/calls?view=active"
$bridgeProcessedCalls = Try-GetJson "$BridgeUrl/api/calls?view=processed"
$bridgeSmsActive = Try-GetJson "$BridgeUrl/api/sms/batches?view=active"

$platformHealth = Try-GetJson "$PlatformApi/health"
$platformQueue = Try-GetJson "$PlatformApi/front-desk/queue"
$platformReview = Try-GetJson "$PlatformApi/front-desk/bridge-review-summary"
$lacrmSafety = Try-GetJson "$PlatformApi/front-desk/lacrm-apply/status"

$markers = [ordered]@{
    data_hub_title = $bridgeHtml.ok -and $bridgeHtml.value -match "Keys Pool Service Data Hub"
    incoming_hud = $bridgeHtml.ok -and $bridgeHtml.value -match "incomingHud"
    hud_caller_title = $bridgeHtml.ok -and $bridgeHtml.value -match "hudCallerTitle"
    hud_history_list = $bridgeHtml.ok -and $bridgeHtml.value -match "hudHistoryList"
    calls_tab = $bridgeHtml.ok -and $bridgeHtml.value -match "Calls \+ voicemail"
    create_task_button = $bridgeHtml.ok -and $bridgeHtml.value -match "callCreateTaskBtn"
    manual_search = $bridgeHtml.ok -and $bridgeHtml.value -match "callSearchInput"
}

$activeCallCount = if ($bridgeActiveCalls.ok) { Count-BridgeItems $bridgeActiveCalls.value } else { 0 }
$processedCallCount = if ($bridgeProcessedCalls.ok) { Count-BridgeItems $bridgeProcessedCalls.value } else { 0 }
$smsBatchCount = if ($bridgeSmsActive.ok) { Count-BridgeItems $bridgeSmsActive.value } else { 0 }

$liveEnabled = $false
$liveArmed = $false
if ($lacrmSafety.ok -and $lacrmSafety.value) {
    $liveEnabled = [bool]$lacrmSafety.value.live_write_enabled
    $liveArmed = [bool]$lacrmSafety.value.live_write_armed
}

$snapshot = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 20"
    purpose = "Read-only incoming call/HUD context parity snapshot"
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
    bridge_readonly_counts = [ordered]@{
        active_calls_visible = $activeCallCount
        processed_calls_visible = $processedCallCount
        active_sms_batches_visible = $smsBatchCount
    }
    platform_context = [ordered]@{
        queue_endpoint_ok = $platformQueue.ok
        bridge_review_summary_ok = $platformReview.ok
        bridge_review_summary = if ($platformReview.ok) { $platformReview.value } else { $null }
    }
    lacrm_safety = [ordered]@{
        status_endpoint_ok = $lacrmSafety.ok
        live_write_enabled = $liveEnabled
        live_write_armed = $liveArmed
        default_mode = if ($lacrmSafety.ok -and $lacrmSafety.value) { $lacrmSafety.value.default_mode } else { "" }
    }
    parity_status = [ordered]@{
        original_hud_present_on_bridge = [bool]$markers.incoming_hud
        platform_call_context_page_added = $true
        read_only_only = $true
        bridge_mutation_performed = $false
        lacrm_call_performed = $false
    }
    next_recommended_actions = @(
        "Add platform-side call queue storage only after read-only snapshots are stable.",
        "Map bridge call/voicemail fields to platform CommunicationEvent and CallSession tables.",
        "Add operator approval before any CRM note/task apply from call context.",
        "Keep the original bridge HUD on 8000 until full parity is confirmed."
    )
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputPath = Join-Path $BackupDir "phase19_call_context_snapshot_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownPath)) {
    $MarkdownPath = [System.IO.Path]::ChangeExtension($OutputPath, ".md")
}

$snapshot | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

$md = @"
# Phase 19 Call Context Snapshot

Generated: $($snapshot.generated_at)

## Runtime

- FastAPI OK: $($snapshot.runtime.fastapi_ok)
- Bridge OK: $($snapshot.runtime.bridge_ok)
- Bridge HUD marker present: $($snapshot.bridge_ui_markers.incoming_hud)

## Counts

- Active bridge calls: $activeCallCount
- Processed bridge calls: $processedCallCount
- Active SMS batches: $smsBatchCount

## Safety

- Read-only only: true
- Bridge mutation performed: false
- LACRM call performed: false
- Live write enabled: $liveEnabled
- Live write armed: $liveArmed

## Next recommended actions

$($snapshot.next_recommended_actions | ForEach-Object { "- $_" } | Out-String)
"@

$md | Set-Content -LiteralPath $MarkdownPath -Encoding UTF8

if ($bridgeHealth.ok -and $markers.incoming_hud -and !$liveEnabled -and !$liveArmed) {
    Write-Host "PASS | call_context_snapshot=$OutputPath | bridge_hud=True | active_calls=$activeCallCount | live_writes_off=True"
} else {
    Write-Host "CHECK | call_context_snapshot=$OutputPath | bridge_ok=$($bridgeHealth.ok) | bridge_hud=$($markers.incoming_hud) | active_calls=$activeCallCount | liveEnabled=$liveEnabled | armed=$liveArmed"
}
