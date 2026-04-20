param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$EvidenceDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

if ([string]::IsNullOrWhiteSpace($EvidenceDir)) {
    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter "phase19_extractor_evidence_*" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        throw "No phase19_extractor_evidence_* folder found in $BackupDir. Run Step 16 option 4 first."
    }

    $EvidenceDir = $latest.FullName
}

$IndexPath = Join-Path $EvidenceDir "phase19_evidence_index.json"
$SummaryPath = Join-Path $EvidenceDir "phase19_evidence_summary.json"
$RedactedPath = Join-Path $EvidenceDir "phase19_redacted_checkpoint.json"

foreach ($path in @($IndexPath, $SummaryPath, $RedactedPath)) {
    if (!(Test-Path -LiteralPath $path)) {
        throw "Evidence file missing: $path"
    }
}

$Index = Get-Content -LiteralPath $IndexPath -Raw | ConvertFrom-Json
$Summary = Get-Content -LiteralPath $SummaryPath -Raw | ConvertFrom-Json
$RedactedText = Get-Content -LiteralPath $RedactedPath -Raw

$PhoneLike = [regex]'(?<!\w)(?:\+?1[\s\-\.]?)?(?:\(?\d{3}\)?[\s\-\.]?)\d{3}[\s\-\.]?\d{4}(?!\w)'
$EmailLike = [regex]'(?i)\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b'

$PhoneLeak = $PhoneLike.IsMatch($RedactedText)
$EmailLeak = $EmailLike.IsMatch($RedactedText)

$SmsMessages = 0
if ($Summary.integration_counts -and $Summary.integration_counts.sms_messages_total) {
    $SmsMessages = [int]$Summary.integration_counts.sms_messages_total
}

$LiveEnabled = $false
$LiveArmed = $false
$ReadyLive = $false
if ($Summary.lacrm_safety) {
    $LiveEnabled = [bool]$Summary.lacrm_safety.live_write_enabled
    $LiveArmed = [bool]$Summary.lacrm_safety.live_write_armed
    $ReadyLive = [bool]$Summary.lacrm_safety.ready_for_live_apply
}

if ($Index.safety_ok -eq $true -and !$PhoneLeak -and !$EmailLeak -and !$LiveEnabled -and !$LiveArmed -and !$ReadyLive) {
    Write-Host "PASS | evidence=$EvidenceDir | sms=$SmsMessages | safety_ok=True | redacted=True | live_writes_off=True"
} else {
    Write-Host "CHECK | evidence=$EvidenceDir | sms=$SmsMessages | safety_ok=$($Index.safety_ok) | phone_leak=$PhoneLeak | email_leak=$EmailLeak | live_enabled=$LiveEnabled | armed=$LiveArmed | ready=$ReadyLive"
}

Write-Host ""
Write-Host "Evidence files:"
Get-ChildItem -LiteralPath $EvidenceDir -File | Select-Object Name, Length, LastWriteTime
