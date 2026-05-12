param(
    [string]$RepoRoot = "",
    [ValidateSet("status", "apply", "smoke", "packet", "all")]
    [string]$Action = "all"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

$Phase = 39
$Step = 10
$Title = "Phase 39 Step 10 - Phase 20 Network Transport Implementation Trusted Production Live Write Activation Gate Readiness Final Boundary Confirmation Packet"

$SafetyMarkers = [ordered]@{
    "planning_only" = "true"
    "no_real_bridge_http_client" = "true"
    "no_network_transport_implementation" = "true"
    "no_bridge_post" = "true"
    "no_network_sockets" = "true"
    "phase39_execution_start" = "false"
    "phase39_implementation_start" = "false"
    "implementation_phase_start" = "false"
    "trusted_production_live_write_activation_gate_start" = "false"
    "trusted_production_live_write_activation_gate_execution_start" = "false"
    "live_write_activation_gate_start" = "false"
    "live_write_activation_gate_execution_start" = "false"
    "live_write_activation_start" = "false"
    "live_write_apply_start" = "false"
    "live_user_access_start" = "false"
    "no_live_user_access" = "true"
    "no_live_write_activation" = "true"
    "no_live_write_apply" = "true"
    "phase40_start" = "false"
    "phase40_boundary_creation" = "false"
    "lacrm_default_mode" = "dry_run"
    "live_write_disabled" = "true"
    "live_write_unarmed" = "true"
}

function Show-Packet {
    Write-Host $Title
    Write-Host ("RepoRoot={0}" -f $RepoRoot)
    Write-Host "Safety posture: planning-only/no-write/no-server/no-network-transport/no-live-write-activation/no-live-write-apply/no-phase40"
    foreach ($Item in $SafetyMarkers.GetEnumerator()) {
        Write-Host ("{0}={1}" -f $Item.Key, $Item.Value)
    }
}

function Assert-Safety {
    $RequiredTrue = @(
        "planning_only",
        "no_real_bridge_http_client",
        "no_network_transport_implementation",
        "no_bridge_post",
        "no_network_sockets",
        "no_live_user_access",
        "no_live_write_activation",
        "no_live_write_apply",
        "live_write_disabled",
        "live_write_unarmed"
    )

    foreach ($Key in $RequiredTrue) {
        if ($SafetyMarkers[$Key] -ne "true") {
            throw ("Required true safety marker failed: {0}" -f $Key)
        }
    }

    if ($SafetyMarkers["lacrm_default_mode"] -ne "dry_run") {
        throw "LACRM default mode must remain dry_run."
    }

    $UnsafePairs = @(
        @("phase40_start", "true"),
        @("phase40_boundary_creation", "true"),
        @("phase39_execution_start", "true"),
        @("phase39_implementation_start", "true"),
        @("implementation_phase_start", "true"),
        @("trusted_production_live_write_activation_gate_start", "true"),
        @("trusted_production_live_write_activation_gate_execution_start", "true"),
        @("live_write_activation_gate_start", "true"),
        @("live_write_activation_gate_execution_start", "true"),
        @("live_write_activation_start", "true"),
        @("live_write_apply_start", "true"),
        @("live_user_access_start", "true"),
        @("no_live_user_access", "false"),
        @("no_live_write_activation", "false"),
        @("no_live_write_apply", "false")
    )

    foreach ($Pair in $UnsafePairs) {
        $Key = $Pair[0]
        $Bad = $Pair[1]
        if ($SafetyMarkers[$Key] -eq $Bad) {
            throw ("Unsafe marker detected: {0}" -f $Key)
        }
    }
}

function Invoke-Apply {
    Assert-Safety
    Write-Host "APPLY PASS"
}

function Invoke-Smoke {
    Assert-Safety
    Write-Host "SMOKE TEST PASS"
}

switch ($Action) {
    "status" { Show-Packet }
    "packet" { Show-Packet }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "all" { Show-Packet; Invoke-Apply; Invoke-Smoke }
}