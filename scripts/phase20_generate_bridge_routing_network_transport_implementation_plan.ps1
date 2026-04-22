param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$ReleaseCheckpointDir = "",
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

function Add-Stage {
    param(
        [System.Collections.ArrayList]$Stages,
        [int]$Order,
        [string]$Stage,
        [string]$Description,
        [bool]$AllowedNow,
        [string]$Boundary,
        [string[]]$Prerequisites = @()
    )

    [void]$Stages.Add([ordered]@{
        order = $Order
        stage = $Stage
        description = $Description
        allowed_now = $AllowedNow
        boundary = $Boundary
        prerequisites = $Prerequisites
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

if ([string]::IsNullOrWhiteSpace($ReleaseCheckpointDir)) {
    $releaseArtifact = Get-LatestArtifact -FolderFilter "phase20_bridge_routing_network_transport_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_release_checkpoint.json" -Required $true
} else {
    $releaseJson = Join-Path $ReleaseCheckpointDir "phase20_bridge_routing_network_transport_release_checkpoint.json"
    if (!(Test-Path -LiteralPath $releaseJson)) {
        throw "Network transport release checkpoint JSON not found: $releaseJson"
    }
    $releaseArtifact = [ordered]@{
        folder = $ReleaseCheckpointDir
        folder_name = Split-Path -Leaf $ReleaseCheckpointDir
        json_path = $releaseJson
        json_name = "phase20_bridge_routing_network_transport_release_checkpoint.json"
        last_write_time = (Get-Item -LiteralPath $releaseJson).LastWriteTime.ToString("o")
    }
}

$artifactSpecs = @(
    @{ key="network_transport_release_checkpoint"; artifact=$releaseArtifact; required=$true },
    @{ key="network_transport_operator_signoff"; filter="phase20_bridge_routing_network_transport_operator_signoff_*"; json="phase20_bridge_routing_network_transport_operator_signoff.json"; required=$false },
    @{ key="network_transport_preflight_matrix"; filter="phase20_bridge_routing_network_transport_preflight_matrix_*"; json="phase20_bridge_routing_network_transport_preflight_matrix.json"; required=$false },
    @{ key="network_transport_dry_run_adapter_validation"; filter="phase20_bridge_routing_network_transport_dry_run_adapter_validation_*"; json="phase20_bridge_routing_network_transport_dry_run_adapter_validation.json"; required=$false },
    @{ key="network_transport_dry_run_adapter"; filter="phase20_bridge_routing_network_transport_dry_run_adapter_*"; json="phase20_bridge_routing_network_transport_dry_run_adapter.json"; required=$false },
    @{ key="network_transport_guard"; filter="phase20_bridge_routing_network_transport_guard_*"; json="phase20_bridge_routing_network_transport_guard.json"; required=$false },
    @{ key="http_client_release_checkpoint"; filter="phase20_bridge_routing_http_client_release_checkpoint_*"; json="phase20_bridge_routing_http_client_release_checkpoint.json"; required=$false }
)

$artifacts = [ordered]@{}
$artifactData = [ordered]@{}
$issues = New-Object System.Collections.ArrayList
$gates = New-Object System.Collections.ArrayList
$stages = New-Object System.Collections.ArrayList

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
        } else {
            Add-Gate $gates "artifact_present_$($spec.key)" $false "review" "Optional artifact not found." $spec.key
        }
    } catch {
        $severity = if ([bool]$spec.required) { "blocker" } else { "review" }
        Add-Issue $issues $severity "missing_artifact_$($spec.key)" $_.Exception.Message $spec.key
        Add-Gate $gates "artifact_present_$($spec.key)" $false $severity $_.Exception.Message $spec.key
    }
}

# Runtime checks are GET-only and review-level if unavailable.
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
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

# Required Step 12 checkpoint invariants.
if ($artifactData.Contains("network_transport_release_checkpoint")) {
    $release = $artifactData.network_transport_release_checkpoint

    Add-Gate $gates "release_checkpoint_is_checkpoint_only" ($release.safety.bridge_routing_network_transport_release_checkpoint_only -eq $true) "blocker" "bridge_routing_network_transport_release_checkpoint_only=$($release.safety.bridge_routing_network_transport_release_checkpoint_only)" "network_transport_release_checkpoint"
    Add-Gate $gates "release_checkpoint_bridge_get_only" ($release.safety.bridge_get_only -eq $true) "blocker" "bridge_get_only=$($release.safety.bridge_get_only)" "network_transport_release_checkpoint"
    Add-Gate $gates "release_checkpoint_no_network_transport" ($release.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($release.safety.network_transport_implemented)" "network_transport_release_checkpoint"
    Add-Gate $gates "release_checkpoint_no_network_enabled" ($release.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($release.safety.network_transport_enabled)" "network_transport_release_checkpoint"
    Add-Gate $gates "release_checkpoint_no_network_armed" ($release.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($release.safety.network_transport_armed)" "network_transport_release_checkpoint"
    Add-Gate $gates "release_checkpoint_no_socket" ($release.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($release.safety.network_socket_opened)" "network_transport_release_checkpoint"
    Add-Gate $gates "release_checkpoint_no_bridge_post" ($release.safety.bridge_post_called -eq $false -and $release.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($release.safety.bridge_post_called); bridge_post_call_implemented=$($release.safety.bridge_post_call_implemented)" "network_transport_release_checkpoint"
    Add-Gate $gates "release_checkpoint_blocks_execution" ($release.release_checkpoint.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($release.release_checkpoint.can_execute_bridge_write_now)" "network_transport_release_checkpoint"
    Add-Gate $gates "release_checkpoint_blocks_network_transport" ($release.release_checkpoint.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($release.release_checkpoint.can_add_network_transport_now)" "network_transport_release_checkpoint"
    Add-Gate $gates "release_checkpoint_blocks_socket" ($release.release_checkpoint.can_open_network_socket_now -eq $false) "blocker" "can_open_network_socket_now=$($release.release_checkpoint.can_open_network_socket_now)" "network_transport_release_checkpoint"
}

# Artifact invariants: no artifact may claim transport/socket/post/mutation.
foreach ($key in $artifactData.Keys) {
    $data = $artifactData[$key]

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

# Future implementation plan stages. All are explicitly not allowed now.
Add-Stage $stages 1 "design_contract_review" "Review the Step 7/8 transport design contract and endpoint shape." $false "review-only, no code implementation" @("Step 12 release checkpoint")
Add-Stage $stages 2 "adapter_interface_scaffold" "Define a future interface shape without socket creation or network libraries." $false "no imports of requests/httpx for bridge calls" @("operator design approval")
Add-Stage $stages 3 "dry_run_invocation_path" "Map a dry-run-only invocation path that returns deterministic simulated responses." $false "no socket, no HTTP request" @("adapter interface scaffold")
Add-Stage $stages 4 "audit_prerequisite_gate" "Require an audit plan row and idempotency key before any future write attempt." $false "metadata-only" @("dry-run invocation path")
Add-Stage $stages 5 "rollback_snapshot_gate" "Require a rollback snapshot before any future transport can be armed." $false "metadata-only" @("audit prerequisite gate")
Add-Stage $stages 6 "environment_gate_design" "Document env flags that must remain false by default for network transport." $false "disabled-by-default" @("rollback snapshot gate")
Add-Stage $stages 7 "operator_confirmation_gate" "Document separate operator confirmations for transport design versus live write." $false "no live write confirmation accepted here" @("environment gate design")
Add-Stage $stages 8 "response_capture_design" "Specify response capture fields for a future dry-run or guarded transport path." $false "no response from bridge because no request is sent" @("operator confirmation gate")
Add-Stage $stages 9 "test_matrix" "Define tests that fail if network transport, sockets, bridge POST, or mutation are introduced." $false "test-only" @("response capture design")
Add-Stage $stages 10 "future_cutover_packet_prerequisite" "Require a new future cutover packet before any transport can be enabled." $false "no cutover in Step 13" @("test matrix")

foreach ($stage in @($stages)) {
    Add-Gate $gates "stage_not_allowed_now_$($stage.stage)" ($stage.allowed_now -eq $false) "blocker" "allowed_now=$($stage.allowed_now)" "implementation_plan"
}

# Convert failed gates into issues.
foreach ($gate in @($gates)) {
    if ($gate.passed -ne $true) {
        Add-Issue $issues $gate.severity $gate.gate $gate.evidence $gate.source
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$planStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "implementation_plan_ready_for_review_no_socket"
} elseif ($blockerCount -eq 0) {
    "implementation_plan_review_required_no_socket"
} else {
    "implementation_plan_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_implementation_plan_$stamp"
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

$plan = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 13"
    purpose = "Bridge routing network transport implementation plan"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_implementation_plan_only = $true
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
    implementation_plan = [ordered]@{
        status = $planStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        artifact_count = $artifactRows.Count
        gate_count = @($gates).Count
        stage_count = @($stages).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        can_add_bridge_post_now = $false
        reason = if ($blockerCount -eq 0) {
            "Network transport implementation plan is suitable for review. Phase 20 Step 13 still implements no real transport, opens no socket, and authorizes no execution."
        } else {
            "Network transport implementation plan has blockers. Resolve blockers before any future real network transport implementation."
        }
    }
    artifacts = $artifactRows
    stages = @($stages)
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
        bridge_health_ok = $bridgeHealth.ok
        bridge_health = if ($bridgeHealth.ok) { $bridgeHealth.value } else { $null }
        bridge_health_error = $bridgeHealth.error
    }
    counts = [ordered]@{
        artifacts = $artifactRows.Count
        stages = @($stages).Count
        gates = @($gates).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review the implementation plan before creating any future transport scaffold.",
        "Do not execute bridge writes from Phase 20 Step 13.",
        "Do not add requests/httpx bridge calls or open sockets in this step.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_implementation_plan.json"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_implementation_plan_artifacts.csv"
$stagesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_implementation_plan_stages.csv"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_implementation_plan_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_implementation_plan_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_implementation_plan.md"

$plan | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$artifactRows | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$stages | Select-Object order, stage, description, allowed_now, boundary | Export-Csv -LiteralPath $stagesCsvPath -NoTypeInformation -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$artifactText = ($artifactRows | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$stageText = (@($stages) | ForEach-Object { "- $($_.order). $($_.stage): allowed_now=$($_.allowed_now); $($_.boundary)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Implementation Plan

Generated: $($plan.generated_at)

## Safety

- Bridge routing network transport implementation plan only: true
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

## Implementation plan

- Status: $planStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Artifacts: $($artifactRows.Count)
- Stages: $(@($stages).Count)
- Can execute bridge write now: false
- Can add network transport now: false
- Can enable network transport now: false
- Can arm network transport now: false
- Can open network socket now: false
- Can add real bridge HTTP client now: false
- Can add bridge POST now: false

## Artifacts

$artifactText

## Stages

$stageText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_implementation_plan=$OutputDir | status=$planStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_implementation_plan=$OutputDir | status=$planStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Network transport implementation plan files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
