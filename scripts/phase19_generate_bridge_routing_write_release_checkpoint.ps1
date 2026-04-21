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

function Add-CheckpointGate {
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
    $operatorSignoff = Get-LatestArtifact -FolderFilter "phase19_bridge_routing_write_operator_signoff_*" -JsonName "phase19_bridge_routing_write_operator_signoff.json" -Required $true
} else {
    $signoffJson = Join-Path $OperatorSignoffDir "phase19_bridge_routing_write_operator_signoff.json"
    if (!(Test-Path -LiteralPath $signoffJson)) {
        throw "Operator signoff JSON not found: $signoffJson"
    }
    $operatorSignoff = [ordered]@{
        folder = $OperatorSignoffDir
        folder_name = Split-Path -Leaf $OperatorSignoffDir
        json_path = $signoffJson
        json_name = "phase19_bridge_routing_write_operator_signoff.json"
        last_write_time = (Get-Item -LiteralPath $signoffJson).LastWriteTime.ToString("o")
    }
}

$artifactSpecs = @(
    @{ key="contract"; filter="phase19_bridge_routing_write_contract_*"; json="phase19_bridge_routing_write_contract.json"; required=$true },
    @{ key="apply_preview"; filter="phase19_routing_bridge_apply_preview_*"; json="phase19_routing_bridge_apply_preview.json"; required=$true },
    @{ key="write_rehearsal"; filter="phase19_bridge_routing_write_rehearsal_*"; json="phase19_bridge_routing_write_rehearsal.json"; required=$true },
    @{ key="audit_plan"; filter="phase19_bridge_routing_write_audit_plan_*"; json="phase19_bridge_routing_write_audit_plan.json"; required=$true },
    @{ key="audit_writer_run"; filter="phase19_bridge_routing_write_audit_writer_run_*"; json="phase19_bridge_routing_write_audit_writer_run.json"; required=$true },
    @{ key="rollback_snapshot"; filter="phase19_bridge_routing_rollback_snapshot_*"; json="phase19_bridge_routing_rollback_snapshot.json"; required=$true },
    @{ key="readiness"; filter="phase19_bridge_routing_write_readiness_*"; json="phase19_bridge_routing_write_readiness.json"; required=$true },
    @{ key="cutover_packet"; filter="phase19_bridge_routing_write_cutover_packet_*"; json="phase19_bridge_routing_write_cutover_packet.json"; required=$true },
    @{ key="implementation_plan"; filter="phase19_bridge_routing_write_implementation_plan_*"; json="phase19_bridge_routing_write_implementation_plan.json"; required=$true },
    @{ key="scaffold"; filter="phase19_bridge_routing_write_scaffold_*"; json="phase19_bridge_routing_write_scaffold.json"; required=$true },
    @{ key="dry_run_bundle"; filter="phase19_bridge_routing_write_dry_run_bundle_*"; json="phase19_bridge_routing_write_dry_run_bundle.json"; required=$true },
    @{ key="dry_run_validation"; filter="phase19_bridge_routing_write_dry_run_validation_*"; json="phase19_bridge_routing_write_dry_run_validation.json"; required=$true },
    @{ key="preflight_matrix"; filter="phase19_bridge_routing_write_preflight_matrix_*"; json="phase19_bridge_routing_write_preflight_matrix.json"; required=$true },
    @{ key="operator_signoff"; artifact=$operatorSignoff; required=$true }
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
            Add-CheckpointGate $gates "artifact_present_$($spec.key)" $true "blocker" $artifact.json_path $spec.key
        }
    } catch {
        Add-Issue $issues "blocker" "missing_artifact_$($spec.key)" $_.Exception.Message $spec.key
        Add-CheckpointGate $gates "artifact_present_$($spec.key)" $false "blocker" $_.Exception.Message $spec.key
    }
}

# Runtime checks stay read-only and review-level if unavailable.
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bundleStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status"
$auditStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-audit/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

if ($executorStatus.ok) {
    Add-CheckpointGate $gates "runtime_executor_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-write-executor/status" "runtime"
    Add-CheckpointGate $gates "runtime_executor_no_execution_endpoint" ($executorStatus.value.execution_endpoint_available -eq $false) "blocker" "execution_endpoint_available=$($executorStatus.value.execution_endpoint_available)" "runtime"
    Add-CheckpointGate $gates "runtime_executor_no_bridge_post_impl" ($executorStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_call_implemented=$($executorStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    Add-CheckpointGate $gates "runtime_executor_status_readable" $false "review" $executorStatus.error "runtime"
}

if ($bundleStatus.ok) {
    Add-CheckpointGate $gates "runtime_bundle_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-write-dry-run-bundle/status" "runtime"
    Add-CheckpointGate $gates "runtime_bundle_no_http_client" ($bundleStatus.value.bridge_http_client_implemented -eq $false) "blocker" "bridge_http_client_implemented=$($bundleStatus.value.bridge_http_client_implemented)" "runtime"
    Add-CheckpointGate $gates "runtime_bundle_no_bridge_post" ($bundleStatus.value.bridge_post_call_implemented -eq $false -and $bundleStatus.value.bridge_post_called -eq $false) "blocker" "bridge_post_call_implemented=$($bundleStatus.value.bridge_post_call_implemented); bridge_post_called=$($bundleStatus.value.bridge_post_called)" "runtime"
} else {
    Add-CheckpointGate $gates "runtime_bundle_status_readable" $false "review" $bundleStatus.error "runtime"
}

if ($auditStatus.ok) {
    Add-CheckpointGate $gates "runtime_audit_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-write-audit/status" "runtime"
    Add-CheckpointGate $gates "runtime_audit_bridge_post_disabled" ($auditStatus.value.bridge_post_enabled -eq $false) "blocker" "bridge_post_enabled=$($auditStatus.value.bridge_post_enabled)" "runtime"
} else {
    Add-CheckpointGate $gates "runtime_audit_status_readable" $false "review" $auditStatus.error "runtime"
}

Add-CheckpointGate $gates "runtime_bridge_health_readable" $bridgeHealth.ok "review" $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "runtime"

# Artifact safety invariants.
foreach ($key in $artifactData.Keys) {
    $data = $artifactData[$key]
    $safety = $data.safety

    if ($null -eq $safety) {
        Add-Issue $issues "review" "artifact_missing_safety_$key" "Artifact does not include a safety block." $key
        continue
    }

    $bridgePostCalled = Get-NestedValue $data @("safety", "bridge_post_called")
    if ($bridgePostCalled -eq $true) {
        Add-Issue $issues "blocker" "artifact_bridge_post_called_$key" "$key reports bridge_post_called=true." $key
    }

    $bridgeMutation = Get-NestedValue $data @("safety", "bridge_mutation_performed")
    if ($bridgeMutation -eq $true) {
        Add-Issue $issues "blocker" "artifact_bridge_mutation_$key" "$key reports bridge_mutation_performed=true." $key
    }

    $platformMutation = Get-NestedValue $data @("safety", "platform_db_mutation_performed")
    if ($platformMutation -eq $true -and $key -notin @("audit_writer_run")) {
        Add-Issue $issues "blocker" "artifact_platform_mutation_$key" "$key reports platform_db_mutation_performed=true outside the audit-writer artifact." $key
    }

    $lacrmCall = Get-NestedValue $data @("safety", "lacrm_call_performed")
    if ($lacrmCall -eq $true) {
        Add-Issue $issues "blocker" "artifact_lacrm_call_$key" "$key reports lacrm_call_performed=true." $key
    }

    $httpClient = Get-NestedValue $data @("safety", "bridge_http_client_implemented")
    if ($httpClient -eq $true) {
        Add-Issue $issues "blocker" "artifact_http_client_implemented_$key" "$key reports bridge_http_client_implemented=true." $key
    }

    $routingEndpoint = Get-NestedValue $data @("safety", "routing_write_endpoint_implemented")
    if ($routingEndpoint -eq $true) {
        Add-Issue $issues "blocker" "artifact_routing_write_endpoint_$key" "$key reports routing_write_endpoint_implemented=true." $key
    }
}

# Higher-level no-execution gates from the newest review artifacts.
if ($artifactData.Contains("preflight_matrix")) {
    $preflight = $artifactData.preflight_matrix
    Add-CheckpointGate $gates "preflight_can_execute_false" ($preflight.preflight.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($preflight.preflight.can_execute_bridge_write_now)" "preflight_matrix"
    Add-CheckpointGate $gates "preflight_can_add_client_false" ($preflight.preflight.can_add_bridge_http_client_now -eq $false) "blocker" "can_add_bridge_http_client_now=$($preflight.preflight.can_add_bridge_http_client_now)" "preflight_matrix"
}

if ($artifactData.Contains("operator_signoff")) {
    $signoff = $artifactData.operator_signoff
    Add-CheckpointGate $gates "operator_signoff_can_execute_false" ($signoff.signoff.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($signoff.signoff.can_execute_bridge_write_now)" "operator_signoff"
    Add-CheckpointGate $gates "operator_signoff_can_add_client_false" ($signoff.signoff.can_add_bridge_http_client_now -eq $false) "blocker" "can_add_bridge_http_client_now=$($signoff.signoff.can_add_bridge_http_client_now)" "operator_signoff"
    Add-CheckpointGate $gates "operator_signoff_not_live_approved" ($signoff.signoff.approved_for_live_bridge_write -ne $true) "blocker" "approved_for_live_bridge_write=$($signoff.signoff.approved_for_live_bridge_write)" "operator_signoff"
}

if ($artifactData.Contains("dry_run_bundle")) {
    $bundle = $artifactData.dry_run_bundle
    $bundleRows = @()
    if ($bundle.bundle -and $bundle.bundle.bundle_rows) { $bundleRows = @($bundle.bundle.bundle_rows) }

    foreach ($row in $bundleRows) {
        if ($row.would_call_bridge -ne $false) {
            Add-Issue $issues "blocker" "bundle_row_would_call_bridge" "A dry-run bundle row says would_call_bridge is not false." "dry_run_bundle"
        }
        if ($row.ready_for_live_execution -ne $false) {
            Add-Issue $issues "blocker" "bundle_row_ready_for_live" "A dry-run bundle row says ready_for_live_execution is not false." "dry_run_bundle"
        }
    }
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
    "release_checkpoint_clean_no_post"
} elseif ($blockerCount -eq 0) {
    "release_checkpoint_review_required_no_post"
} else {
    "release_checkpoint_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase19_bridge_routing_write_release_checkpoint_$stamp"
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
    phase = "Phase 19 Step 50"
    purpose = "Bridge routing write no-POST release checkpoint"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_write_release_checkpoint_only = $true
        bridge_get_only = $true
        platform_db_mutation_performed = $false
        bridge_mutation_performed = $false
        bridge_post_called = $false
        lacrm_call_performed = $false
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
        can_add_bridge_http_client_now = $false
        release_freeze_label = "phase19_bridge_routing_write_no_post_checkpoint"
        reason = if ($blockerCount -eq 0) {
            "Release checkpoint is suitable for review. Step 50 still implements no bridge write and authorizes no execution."
        } else {
            "Release checkpoint has blockers. Resolve blockers before any future bridge HTTP client design."
        }
    }
    artifacts = $artifactRows
    gates = @($gates)
    issues = @($issues)
    runtime_status = [ordered]@{
        executor_status_ok = $executorStatus.ok
        executor_status = if ($executorStatus.ok) { $executorStatus.value } else { $null }
        bundle_status_ok = $bundleStatus.ok
        bundle_status = if ($bundleStatus.ok) { $bundleStatus.value } else { $null }
        audit_status_ok = $auditStatus.ok
        audit_status = if ($auditStatus.ok) { $auditStatus.value } else { $null }
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
        "Review this release checkpoint before starting any new phase that adds a bridge HTTP client.",
        "Do not execute bridge writes from Step 50.",
        "Future bridge HTTP client work must begin from a new explicitly guarded phase and keep dry-run as default.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase19_bridge_routing_write_release_checkpoint.json"
$artifactsCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_release_checkpoint_artifacts.csv"
$gatesCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_release_checkpoint_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase19_bridge_routing_write_release_checkpoint_issues.csv"
$mdPath = Join-Path $OutputDir "phase19_bridge_routing_write_release_checkpoint.md"

$checkpoint | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$artifactRows | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$artifactText = ($artifactRows | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$gateText = (@($gates) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.gate): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 19 Bridge Routing Write Release Checkpoint

Generated: $($checkpoint.generated_at)

## Safety

- Bridge routing write release checkpoint only: true
- Bridge GET only: true
- Platform DB mutation performed: false
- Bridge mutation performed: false
- Bridge POST called: false
- LACRM call performed: false
- Bridge HTTP client implemented: false
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
- Can add bridge HTTP client now: false

## Artifacts

$artifactText

## Gates

$gateText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_write_release_checkpoint=$OutputDir | status=$checkpointStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_write_release_checkpoint=$OutputDir | status=$checkpointStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Release checkpoint files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
