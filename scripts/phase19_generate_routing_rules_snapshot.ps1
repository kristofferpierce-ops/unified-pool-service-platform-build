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

function Items-From-Payload {
    param($Value)
    if (!$Value) { return @() }
    if ($Value -is [System.Array]) { return @($Value) }
    foreach ($key in @("items", "batches", "results", "queue", "sms_batches")) {
        if ($Value.$key -is [System.Array]) { return @($Value.$key) }
    }
    return @()
}

function Rule-Key {
    param($Rule, $Phone)
    $phoneValue = ""
    if ($Rule -and $Rule.phone) { $phoneValue = [string]$Rule.phone }
    elseif ($Phone) { $phoneValue = [string]$Phone }
    return $phoneValue.Trim()
}

function Extract-Rules-From-Batches {
    param($Payload, [string]$SourceView)

    $rows = @()
    $items = Items-From-Payload $Payload
    foreach ($item in $items) {
        if (!$item) { continue }
        $rule = $item.routing_rule
        $phone = $item.external_phone
        if (!$rule) {
            $rows += [ordered]@{
                source_view = $SourceView
                phone = $phone
                mode = ""
                owner_type = ""
                label = ""
                default_contact_count = 0
                notes = ""
                updated_at = ""
                batch_id = $item.id
                batch_status = $item.status
                batch_date = $item.batch_date
                has_rule = $false
            }
            continue
        }

        $contacts = @()
        if ($rule.default_contact_ids -is [System.Array]) { $contacts = @($rule.default_contact_ids) }

        $rows += [ordered]@{
            source_view = $SourceView
            phone = Rule-Key $rule $phone
            mode = [string]$rule.mode
            owner_type = [string]$rule.owner_type
            label = [string]$rule.label
            default_contact_count = $contacts.Count
            notes = [string]$rule.notes
            updated_at = [string]$rule.updated_at
            batch_id = $item.id
            batch_status = $item.status
            batch_date = $item.batch_date
            has_rule = $true
        }
    }
    return $rows
}

function Group-Rules {
    param($Rows)
    $groups = @{}
    foreach ($row in $Rows) {
        $key = "$($row.phone)|$($row.mode)|$($row.owner_type)|$($row.label)"
        if (!$groups.ContainsKey($key)) {
            $groups[$key] = [ordered]@{
                phone = $row.phone
                mode = $row.mode
                owner_type = $row.owner_type
                label = $row.label
                default_contact_count = $row.default_contact_count
                notes = $row.notes
                latest_rule_updated_at = $row.updated_at
                batch_count = 0
                source_views = @{}
                sample_batch_ids = @()
            }
        }
        $groups[$key].batch_count += 1
        $groups[$key].source_views[$row.source_view] = $true
        if ($groups[$key].sample_batch_ids.Count -lt 5 -and $row.batch_id) {
            $groups[$key].sample_batch_ids += $row.batch_id
        }
    }

    $out = @()
    foreach ($g in $groups.Values) {
        $out += [ordered]@{
            phone = $g.phone
            mode = $g.mode
            owner_type = $g.owner_type
            label = $g.label
            default_contact_count = $g.default_contact_count
            notes = $g.notes
            latest_rule_updated_at = $g.latest_rule_updated_at
            batch_count = $g.batch_count
            source_views = @($g.source_views.Keys)
            sample_batch_ids = $g.sample_batch_ids
        }
    }
    return $out | Sort-Object phone, mode, owner_type
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
$rulesEndpoint = Try-GetJson "$BridgeUrl/api/routing-rules"
$platformHealth = Try-GetJson "$PlatformApi/health"
$platformSummary = Try-GetJson "$PlatformApi/front-desk/bridge-review-summary"
$lacrmSafety = Try-GetJson "$PlatformApi/front-desk/lacrm-apply/status"

$markers = [ordered]@{
    data_hub_title = $bridgeHtml.ok -and $bridgeHtml.value -match "Keys Pool Service Data Hub"
    routing_rule_summary = $bridgeHtml.ok -and $bridgeHtml.value -match "routingRuleSummary"
    set_manual_button = $bridgeHtml.ok -and $bridgeHtml.value -match "setManualBtn"
    text_summaries_tab = $bridgeHtml.ok -and $bridgeHtml.value -match "Text summaries"
    candidate_controls = $bridgeHtml.ok -and $bridgeHtml.value -match "Set auto homeowner|Save PM property|set auto"
}

$rows = @()
if ($activeBatches.ok) { $rows += Extract-Rules-From-Batches $activeBatches.value "active" }
if ($processedBatches.ok) { $rows += Extract-Rules-From-Batches $processedBatches.value "processed" }
$uniqueRules = Group-Rules $rows

$modeCounts = @{}
$ownerTypeCounts = @{}
foreach ($rule in $uniqueRules) {
    $mode = if ([string]::IsNullOrWhiteSpace($rule.mode)) { "blank" } else { $rule.mode }
    $owner = if ([string]::IsNullOrWhiteSpace($rule.owner_type)) { "blank" } else { $rule.owner_type }
    if (!$modeCounts.ContainsKey($mode)) { $modeCounts[$mode] = 0 }
    if (!$ownerTypeCounts.ContainsKey($owner)) { $ownerTypeCounts[$owner] = 0 }
    $modeCounts[$mode] += 1
    $ownerTypeCounts[$owner] += 1
}

$liveEnabled = $false
$liveArmed = $false
if ($lacrmSafety.ok -and $lacrmSafety.value) {
    $liveEnabled = [bool]$lacrmSafety.value.live_write_enabled
    $liveArmed = [bool]$lacrmSafety.value.live_write_armed
}

$snapshot = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 19 Step 22"
    purpose = "Read-only bridge routing-rule parity snapshot"
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
    source_endpoints = [ordered]@{
        active_batches_ok = $activeBatches.ok
        processed_batches_ok = $processedBatches.ok
        routing_rules_endpoint_ok = $rulesEndpoint.ok
        routing_rules_endpoint_error = $rulesEndpoint.error
    }
    routing_rules = [ordered]@{
        batch_rows_scanned = @($rows).Count
        unique_rule_count = @($uniqueRules).Count
        mode_counts = $modeCounts
        owner_type_counts = $ownerTypeCounts
        rules_preview = @($uniqueRules | Select-Object -First 100)
    }
    platform_context = [ordered]@{
        bridge_review_summary_ok = $platformSummary.ok
        bridge_review_summary = if ($platformSummary.ok) { $platformSummary.value } else { $null }
    }
    lacrm_safety = [ordered]@{
        status_endpoint_ok = $lacrmSafety.ok
        live_write_enabled = $liveEnabled
        live_write_armed = $liveArmed
        default_mode = if ($lacrmSafety.ok -and $lacrmSafety.value) { $lacrmSafety.value.default_mode } else { "" }
    }
    parity_status = [ordered]@{
        original_routing_ui_present_on_bridge = [bool]$markers.routing_rule_summary
        platform_routing_snapshot_page_added = $true
        read_only_only = $true
        bridge_routing_mutation_performed = $false
        bridge_routing_post_called = $false
        lacrm_call_performed = $false
    }
    next_recommended_actions = @(
        "Design platform-side routing-rule review table with explicit operator approval.",
        "Add dry-run migration preview before writing any routing preferences.",
        "Map bridge routing modes to platform RoutingPreference entities.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputPath = Join-Path $BackupDir "phase19_routing_rules_snapshot_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownPath)) {
    $MarkdownPath = [System.IO.Path]::ChangeExtension($OutputPath, ".md")
}

$snapshot | ConvertTo-Json -Depth 25 | Set-Content -LiteralPath $OutputPath -Encoding UTF8

$modeText = ($modeCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"
$ownerText = ($ownerTypeCounts.GetEnumerator() | Sort-Object Name | ForEach-Object { "- $($_.Name): $($_.Value)" }) -join "`n"

$md = @"
# Phase 19 Routing Rules Snapshot

Generated: $($snapshot.generated_at)

## Runtime

- FastAPI OK: $($snapshot.runtime.fastapi_ok)
- Bridge OK: $($snapshot.runtime.bridge_ok)
- Routing UI marker present: $($snapshot.bridge_ui_markers.routing_rule_summary)

## Routing counts

- Batch rows scanned: $($snapshot.routing_rules.batch_rows_scanned)
- Unique rule count: $($snapshot.routing_rules.unique_rule_count)

### Mode counts

$modeText

### Owner type counts

$ownerText

## Safety

- Read-only only: true
- Bridge routing mutation performed: false
- Bridge routing POST called: false
- LACRM call performed: false
- Live write enabled: $liveEnabled
- Live write armed: $liveArmed

## Next recommended actions

$($snapshot.next_recommended_actions | ForEach-Object { "- $_" } | Out-String)
"@

$md | Set-Content -LiteralPath $MarkdownPath -Encoding UTF8

if ($bridgeHealth.ok -and $markers.routing_rule_summary -and !$liveEnabled -and !$liveArmed) {
    Write-Host "PASS | routing_rules_snapshot=$OutputPath | routing_ui=True | unique_rules=$($snapshot.routing_rules.unique_rule_count) | live_writes_off=True"
} else {
    Write-Host "CHECK | routing_rules_snapshot=$OutputPath | bridge_ok=$($bridgeHealth.ok) | routing_ui=$($markers.routing_rule_summary) | unique_rules=$($snapshot.routing_rules.unique_rule_count) | liveEnabled=$liveEnabled | armed=$liveArmed"
}
