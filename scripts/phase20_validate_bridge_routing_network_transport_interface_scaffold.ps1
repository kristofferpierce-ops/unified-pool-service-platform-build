param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$InterfaceScaffoldDir = "",
    [string]$ImplementationPlanDir = "",
    [string]$NetworkReleaseCheckpointDir = "",
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

function Normalize-String {
    param($Value)
    if ($null -eq $Value) { return "" }
    return ([string]$Value).Trim()
}

function Test-HasProperty {
    param($Object, [string]$Name)
    if ($null -eq $Object) { return $false }
    return $Object.PSObject.Properties.Name -contains $Name
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($InterfaceScaffoldDir)) {
    $InterfaceScaffoldDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_interface_scaffold_*" -JsonName "phase20_bridge_routing_network_transport_interface_scaffold.json"
}
if ([string]::IsNullOrWhiteSpace($ImplementationPlanDir)) {
    $ImplementationPlanDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_implementation_plan_*" -JsonName "phase20_bridge_routing_network_transport_implementation_plan.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($NetworkReleaseCheckpointDir)) {
    $NetworkReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_release_checkpoint.json" -Required $false
}

$scaffoldPath = Join-Path $InterfaceScaffoldDir "phase20_bridge_routing_network_transport_interface_scaffold.json"
$planPath = if (![string]::IsNullOrWhiteSpace($ImplementationPlanDir)) { Join-Path $ImplementationPlanDir "phase20_bridge_routing_network_transport_implementation_plan.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($NetworkReleaseCheckpointDir)) { Join-Path $NetworkReleaseCheckpointDir "phase20_bridge_routing_network_transport_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $scaffoldPath)) {
    throw "Network transport interface scaffold JSON not found: $scaffoldPath"
}

$scaffold = Read-JsonFile $scaffoldPath
$plan = if (![string]::IsNullOrWhiteSpace($planPath) -and (Test-Path -LiteralPath $planPath)) { Read-JsonFile $planPath } else { $null }
$release = if (![string]::IsNullOrWhiteSpace($releasePath) -and (Test-Path -LiteralPath $releasePath)) { Read-JsonFile $releasePath } else { $null }

$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$gates = New-Object System.Collections.ArrayList

# Artifact-level safety gates.
Add-Gate $gates "interface_scaffold_artifact_exists" $true "blocker" $scaffoldPath "interface_scaffold"
Add-Gate $gates "scaffold_is_scaffold_only" ($scaffold.safety.bridge_routing_network_transport_interface_scaffold_only -eq $true) "blocker" "bridge_routing_network_transport_interface_scaffold_only=$($scaffold.safety.bridge_routing_network_transport_interface_scaffold_only)" "interface_scaffold"
Add-Gate $gates "scaffold_has_no_real_http_client" ($scaffold.safety.real_bridge_http_client_implemented -eq $false) "blocker" "real_bridge_http_client_implemented=$($scaffold.safety.real_bridge_http_client_implemented)" "interface_scaffold"
Add-Gate $gates "scaffold_has_no_network_transport" ($scaffold.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($scaffold.safety.network_transport_implemented)" "interface_scaffold"
Add-Gate $gates "scaffold_has_no_network_transport_enabled" ($scaffold.safety.network_transport_enabled -eq $false) "blocker" "network_transport_enabled=$($scaffold.safety.network_transport_enabled)" "interface_scaffold"
Add-Gate $gates "scaffold_has_no_network_transport_armed" ($scaffold.safety.network_transport_armed -eq $false) "blocker" "network_transport_armed=$($scaffold.safety.network_transport_armed)" "interface_scaffold"
Add-Gate $gates "scaffold_has_no_socket_opened" ($scaffold.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($scaffold.safety.network_socket_opened)" "interface_scaffold"
Add-Gate $gates "scaffold_has_no_bridge_post_impl" ($scaffold.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_call_implemented=$($scaffold.safety.bridge_post_call_implemented)" "interface_scaffold"
Add-Gate $gates "scaffold_has_no_bridge_post_called" ($scaffold.safety.bridge_post_called -eq $false) "blocker" "bridge_post_called=$($scaffold.safety.bridge_post_called)" "interface_scaffold"
Add-Gate $gates "scaffold_has_no_bridge_mutation" ($scaffold.safety.bridge_mutation_performed -eq $false) "blocker" "bridge_mutation_performed=$($scaffold.safety.bridge_mutation_performed)" "interface_scaffold"
Add-Gate $gates "scaffold_has_no_platform_mutation" ($scaffold.safety.platform_db_mutation_performed -eq $false) "blocker" "platform_db_mutation_performed=$($scaffold.safety.platform_db_mutation_performed)" "interface_scaffold"
Add-Gate $gates "scaffold_has_no_lacrm_call" ($scaffold.safety.lacrm_call_performed -eq $false) "blocker" "lacrm_call_performed=$($scaffold.safety.lacrm_call_performed)" "interface_scaffold"
Add-Gate $gates "scaffold_has_no_routing_write_endpoint" ($scaffold.safety.routing_write_endpoint_implemented -eq $false) "blocker" "routing_write_endpoint_implemented=$($scaffold.safety.routing_write_endpoint_implemented)" "interface_scaffold"

foreach ($item in @($scaffold.safety_errors)) {
    Add-Issue $issues "blocker" "source_scaffold_safety_error" "$item" "interface_scaffold"
}

# Preview-level gates.
$preview = $scaffold.preview
$interface = $preview.interface_scaffold
$sampleRequest = $preview.sample_request
$sampleResult = $preview.sample_result

Add-Gate $gates "preview_is_blocked" ($preview.blocked -eq $true) "blocker" "blocked=$($preview.blocked)" "preview"
Add-Gate $gates "preview_is_preview_only" ($preview.preview_only -eq $true) "blocker" "preview_only=$($preview.preview_only)" "preview"
Add-Gate $gates "preview_is_interface_scaffold_only" ($preview.interface_scaffold_only -eq $true) "blocker" "interface_scaffold_only=$($preview.interface_scaffold_only)" "preview"
Add-Gate $gates "preview_would_not_add_network_transport" ($preview.would_add_network_transport -eq $false) "blocker" "would_add_network_transport=$($preview.would_add_network_transport)" "preview"
Add-Gate $gates "preview_would_not_enable_network_transport" ($preview.would_enable_network_transport -eq $false) "blocker" "would_enable_network_transport=$($preview.would_enable_network_transport)" "preview"
Add-Gate $gates "preview_would_not_arm_network_transport" ($preview.would_arm_network_transport -eq $false) "blocker" "would_arm_network_transport=$($preview.would_arm_network_transport)" "preview"
Add-Gate $gates "preview_would_not_open_socket" ($preview.would_open_socket -eq $false) "blocker" "would_open_socket=$($preview.would_open_socket)" "preview"
Add-Gate $gates "preview_would_not_send_http_request" ($preview.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($preview.would_send_http_request)" "preview"
Add-Gate $gates "preview_would_not_call_bridge" ($preview.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($preview.would_call_bridge)" "preview"
Add-Gate $gates "preview_would_not_mutate_bridge" ($preview.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($preview.would_mutate_bridge)" "preview"
Add-Gate $gates "preview_would_not_mutate_platform" ($preview.would_mutate_platform -eq $false) "blocker" "would_mutate_platform=$($preview.would_mutate_platform)" "preview"
Add-Gate $gates "preview_would_not_call_lacrm" ($preview.would_call_lacrm -eq $false) "blocker" "would_call_lacrm=$($preview.would_call_lacrm)" "preview"

# Interface-shape gates.
Add-Gate $gates "interface_module_present" ((Normalize-String $interface.module) -eq "app.services.routing_bridge_network_transport_interface_scaffold") "blocker" "module=$($interface.module)" "interface"
Add-Gate $gates "interface_adapter_name_present" ((Normalize-String $interface.adapter_name) -eq "BridgeRoutingTransportAdapterInterface") "blocker" "adapter_name=$($interface.adapter_name)" "interface"
Add-Gate $gates "interface_kind_scaffold_only" ((Normalize-String $interface.implementation_kind) -eq "interface_scaffold_only") "blocker" "implementation_kind=$($interface.implementation_kind)" "interface"
Add-Gate $gates "interface_no_network_transport" ($interface.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($interface.network_transport_implemented)" "interface"
Add-Gate $gates "interface_no_socket_opened" ($interface.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($interface.network_socket_opened)" "interface"
Add-Gate $gates "interface_no_bridge_post_impl" ($interface.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_call_implemented=$($interface.bridge_post_call_implemented)" "interface"
Add-Gate $gates "interface_execute_raises" ((Normalize-String $interface.execute_method_behavior) -eq "raises_runtime_error_no_transport") "blocker" "execute_method_behavior=$($interface.execute_method_behavior)" "interface"
Add-Gate $gates "interface_simulate_no_network" ((Normalize-String $interface.simulate_method_behavior) -eq "shape_only_no_network") "blocker" "simulate_method_behavior=$($interface.simulate_method_behavior)" "interface"
Add-Gate $gates "interface_has_hash" (![string]::IsNullOrWhiteSpace((Normalize-String $preview.interface_scaffold_hash))) "blocker" "interface_scaffold_hash=$($preview.interface_scaffold_hash)" "interface"

foreach ($className in @("BridgeRoutingTransportRequest", "BridgeRoutingTransportResult", "BridgeRoutingTransportAdapterInterface")) {
    $hasClass = @($interface.classes) -contains $className
    Add-Gate $gates "interface_has_class_$className" $hasClass "blocker" "class=$className" "interface"
}

foreach ($field in @("phone", "mode", "owner_type", "label", "default_contact_ids", "notes", "idempotency_key")) {
    $hasField = @($interface.request_fields) -contains $field
    Add-Gate $gates "request_shape_has_$field" $hasField "blocker" "request field $field" "interface"
}

foreach ($field in @("ok", "status_code", "transport_mode", "would_open_socket", "would_send_http_request", "would_call_bridge", "would_mutate_bridge", "message")) {
    $hasField = @($interface.result_fields) -contains $field
    Add-Gate $gates "result_shape_has_$field" $hasField "blocker" "result field $field" "interface"
}

foreach ($gateName in @("audit_prerequisite_gate", "rollback_snapshot_gate", "environment_gate_design", "operator_confirmation_gate", "response_capture_design", "future_cutover_packet_prerequisite")) {
    $hasFutureGate = @($interface.required_future_gates) -contains $gateName
    Add-Gate $gates "required_future_gate_$gateName" $hasFutureGate "blocker" "future gate $gateName" "interface"
}

# Sample request/result gates.
Add-Gate $gates "sample_request_mode_dry_run" ((Normalize-String $sampleRequest.mode) -eq "dry_run") "blocker" "mode=$($sampleRequest.mode)" "sample"
Add-Gate $gates "sample_request_has_idempotency_key" (![string]::IsNullOrWhiteSpace((Normalize-String $sampleRequest.idempotency_key))) "blocker" "idempotency_key=$($sampleRequest.idempotency_key)" "sample"
Add-Gate $gates "sample_result_not_ok" ($sampleResult.ok -eq $false) "blocker" "ok=$($sampleResult.ok)" "sample"
Add-Gate $gates "sample_result_status_code_zero" ([int]$sampleResult.status_code -eq 0) "blocker" "status_code=$($sampleResult.status_code)" "sample"
Add-Gate $gates "sample_result_mode_no_network" ((Normalize-String $sampleResult.transport_mode) -eq "dry_run_no_network") "blocker" "transport_mode=$($sampleResult.transport_mode)" "sample"
Add-Gate $gates "sample_result_would_not_open_socket" ($sampleResult.would_open_socket -eq $false) "blocker" "would_open_socket=$($sampleResult.would_open_socket)" "sample"
Add-Gate $gates "sample_result_would_not_send_http_request" ($sampleResult.would_send_http_request -eq $false) "blocker" "would_send_http_request=$($sampleResult.would_send_http_request)" "sample"
Add-Gate $gates "sample_result_would_not_call_bridge" ($sampleResult.would_call_bridge -eq $false) "blocker" "would_call_bridge=$($sampleResult.would_call_bridge)" "sample"
Add-Gate $gates "sample_result_would_not_mutate_bridge" ($sampleResult.would_mutate_bridge -eq $false) "blocker" "would_mutate_bridge=$($sampleResult.would_mutate_bridge)" "sample"

# Optional upstream artifacts.
if ($plan -ne $null) {
    Add-Gate $gates "implementation_plan_present" $true "review" $planPath "implementation_plan"
    Add-Gate $gates "implementation_plan_has_no_network_transport" ($plan.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($plan.safety.network_transport_implemented)" "implementation_plan"
    Add-Gate $gates "implementation_plan_has_no_socket" ($plan.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($plan.safety.network_socket_opened)" "implementation_plan"
    Add-Gate $gates "implementation_plan_blocks_network_transport" ($plan.implementation_plan.can_add_network_transport_now -eq $false) "blocker" "can_add_network_transport_now=$($plan.implementation_plan.can_add_network_transport_now)" "implementation_plan"
    Add-Gate $gates "implementation_plan_blocks_bridge_post" ($plan.implementation_plan.can_add_bridge_post_now -eq $false) "blocker" "can_add_bridge_post_now=$($plan.implementation_plan.can_add_bridge_post_now)" "implementation_plan"
} else {
    Add-Gate $gates "implementation_plan_present" $false "review" "Phase 20 Step 13 implementation plan not found." "implementation_plan"
}

if ($release -ne $null) {
    Add-Gate $gates "network_release_checkpoint_present" $true "review" $releasePath "network_release_checkpoint"
    Add-Gate $gates "network_release_has_no_network_transport" ($release.safety.network_transport_implemented -eq $false) "blocker" "network_transport_implemented=$($release.safety.network_transport_implemented)" "network_release_checkpoint"
    Add-Gate $gates "network_release_has_no_socket" ($release.safety.network_socket_opened -eq $false) "blocker" "network_socket_opened=$($release.safety.network_socket_opened)" "network_release_checkpoint"
    Add-Gate $gates "network_release_has_no_bridge_post" ($release.safety.bridge_post_called -eq $false -and $release.safety.bridge_post_call_implemented -eq $false) "blocker" "bridge_post_called=$($release.safety.bridge_post_called); bridge_post_call_implemented=$($release.safety.bridge_post_call_implemented)" "network_release_checkpoint"
} else {
    Add-Gate $gates "network_release_checkpoint_present" $false "review" "Phase 20 Step 12 release checkpoint not found." "network_release_checkpoint"
}

# Runtime checks. Unreachable runtime is review-level because artifact validation remains useful offline.
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
} else {
    Add-Gate $gates "runtime_executor_status_readable" $false "review" $executorStatus.error "runtime"
}

Add-Gate $gates "runtime_bridge_health_readable" $bridgeHealth.ok "review" $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "runtime"

# Convert failed gates into issues.
foreach ($gate in @($gates)) {
    if ($gate.passed -ne $true) {
        Add-Issue $issues $gate.severity $gate.gate $gate.evidence $gate.source
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$validationStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "valid_interface_scaffold"
} elseif ($blockerCount -eq 0) {
    "valid_with_review_items"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_interface_scaffold_validation_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 15"
    purpose = "Bridge routing network transport interface scaffold validation"
    source_interface_scaffold = $scaffoldPath
    source_implementation_plan = $planPath
    source_network_release_checkpoint = $releasePath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_interface_scaffold_validation_only = $true
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
    validation = [ordered]@{
        status = $validationStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        gate_count = @($gates).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        can_add_bridge_post_now = $false
        reason = if ($blockerCount -eq 0) {
            "Interface scaffold is structurally valid for review. Phase 20 Step 15 still implements no real network transport."
        } else {
            "Interface scaffold validation found blockers. Resolve blockers before any future real transport design."
        }
    }
    gates = @($gates)
    issues = @($issues)
    interface_scaffold = $interface
    sample_request = $sampleRequest
    sample_result = $sampleResult
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
        gates = @($gates).Count
        issues = @($issues).Count
        blockers = $blockerCount
        reviews = $reviewCount
        interface_classes = @($interface.classes).Count
        request_fields = @($interface.request_fields).Count
        result_fields = @($interface.result_fields).Count
    }
    next_recommended_actions = @(
        "Review this validation before adding any future transport adapter.",
        "Do not call bridge POST endpoints from Phase 20 Step 15.",
        "Do not add requests/httpx bridge calls or open sockets in this step.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_validation.json"
$gatesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_validation_gates.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_validation_issues.csv"
$classesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_validation_classes.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_validation.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$gates | Export-Csv -LiteralPath $gatesCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

@($interface.classes) | ForEach-Object {
    [ordered]@{
        class_name = $_
        implementation_kind = $interface.implementation_kind
        network_transport_implemented = $interface.network_transport_implemented
        network_socket_opened = $interface.network_socket_opened
        bridge_post_call_implemented = $interface.bridge_post_call_implemented
        scaffold_hash = $preview.interface_scaffold_hash
    }
} | Export-Csv -LiteralPath $classesCsvPath -NoTypeInformation -Encoding UTF8

$gateText = (@($gates) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.gate): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Interface Scaffold Validation

Generated: $($report.generated_at)

Source interface scaffold report:

``````
$scaffoldPath
``````

## Safety

- Bridge routing network transport interface scaffold validation only: true
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

## Validation

- Status: $validationStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Gates: $(@($gates).Count)
- Can execute bridge write now: false
- Can add network transport now: false
- Can enable network transport now: false
- Can arm network transport now: false
- Can open network socket now: false
- Can add real bridge HTTP client now: false
- Can add bridge POST now: false

## Gates

$gateText

## Issues

$issueText
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_interface_scaffold_validation=$OutputDir | status=$validationStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_interface_scaffold_validation=$OutputDir | status=$validationStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Network transport interface scaffold validation files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
