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
    $operatorSignoffArtifact = Get-LatestArtifact -FolderFilter "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff_*" -JsonName "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff.json" -Required $true
} else {
    $signoffJson = Join-Path $OperatorSignoffDir "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff.json"
    if (!(Test-Path -LiteralPath $signoffJson)) {
        throw "Interface scaffold operator signoff JSON not found: $signoffJson"
    }
    $operatorSignoffArtifact = [ordered]@{
        folder = $OperatorSignoffDir
        folder_name = Split-Path -Leaf $OperatorSignoffDir
        json_path = $signoffJson
        json_name = "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff.json"
        last_write_time = (Get-Item -LiteralPath $signoffJson).LastWriteTime.ToString("o")
    }
}

$artifactSpecs = @(
    @{ key="network_transport_release_checkpoint"; filter="phase20_bridge_routing_network_transport_release_checkpoint_*"; json="phase20_bridge_routing_network_transport_release_checkpoint.json"; required=$true },
    @{ key="network_transport_implementation_plan"; filter="phase20_bridge_routing_network_transport_implementation_plan_*"; json="phase20_bridge_routing_network_transport_implementation_plan.json"; required=$true },
    @{ key="interface_scaffold"; filter="phase20_bridge_routing_network_transport_interface_scaffold_*"; json="phase20_bridge_routing_network_transport_interface_scaffold.json"; required=$true },
    @{ key="interface_scaffold_validation"; filter="phase20_bridge_routing_network_transport_interface_scaffold_validation_*"; json="phase20_bridge_routing_network_transport_interface_scaffold_validation.json"; required=$true },
    @{ key="interface_scaffold_preflight_matrix"; filter="phase20_bridge_routing_network_transport_interface_scaffold_preflight_matrix_*"; json="phase20_bridge_routing_network_transport_interface_scaffold_preflight_matrix.json"; required=$true },
    @{ key="interface_scaffold_operator_signoff"; artifact=$operatorSignoffArtifact; required=$true }
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
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

if ($scaffoldStatus.ok) {
    Add-Gate $gates "runtime_scaffold_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status" "runtime"
    Add-Gate $gates "runtime_scaffold_no_network_transport" ($scaffoldStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($scaffoldStatus.value.network_transport_implemented)" "runtime"
    Add-Gate $gates "runtime_scaffold_no_socket" ($scaffoldStatus.value.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($scaffoldStatus.value.network_socket_opened)" "runtime"
    Add-Gate $gates "runtime_scaffold_no_bridge_post" ($scaffoldStatus.value.bridge_post_called -eq $false -and $scaffoldStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($scaffoldStatus.value.bridge_post_called); bridge_post_call_implemented=$($scaffoldStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_scaffold_status_readable" $false "review" $scaffoldStatus.error "runtime"
}

if ($adapterStatus.ok) {
    Add-Gate $gates "runtime_adapter_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status" "runtime"
    Add-Gate $gates "runtime_adapter_no_network_transport" ($adapterStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($adapterStatus.value.network_transport_implemented)" "runtime"
    Add-Gate $gates "runtime_adapter_no_socket" ($adapterStatus.value.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($adapterStatus.value.network_socket_opened)" "runtime"
} else {
    Add-Gate $gates "runtime_adapter_status_readable" $false "review" $adapterStatus.error "runtime"
}

if ($guardStatus.ok) {
    Add-Gate $gates "runtime_guard_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status" "runtime"
    Add-Gate $gates "runtime_guard_no_network_transport" ($guardStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($guardStatus.value.network_transport_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_guard_status_readable" $false "review" $guardStatus.error "runtime"
}

if ($httpDryRunStatus.ok) {
    Add-Gate $gates "runtime_http_dry_run_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status" "runtime"
    Add-Gate $gates "runtime_http_dry_run_no_network_transport" ($httpDryRunStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($httpDryRunStatus.value.network_transport_implemented)" "runtime"
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

Add-Gate $gates "runtime_bridge_health_readable" $bridgeHealth.ok "review" $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "runtime"

# Artifact invariants across the interface scaffold chain.
foreach ($key in $artifactData.Keys) {
    $data = $artifactData[$key]
    $safety = $data.safety

    if ($null -eq $safety) {
        Add-Issue $issues "review" "artifact_missing_safety_$key" "Artifact does not include a safety block." $key
        continue
    }

    $forbiddenTrue = @(
        "bridge_post_called",
        "bridge_post_call_implemented",
        "bridge_mutation_performed",
        "platform_db_mutation_performed",
        "lacrm_call_performed",
        "real_bridge_http_client_implemented",
        "network_transport_implemented",
        "network_transport_enabled",
        "network_transport_armed",
        "network_socket_opened",
        "routing_write_endpoint_implemented",
        "live_write_enabled"
    )

    foreach ($flag in $forbiddenTrue) {
        if ((Get-NestedValue $data @("safety", $flag)) -eq $true) {
            Add-Issue $issues "blocker" "artifact_forbidden_true_$($key)_$flag" "$key reports $flag=true." $key
        }
    }

    foreach ($issue in @($data.issues)) {
        if ($issue.severity -eq "blocker") {
            Add-Issue $issues "blocker" "upstream_blocker_$($key)_$($issue.code)" "$($issue.message)" $key
        }
    }
}

# Higher-level no-execution gates.
if ($artifactData.Contains("network_transport_release_checkpoint")) {
    $release = $artifactData.network_transport_release_checkpoint
    Add-Gate $gates "network_release_can_execute_false" ($release.release_checkpoint.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($release.release_checkpoint.can_execute_bridge_write_now)" "network_transport_release_checkpoint"
    Add-Gate $gates "network_release_can_add_network_false" ($release.release_checkpoint.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($release.release_checkpoint.can_add_network_transport_now)" "network_transport_release_checkpoint"
    Add-Gate $gates "network_release_can_open_socket_false" ($release.release_checkpoint.can_open_network_socket_now -eq $false) "blocker" "can_open_network_socket_now=$($release.release_checkpoint.can_open_network_socket_now)" "network_transport_release_checkpoint"
}

if ($artifactData.Contains("network_transport_implementation_plan")) {
    $plan = $artifactData.network_transport_implementation_plan
    Add-Gate $gates "implementation_plan_can_execute_false" ($plan.implementation_plan.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($plan.implementation_plan.can_execute_bridge_write_now)" "network_transport_implementation_plan"
    Add-Gate $gates "implementation_plan_can_add_network_false" ($plan.implementation_plan.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($plan.implementation_plan.can_add_network_transport_now)" "network_transport_implementation_plan"
    Add-Gate $gates "implementation_plan_can_add_bridge_post_false" ($plan.implementation_plan.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($plan.implementation_plan.can_add_bridge_post_now)" "network_transport_implementation_plan"
}

if ($artifactData.Contains("interface_scaffold")) {
    $scaffold = $artifactData.interface_scaffold
    Add-Gate $gates "interface_scaffold_preview_no_network" ($scaffold.preview.would_add_network_transport -eq $false) "blocker" "would_add_network_transport=$($scaffold.preview.would_add_network_transport)" "interface_scaffold"
    Add-Gate $gates "interface_scaffold_preview_no_socket" ($scaffold.preview.would_open_socket -eq $false) "blocker" "would_open_socket=$($scaffold.preview.would_open_socket)" "interface_scaffold"
    Add-Gate $gates "interface_scaffold_preview_no_http_send" ($scaffold.preview.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($scaffold.preview.would_send_http_request)" "interface_scaffold"
    Add-Gate $gates "interface_scaffold_preview_no_bridge_call" ($scaffold.preview.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($scaffold.preview.would_call_bridge)" "interface_scaffold"
    Add-Gate $gates "interface_execute_raises_no_transport" ($scaffold.preview.interface_scaffold.execute_method_behavior -eq "raises_runtime_error_no_transport") "blocker" "execute_method_behavior=$($scaffold.preview.interface_scaffold.execute_method_behavior)" "interface_scaffold"
}

if ($artifactData.Contains("interface_scaffold_validation")) {
    $validation = $artifactData.interface_scaffold_validation
    Add-Gate $gates "validation_can_execute_false" ($validation.validation.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($validation.validation.can_execute_bridge_write_now)" "interface_scaffold_validation"
    Add-Gate $gates "validation_can_add_bridge_post_false" ($validation.validation.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($validation.validation.can_add_bridge_post_now)" "interface_scaffold_validation"
}

if ($artifactData.Contains("interface_scaffold_preflight_matrix")) {
    $preflight = $artifactData.interface_scaffold_preflight_matrix
    Add-Gate $gates "preflight_can_execute_false" ($preflight.preflight.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($preflight.preflight.can_execute_bridge_write_now)" "interface_scaffold_preflight_matrix"
    Add-Gate $gates "preflight_can_add_network_false" ($preflight.preflight.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($preflight.preflight.can_add_network_transport_now)" "interface_scaffold_preflight_matrix"
    Add-Gate $gates "preflight_can_enable_network_false" ($preflight.preflight.can_enable_network_transport_now -eq $false) "blocker" "can_enable_network_transport_now=$($preflight.preflight.can_enable_network_transport_now)" "interface_scaffold_preflight_matrix"
    Add-Gate $gates "preflight_can_arm_network_false" ($preflight.preflight.can_arm_network_transport_now -eq $false) "blocker" "can_arm_network_transport_now=$($preflight.preflight.can_arm_network_transport_now)" "interface_scaffold_preflight_matrix"
    Add-Gate $gates "preflight_can_open_socket_false" ($preflight.preflight.can_open_network_socket_now -eq $false) "blocker" "can_open_network_socket_now=$($preflight.preflight.can_open_network_socket_now)" "interface_scaffold_preflight_matrix"
    Add-Gate $gates "preflight_can_add_real_client_false" ($preflight.preflight.can_add_real_bridge_http_client_now -eq $false) "blocker" "can_add_real_bridge_http_client_now=$($preflight.preflight.can_add_real_bridge_http_client_now)" "interface_scaffold_preflight_matrix"
    Add-Gate $gates "preflight_can_add_bridge_post_false" ($preflight.preflight.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($preflight.preflight.can_add_bridge_post_now)" "interface_scaffold_preflight_matrix"
}

if ($artifactData.Contains("interface_scaffold_operator_signoff")) {
    $signoff = $artifactData.interface_scaffold_operator_signoff
    Add-Gate $gates "operator_signoff_can_execute_false" ($signoff.signoff.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($signoff.signoff.can_execute_bridge_write_now)" "interface_scaffold_operator_signoff"
    Add-Gate $gates "operator_signoff_can_add_network_false" ($signoff.signoff.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($signoff.signoff.can_add_network_transport_now)" "interface_scaffold_operator_signoff"
    Add-Gate $gates "operator_signoff_can_open_socket_false" ($signoff.signoff.can_open_network_socket_now -eq $false) "blocker" "can_open_network_socket_now=$($signoff.signoff.can_open_network_socket_now)" "interface_scaffold_operator_signoff"
    Add-Gate $gates "operator_signoff_can_add_bridge_post_false" ($signoff.signoff.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($signoff.signoff.can_add_bridge_post_now)" "interface_scaffold_operator_signoff"
    Add-Gate $gates "operator_signoff_not_live_approved" ($signoff.signoff.approved_for_live_bridge_write -ne $true) "blocker" "approved_for_live_bridge_write=$($signoff.signoff.approved_for_live_bridge_write)" "interface_scaffold_operator_signoff"
    Add-Gate $gates "operator_signoff_not_network_approved" ($signoff.signoff.approved_for_real_network_transport -ne $true) "blocker" "approved_for_real_network_transport=$($signoff.signoff.approved_for_real_network_transport)" "interface_scaffold_operator_signoff"
    Add-Gate $gates "operator_signoff_not_socket_approved" ($signoff.signoff.approved_to_open_network_socket -ne $true) "blocker" "approved_to_open_network_socket=$($signoff.signoff.approved_to_open_network_socket)" "interface_scaffold_operator_signoff"
    Add-Gate $gates "operator_signoff_not_bridge_post_approved" ($signoff.signoff.approved_to_add_bridge_post -ne $true) "blocker" "approved_to_add_bridge_post=$($signoff.signoff.approved_to_add_bridge_post)" "interface_scaffold_operator_signoff"
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
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint_$stamp"
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
    phase = "Phase 20 Step 18"
    purpose = "Bridge routing network transport interface scaffold no-socket release checkpoint"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_interface_scaffold_release_checkpoint_only = $true
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
        can_add_bridge_post_now = $false
        release_freeze_label = "phase20_bridge_routing_network_transport_interface_scaffold_no_socket_checkpoint"
        reason = if ($blockerCount -eq 0) {
            "Interface scaffold release checkpoint is suitable for review. Phase 20 Step 18 still implements no real network transport, opens no socket, adds no bridge POST, and authorizes no execution."
        } else {
            "Interface scaffold release checkpoint has blockers. Resolve blockers before any future real network transport design."
        }
    }
    artifacts = $artifactRows
    gates = @($gates)
    issues = @($issues)
    runtime_status = [ordered]@{
        scaffold_status_ok = $scaffoldStatus.ok
        scaffold_status = if ($scaffoldStatus.ok) { $scaffoldStatus.value } else { $null }
        adapter_status_ok = $adapterStatus.ok
        adapter_status = if ($adapterStatus.ok) { $adapterStatus.value } else { $null }
        guard_status_ok = $guardStatus.ok
        guard_status = if ($guardStatus.ok) { $guardStatus.value } else { $null }
        http_dry_run_status_ok = $httpDryRunStatus.ok
        http_dry_run_status = if ($httpDryRunStatus.ok) { $httpDryRunStatus.value } else { $null }
        executor_status_ok = $executorStatus.ok
        executor_status = if ($executorStatus.ok) { $executorStatus.value } else { $null }
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
        "Review this release checkpoint before starting any future interface-backed transport adapter work.",
        "Do not execute bridge writes from Phase 20 Step 18.",
        "Future real transport work must begin from a new explicitly guarded step and keep dry-run as default.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint.json"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint_artifacts.csv"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_release_checkpoint.md"

$checkpoint | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$artifactRows | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$artifactText = ($artifactRows | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$gateText = (@($gates) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.gate): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Interface Scaffold Release Checkpoint

Generated: $($checkpoint.generated_at)

## Safety

- Bridge routing network transport interface scaffold release checkpoint only: true
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
- Can add bridge POST now: false

## Artifacts

$artifactText

## Gates

$gateText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_interface_scaffold_release_checkpoint=$OutputDir | status=$checkpointStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_interface_scaffold_release_checkpoint=$OutputDir | status=$checkpointStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Interface scaffold release checkpoint files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
