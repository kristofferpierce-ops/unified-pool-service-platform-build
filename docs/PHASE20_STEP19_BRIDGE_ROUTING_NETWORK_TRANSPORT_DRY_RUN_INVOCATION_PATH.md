# Phase 20 Step 19 — Bridge Routing Network Transport Dry-run Invocation Path

## Purpose

Phase 20 Step 19 adds a no-network dry-run invocation path for future bridge routing network transport work.

It reads the Phase 20 Step 18 interface scaffold release checkpoint, validates that the no-socket boundary is still intact, and defines a deterministic dry-run invocation request/result/contract. It does not add real network transport, does not open a socket, and does not call the bridge.

## Files

```text
app/services/routing_bridge_network_transport_dry_run_invocation_path.py
app/api/routes/routing_bridge_network_transport_dry_run_invocation_path.py
app/api/app.py
scripts/phase20_generate_bridge_routing_network_transport_dry_run_invocation_path.ps1
ui/pages/71_Bridge_Routing_Network_Transport_Dry_Run_Invocation_Path.py
docs/PHASE20_STEP19_BRIDGE_ROUTING_NETWORK_TRANSPORT_DRY_RUN_INVOCATION_PATH.md
tests/test_phase20_bridge_routing_network_transport_dry_run_invocation_path.py
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
- open network sockets
- add a bridge POST implementation
- add a live bridge write execution endpoint
- enable live writes

This step is network-transport-dry-run-invocation-path-only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## API endpoints

```text
GET  /front-desk/routing/bridge-network-transport-dry-run-invocation-path/status
POST /front-desk/routing/bridge-network-transport-dry-run-invocation-path/preview
```

The POST endpoint is a local platform preview endpoint only. It does not call the bridge.

## Safe invocation path command

From the platform repo, with FastAPI running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase20_generate_bridge_routing_network_transport_dry_run_invocation_path.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase20_bridge_routing_network_transport_dry_run_invocation_path_<timestamp>
```

## Commit guard

Stage only the Phase 20 Step 19 files. Do not stage generated dry-run invocation reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
