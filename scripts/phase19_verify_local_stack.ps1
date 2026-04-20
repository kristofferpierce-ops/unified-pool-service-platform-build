param(
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$StreamlitUrl = "http://127.0.0.1:8501",
    [string]$BridgeUrl = "http://127.0.0.1:8000"
)
$ErrorActionPreference = "Stop"
try {
    $api = Invoke-RestMethod "$PlatformApi/health" -TimeoutSec 15
    $ing = Invoke-RestMethod "$PlatformApi/connectors/ringcentral/ingestion-status" -TimeoutSec 15
    $safety = Invoke-RestMethod "$PlatformApi/front-desk/lacrm-apply/status" -TimeoutSec 15
    $stream = (Invoke-WebRequest $StreamlitUrl -UseBasicParsing -TimeoutSec 15).Content
    $bridge = (Invoke-WebRequest $BridgeUrl -UseBasicParsing -TimeoutSec 15).Content
    $streamOk = $stream -match "Streamlit"
    $bridgeOk = ($bridge -match "Keys Pool Service Data Hub" -and $bridge -match "incomingHud" -and $bridge -match "Search LACRM")
    $liveOff = ($safety.live_write_enabled -eq $false -and $safety.live_write_armed -eq $false)
    if ($api.status -eq "ok" -and $streamOk -and $bridgeOk -and $liveOff -and [int]$ing.sms_messages_total -ge 1) {
        "PASS | FastAPI=ok | Streamlit=ok | Bridge=original Data Hub | SMS=$($ing.sms_messages_total) | live_enabled=$($safety.live_write_enabled) | armed=$($safety.live_write_armed)"
    } else {
        "CHECK | FastAPI=$($api.status) | Streamlit=$streamOk | BridgeOriginal=$bridgeOk | SMS=$($ing.sms_messages_total) | liveOff=$liveOff"
    }
} catch {
    "FAIL | $($_.Exception.Message)"
}
