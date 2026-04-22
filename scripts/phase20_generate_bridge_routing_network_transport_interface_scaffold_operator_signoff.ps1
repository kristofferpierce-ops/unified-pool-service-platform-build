param(
    [string]$Workspace = "C:\Users\krist\Desktop\unified_pool_service_platform_build",
    [string]$PlatformApi = "http://127.0.0.1:8010",
    [string]$BridgeUrl = "http://127.0.0.1:8000",
    [string]$PreflightMatrixDir = "",
    [string]$ScaffoldValidationDir = "",
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

function Add-SignoffItem {
    param(
        [System.Collections.ArrayList]$Items,
        [string]$Category,
        [string]$Item,
        [bool]$Passed,
        [string]$Evidence = "",
        [string]$Required = "yes",
        [string]$OperatorNote = ""
    )

    [void]$Items.Add([ordered]@{
        category = $Category
        item = $Item
        passed = $Passed
        evidence = $Evidence
        required = $Required
        operator_note = $OperatorNote
    })
}

New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null

if ([string]::IsNullOrWhiteSpace($PreflightMatrixDir)) {
    $PreflightMatrixDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_interface_scaffold_preflight_matrix_*" -JsonName "phase20_bridge_routing_network_transport_interface_scaffold_preflight_matrix.json"
}
if ([string]::IsNullOrWhiteSpace($ScaffoldValidationDir)) {
    $ScaffoldValidationDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_interface_scaffold_validation_*" -JsonName "phase20_bridge_routing_network_transport_interface_scaffold_validation.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($InterfaceScaffoldDir)) {
    $InterfaceScaffoldDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_interface_scaffold_*" -JsonName "phase20_bridge_routing_network_transport_interface_scaffold.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($ImplementationPlanDir)) {
    $ImplementationPlanDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_implementation_plan_*" -JsonName "phase20_bridge_routing_network_transport_implementation_plan.json" -Required $false
}
if ([string]::IsNullOrWhiteSpace($NetworkReleaseCheckpointDir)) {
    $NetworkReleaseCheckpointDir = Get-LatestArtifactDir -FolderFilter "phase20_bridge_routing_network_transport_release_checkpoint_*" -JsonName "phase20_bridge_routing_network_transport_release_checkpoint.json" -Required $false
}

$preflightPath = Join-Path $PreflightMatrixDir "phase20_bridge_routing_network_transport_interface_scaffold_preflight_matrix.json"
$validationPath = if (![string]::IsNullOrWhiteSpace($ScaffoldValidationDir)) { Join-Path $ScaffoldValidationDir "phase20_bridge_routing_network_transport_interface_scaffold_validation.json" } else { "" }
$scaffoldPath = if (![string]::IsNullOrWhiteSpace($InterfaceScaffoldDir)) { Join-Path $InterfaceScaffoldDir "phase20_bridge_routing_network_transport_interface_scaffold.json" } else { "" }
$planPath = if (![string]::IsNullOrWhiteSpace($ImplementationPlanDir)) { Join-Path $ImplementationPlanDir "phase20_bridge_routing_network_transport_implementation_plan.json" } else { "" }
$releasePath = if (![string]::IsNullOrWhiteSpace($NetworkReleaseCheckpointDir)) { Join-Path $NetworkReleaseCheckpointDir "phase20_bridge_routing_network_transport_release_checkpoint.json" } else { "" }

if (!(Test-Path -LiteralPath $preflightPath)) {
    throw "Interface scaffold preflight matrix JSON not found: $preflightPath"
}

$preflight = Read-JsonFile $preflightPath
$validation = if (![string]::IsNullOrWhiteSpace($validationPath) -and (Test-Path -LiteralPath $validationPath)) { Read-JsonFile $validationPath } else { $null }
$scaffold = if (![string]::IsNullOrWhiteSpace($scaffoldPath) -and (Test-Path -LiteralPath $scaffoldPath)) { Read-JsonFile $scaffoldPath } else { $null }
$plan = if (![string]::IsNullOrWhiteSpace($planPath) -and (Test-Path -LiteralPath $planPath)) { Read-JsonFile $planPath } else { $null }
$release = if (![string]::IsNullOrWhiteSpace($releasePath) -and (Test-Path -LiteralPath $releasePath)) { Read-JsonFile $releasePath } else { $null }

$scaffoldStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status"
$adapterStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status"
$guardStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status"
$httpDryRunStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status"
$executorStatus = Try-GetJson "$PlatformApi/front-desk/routing/bridge-write-executor/status"
$bridgeHealth = Try-GetJson "$BridgeUrl/health"

$issues = New-Object System.Collections.ArrayList
$signoffItems = New-Object System.Collections.ArrayList

Add-SignoffItem $signoffItems "artifact" "Interface scaffold preflight matrix exists" $true $preflightPath
Add-SignoffItem $signoffItems "safety" "Preflight matrix is preflight-matrix-only" ($preflight.safety.bridge_routing_network_transport_interface_scaffold_preflight_matrix_only -eq $true) "bridge_routing_network_transport_interface_scaffold_preflight_matrix_only=$($preflight.safety.bridge_routing_network_transport_interface_scaffold_preflight_matrix_only)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix is bridge GET only" ($preflight.safety.bridge_get_only -eq $true) "bridge_get_only=$($preflight.safety.bridge_get_only)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no platform DB mutation" ($preflight.safety.platform_db_mutation_performed -eq $false) "platform_db_mutation_performed=$($preflight.safety.platform_db_mutation_performed)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no bridge mutation" ($preflight.safety.bridge_mutation_performed -eq $false) "bridge_mutation_performed=$($preflight.safety.bridge_mutation_performed)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no bridge POST" ($preflight.safety.bridge_post_called -eq $false -and $preflight.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($preflight.safety.bridge_post_called); bridge_post_call_implemented=$($preflight.safety.bridge_post_call_implemented)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no real HTTP client" ($preflight.safety.real_bridge_http_client_implemented -eq $false) "real_bridge_http_client_implemented=$($preflight.safety.real_bridge_http_client_implemented)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no network transport" ($preflight.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($preflight.safety.network_transport_implemented)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no network transport enabled" ($preflight.safety.network_transport_enabled -eq $false) "network_transport_enabled=$($preflight.safety.network_transport_enabled)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no network transport armed" ($preflight.safety.network_transport_armed -eq $false) "network_transport_armed=$($preflight.safety.network_transport_armed)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no socket opened" ($preflight.safety.network_socket_opened -eq $false) "network_socket_opened=$($preflight.safety.network_socket_opened)"
Add-SignoffItem $signoffItems "safety" "Preflight matrix has no LACRM call" ($preflight.safety.lacrm_call_performed -eq $false) "lacrm_call_performed=$($preflight.safety.lacrm_call_performed)"

Add-SignoffItem $signoffItems "gate" "Preflight says bridge write cannot execute now" ($preflight.preflight.can_execute_bridge_write_now -eq $false) "can_execute_bridge_write_now=$($preflight.preflight.can_execute_bridge_write_now)"
Add-SignoffItem $signoffItems "gate" "Preflight says network transport cannot be added now" ($preflight.preflight.can_add_network_transport_now -eq $false) "can_add_network_transport_now=$($preflight.preflight.can_add_network_transport_now)"
Add-SignoffItem $signoffItems "gate" "Preflight says network transport cannot be enabled now" ($preflight.preflight.can_enable_network_transport_now -eq $false) "can_enable_network_transport_now=$($preflight.preflight.can_enable_network_transport_now)"
Add-SignoffItem $signoffItems "gate" "Preflight says network transport cannot be armed now" ($preflight.preflight.can_arm_network_transport_now -eq $false) "can_arm_network_transport_now=$($preflight.preflight.can_arm_network_transport_now)"
Add-SignoffItem $signoffItems "gate" "Preflight says network socket cannot be opened now" ($preflight.preflight.can_open_network_socket_now -eq $false) "can_open_network_socket_now=$($preflight.preflight.can_open_network_socket_now)"
Add-SignoffItem $signoffItems "gate" "Preflight says real bridge HTTP client cannot be added now" ($preflight.preflight.can_add_real_bridge_http_client_now -eq $false) "can_add_real_bridge_http_client_now=$($preflight.preflight.can_add_real_bridge_http_client_now)"
Add-SignoffItem $signoffItems "gate" "Preflight says bridge POST cannot be added now" ($preflight.preflight.can_add_bridge_post_now -eq $false) "can_add_bridge_post_now=$($preflight.preflight.can_add_bridge_post_now)"
Add-SignoffItem $signoffItems "gate" "Preflight has zero hard blockers" ([int]$preflight.preflight.blocker_count -eq 0) "blocker_count=$($preflight.preflight.blocker_count)"
Add-SignoffItem $signoffItems "gate" "Preflight has zero review items" ([int]$preflight.preflight.review_count -eq 0) "review_count=$($preflight.preflight.review_count)" "recommended"

foreach ($issue in @($preflight.issues)) {
    $severity = if ($issue.severity) { [string]$issue.severity } else { "review" }
    Add-Issue $issues $severity "preflight_$($issue.code)" "$($issue.message)" "preflight"
}

# Interface rows
$validInterfaceRows = 0
foreach ($row in @($preflight.interface_rows)) {
    if ($row.row_status -eq "preflight_valid_for_future_interface_adapter_design") {
        $validInterfaceRows += 1
    }
}
Add-SignoffItem $signoffItems "interface" "At least one valid interface scaffold row exists" ($validInterfaceRows -ge 1) "valid_rows=$validInterfaceRows; total_rows=$(@($preflight.interface_rows).Count)"
foreach ($row in @($preflight.interface_rows)) {
    Add-SignoffItem $signoffItems "interface" "Interface row blocks real network transport" ($row.network_transport_implemented -eq $false) "row_index=$($row.row_index); network_transport_implemented=$($row.network_transport_implemented)"
    Add-SignoffItem $signoffItems "interface" "Interface row blocks socket opening" ($row.network_socket_opened -eq $false) "row_index=$($row.row_index); network_socket_opened=$($row.network_socket_opened)"
    Add-SignoffItem $signoffItems "interface" "Interface row blocks bridge POST implementation" ($row.bridge_post_call_implemented -eq $false) "row_index=$($row.row_index); bridge_post_call_implemented=$($row.bridge_post_call_implemented)"
    Add-SignoffItem $signoffItems "interface" "Interface row execute method raises no-transport error" ($row.execute_method_behavior -eq "raises_runtime_error_no_transport") "row_index=$($row.row_index); execute_method_behavior=$($row.execute_method_behavior)"
    Add-SignoffItem $signoffItems "interface" "Interface row simulate method is shape-only no-network" ($row.simulate_method_behavior -eq "shape_only_no_network") "row_index=$($row.row_index); simulate_method_behavior=$($row.simulate_method_behavior)"
}

if ($validation -ne $null) {
    Add-SignoffItem $signoffItems "artifact" "Interface scaffold validation report exists" $true $validationPath
    Add-SignoffItem $signoffItems "safety" "Interface scaffold validation has no network transport" ($validation.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($validation.safety.network_transport_implemented)"
    Add-SignoffItem $signoffItems "safety" "Interface scaffold validation has no socket opened" ($validation.safety.network_socket_opened -eq $false) "network_socket_opened=$($validation.safety.network_socket_opened)"
    Add-SignoffItem $signoffItems "safety" "Interface scaffold validation has no bridge POST" ($validation.safety.bridge_post_called -eq $false -and $validation.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($validation.safety.bridge_post_called); bridge_post_call_implemented=$($validation.safety.bridge_post_call_implemented)"
    Add-SignoffItem $signoffItems "gate" "Interface scaffold validation says bridge POST cannot be added now" ($validation.validation.can_add_bridge_post_now -eq $false) "can_add_bridge_post_now=$($validation.validation.can_add_bridge_post_now)"
} else {
    Add-SignoffItem $signoffItems "artifact" "Interface scaffold validation report exists" $false "Phase 20 Step 15 validation artifact not found." "recommended"
    Add-Issue $issues "review" "interface_scaffold_validation_missing" "Phase 20 Step 15 validation artifact was not found." "scaffold_validation"
}

if ($scaffold -ne $null) {
    Add-SignoffItem $signoffItems "artifact" "Interface scaffold report exists" $true $scaffoldPath
    Add-SignoffItem $signoffItems "safety" "Interface scaffold report has no network transport" ($scaffold.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($scaffold.safety.network_transport_implemented)"
    Add-SignoffItem $signoffItems "safety" "Interface scaffold report has no socket opened" ($scaffold.safety.network_socket_opened -eq $false) "network_socket_opened=$($scaffold.safety.network_socket_opened)"
    Add-SignoffItem $signoffItems "safety" "Interface scaffold preview would not open socket" ($scaffold.preview.would_open_socket -eq $false) "would_open_socket=$($scaffold.preview.would_open_socket)"
    Add-SignoffItem $signoffItems "safety" "Interface scaffold preview would not send HTTP request" ($scaffold.preview.would_send_http_request -eq $false) "would_send_http_request=$($scaffold.preview.would_send_http_request)"
    Add-SignoffItem $signoffItems "safety" "Interface scaffold preview would not call bridge" ($scaffold.preview.would_call_bridge -eq $false) "would_call_bridge=$($scaffold.preview.would_call_bridge)"
} else {
    Add-SignoffItem $signoffItems "artifact" "Interface scaffold report exists" $false "Phase 20 Step 14 interface scaffold artifact not found." "recommended"
    Add-Issue $issues "review" "interface_scaffold_missing" "Phase 20 Step 14 interface scaffold artifact was not found." "interface_scaffold"
}

if ($plan -ne $null) {
    Add-SignoffItem $signoffItems "artifact" "Implementation plan exists" $true $planPath
    Add-SignoffItem $signoffItems "safety" "Implementation plan has no network transport" ($plan.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($plan.safety.network_transport_implemented)"
    Add-SignoffItem $signoffItems "safety" "Implementation plan has no socket opened" ($plan.safety.network_socket_opened -eq $false) "network_socket_opened=$($plan.safety.network_socket_opened)"
    Add-SignoffItem $signoffItems "gate" "Implementation plan says bridge POST cannot be added now" ($plan.implementation_plan.can_add_bridge_post_now -eq $false) "can_add_bridge_post_now=$($plan.implementation_plan.can_add_bridge_post_now)"
} else {
    Add-SignoffItem $signoffItems "artifact" "Implementation plan exists" $false "Phase 20 Step 13 implementation plan artifact not found." "recommended"
    Add-Issue $issues "review" "implementation_plan_missing" "Phase 20 Step 13 implementation plan artifact was not found." "implementation_plan"
}

if ($release -ne $null) {
    Add-SignoffItem $signoffItems "artifact" "Network transport release checkpoint exists" $true $releasePath
    Add-SignoffItem $signoffItems "safety" "Network transport release checkpoint has no network transport" ($release.safety.network_transport_implemented -eq $false) "network_transport_implemented=$($release.safety.network_transport_implemented)"
    Add-SignoffItem $signoffItems "safety" "Network transport release checkpoint has no socket opened" ($release.safety.network_socket_opened -eq $false) "network_socket_opened=$($release.safety.network_socket_opened)"
    Add-SignoffItem $signoffItems "safety" "Network transport release checkpoint has no bridge POST" ($release.safety.bridge_post_called -eq $false -and $release.safety.bridge_post_call_implemented -eq $false) "bridge_post_called=$($release.safety.bridge_post_called); bridge_post_call_implemented=$($release.safety.bridge_post_call_implemented)"
} else {
    Add-SignoffItem $signoffItems "artifact" "Network transport release checkpoint exists" $false "Phase 20 Step 12 release checkpoint artifact not found." "recommended"
    Add-Issue $issues "review" "network_release_checkpoint_missing" "Phase 20 Step 12 release checkpoint artifact was not found." "network_release_checkpoint"
}

# Runtime checks are review-level when unreachable, but safety contradictions are required.
if ($scaffoldStatus.ok) {
    Add-SignoffItem $signoffItems "runtime" "Interface scaffold status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-interface-scaffold/status" "recommended"
    Add-SignoffItem $signoffItems "runtime" "Runtime interface scaffold has no network transport" ($scaffoldStatus.value.network_transport_implemented -eq $false) "network_transport_implemented=$($scaffoldStatus.value.network_transport_implemented)"
    Add-SignoffItem $signoffItems "runtime" "Runtime interface scaffold has no socket opened" ($scaffoldStatus.value.network_socket_opened -eq $false) "network_socket_opened=$($scaffoldStatus.value.network_socket_opened)"
    Add-SignoffItem $signoffItems "runtime" "Runtime interface scaffold has no bridge POST" ($scaffoldStatus.value.bridge_post_called -eq $false -and $scaffoldStatus.value.bridge_post_call_implemented -eq $false) "bridge_post_called=$($scaffoldStatus.value.bridge_post_called); bridge_post_call_implemented=$($scaffoldStatus.value.bridge_post_call_implemented)"
} else {
    Add-SignoffItem $signoffItems "runtime" "Interface scaffold status readable" $false $scaffoldStatus.error "recommended"
    Add-Issue $issues "review" "scaffold_status_unreadable" "Could not read scaffold status: $($scaffoldStatus.error)" "runtime"
}

if ($adapterStatus.ok) {
    Add-SignoffItem $signoffItems "runtime" "Dry-run adapter status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-dry-run-adapter/status" "recommended"
    Add-SignoffItem $signoffItems "runtime" "Runtime dry-run adapter has no network transport" ($adapterStatus.value.network_transport_implemented -eq $false) "network_transport_implemented=$($adapterStatus.value.network_transport_implemented)"
    Add-SignoffItem $signoffItems "runtime" "Runtime dry-run adapter has no socket opened" ($adapterStatus.value.network_socket_opened -eq $false) "network_socket_opened=$($adapterStatus.value.network_socket_opened)"
} else {
    Add-SignoffItem $signoffItems "runtime" "Dry-run adapter status readable" $false $adapterStatus.error "recommended"
    Add-Issue $issues "review" "adapter_status_unreadable" "Could not read adapter status: $($adapterStatus.error)" "runtime"
}

if ($guardStatus.ok) {
    Add-SignoffItem $signoffItems "runtime" "Network transport guard status readable" $true "$PlatformApi/front-desk/routing/bridge-network-transport-guard/status" "recommended"
    Add-SignoffItem $signoffItems "runtime" "Runtime guard has no network transport" ($guardStatus.value.network_transport_implemented -eq $false) "network_transport_implemented=$($guardStatus.value.network_transport_implemented)"
} else {
    Add-SignoffItem $signoffItems "runtime" "Network transport guard status readable" $false $guardStatus.error "recommended"
    Add-Issue $issues "review" "guard_status_unreadable" "Could not read guard status: $($guardStatus.error)" "runtime"
}

if ($httpDryRunStatus.ok) {
    Add-SignoffItem $signoffItems "runtime" "HTTP client dry-run status readable" $true "$PlatformApi/front-desk/routing/bridge-http-client-dry-run/status" "recommended"
    Add-SignoffItem $signoffItems "runtime" "HTTP client dry-run has no network transport" ($httpDryRunStatus.value.network_transport_implemented -eq $false) "network_transport_implemented=$($httpDryRunStatus.value.network_transport_implemented)"
} else {
    Add-SignoffItem $signoffItems "runtime" "HTTP client dry-run status readable" $false $httpDryRunStatus.error "recommended"
    Add-Issue $issues "review" "http_dry_run_status_unreadable" "Could not read HTTP dry-run status: $($httpDryRunStatus.error)" "runtime"
}

if ($executorStatus.ok) {
    Add-SignoffItem $signoffItems "runtime" "Executor status readable" $true "$PlatformApi/front-desk/routing/bridge-write-executor/status" "recommended"
    Add-SignoffItem $signoffItems "runtime" "Executor has no execution endpoint" ($executorStatus.value.execution_endpoint_available -eq $false) "execution_endpoint_available=$($executorStatus.value.execution_endpoint_available)"
    Add-SignoffItem $signoffItems "runtime" "Executor has no bridge POST implementation" ($executorStatus.value.bridge_post_call_implemented -eq $false) "bridge_post_call_implemented=$($executorStatus.value.bridge_post_call_implemented)"
} else {
    Add-SignoffItem $signoffItems "runtime" "Executor status readable" $false $executorStatus.error "recommended"
    Add-Issue $issues "review" "executor_status_unreadable" "Could not read executor status: $($executorStatus.error)" "runtime"
}

Add-SignoffItem $signoffItems "runtime" "Bridge health readable" $bridgeHealth.ok $(if ($bridgeHealth.ok) { "$BridgeUrl/health" } else { $bridgeHealth.error }) "recommended"

# Convert failed signoff items into issues.
foreach ($item in @($signoffItems)) {
    if ($item.passed -ne $true -and $item.required -eq "yes") {
        Add-Issue $issues "blocker" ("signoff_" + ($item.item -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $item.evidence $item.category
    } elseif ($item.passed -ne $true -and $item.required -eq "recommended") {
        Add-Issue $issues "review" ("signoff_" + ($item.item -replace "[^A-Za-z0-9]+", "_").Trim("_").ToLowerInvariant()) $item.evidence $item.category
    }
}

$blockerCount = @($issues | Where-Object { $_.severity -eq "blocker" }).Count
$reviewCount = @($issues | Where-Object { $_.severity -eq "review" }).Count

$signoffStatus = if ($blockerCount -eq 0 -and $reviewCount -eq 0) {
    "ready_for_operator_interface_adapter_design_review"
} elseif ($blockerCount -eq 0) {
    "operator_review_required"
} else {
    "blocked"
}

if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutputDir = Join-Path $BackupDir "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff_$stamp"
}

New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

$operatorAttestation = [ordered]@{
    operator_name = ""
    reviewed_at = ""
    approved_for_future_interface_adapter_design_only = $false
    approved_for_live_bridge_write = $false
    approved_for_real_network_transport = $false
    approved_to_enable_network_transport = $false
    approved_to_arm_network_transport = $false
    approved_to_open_network_socket = $false
    approved_to_add_bridge_post = $false
    required_statement = "I reviewed the no-socket interface scaffold preflight matrix and understand this packet does not authorize live bridge routing writes, real bridge network transport, bridge POST calls, or opening network sockets."
    notes = ""
}

$report = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    phase = "Phase 20 Step 17"
    purpose = "Bridge routing network transport interface scaffold operator signoff dossier"
    source_preflight_matrix = $preflightPath
    source_scaffold_validation = $validationPath
    source_interface_scaffold = $scaffoldPath
    source_implementation_plan = $planPath
    source_network_release_checkpoint = $releasePath
    workspace = $Workspace
    platform_api = $PlatformApi
    bridge_url = $BridgeUrl
    safety = [ordered]@{
        bridge_routing_network_transport_interface_scaffold_operator_signoff_only = $true
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
    signoff = [ordered]@{
        status = $signoffStatus
        blocker_count = $blockerCount
        review_count = $reviewCount
        checklist_items = @($signoffItems).Count
        can_execute_bridge_write_now = $false
        can_add_network_transport_now = $false
        can_enable_network_transport_now = $false
        can_arm_network_transport_now = $false
        can_open_network_socket_now = $false
        can_add_real_bridge_http_client_now = $false
        can_add_bridge_post_now = $false
        operator_signoff_required = $true
        approved_for_live_bridge_write = $false
        approved_for_real_network_transport = $false
        approved_to_enable_network_transport = $false
        approved_to_arm_network_transport = $false
        approved_to_open_network_socket = $false
        approved_to_add_bridge_post = $false
        reason = if ($blockerCount -eq 0) {
            "Interface scaffold operator signoff dossier can be reviewed. Phase 20 Step 17 still implements no real transport, opens no socket, adds no bridge POST, and authorizes no execution."
        } else {
            "Interface scaffold operator signoff dossier has blockers. Resolve blockers before any future real network transport design."
        }
    }
    operator_attestation = $operatorAttestation
    checklist = @($signoffItems)
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
        checklist_items = @($signoffItems).Count
        blockers = $blockerCount
        reviews = $reviewCount
        valid_interface_rows = $validInterfaceRows
    }
    next_recommended_actions = @(
        "Resolve signoff blockers before designing any real bridge network transport.",
        "If only review items remain, operator can review and decide whether future design can continue.",
        "Do not call bridge POST endpoints from Phase 20 Step 17.",
        "Keep bridge routing controls as the operational write path until explicit cutover."
    )
}

$jsonPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff.json"
$checklistCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff_checklist.csv"
$issuesCsvPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff_issues.csv"
$mdPath = Join-Path $OutputDir "phase20_bridge_routing_network_transport_interface_scaffold_operator_signoff.md"

$report | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $jsonPath -Encoding UTF8
$signoffItems | Export-Csv -LiteralPath $checklistCsvPath -NoTypeInformation -Encoding UTF8
$issues | Export-Csv -LiteralPath $issuesCsvPath -NoTypeInformation -Encoding UTF8

$checklistText = (@($signoffItems) | ForEach-Object { "- [$($_.category)] $($_.item): $($_.passed) - $($_.evidence)" }) -join "`n"
$issueText = if (@($issues).Count -gt 0) { (@($issues) | ForEach-Object { "- [$($_.severity)] $($_.source) / $($_.code): $($_.message)" }) -join "`n" } else { "- none" }

$md = @"
# Phase 20 Bridge Routing Network Transport Interface Scaffold Operator Signoff

Generated: $($report.generated_at)

Source interface scaffold preflight matrix:

``````
$preflightPath
``````

## Safety

- Bridge routing network transport interface scaffold operator signoff only: true
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

## Signoff

- Status: $signoffStatus
- Blockers: $blockerCount
- Review items: $reviewCount
- Can execute bridge write now: false
- Can add network transport now: false
- Can enable network transport now: false
- Can arm network transport now: false
- Can open network socket now: false
- Can add real bridge HTTP client now: false
- Can add bridge POST now: false
- Approved for live bridge write: false
- Approved for real network transport: false
- Approved to enable network transport: false
- Approved to arm network transport: false
- Approved to open network socket: false
- Approved to add bridge POST: false

## Checklist

$checklistText

## Issues

$issueText

## Operator attestation

- Operator name:
- Reviewed at:
- Approved for future interface adapter design only: false
- Approved for live bridge write: false
- Approved for real network transport: false
- Approved to enable network transport: false
- Approved to arm network transport: false
- Approved to open network socket: false
- Approved to add bridge POST: false
- Required statement: I reviewed the no-socket interface scaffold preflight matrix and understand this packet does not authorize live bridge routing writes, real bridge network transport, bridge POST calls, or opening network sockets.
- Notes:
"@

$md | Set-Content -LiteralPath $mdPath -Encoding UTF8

if ($blockerCount -eq 0) {
    Write-Host "PASS | bridge_routing_network_transport_interface_scaffold_operator_signoff=$OutputDir | status=$signoffStatus | bridge_post_called=False"
} else {
    Write-Host "CHECK | bridge_routing_network_transport_interface_scaffold_operator_signoff=$OutputDir | status=$signoffStatus | blockers=$blockerCount | bridge_post_called=False"
}

Write-Host ""
Write-Host "Interface scaffold operator signoff files:"
Get-ChildItem -LiteralPath $OutputDir -File | Select-Object Name, Length, LastWriteTime
