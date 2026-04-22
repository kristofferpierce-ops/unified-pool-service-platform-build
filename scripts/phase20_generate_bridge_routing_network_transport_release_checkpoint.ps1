param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$OperatorSignoffDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestArtifact {
    param(
        [string]$FolderFilter,
        [string]$JsonName,
        [bool]$Required = $true
    )

    $latest = Get-ChildItem -LiteralPath $BackupDir -Directory -Filter $FolderFilter -ErrorAction SilentlyContinue |
        Where-Object {
            Test-Path -LiteralPath (Join-Path $_.FullName $JsonName)
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if (!$latest) {
        if ($Required) {
            throw "No $FolderFilter folder containing $JsonName found in $BackupDir."
        }
        return $null
    }

    return [ordered]@{
        folder = $latest.FullName
        folder_name = $latest.Name
        json_path = Join-Path $latest.FullName $JsonName
        json_name = $JsonName
        last_write_time = $latest.LastWriteTime.ToString("o")
    }
}

function Try-GetJson {
    param([string]$Url)
    try {
        return @{ ok = $true; value = Invoke-RestMethod $Url -TimeoutSec 30; error = "" }
    } catch {
        return @{ ok = $false; value = $null; error = $_.Exception.Message }
    }
}

function Read-JsonFile {
    param([string]$Path)
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Get-FileSha256 {
    param([string]$Path)
    if (!(Test-Path -LiteralPath $Path)) { return "" }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Add-Issue {
    param(
        [System.Collections.ArrayList]$Issues,
        [string]$Severity,
        [string]$Code,
        [string]$Message,
        [string]$Source = ""
    )

    [void]$Issues.Add([ordered]@{
        severity = $Severity
        code = $Code
        source = $Source
        message = $Message
    })
}

function Add-Gate {
    param(
        [System.Collections.ArrayList]$Gates,
        [string]$Gate,
        [bool]$Passed,
        [string]$Severity,
        [string]$Evidence,
        [string]$Source = ""
    )

    [void]$Gates.Add([ordered]@{
        gate = $Gate
        passed = $Passed
        severity = $Severity
        evidence = $Evidence
        source = $Source
    })
}

function Get-NestedValue {
    param($Object, [string[]]$Path)
    $value = $Object
    foreach ($part in $Path) {
        if ($null -eq $value) { return $null }
        if ($value.PSObject.Properties.Name -contains $part) {
            $value = $value.$part
        } else {
            return $null
        }
    }
    return $value
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($OperatorSignoffDir)) {
    $operatorSignoffArtifact = Get-LatestArtifact -FolderFilter "phase20_bridge_routing_network_transport_operator_signoff_*" -JsonName "phase20_bridge_routing_network_transport_operator_signoff.json" -Required $true
} else {
    $signoffJson = Join-Path $OperatorSignoffDir "phase20_bridge_routing_network_transport_operator_signoff.json"
    if (!(Test-Path -LiteralPath $signoffJson)) {
        throw "Network transport operator signoff JSON not found: $signoffJson"
    }
    $operatorSignoffArtifact = [ordered]@{
        folder = $OperatorSignoffDir
        folder_name = Split-Path -Leaf $OperatorSignoffDir
        json_path = $signoffJson
        json_name = "phase20_bridge_routing_network_transport_operator_signoff.json"
        last_write_time = (Get-Item -LiteralPath $signoffJson).LastWriteTime.ToString("o")
    }
}

$artifactSpecs = @(
    @{ key="http_client_release_checkpoint"; filter="phase20_bridge_routing_http_client_release_checkpoint_*"; json="phase20_bridge_routing_http_client_release_checkpoint.json"; required=$true },
    @{ key="network_transport_guard"; filter="phase20_bridge_routing_network_transport_guard_*"; json="phase20_bridge_routing_network_transport_guard.json"; required=$true },
    @{ key="network_transport_dry_run_adapter"; filter="phase20_bridge_routing_network_transport_dry_run_adapter_*"; json="phase20_bridge_routing_network_transport_dry_run_adapter.json"; required=$true },
    @{ key="network_transport_dry_run_adapter_validation"; filter="phase20_bridge_routing_network_transport_dry_run_adapter_validation_*"; json="phase20_bridge_routing_network_transport_dry_run_adapter_validation.json"; required=$true },
    @{ key="network_transport_preflight_matrix"; filter="phase20_bridge_routing_network_transport_preflight_matrix_*"; json="phase20_bridge_routing_network_transport_preflight_matrix.json"; required=$true },
    @{ key="network_transport_operator_signoff"; artifact=$operatorSignoffArtifact; required=$true }
)

$artifacts = [ordered]@{}
$artifactData = [ordered]@{}
$issues = New-Object System.Collections.ArrayList
$gates = New-Object System.Collections.ArrayList

foreach ($spec in $artifactSpecs) {
    try {
        if ($spec.ContainsKey("artifact")) {
            $artifact = $spec.artifact
        } else {
            $artifact = Get-LatestArtifact -FolderFilter $spec.filter -JsonName $spec.json -Required ([bool]$spec.required)
        }

        if ($null -ne $artifact) {
            $artifact["sha256"] = Get-FileSha256 $artifact.json_path
            $artifacts[$spec.key] = $artifact
            $artifactData[$spec.key] = Read-JsonFile $artifact.json_path
            Add-Gate $gates "artifact_present_$($spec.key)" $true "blocker" $artifact.json_path $spec.key
        }
    } catch {
        Add-Issue $issues "blocker" "missing_artifact_$($spec.key)" $_.Exception.Message $spec.key
        Add-Gate $gates "artifact_present_$($spec.key)" $false "blocker" $_.Exception.Message $spec.key
    }
}

# Runtime checks are GET-only and review-level if unavailable.
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bundleStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

if ($adapterStatus.ok) {
    Add-Gate $gates "runtime_adapter_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status" "runtime"
    Add-Gate $gates "runtime_adapter_no_network_transport" ($adapterStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($adapterStatus.value.network_transport_implemented)" "runtime"
    Add-Gate $gates "runtime_adapter_no_socket" ($adapterStatus.value.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($adapterStatus.value.network_socket_opened)" "runtime"
    Add-Gate $gates "runtime_adapter_no_bridge_post" ($adapterStatus.value.bridge_post_called -eq $false -and $adapterStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($adapterStatus.value.bridge_post_called); bridge_post_call_implemented=$($adapterStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_adapter_status_readable" $false "review" $adapterStatus.error "runtime"
}

if ($guardStatus.ok) {
    Add-Gate $gates "runtime_guard_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status" "runtime"
    Add-Gate $gates "runtime_guard_no_network_transport" ($guardStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($guardStatus.value.network_transport_implemented)" "runtime"
    Add-Gate $gates "runtime_guard_no_bridge_post" ($guardStatus.value.bridge_post_called -eq $false -and $guardStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($guardStatus.value.bridge_post_called); bridge_post_call_implemented=$($guardStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_guard_status_readable" $false "review" $guardStatus.error "runtime"
}

if ($httpDryRunStatus.ok) {
    Add-Gate $gates "runtime_http_dry_run_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status" "runtime"
    Add-Gate $gates "runtime_http_dry_run_no_network_transport" ($httpDryRunStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($httpDryRunStatus.value.network_transport_implemented)" "runtime"
    Add-Gate $gates "runtime_http_dry_run_no_bridge_post" ($httpDryRunStatus.value.bridge_post_called -eq $false -and $httpDryRunStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($httpDryRunStatus.value.bridge_post_called); bridge_post_call_implemented=$($httpDryRunStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_http_dry_run_status_readable" $false "review" $httpDryRunStatus.error "runtime"
}

if ($executorStatus.ok) {
    Add-Gate $gates "runtime_executor_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-write-executor/status" "runtime"
    Add-Gate $gates "runtime_executor_no_execution_endpoint" ($executorStatus.value.execution_endpoint_available -eq $false) "blocker" "execution_endpoint_available=$($executorStatus.value.execution_endpoint_available)" "runtime"
    Add-Gate $gates "runtime_executor_no_bridge_post_impl" ($executorStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_call_implemented=$($executorStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_executor_status_readable" $false "review" $executorStatus.error "runtime"
}

if ($bundleStatus.ok) {
    Add-Gate $gates "runtime_bundle_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status" "runtime"
    Add-Gate $gates "runtime_bundle_no_bridge_post" ($bundleStatus.value.bridge_post_called -eq $false -and $bundleStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($bundleStatus.value.bridge_post_called); bridge_post_call_implemented=$($bundleStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_bundle_status_readable" $false "review" $bundleStatus.error "runtime"
}

Add-Gate $gates "runtime_bridge_health_readable" $bridgeHealth.ok "review" $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "runtime"

# Artifact invariants across the network transport no-socket chain.
foreach ($key in $artifactData.Keys) {
    $data = $artifactData[$key]
    $safety = $data.safety

    if ($null -eq $safety) {
        Add-Issue $issues "review" "artifact_missing_safety_$key" "Artifact does not include a safety block." $key
        continue
    }

    if ((Get-NestedValue $data @("safety", "bridge_post_called")) -eq $true) {
        Add-Issue $issues "blocker" "artifact_bridge_post_called_$key" "$key reports bridge_post_called=true." $key
    }
    if ((Get-NestedValue $data @("safety", "bridge_post_call_implemented")) -eq $true) {
        Add-Issue $issues "blocker" "artifact_bridge_post_call_implemented_$key" "$key reports bridge_post_call_implemented=true." $key
    }
    if ((Get-NestedValue $data @("safety", "bridge_mutation_performed")) -eq $true) {
        Add-Issue $issues "blocker" "artifact_bridge_mutation_$key" "$key reports bridge_mutation_performed=true." $key
    }
    if ((Get-NestedValue $data @("safety", "platform_db_mutation_performed")) -eq $true) {
        Add-Issue $issues "blocker" "artifact_platform_mutation_$key" "$key reports platform_db_mutation_performed=true." $key
    }
    if ((Get-NestedValue $data @("safety", "lacrm_call_performed")) -eq $true) {
        Add-Issue $issues "blocker" "artifact_lacrm_call_$key" "$key reports lacrm_call_performed=true." $key
    }
    if ((Get-NestedValue $data @("safety", "real_bridge_http_client_implemented")) -eq $true) {
        Add-Issue $issues "blocker" "artifact_real_http_client_$key" "$key reports real_bridge_http_client_implemented=true." $key
    }
    if ((Get-NestedValue $data @("safety", "network_transport_implemented")) -eq $true) {
        Add-Issue $issues "blocker" "artifact_network_transport_$key" "$key reports network_transport_implemented=true." $key
    }
    if ((Get-NestedValue $data @("safety", "network_transport_enabled")) -eq $true) {
        Add-Issue $issues "blocker" "artifact_network_transport_enabled_$key" "$key reports network_transport_enabled=true." $key
    }
    if ((Get-NestedValue $data @("safety", "network_transport_armed")) -eq $true) {
        Add-Issue $issues "blocker" "artifact_network_transport_armed_$key" "$key reports network_transport_armed=true." $key
    }
    if ((Get-NestedValue $data @("safety", "network_socket_opened")) -eq $true) {
        Add-Issue $issues "blocker" "artifact_network_socket_opened_$key" "$key reports network_socket_opened=true." $key
    }
    if ((Get-NestedValue $data @("safety", "routing_write_endpoint_implemented")) -eq $true) {
        Add-Issue $issues "blocker" "artifact_routing_write_endpoint_$key" "$key reports routing_write_endpoint_implemented=true." $key
    }
}

# Higher-level no-execution gates.
if ($artifactData.Contains("network_transport_preflight_matrix")) {
    $preflight = $artifactData.network_transport_preflight_matrix
    Add-Gate $gates "preflight_can_execute_false" ($preflight.preflight.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($preflight.preflight.can_execute_bridge_write_now)" "network_transport_preflight_matrix"
    Add-Gate $gates "preflight_can_add_network_false" ($preflight.preflight.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($preflight.preflight.can_add_network_transport_now)" "network_transport_preflight_matrix"
    Add-Gate $gates "preflight_can_enable_network_false" ($preflight.preflight.can_enable_network_transport_now -eq $false) "blocker" "can_enable_network_transport_now=$($preflight.preflight.can_enable_network_transport_now)" "network_transport_preflight_matrix"
    Add-Gate $gates "preflight_can_arm_network_false" ($preflight.preflight.can_arm_network_transport_now -eq $false) "blocker" "can_arm_network_transport_now=$($preflight.preflight.can_arm_network_transport_now)" "network_transport_preflight_matrix"
    Add-Gate $gates "preflight_can_open_socket_false" ($preflight.preflight.can_open_network_socket_now -eq $false) "blocker" "can_open_network_socket_now=$($preflight.preflight.can_open_network_socket_now)" "network_transport_preflight_matrix"
    Add-Gate $gates "preflight_can_add_real_client_false" ($preflight.preflight.can_add_real_bridge_http_client_now -eq $false) "blocker" "can_add_real_bridge_http_client_now=$($preflight.preflight.can_add_real_bridge_http_client_now)" "network_transport_preflight_matrix"
}

if ($artifactData.Contains("network_transport_operator_signoff")) {
    $signoff = $artifactData.network_transport_operator_signoff
    Add-Gate $gates "operator_signoff_can_execute_false" ($signoff.signoff.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($signoff.signoff.can_execute_bridge_write_now)" "network_transport_operator_signoff"
    Add-Gate $gates "operator_signoff_can_add_network_false" ($signoff.signoff.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($signoff.signoff.can_add_network_transport_now)" "network_transport_operator_signoff"
    Add-Gate $gates "operator_signoff_can_enable_network_false" ($signoff.signoff.can_enable_network_transport_now -eq $false) "blocker" "can_enable_network_transport_now=$($signoff.signoff.can_enable_network_transport_now)" "network_transport_operator_signoff"
    Add-Gate $gates "operator_signoff_can_arm_network_false" ($signoff.signoff.can_arm_network_transport_now -eq $false) "blocker" "can_arm_network_transport_now=$($signoff.signoff.can_arm_network_transport_now)" "network_transport_operator_signoff"
    Add-Gate $gates "operator_signoff_can_open_socket_false" ($signoff.signoff.can_open_network_socket_now -eq $false) "blocker" "can_open_network_socket_now=$($signoff.signoff.can_open_network_socket_now)" "network_transport_operator_signoff"
    Add-Gate $gates "operator_signoff_not_live_approved" ($signoff.signoff.approved_for_live_bridge_write -ne $true) "blocker" "approved_for_live_bridge_write=$($signoff.signoff.approved_for_live_bridge_write)" "network_transport_operator_signoff"
    Add-Gate $gates "operator_signoff_not_network_approved" ($signoff.signoff.approved_for_real_network_transport -ne $true) "blocker" "approved_for_real_network_transport=$($signoff.signoff.approved_for_real_network_transport)" "network_transport_operator_signoff"
    Add-Gate $gates "operator_signoff_not_enable_approved" ($signoff.signoff.approved_to_enable_network_transport -ne $true) "blocker" "approved_to_enable_network_transport=$($signoff.signoff.approved_to_enable_network_transport)" "network_transport_operator_signoff"
    Add-Gate $gates "operator_signoff_not_arm_approved" ($signoff.signoff.approved_to_arm_network_transport -ne $true) "blocker" "approved_to_arm_network_transport=$($signoff.signoff.approved_to_arm_network_transport)" "network_transport_operator_signoff"
    Add-Gate $gates "operator_signoff_not_socket_approved" ($signoff.signoff.approved_to_open_network_socket -ne $true) "blocker" "approved_to_open_network_socket=$($signoff.signoff.approved_to_open_network_socket)" "network_transport_operator_signoff"
}

if ($artifactData.Contains("network_transport_dry_run_adapter")) {
    $adapter = $artifactData.network_transport_dry_run_adapter
    Add-Gate $gates "adapter_simulated_would_not_open_socket" ($adapter.simulation.simulated_adapter_result.would_open_socket -eq $false) "blocker" "would_open_socket=$($adapter.simulation.simulated_adapter_result.would_open_socket)" "network_transport_dry_run_adapter"
    Add-Gate $gates "adapter_simulated_would_not_send_http_request" ($adapter.simulation.simulated_adapter_result.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($adapter.simulation.simulated_adapter_result.would_send_http_request)" "network_transport_dry_run_adapter"
    Add-Gate $gates "adapter_simulated_would_not_call_bridge" ($adapter.simulation.simulated_adapter_result.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($adapter.simulation.simulated_adapter_result.would_call_bridge)" "network_transport_dry_run_adapter"
    Add-Gate $gates "adapter_contract_transport_no_network" ($adapter.simulation.adapter_dry_run_contract.transport_mode -eq "dry_run_no_network") "blocker" "transport_mode=$($adapter.simulation.adapter_dry_run_contract.transport_mode)" "network_transport_dry_run_adapter"
}

# Turn failed gates into issues.
foreach ($gate in @($gates)) {
    if ($gate.passed -ne $true) {
        Add-Issue $issues $gate.severity $gate.gate $gate.evidence $gate.source
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$checkpointStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "release_checkpoint_clean_no_socket"
} elseif ($blockerCount -eq 0) {
    "release_checkpoint_review_required_no_socket"
} else {
    "release_checkpoint_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_release_checkpoint_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$artifactRows = @()
foreach ($key in $artifacts.Keys) {
    $artifactRows += [ordered]@{
        key = $key
        folder = $artifacts[$key].folder
        json_name = $artifacts[$key].json_name
        json_path = $artifacts[$key].json_path
        sha256 = $artifacts[$key].sha256
        last_write_time = $artifacts[$key].last_write_time
    }
}

$checkpoint = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 12"
    purpose = "Bridge routing network transport no-socket release checkpoint"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_release_checkpoint_only = $true
        bridge_get_only = $true
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
    release_checkpoint = [ordered]@{
        status = $checkpointStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        artifact_count = $artifactRows.Count
        gate_count = @($gates).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        release_freeze_label = "phase20_bridge_routing_network_transport_no_socket_checkpoint"
        reason = if ($blockerCount -eq 0) {
            "Network transport release checkpoint is suitable for review. Phase 20 Step 12 still implements no real network transport, opens no socket, and authorizes no execution."
        } else {
            "Network transport release checkpoint has blockers. Resolve blockers before any future real network transport design."
        }
    }
    artifacts = $artifactRows
    gates = @($gates)
    issues = @($issues)
    runtime_status = [ordered]@{
        adapter_status_ok = $adapterStatus.ok
        adapter_status = if ($adapterStatus.ok) { $adapterStatus.value } else { $null }
        guard_status_ok = $guardStatus.ok
        guard_status = if ($guardStatus.ok) { $guardStatus.value } else { $null }
        http_dry_run_status_ok = $httpDryRunStatus.ok
        http_dry_run_status = if ($httpDryRunStatus.ok) { $httpDryRunStatus.value } else { $null }
        executor_status_ok = $executorStatus.ok
        executor_status = if ($executorStatus.ok) { $executorStatus.value } else { $null }
        bundle_status_ok = $bundleStatus.ok
        bundle_status = if ($bundleStatus.ok) { $bundleStatus.value } else { $null }
        bridge_health_ok = $bridgeHealth.ok
        bridge_health = if ($bridgeHealth.ok) { $bridgeHealth.value } else { $null }
        bridge_health_error = $bridgeHealth.error
    }
    counts = [ordered]@{
        artifacts = $artifactRows.Count
        gates = @($gates).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this release checkpoint before starting any step that adds real network transport.",
        "Do not execute bridge writes from Phase 20 Step 12.",
        "Future real transport work must begin from a new explicitly guarded step and keep dry-run as default.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_release_checkpoint.json"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_release_checkpoint_artifacts.csv"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_release_checkpoint_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_release_checkpoint_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_release_checkpoint.md"

$checkpoint | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$artifactRows | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$artifactText = ($artifactRows | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$gateText = (@($gates) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.gate): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Release Checkpoint

Generated: $($checkpoint.generated_at)

## Safety

- Bridge routing network transport release checkpoint only: true
- Bridge GET only: true
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

## Release checkpoint

- Status: $checkpointStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Artifacts: $($artifactRows.Count)
- Gates: $(@($gates).Count)
- Can execute bridge write now: false
- Can add network transport now: false
- Can enable network transport now: false
- Can arm network transport now: false
- Can open network socket now: false
- Can add real bridge HTTP client now: false

## Artifacts

$artifactText

## Gates

$gateText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_release_checkpoint=$OutputDir | status=$checkpointStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_release_checkpoint=$OutputDir | status=$checkpointStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Network transport release checkpoint files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
