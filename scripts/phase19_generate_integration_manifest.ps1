param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$OutputPath = "",
    [string]$MarkdownPath = ""
)

$ErrorActionPreference = "Stop"

$PlatformDir = Join-Path $Workspace "unified_pool_service_platform_build"
$BridgeLiveDir = Join-Path $Workspace "front_desk_bridge"
$BridgeRepoDir = Join-Path $Workspace "front_desk_bridge_repo"
$ExtractorDir = Join-Path $Workspace "start_here_extractor_m1_completion"
$BackupDir = Join-Path $Workspace "backups"

function Get-GitInfo {
    param([string]$Path)

    if (!(Test-Path -LiteralPath $Path)) {
        return @{
            path = $Path
            exists = $false
            is_git_repo = $false
            branch = ""
            head = ""
            remote = ""
            status_short = @("missing")
        }
    }

    if (!(Test-Path -LiteralPath (Join-Path $Path ".git"))) {
        return @{
            path = $Path
            exists = $true
            is_git_repo = $false
            branch = ""
            head = ""
            remote = ""
            status_short = @("not a git repo")
        }
    }

    $branch = (& git -C $Path branch --show-current 2>$null | Out-String).Trim()
    $head = (& git -C $Path rev-parse --short HEAD 2>$null | Out-String).Trim()
    $remote = (& git -C $Path remote -v 2>$null | Out-String).Trim()
    $status = @(& git -C $Path status --short 2>$null)

    return @{
        path = $Path
        exists = $true
        is_git_repo = $true
        branch = $branch
        head = $head
        remote = $remote
        status_short = $status
    }
}

function Get-LatestFile {
    param([string]$Filter)
    $item = Get-ChildItem -LiteralPath $BackupDir -Filter $Filter -File -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($item) { return $item.FullName }
    return ""
}

function Get-LatestDir {
    param([string]$Filter)
    $item = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter $Filter -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($item) { return $item.FullName }
    return ""
}

function Get-JsonFile {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path) -or !(Test-Path -LiteralPath $Path)) { return $null }
    try {
        return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    } catch {
        return $null
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

function Try-GetText {
    param([string]$Url)
    try {
        return @{
            ok = $true
            value = (Invoke-WebRequest $Url -UseBasicParsing -TimeoutSec 10).Content
            error = ""
        }
    } catch {
        return @{ ok = $false; value = ""; error = $_.Exception.Message }
    }
}

function Try-GetJson {
    param([string]$Url)
    try {
        return @{
            ok = $true
            value = Invoke-RestMethod $Url -TimeoutSec 10
            error = ""
        }
    } catch {
        return @{ ok = $false; value = $null; error = $_.Exception.Message }
    }
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$latestCheckpoint = Get-LatestFile "phase19_release_checkpoint_*.json"
$latestEvidenceDir = Get-LatestDir "phase19_extractor_evidence_*"
$latestEvidenceIndex = ""
if ($latestEvidenceDir) {
    $candidate = Join-Path $latestEvidenceDir "phase19_evidence_index.json"
    if (Test-Path -LiteralPath $candidate) { $latestEvidenceIndex = $candidate }
}

$checkpointJson = Get-JsonFile $latestCheckpoint
$evidenceJson = Get-JsonFile $latestEvidenceIndex

$api = Try-GetJson "http://127.0.0.1:8010/health"
$ingestion = Try-GetJson "http://127.0.0.1:8010/connectors/ringcentral/ingestion-status"
$safety = Try-GetJson "http://127.0.0.1:8010/front-desk/lacrm-apply/status"
$bridge = Try-GetText "http://127.0.0.1:8000"
$streamlit = Try-GetText "http://127.0.0.1:8501"

$bridgeOriginal = $bridge.ok -and $bridge.value -match "Keys Pool Service Data Hub" -and $bridge.value -match "incomingHud" -and $bridge.value -match "Search LACRM"
$streamlitOk = $streamlit.ok -and $streamlit.value -match "Streamlit"
$apiOk = $api.ok -and $api.value.status -eq "ok"

$platformGit = Get-GitInfo $PlatformDir
$bridgeRepoGit = Get-GitInfo $BridgeRepoDir
$extractorGit = Get-GitInfo $ExtractorDir
$bridgeLiveGit = Get-GitInfo $BridgeLiveDir

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
$platformStatusText = ($platformGit.status_short -join "`n")
$blockedVisible = @()
foreach ($pattern in $blockedPatterns) {
    if ($platformStatusText -like "*$pattern*") { $blockedVisible += $pattern }
}

$smsMessages = 0
$smsThreads = 0
if ($ingestion.ok -and $ingestion.value) {
    if ($ingestion.value.sms_messages_total) { $smsMessages = [int]$ingestion.value.sms_messages_total }
    if ($ingestion.value.sms_threads_total) { $smsThreads = [int]$ingestion.value.sms_threads_total }
}

$liveEnabled = $false
$liveArmed = $false
if ($safety.ok -and $safety.value) {
    $liveEnabled = [bool]$safety.value.live_write_enabled
    $liveArmed = [bool]$safety.value.live_write_armed
}

$ready = $apiOk -and $streamlitOk -and $bridgeOriginal -and ($smsMessages -ge 1) -and (-not $liveEnabled) -and (-not $liveArmed) -and ($platformGit.is_git_repo) -and ($bridgeRepoGit.is_git_repo) -and ($extractorGit.is_git_repo) -and ($latestCheckpoint -ne "") -and ($latestEvidenceIndex -ne "")

$manifest = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 18"
    workspace = $Workspace
    app_map = [ordered]@{
        streamlit_dashboard = "http://127.0.0.1:8501"
        fastapi_backend = "http://127.0.0.1:8010"
        original_bridge_data_hub = "http://127.0.0.1:8000"
    }
    runtime = [ordered]@{
        fastapi_ok = $apiOk
        streamlit_ok = $streamlitOk
        bridge_original_data_hub = $bridgeOriginal
        fastapi_port_listening = Test-Port 8010
        streamlit_port_listening = Test-Port 8501
        bridge_port_listening = Test-Port 8000
    }
    integration = [ordered]@{
        sms_messages_total = $smsMessages
        sms_threads_total = $smsThreads
        ingestion_endpoint_ok = $ingestion.ok
    }
    lacrm_safety = [ordered]@{
        status_endpoint_ok = $safety.ok
        live_write_enabled = $liveEnabled
        live_write_armed = $liveArmed
        default_mode = if ($safety.ok -and $safety.value) { $safety.value.default_mode } else { "" }
        status_counts = if ($safety.ok -and $safety.value) { $safety.value.status_counts } else { @{} }
    }
    repos = [ordered]@{
        platform = $platformGit
        bridge_repo = $bridgeRepoGit
        bridge_live_folder = $bridgeLiveGit
        extractor = $extractorGit
    }
    evidence = [ordered]@{
        latest_release_checkpoint = $latestCheckpoint
        latest_extractor_evidence_dir = $latestEvidenceDir
        latest_extractor_evidence_index = $latestEvidenceIndex
        checkpoint_phase = if ($checkpointJson) { $checkpointJson.phase } else { "" }
        evidence_index_version = if ($evidenceJson) { $evidenceJson.evidence_index_version } else { "" }
        evidence_safety_ok = if ($evidenceJson) { [bool]$evidenceJson.safety_ok } else { $false }
    }
    guardrails = [ordered]@{
        ready_for_next_phase = $ready
        platform_blocked_patterns_visible = $blockedVisible
        commit_database = $false
        commit_env_files = $false
        bridge_live_folder_is_not_repo_expected = -not $bridgeLiveGit.is_git_repo
        bridge_repo_should_remain_separate = $true
        live_lacrm_apply_allowed = $false
        lacrm_live_writes_allowed = $false
    }
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputPath = Join-Path $BackupDir "phase19_integration_manifest_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownPath)) {
    $MarkdownPath = [System.IO.Path]::ChangeExtension($OutputPath, ".md")
}

$manifest | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

$md = @"
# Phase 19 Integration Manifest

Generated: $($manifest.generated_at)

## App map

- Streamlit dashboard: http://127.0.0.1:8501
- FastAPI backend/API: http://127.0.0.1:8010
- Original KPS Bridge / Data Hub: http://127.0.0.1:8000

## Runtime

- FastAPI OK: $($manifest.runtime.fastapi_ok)
- Streamlit OK: $($manifest.runtime.streamlit_ok)
- Bridge original Data Hub: $($manifest.runtime.bridge_original_data_hub)

## Integration

- SMS messages: $($manifest.integration.sms_messages_total)
- SMS threads: $($manifest.integration.sms_threads_total)

## LACRM safety

- Live write enabled: $($manifest.lacrm_safety.live_write_enabled)
- Live write armed: $($manifest.lacrm_safety.live_write_armed)
- Default mode: $($manifest.lacrm_safety.default_mode)

## Repositories

- Platform branch: $($manifest.repos.platform.branch)
- Bridge repo branch: $($manifest.repos.bridge_repo.branch)
- Extractor branch: $($manifest.repos.extractor.branch)

## Evidence

- Release checkpoint: $($manifest.evidence.latest_release_checkpoint)
- Extractor evidence index: $($manifest.evidence.latest_extractor_evidence_index)
- Evidence safety OK: $($manifest.evidence.evidence_safety_ok)

## Guardrails

- Ready for next phase: $($manifest.guardrails.ready_for_next_phase)
- Commit database: false
- Commit env files: false
- LACRM live writes allowed: false
- Bridge live folder is not a Git repo: $($manifest.guardrails.bridge_live_folder_is_not_repo_expected)

Blocked platform status markers visible:

``````
$($manifest.guardrails.platform_blocked_patterns_visible -join "`n")
``````
"@

$md | Set-Content -LiteralPath $MarkdownPath -Encoding UTF8

if ($ready) {
    Write-Host "PASS | manifest=$OutputPath | markdown=$MarkdownPath | apps=ok | sms=$smsMessages | evidence=ok | live_writes_off=True"
} else {
    Write-Host "CHECK | manifest=$OutputPath | markdown=$MarkdownPath | FastAPI=$apiOk | Streamlit=$streamlitOk | Bridge=$bridgeOriginal | sms=$smsMessages | evidence=$($manifest.evidence.evidence_safety_ok) | liveEnabled=$liveEnabled | liveArmed=$liveArmed"
}

