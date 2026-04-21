param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"
$BridgeLiveDir = Join-Path $Workspace "front_desk_bridge"
$BridgeRepoDir = Join-Path $Workspace "front_desk_bridge_repo"

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

function Test-Port {
    param([int]$Port)
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop | Select-Object -First 1
        return $null -ne $conn
    } catch {
        return $false
    }
}

function Scan-SourceForPatterns {
    param(
        [string]$Root,
        [string[]]$Patterns,
        [int]$MaxMatchesPerPattern = 40
    )

    $results = [ordered]@{}

    foreach ($pattern in $Patterns) {
        $results[$pattern] = @()
    }

    if (!(Test-Path -LiteralPath $Root)) {
        return [ordered]@{
            root = $Root
            exists = $false
            pattern_matches = $results
        }
    }

    $files = Get-ChildItem -LiteralPath $Root -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Extension -in @(".py", ".js", ".html", ".htm", ".ts", ".tsx", ".json", ".ps1", ".md")
        } |
        Select-Object -First 2000

    foreach ($file in $files) {
        $text = ""
        try {
            $text = Get-Content -LiteralPath $file.FullName -Raw -ErrorAction Stop
        } catch {
            continue
        }

        foreach ($pattern in $Patterns) {
            if ($results[$pattern].Count -ge $MaxMatchesPerPattern) { continue }
            if ($text -match [regex]::Escape($pattern)) {
                $relative = $file.FullName.Substring($Root.Length).TrimStart("\", "/")
                $results[$pattern] += [ordered]@{
                    file = $relative
                    pattern = $pattern
                }
            }
        }
    }

    return [ordered]@{
        root = $Root
        exists = $true
        scanned_file_count = @($files).Count
        pattern_matches = $results
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

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

$bridgeHtml = Try-GetText $BridgeUrl
$bridgeHealth = Try-GetJson "$BridgeUrl/health"
$activeBatches = Try-GetJson "$BridgeUrl/api/sms/batches?view=active"
$processedBatches = Try-GetJson "$BridgeUrl/api/sms/batches?view=processed"
$routingRulesGet = Try-GetJson "$BridgeUrl/api/routing-rules"

$patterns = @(
    "routingRuleSummary",
    "setManualBtn",
    "Set auto homeowner",
    "Save PM property",
    "routing_rule",
    "routing-rules",
    "/api/routing-rules",
    "default_contact_ids",
    "owner_type",
    "mode",
    "fetch(",
    "method: 'POST'",
    'method: "POST"',
    "runEodBtn",
    "forceBatchBtn",
    "Search LACRM",
    "taskModal"
)

$liveScan = Scan-SourceForPatterns -Root $BridgeLiveDir -Patterns $patterns
$repoScan = Scan-SourceForPatterns -Root $BridgeRepoDir -Patterns $patterns

$markers = [ordered]@{
    data_hub_title = $bridgeHtml.ok -and $bridgeHtml.value -match "Keys Pool Service Data Hub"
    routing_rule_summary = $bridgeHtml.ok -and $bridgeHtml.value -match "routingRuleSummary"
    set_manual_button = $bridgeHtml.ok -and $bridgeHtml.value -match "setManualBtn"
    text_summaries_tab = $bridgeHtml.ok -and $bridgeHtml.value -match "Text summaries"
    candidate_controls = $bridgeHtml.ok -and ($bridgeHtml.value -match "Set auto homeowner" -or $bridgeHtml.value -match "Save PM property" -or $bridgeHtml.value -match "set auto")
    task_modal = $bridgeHtml.ok -and $bridgeHtml.value -match "taskModal"
}

$activeCount = if ($activeBatches.ok) { Count-Items $activeBatches.value } else { 0 }
$processedCount = if ($processedBatches.ok) { Count-Items $processedBatches.value } else { 0 }

$sourceConfirmsRoutingEndpoint = $false
foreach ($scan in @($liveScan, $repoScan)) {
    if ($scan.exists -and $scan.pattern_matches["/api/routing-rules"].Count -gt 0) {
        $sourceConfirmsRoutingEndpoint = $true
    }
    if ($scan.exists -and $scan.pattern_matches["routing-rules"].Count -gt 0) {
        $sourceConfirmsRoutingEndpoint = $true
    }
}

$sourceConfirmsPostMarkers = $false
foreach ($scan in @($liveScan, $repoScan)) {
    if ($scan.exists -and (($scan.pattern_matches["method: 'POST'"].Count -gt 0) -or ($scan.pattern_matches['method: "POST"'].Count -gt 0))) {
        $sourceConfirmsPostMarkers = $true
    }
}

$contract = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 36"
    purpose = "Read-only bridge routing write contract inspection"
    app_map = [ordered]@{
        original_bridge_data_hub = $BridgeUrl
        platform_streamlit = "http://127.0.0.1:8501"
        platform_fastapi = "http://127.0.0.1:8010"
    }
    runtime = [ordered]@{
        bridge_port_listening = Test-Port 8000
        bridge_health_ok = $bridgeHealth.ok
        bridge_health = if ($bridgeHealth.ok) { $bridgeHealth.value } else { $null }
    }
    bridge_ui_markers = $markers
    bridge_read_contract = [ordered]@{
        active_sms_batches_endpoint = "$BridgeUrl/api/sms/batches?view=active"
        processed_sms_batches_endpoint = "$BridgeUrl/api/sms/batches?view=processed"
        routing_rules_get_endpoint = "$BridgeUrl/api/routing-rules"
        active_batches_ok = $activeBatches.ok
        processed_batches_ok = $processedBatches.ok
        routing_rules_get_ok = $routingRulesGet.ok
        active_batch_count = $activeCount
        processed_batch_count = $processedCount
        routing_rules_get_error = $routingRulesGet.error
    }
    source_inspection = [ordered]@{
        live_bridge_folder = $liveScan
        sanitized_bridge_repo = $repoScan
        source_confirms_routing_endpoint_marker = $sourceConfirmsRoutingEndpoint
        source_confirms_post_marker = $sourceConfirmsPostMarkers
    }
    proposed_write_contract = [ordered]@{
        contract_status = if ($sourceConfirmsRoutingEndpoint) { "source_marker_found_review_required" } else { "not_confirmed_review_required" }
        likely_target_endpoint = "/api/routing-rules"
        likely_http_method = "POST"
        expected_payload_fields = @(
            "phone",
            "mode",
            "owner_type",
            "label",
            "default_contact_ids",
            "notes"
        )
        required_future_safety_gates = @(
            "PLATFORM_BRIDGE_ROUTING_WRITE_ENABLED=true",
            "PLATFORM_BRIDGE_ROUTING_WRITE_ARMED=true",
            "operator confirmation phrase",
            "routing bridge apply preview exists",
            "routing candidate reconciliation clean",
            "admin token configured if bridge requires it",
            "idempotency key generated"
        )
        rollback_requirements = @(
            "capture previous bridge routing rule before write",
            "write audit row before and after any future bridge POST",
            "support explicit restore payload for changed phone"
        )
    }
    safety = [ordered]@{
        bridge_routing_write_contract_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
        bridge_write_endpoint_implemented = $false
        live_write_enabled = $false
    }
    next_recommended_actions = @(
        "Review source markers for the exact bridge routing write endpoint before adding any guarded write code.",
        "Keep Step 35 bridge apply preview as the source of payload shape.",
        "Do not call bridge POST endpoints until a separate guarded rehearsal step exists.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_contract_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_contract.json"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_contract.md"
$patternsCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_contract_source_matches.csv"

$contract | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$matchRows = @()
foreach ($scanName in @("live_bridge_folder", "sanitized_bridge_repo")) {
    $scan = $contract.source_inspection[$scanName]
    if (!$scan.exists) { continue }
    foreach ($pattern in $scan.pattern_matches.Keys) {
        foreach ($match in @($scan.pattern_matches[$pattern])) {
            $matchRows += [ordered]@{
                source = $scanName
                root = $scan.root
                file = $match.file
                pattern = $pattern
            }
        }
    }
}
$matchRows | Export-Csv -LiteralPath $patternsCsvPath -NoTypeInformation -Encoding UTF8

$markerText = ($markers.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
$payloadText = ($contract.proposed_write_contract.expected_payload_fields | ForEach-Object { "- $_" }) -join "`n"
$gateText = ($contract.proposed_write_contract.required_future_safety_gates | ForEach-Object { "- $_" }) -join "`n"

$md = @"
# Phase 19 Bridge Routing Write Contract

Generated: $($contract.generated_at)

## Safety

- Bridge routing write contract only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Bridge write endpoint implemented: false

## Bridge UI markers

$markerText

## Read contract

- Active SMS batches endpoint OK: $($contract.bridge_read_contract.active_batches_ok)
- Processed SMS batches endpoint OK: $($contract.bridge_read_contract.processed_batches_ok)
- Routing rules GET endpoint OK: $($contract.bridge_read_contract.routing_rules_get_ok)
- Active batch count: $activeCount
- Processed batch count: $processedCount

## Proposed write contract

- Contract status: $($contract.proposed_write_contract.contract_status)
- Likely target endpoint: $($contract.proposed_write_contract.likely_target_endpoint)
- Likely HTTP method: $($contract.proposed_write_contract.likely_http_method)

### Expected payload fields

$payloadText

### Required future safety gates

$gateText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($bridgeHealth.ok -and $markers.routing_rule_summary -and $contract.safety.bridge_post_called -eq $false) {
    Write-Host "PASS | bridge_routing_write_contract=$OutputDir | routing_ui=True | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_write_contract=$OutputDir | bridge_ok=$($bridgeHealth.ok) | routing_ui=$($markers.routing_rule_summary) | bridge_post_called=False"
}

Write-Host ""
Write-Host "Contract files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
