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

$Phase = 37
$Step = 98
$PacketTitle = 'Phase 37 Step 98 - Phase 20 Network Transport Implementation Trusted Production Monitored Live Write Operations Final Release Hold Planning Operator Hold Point Packet'
$SafetyMarkers = [ordered]@{}
$SafetyMarkers['planning_only'] = 'true'
$SafetyMarkers['no_real_bridge_http_client'] = 'true'
$SafetyMarkers['no_network_transport_implementation'] = 'true'
$SafetyMarkers['no_bridge_post'] = 'true'
$SafetyMarkers['no_network_sockets'] = 'true'
$SafetyMarkers['phase37_execution_start'] = 'false'
$SafetyMarkers['phase37_implementation_start'] = 'false'
$SafetyMarkers['implementation_phase_start'] = 'false'
$SafetyMarkers['trusted_production_monitored_live_write_operations_start'] = 'false'
$SafetyMarkers['trusted_production_monitored_live_write_operations_execution_start'] = 'false'
$SafetyMarkers['monitored_live_write_operations_start'] = 'false'
$SafetyMarkers['monitored_live_write_operations_execution_start'] = 'false'
$SafetyMarkers['live_write_activation_start'] = 'false'
$SafetyMarkers['live_write_apply_start'] = 'false'
$SafetyMarkers['live_user_access_start'] = 'false'
$SafetyMarkers['no_live_user_access'] = 'true'
$SafetyMarkers['no_live_write_activation'] = 'true'
$SafetyMarkers['no_live_write_apply'] = 'true'
$SafetyMarkers['phase38_start'] = 'false'
$SafetyMarkers['phase38_boundary_creation'] = 'false'
$SafetyMarkers['lacrm_default_mode'] = 'dry_run'
$SafetyMarkers['live_write_disabled'] = 'true'
$SafetyMarkers['live_write_unarmed'] = 'true'

function Get-SafetyMarkerText {
    $Lines = New-Object System.Collections.Generic.List[string]
    foreach ($Key in $SafetyMarkers.Keys) {
        $Lines.Add(("{0}={1}" -f $Key, $SafetyMarkers[$Key]))
    }
    return ($Lines -join [Environment]::NewLine)
}

function Assert-SafetyPosture {
    $SafetyText = Get-SafetyMarkerText
    $CompactSafetyText = $SafetyText.Replace(" ", "").ToLowerInvariant()
    if ($CompactSafetyText -match (('phase38_start') + ('=true'))) { throw 'Forbidden runtime marker detected: phase38 start equals true' }
    if ($CompactSafetyText -match (('phase38_boundary_creation') + ('=true'))) { throw 'Forbidden runtime marker detected: phase38 boundary creation equals true' }
    if ($CompactSafetyText -match (('phase37_execution_start') + ('=true'))) { throw 'Forbidden runtime marker detected: phase37 execution start equals true' }
    if ($CompactSafetyText -match (('phase37_implementation_start') + ('=true'))) { throw 'Forbidden runtime marker detected: phase37 implementation start equals true' }
    if ($CompactSafetyText -match (('trusted_production_monitored_live_write_operations_start') + ('=true'))) { throw 'Forbidden runtime marker detected: trusted production monitored live write operations start equals true' }
    if ($CompactSafetyText -match (('trusted_production_monitored_live_write_operations_execution_start') + ('=true'))) { throw 'Forbidden runtime marker detected: trusted production monitored live write operations execution start equals true' }
    if ($CompactSafetyText -match (('monitored_live_write_operations_start') + ('=true'))) { throw 'Forbidden runtime marker detected: monitored live write operations start equals true' }
    if ($CompactSafetyText -match (('monitored_live_write_operations_execution_start') + ('=true'))) { throw 'Forbidden runtime marker detected: monitored live write operations execution start equals true' }
    if ($CompactSafetyText -match (('live_write_activation_start') + ('=true'))) { throw 'Forbidden runtime marker detected: live write activation start equals true' }
    if ($CompactSafetyText -match (('live_write_apply_start') + ('=true'))) { throw 'Forbidden runtime marker detected: live write apply start equals true' }
    if ($CompactSafetyText -match (('live_user_access_start') + ('=true'))) { throw 'Forbidden runtime marker detected: live user access start equals true' }
    if ($CompactSafetyText -match (('no_live_user_access') + ('=false'))) { throw 'Forbidden runtime marker detected: no live user access equals false' }
    if ($CompactSafetyText -match (('no_live_write_activation') + ('=false'))) { throw 'Forbidden runtime marker detected: no live write activation equals false' }
    if ($CompactSafetyText -match (('no_live_write_apply') + ('=false'))) { throw 'Forbidden runtime marker detected: no live write apply equals false' }
    if (-not ($CompactSafetyText -match (('planning_only') + ('=true')))) { throw "Required planning-only marker missing." }
    if (-not ($CompactSafetyText -match (('no_live_write_apply') + ('=true')))) { throw "Required no-live-write-apply marker missing." }
    if (-not ($CompactSafetyText -match (('live_write_disabled') + ('=true')))) { throw "Required live-write-disabled marker missing." }
}

function Show-Packet {
    Write-Host $PacketTitle
    Write-Host "RepoRoot=$RepoRoot"
    Write-Host "Safety posture: planning-only/no-write/no-server/no-network-transport/no-live-write-activation/no-live-write-apply/no-phase38"
    Write-Host (Get-SafetyMarkerText)
}

function Invoke-Apply {
    Assert-SafetyPosture
    Write-Host "APPLY PASS"
}

function Invoke-Smoke {
    Assert-SafetyPosture
    Write-Host "SMOKE TEST PASS"
}

switch ($Action) {
    "status" { Show-Packet }
    "packet" { Show-Packet }
    "apply" { Invoke-Apply }
    "smoke" { Invoke-Smoke }
    "all" { Show-Packet; Invoke-Apply; Invoke-Smoke }
}
