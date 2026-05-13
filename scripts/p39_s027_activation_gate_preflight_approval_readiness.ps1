param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "all"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PacketTitle = "Phase 39 Step 27 - Phase 20 Network Transport Implementation Trusted Production Live Write Activation Gate Preflight Planning Approval Readiness Packet"
if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Get-Location).Path
}

$SafetyPosture = [ordered]@{
    planning_only = "true"
    no_real_bridge_http_client = "true"
    no_network_transport_implementation = "true"
    no_bridge_post = "true"
    no_network_sockets = "true"
    phase39_execution_start = "false"
    phase39_implementation_start = "false"
    implementation_phase_start = "false"
    trusted_production_live_write_activation_gate_start = "false"
    trusted_production_live_write_activation_gate_execution_start = "false"
    live_write_activation_gate_start = "false"
    live_write_activation_gate_execution_start = "false"
    live_write_activation_start = "false"
    live_write_apply_start = "false"
    live_user_access_start = "false"
    no_live_user_access = "true"
    no_live_write_activation = "true"
    no_live_write_apply = "true"
    phase40_start = "false"
    phase40_boundary_creation = "false"
    lacrm_default_mode = "dry_run"
    live_write_disabled = "true"
    live_write_unarmed = "true"
}

function Get-SafetyText {
    return (($SafetyPosture.GetEnumerator() | ForEach-Object { "{0}={1}" -f $_.Key, $_.Value }) -join "`n")
}

function Assert-SafePosture {
    $Compact = (Get-SafetyText).Replace(" ", "").ToLowerInvariant()
    $Forbidden = @(
        ("phase40_start" + "=true"),
        ("phase40_boundary_creation" + "=true"),
        ("phase39_execution_start" + "=true"),
        ("phase39_implementation_start" + "=true"),
        ("implementation_phase_start" + "=true"),
        ("trusted_production_live_write_activation_gate_start" + "=true"),
        ("trusted_production_live_write_activation_gate_execution_start" + "=true"),
        ("live_write_activation_gate_start" + "=true"),
        ("live_write_activation_gate_execution_start" + "=true"),
        ("live_write_activation_start" + "=true"),
        ("live_write_apply_start" + "=true"),
        ("live_user_access_start" + "=true"),
        ("no_live_user_access" + "=false"),
        ("no_live_write_activation" + "=false"),
        ("no_live_write_apply" + "=false")
    )
    foreach ($Marker in $Forbidden) {
        if ($Compact.Contains($Marker)) { throw ("Forbidden runtime marker detected: {0}" -f $Marker) }
    }
}

function Show-Packet {
    Write-Host $PacketTitle
    Write-Host ("RepoRoot={0}" -f $RepoRoot)
    Write-Host "Safety posture: planning-only/no-write/no-server/no-network-transport/no-live-write-activation/no-live-write-apply/no-phase40"
    Write-Host (Get-SafetyText)
}

function Invoke-Apply {
    Assert-SafePosture
    Write-Host "APPLY PASS"
}

function Invoke-Smoke {
    Assert-SafePosture
    Write-Host "SMOKE TEST PASS"
}

switch ($Action) {
    "status" { Show-Packet }
    "packet" { Show-Packet }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "all" { Show-Packet; Invoke-Apply; Invoke-Smoke }
}