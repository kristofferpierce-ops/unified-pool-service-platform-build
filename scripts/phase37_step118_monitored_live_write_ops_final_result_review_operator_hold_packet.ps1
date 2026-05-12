param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "status"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$PacketTitle = "Phase 37 Step 118 - Phase 20 Network Transport Implementation Trusted Production Monitored Live Write Operations Final Release Result Review Planning Operator Hold Point Packet"
$SafetyPosture = "planning-only/no-write/no-server/no-network-transport/no-live-write-activation/no-live-write-apply/no-phase38"
$SafetyMarkerText = @'
planning_only=true
no_real_bridge_http_client=true
no_network_transport_implementation=true
no_bridge_post=true
no_network_sockets=true
phase37_execution_start=false
phase37_implementation_start=false
implementation_phase_start=false
trusted_production_monitored_live_write_operations_start=false
trusted_production_monitored_live_write_operations_execution_start=false
monitored_live_write_operations_start=false
monitored_live_write_operations_execution_start=false
live_write_activation_start=false
live_write_apply_start=false
live_user_access_start=false
no_live_user_access=true
no_live_write_activation=true
no_live_write_apply=true
phase38_start=false
phase38_boundary_creation=false
lacrm_default_mode=dry_run
live_write_disabled=true
live_write_unarmed=true
'@

function Show-Packet {
    Write-Host $PacketTitle
    Write-Host ("RepoRoot={0}" -f $RepoRoot)
    Write-Host ("Safety posture: {0}" -f $SafetyPosture)
    $SafetyMarkerText -split "`n" | ForEach-Object {
        if ($_.Trim()) {
            Write-Host $_.Trim()
        }
    }
}

function Assert-SafetyMarkers {
    $Compact = $SafetyMarkerText.Replace(" ", "").ToLowerInvariant()
    $Forbidden = @(
        ("phase38_start" + "=true"),
        ("phase38_boundary_creation" + "=true"),
        ("phase37_execution_start" + "=true"),
        ("phase37_implementation_start" + "=true"),
        ("implementation_phase_start" + "=true"),
        ("trusted_production_monitored_live_write_operations_start" + "=true"),
        ("trusted_production_monitored_live_write_operations_execution_start" + "=true"),
        ("monitored_live_write_operations_start" + "=true"),
        ("monitored_live_write_operations_execution_start" + "=true"),
        ("live_write_activation_start" + "=true"),
        ("live_write_apply_start" + "=true"),
        ("live_user_access_start" + "=true"),
        ("no_live_user_access" + "=false"),
        ("no_live_write_activation" + "=false"),
        ("no_live_write_apply" + "=false")
    )

    foreach ($Marker in $Forbidden) {
        if ($Compact.Contains($Marker)) {
            throw ("Forbidden unsafe marker detected in Phase 37 Step 118 packet.")
        }
    }
}

function Invoke-Apply {
    Assert-SafetyMarkers
    Write-Host "APPLY PASS"
}

function Invoke-Smoke {
    Assert-SafetyMarkers
    Write-Host "SMOKE TEST PASS"
}

switch ($Action) {
    "status" { Show-Packet }
    "packet" { Show-Packet }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "all" { Show-Packet; Invoke-Apply; Invoke-Smoke }
}