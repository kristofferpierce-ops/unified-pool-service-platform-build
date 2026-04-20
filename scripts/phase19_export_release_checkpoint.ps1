param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$StreamlitUrl = "http://127.0.0.1:8501",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

$PlatformDir = Join-Path $Workspace "unified_pool_service_platform_build"
$ExtractorDir = Join-Path $Workspace "start_here_extractor_m1_completion"
$BridgeLiveDir = Join-Path $Workspace "front_desk_bridge"
$BridgeRepoDir = Join-Path $Workspace "front_desk_bridge_repo"
$BackupDir = Join-Path $Workspace "backups"

function Get-GitInfo {
    param([string]$Path)
    if (!(Test-Path -LiteralPath (Join-Path $Path ".git"))) {
        return @{
            path = $Path
            is_git_repo = $false
            branch = ""
            remote = ""
            status_short = @()
        }
    }

    $branch = (& git -C $Path branch --show-current 2>$null | Out-String).Trim()
    $remote = (& git -C $Path remote -v 2>$null | Out-String).Trim()
    $status = @(& git -C $Path status --short 2>$null)

    return @{
        path = $Path
        is_git_repo = $true
        branch = $branch
        remote = $remote
        status_short = $status
    }
}

function Try-GetJson {
    param([string]$Url)
    try {
        $value = Invoke-RestMethod $Url -TimeoutSec 15
        return @{ ok = $true; value = $value; error = "" }
    } catch {
        return @{ ok = $false; value = $null; error = $_.Exception.Message }
    }
}

function Try-GetText {
    param([string]$Url)
    try {
        $value = (Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 15).Content
        return @{ ok = $true; value = $value; error = "" }
    } catch {
        return @{ ok = $false; value = ""; error = $_.Exception.Message }
    }
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$health = Try-GetJson "$PlatformApi/health"
$ingestion = Try-GetJson "$PlatformApi/connectors/ringcentral/ingestion-status"
$safety = Try-GetJson "$PlatformApi/front-desk/lacrm-apply/status"
$liveReadiness = Try-GetJson "$PlatformApi/front-desk/lacrm-apply/live-readiness"
$textQuality = Try-GetJson "$PlatformApi/front-desk/text-quality/summary?sample_limit=5"
$bridge = Try-GetText $BridgeUrl
$streamlit = Try-GetText $StreamlitUrl

$bridgeOriginal = $bridge.ok -and $bridge.value -match "Keys Pool Service Data Hub" -and $bridge.value -match "incomingHud" -and $bridge.value -match "Search LACRM"
$streamlitReachable = $streamlit.ok -and $streamlit.value -match "Streamlit"
$liveOff = $safety.ok -and ($safety.value.live_write_enabled -eq $false) -and ($safety.value.live_write_armed -eq $false)

$platformStatus = Get-GitInfo $PlatformDir
$bridgeRepoStatus = Get-GitInfo $BridgeRepoDir
$extractorStatus = Get-GitInfo $ExtractorDir

$blockedPatterns = @(
    "data/unified_pool_service_platform.db",
    ".env",
    ".venv",
    "front_desk_bridge",
    "front_desk_bridge_repo",
    "app/services/replaster_quote.py",
    "docs/26_REPLASTER_QUOTE_TOOL_PLAN.md",
    "tests/test_replaster_quote.py",
    "ui/pages/13_Replaster_Quote.py"
)

$platformStatusText = ($platformStatus.status_short -join "`n")
$blockedVisible = @()
foreach ($pattern in $blockedPatterns) {
    if ($platformStatusText -like "*$pattern*") {
        $blockedVisible += $pattern
    }
}

$checkpoint = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 15"
    workspace = $Workspace
    app_map = [ordered]@{
        streamlit_dashboard = $StreamlitUrl
        fastapi_backend = $PlatformApi
        original_bridge_data_hub = $BridgeUrl
    }
    runtime = [ordered]@{
        fastapi_health_ok = $health.ok
        fastapi_health = $health.value
        streamlit_reachable = $streamlitReachable
        bridge_original_data_hub = $bridgeOriginal
    }
    integration = [ordered]@{
        ingestion_ok = $ingestion.ok
        ingestion_status = $ingestion.value
        text_quality_ok = $textQuality.ok
        text_quality_summary = $textQuality.value
    }
    lacrm_safety = [ordered]@{
        status_ok = $safety.ok
        status = $safety.value
        live_readiness_ok = $liveReadiness.ok
        live_readiness = $liveReadiness.value
        live_writes_off = $liveOff
    }
    git = [ordered]@{
        platform = $platformStatus
        bridge_repo = $bridgeRepoStatus
        extractor = $extractorStatus
        blocked_patterns_visible_in_platform_status = $blockedVisible
    }
    recommendation = [ordered]@{
        commit_database = $false
        commit_env_files = $false
        live_lacrm_apply_allowed = $false
        bridge_repo_should_remain_separate = $true
    }
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputPath = Join-Path $BackupDir "phase19_release_checkpoint_$stamp.json"
}

$checkpoint | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

$ingSms = 0
if ($ingestion.ok -and $ingestion.value -and $ingestion.value.sms_messages_total) {
    $ingSms = [int]$ingestion.value.sms_messages_total
}

if ($health.ok -and $bridgeOriginal -and $streamlitReachable -and $liveOff -and $ingSms -ge 1) {
    Write-Host "PASS | checkpoint=$OutputPath | FastAPI=ok | Streamlit=ok | Bridge=original Data Hub | SMS=$ingSms | live_writes_off=True"
} else {
    Write-Host "CHECK | checkpoint=$OutputPath | FastAPI=$($health.ok) | Streamlit=$streamlitReachable | BridgeOriginal=$bridgeOriginal | SMS=$ingSms | liveOff=$liveOff"
}
