param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$DryRunInvocationReleaseCheckpointDir = "",
    [string]$DryRunInvocationOperatorSignoffDir = "",
    [string]$DryRunInvocationPreflightMatrixDir = "",
    [string]$DryRunInvocationValidationDir = "",
    [string]$DryRunInvocationPathDir = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$BackupDir = Join-Path $Workspace "backups"

function Get-LatestArtifactDir {
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
        return ""
    }

    return $latest.FullName
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

function Add-Requirement {
    param(
        [System.Collections.ArrayList]$Requirements,
        [string]$Category,
        [string]$Requirement,
        [string]$FieldName,
        [string]$Reason,
        [string]$Status = "required_for_future",
        [bool]$ImplementedNow = $false,
        [bool]$AllowsLiveWriteNow = $false
    )

    [void]$Requirements.Add([ordered]@{
        category = $Category
        requirement = $Requirement
        field_name = $FieldName
        reason = $Reason
        status = $Status
        implemented_now = $ImplementedNow
        allows_live_write_now = $AllowsLiveWriteNow
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

if ([string]::IsNullOrWhiteSpace($DryRunInvocationReleaseCheckpointDir)) {
    $DryRunInvocationReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json"
}
if ([string]::IsNullOrWhiteSpace($DryRunInvocationOperatorSignoffDir)) {
    $DryRunInvocationOperatorSignoffDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_operator_signoff_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path_operator_signoff.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($DryRunInvocationPreflightMatrixDir)) {
    $DryRunInvocationPreflightMatrixDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($DryRunInvocationValidationDir)) {
    $DryRunInvocationValidationDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($DryRunInvocationPathDir)) {
    $DryRunInvocationPathDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_dry_run_invocation_path_*" -JsonName "phase20_bridge_routing_network_transport_dry_run_invocation_path.json" -Required $false
}

$releasePath = Join-Path $DryRunInvocationReleaseCheckpointDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint.json"
$signoffPath = if (![string]::IsNullOrWhiteSpace($DryRunInvocationOperatorSignoffDir)) { Join-Path $DryRunInvocationOperatorSignoffDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_operator_signoff.json" } else { "" }
$preflightPath = if (![string]::IsNullOrWhiteSpace($DryRunInvocationPreflightMatrixDir)) { Join-Path $DryRunInvocationPreflightMatrixDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_preflight_matrix.json" } else { "" }
$validationPath = if (![string]::IsNullOrWhiteSpace($DryRunInvocationValidationDir)) { Join-Path $DryRunInvocationValidationDir "phase20_bridge_routing_network_transport_dry_run_invocation_path_validation.json" } else { "" }
$invocationPath = if (![string]::IsNullOrWhiteSpace($DryRunInvocationPathDir)) { Join-Path $DryRunInvocationPathDir "phase20_bridge_routing_network_transport_dry_run_invocation_path.json" } else { "" }

if (!(Test-Path -LiteralPath $releasePath)) {
    throw "Dry-run invocation path release checkpoint JSON not found: $releasePath"
}

$release = Read-JsonFile $releasePath
$signoff = if (![string]::IsNullOrWhiteSpace($signoffPath) -and (Test-Path -LiteralPath $signoffPath)) { Read-JsonFile $signoffPath } else { $null }
$preflight = if (![string]::IsNullOrWhiteSpace($preflightPath) -and (Test-Path -LiteralPath $preflightPath)) { Read-JsonFile $preflightPath } else { $null }
$validation = if (![string]::IsNullOrWhiteSpace($validationPath) -and (Test-Path -LiteralPath $validationPath)) { Read-JsonFile $validationPath } else { $null }
$invocation = if (![string]::IsNullOrWhiteSpace($invocationPath) -and (Test-Path -LiteralPath $invocationPath)) { Read-JsonFile $invocationPath } else { $null }

$invocationStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status"
$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$gates = New-Object System.Collections.ArrayList
$requirements = New-Object System.Collections.ArrayList

# Source release checkpoint safety gates.
Add-Gate $gates "dry_run_invocation_release_checkpoint_exists" $true "blocker" $releasePath "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_is_release_only" ($release.safety.bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_only -eq $true) "blocker" "bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_only=$($release.safety.bridge_routing_network_transport_dry_run_invocation_path_release_checkpoint_only)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_bridge_get_only" ($release.safety.bridge_get_only -eq $true) "blocker" "bridge_get_only=$($release.safety.bridge_get_only)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_no_network_transport" ($release.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($release.safety.network_transport_implemented)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_no_network_enabled" ($release.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($release.safety.network_transport_enabled)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_no_network_armed" ($release.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($release.safety.network_transport_armed)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_no_socket" ($release.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($release.safety.network_socket_opened)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_no_real_http_client" ($release.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($release.safety.real_bridge_http_client_implemented)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_no_bridge_post" ($release.safety.bridge_post_called -eq $false -and $release.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($release.safety.bridge_post_called); bridge_post_call_implemented=$($release.safety.bridge_post_call_implemented)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_no_mutation" ($release.safety.platform_db_mutation_performed -eq $false -and $release.safety.bridge_mutation_performed -eq $false) "blocker" "platform_db_mutation=$($release.safety.platform_db_mutation_performed); bridge_mutation=$($release.safety.bridge_mutation_performed)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_no_lacrm" ($release.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($release.safety.lacrm_call_performed)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_blocks_execution" ($release.release_checkpoint.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($release.release_checkpoint.can_execute_bridge_write_now)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_blocks_network_transport" ($release.release_checkpoint.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($release.release_checkpoint.can_add_network_transport_now)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_blocks_bridge_post" ($release.release_checkpoint.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($release.release_checkpoint.can_add_bridge_post_now)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_has_no_blockers" ([int]$release.release_checkpoint.blocker_count -eq 0) "blocker" "blocker_count=$($release.release_checkpoint.blocker_count)" "dry_run_invocation_release_checkpoint"
Add-Gate $gates "release_checkpoint_has_no_review_items" ([int]$release.release_checkpoint.review_count -eq 0) "review" "review_count=$($release.release_checkpoint.review_count)" "dry_run_invocation_release_checkpoint"

foreach ($issue in @($release.issues)) {
    if ($issue.severity -eq "blocker") {
        Add-Issue $issues "blocker" "release_checkpoint_$($issue.code)" "$($issue.message)" "dry_run_invocation_release_checkpoint"
    } elseif ($issue.severity -eq "review") {
        Add-Issue $issues "review" "release_checkpoint_$($issue.code)" "$($issue.message)" "dry_run_invocation_release_checkpoint"
    }
}

# Optional upstream evidence.
if ($signoff -ne $null) {
    Add-Gate $gates "operator_signoff_present" $true "review" $signoffPath "dry_run_invocation_operator_signoff"
    Add-Gate $gates "operator_signoff_blocks_bridge_post" ($signoff.signoff.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($signoff.signoff.can_add_bridge_post_now)" "dry_run_invocation_operator_signoff"
    Add-Gate $gates "operator_signoff_not_live_approved" ($signoff.signoff.approved_for_live_bridge_write -ne $true) "blocker" "approved_for_live_bridge_write=$($signoff.signoff.approved_for_live_bridge_write)" "dry_run_invocation_operator_signoff"
} else {
    Add-Gate $gates "operator_signoff_present" $false "review" "Phase 20 Step 22 operator signoff not found." "dry_run_invocation_operator_signoff"
}

if ($preflight -ne $null) {
    Add-Gate $gates "preflight_matrix_present" $true "review" $preflightPath "dry_run_invocation_preflight"
    Add-Gate $gates "preflight_blocks_execution" ($preflight.preflight.can_execute_bridge_write_now -eq $false) "blocker" "can_execute_bridge_write_now=$($preflight.preflight.can_execute_bridge_write_now)" "dry_run_invocation_preflight"
    Add-Gate $gates "preflight_blocks_network_transport" ($preflight.preflight.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($preflight.preflight.can_add_network_transport_now)" "dry_run_invocation_preflight"
} else {
    Add-Gate $gates "preflight_matrix_present" $false "review" "Phase 20 Step 21 preflight matrix not found." "dry_run_invocation_preflight"
}

if ($validation -ne $null) {
    Add-Gate $gates "validation_present" $true "review" $validationPath "dry_run_invocation_validation"
    Add-Gate $gates "validation_blocks_bridge_post" ($validation.validation.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($validation.validation.can_add_bridge_post_now)" "dry_run_invocation_validation"
} else {
    Add-Gate $gates "validation_present" $false "review" "Phase 20 Step 20 validation not found." "dry_run_invocation_validation"
}

if ($invocation -ne $null) {
    Add-Gate $gates "dry_run_invocation_path_present" $true "review" $invocationPath "dry_run_invocation_path"
    Add-Gate $gates "invocation_path_would_not_call_bridge" ($invocation.preview.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($invocation.preview.would_call_bridge)" "dry_run_invocation_path"
    Add-Gate $gates "invocation_path_would_not_mutate_bridge" ($invocation.preview.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($invocation.preview.would_mutate_bridge)" "dry_run_invocation_path"
} else {
    Add-Gate $gates "dry_run_invocation_path_present" $false "review" "Phase 20 Step 19 dry-run invocation path not found." "dry_run_invocation_path"
}

# Runtime checks. Unreachable runtime is review-level; contradictions are blockers.
if ($invocationStatus.ok) {
    Add-Gate $gates "runtime_invocation_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-invocation-path/status" "runtime"
    Add-Gate $gates "runtime_invocation_no_network_transport" ($invocationStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($invocationStatus.value.network_transport_implemented)" "runtime"
    Add-Gate $gates "runtime_invocation_no_socket" ($invocationStatus.value.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($invocationStatus.value.network_socket_opened)" "runtime"
    Add-Gate $gates "runtime_invocation_no_bridge_post" ($invocationStatus.value.bridge_post_called -eq $false -and $invocationStatus.value.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($invocationStatus.value.bridge_post_called); bridge_post_call_implemented=$($invocationStatus.value.bridge_post_call_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_invocation_status_readable" $false "review" $invocationStatus.error "runtime"
}

if ($scaffoldStatus.ok) {
    Add-Gate $gates "runtime_scaffold_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status" "runtime"
    Add-Gate $gates "runtime_scaffold_no_network_transport" ($scaffoldStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($scaffoldStatus.value.network_transport_implemented)" "runtime"
} else {
    Add-Gate $gates "runtime_scaffold_status_readable" $false "review" $scaffoldStatus.error "runtime"
}

if ($adapterStatus.ok) {
    Add-Gate $gates "runtime_adapter_status_readable" $true "review" "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status" "runtime"
    Add-Gate $gates "runtime_adapter_no_network_transport" ($adapterStatus.value.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($adapterStatus.value.network_transport_implemented)" "runtime"
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

# Audit prerequisites for future real transport. These are requirements only, not writes.
Add-Requirement $requirements "identity" "Every future transport attempt must have a stable transport execution id." "transport_execution_id" "Allows audit rows, rollback snapshots, and operator reports to refer to the same future attempt."
Add-Requirement $requirements "identity" "Every future transport attempt must have an idempotency key." "idempotency_key" "Prevents duplicate bridge writes if an operator retries a future transport call."
Add-Requirement $requirements "operator" "Every future transport attempt must record the operator name." "operator_name" "Associates any future write with a human review action."
Add-Requirement $requirements "operator" "Every future live attempt must store the typed confirmation phrase result." "confirmation_phrase_matched" "Proves whether the operator provided the exact confirmation required for a future live path."
Add-Requirement $requirements "request" "Every future transport attempt must store a canonical request hash." "request_hash" "Supports tamper-evident audit comparison without storing sensitive request detail in every report."
Add-Requirement $requirements "request" "Every future transport attempt must store request mode and dry-run flag." "dry_run" "Separates no-network dry-runs from any future live/network attempt."
Add-Requirement $requirements "request" "Every future transport attempt must store source artifact references." "source_checkpoint_paths" "Links execution back to release checkpoints, signoff packets, and preflight evidence."
Add-Requirement $requirements "safety" "Every future transport attempt must store enabled and armed gate states." "network_transport_enabled,network_transport_armed" "Proves future transport was not accidentally executed while disabled or unarmed."
Add-Requirement $requirements "safety" "Every future transport attempt must store socket and bridge POST booleans." "network_socket_opened,bridge_post_called" "Makes the network boundary visible in audit evidence."
Add-Requirement $requirements "response" "Every future transport attempt must store response status and response hash." "response_status_code,response_hash" "Supports response capture without requiring raw bridge response disclosure in summaries."
Add-Requirement $requirements "response" "Every future failed transport attempt must store error class and message." "error_code,error_message" "Allows future rollback and troubleshooting without re-running a write."
Add-Requirement $requirements "rollback" "Every future live attempt must have a rollback snapshot reference before execution." "rollback_snapshot_id" "Prevents future writes from proceeding without a known rollback point."
Add-Requirement $requirements "timing" "Every future transport attempt must store created, started, and finished timestamps." "created_at,started_at,finished_at" "Enables duration and ordering review."
Add-Requirement $requirements "immutability" "Audit rows must be append-only in future work." "append_only" "Prevents a future transport layer from overwriting audit history."
Add-Requirement $requirements "boundary" "Phase 20 Step 24 must not create audit rows." "audit_row_created" "This step is only an audit prerequisite gate." "not_created_in_step_24" $false $false

Add-Gate $gates "audit_requirement_count_minimum" (@($requirements).Count -ge 12) "blocker" "requirements=$(@($requirements).Count)" "audit_prerequisites"
Add-Gate $gates "audit_rows_not_created" $true "blocker" "audit_row_created=False" "audit_prerequisites"
Add-Gate $gates "rollback_rows_not_created" $true "blocker" "rollback_row_created=False" "audit_prerequisites"

# Convert failed gates into issues.
foreach ($gate in @($gates)) {
    if ($gate.passed -ne $true) {
        Add-Issue $issues $gate.severity $gate.gate $gate.evidence $gate.source
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$gateStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "audit_prerequisite_ready_for_review_no_write"
} elseif ($blockerCount -eq 0) {
    "audit_prerequisite_review_required_no_write"
} else {
    "audit_prerequisite_blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$sourceArtifacts = @(
    [ordered]@{ key="dry_run_invocation_path_release_checkpoint"; json_path=$releasePath; sha256=Get-FileSha256 $releasePath },
    [ordered]@{ key="dry_run_invocation_path_operator_signoff"; json_path=$signoffPath; sha256=Get-FileSha256 $signoffPath },
    [ordered]@{ key="dry_run_invocation_path_preflight_matrix"; json_path=$preflightPath; sha256=Get-FileSha256 $preflightPath },
    [ordered]@{ key="dry_run_invocation_path_validation"; json_path=$validationPath; sha256=Get-FileSha256 $validationPath },
    [ordered]@{ key="dry_run_invocation_path"; json_path=$invocationPath; sha256=Get-FileSha256 $invocationPath }
)

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 24"
    purpose = "Bridge routing network transport audit prerequisite gate"
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_audit_prerequisite_gate_only = $true
        bridge_get_only = $true
        audit_row_created = $false
        rollback_row_created = $false
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
    audit_prerequisite_gate = [ordered]@{
        status = $gateStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        gate_count = @($gates).Count
        requirement_count = @($requirements).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        can_add_bridge_post_now = $false
        can_create_audit_rows_now = $false
        can_create_rollback_rows_now = $false
        reason = if ($blockerCount -eq 0) {
            "Audit prerequisites are ready for review. Phase 20 Step 24 still creates no audit rows, opens no socket, calls no bridge POST, and authorizes no execution."
        } else {
            "Audit prerequisite gate has blockers. Resolve blockers before any future real network transport design."
        }
    }
    source_artifacts = $sourceArtifacts
    audit_requirements = @($requirements)
    gates = @($gates)
    issues = @($issues)
    runtime_status = [ordered]@{
        invocation_status_ok = $invocationStatus.ok
        invocation_status = if ($invocationStatus.ok) { $invocationStatus.value } else { $null }
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
        source_artifacts = @($sourceArtifacts).Count
        audit_requirements = @($requirements).Count
        gates = @($gates).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
    }
    next_recommended_actions = @(
        "Review this audit prerequisite gate before designing future audit-row writes.",
        "Do not create audit rows from Phase 20 Step 24.",
        "Do not call bridge POST endpoints from Phase 20 Step 24.",
        "Future real transport work must prove audit and rollback prerequisites before execution.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate.json"
$requirementsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate_requirements.csv"
$artifactsCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate_artifacts.csv"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_audit_prerequisite_gate.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$requirements | Export-Csv -LiteralPath $requirementsCsvPath -NoTypeInformation -Encoding UTF8
$sourceArtifacts | Export-Csv -LiteralPath $artifactsCsvPath -NoTypeInformation -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$requirementText = (@($requirements) | ForEach-Object { "- [$($_.category)] $($_.field_name): $($_.requirement) (implemented now: $($_.implemented_now))" }) -join "`n"
$artifactText = (@($sourceArtifacts) | ForEach-Object { "- $($_.key): $($_.json_path) [$($_.sha256)]" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Audit Prerequisite Gate

Generated: $($report.generated_at)

Source dry-run invocation path release checkpoint:

``````
$releasePath
``````

## Safety

- Bridge routing network transport audit prerequisite gate only: true
- Bridge GET only: true
- Audit row created: false
- Rollback row created: false
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

## Audit prerequisite gate

- Status: $gateStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Requirements: $(@($requirements).Count)
- Can execute bridge write now: false
- Can add network transport now: false
- Can enable network transport now: false
- Can arm network transport now: false
- Can open network socket now: false
- Can add real bridge HTTP client now: false
- Can add bridge POST now: false
- Can create audit rows now: false
- Can create rollback rows now: false

## Source artifacts

$artifactText

## Future audit requirements

$requirementText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_audit_prerequisite_gate=$OutputDir | status=$gateStatus | bridge_post_called=False | audit_row_created=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_audit_prerequisite_gate=$OutputDir | status=$gateStatus | blockers=$blockerCount | bridge_post_called=False | audit_row_created=False"
}

Write-Host ""
Write-Host "Audit prerequisite gate files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
