# Phase 20 Step 7 — Bridge Routing Network Transport Guard

## Purpose

Phase 20 Step 7 starts the next guarded segment after the Phase 20 Step 6 no-network release checkpoint.

It reads the HTTP-client release checkpoint, validates that the no-network boundary is still intact, and produces a transport design guard preview. It does not add real network transport and does not call the bridge.

## Files

```text
app/services/routing_bridge_network_transport_guard.py
app/api/routes/routing_bridge_network_transport_guard.py
app/api/app.py
scripts/phase20_generate_bridge_routing_network_transport_guard.ps1
ui/pages/59_Bridge_Routing_Network_Transport_Guard.py
docs/PHASE20_STEP7_BRIDGE_ROUTING_NETWORK_TRANSPORT_GUARD.md
tests/test_phase20_bridge_routing_network_transport_guard.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- save routing rules
- call bridge POST endpoints
- mutate bridge state
- mutate platform records
- create audit rows
- create rollback rows
- add a real bridge HTTP client
- add network transport
- enable network transport
- arm network transport
- add a live bridge write execution endpoint
- enable live writes

This step is network-transport-guard-only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## API endpoints

```text
GET  /front-desk/routing/bridge-network-transport-guard/status
POST /front-desk/routing/bridge-network-transport-guard/preview
```

The POST endpoint is a local platform preview endpoint only. It does not call the bridge.

## Safe guard command

From the platform repo, with FastAPI running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase20_generate_bridge_routing_network_transport_guard.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase20_bridge_routing_network_transport_guard_<timestamp>
```

## Commit guard

Stage only the Phase 20 Step 7 files. Do not stage generated guard reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
