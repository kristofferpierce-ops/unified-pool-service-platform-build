# Phase 20 Step 8 — Bridge Routing Network Transport Dry-run Adapter

## Purpose

Phase 20 Step 8 adds a dry-run adapter harness for the bridge routing network transport path.

It reads the Phase 20 Step 7 network transport guard report, validates the guard boundary, and builds a dry-run adapter contract plus simulated adapter result. It does not add real network transport, does not open a socket, and does not call the bridge.

## Files

```text
app/services/routing_bridge_network_transport_dry_run_adapter.py
app/api/routes/routing_bridge_network_transport_dry_run_adapter.py
app/api/app.py
scripts/phase20_generate_bridge_routing_network_transport_dry_run_adapter.ps1
ui/pages/60_Bridge_Routing_Network_Transport_Dry_Run_Adapter.py
docs/PHASE20_STEP8_BRIDGE_ROUTING_NETWORK_TRANSPORT_DRY_RUN_ADAPTER.md
tests/test_phase20_bridge_routing_network_transport_dry_run_adapter.py
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
- add a live bridge write execution endpoint
- enable live writes

This step is network-transport-dry-run-adapter-only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## API endpoints

```text
GET  /front-desk/routing/bridge-network-transport-dry-run-adapter/status
POST /front-desk/routing/bridge-network-transport-dry-run-adapter/simulate
```

The POST endpoint is a local platform simulation endpoint only. It does not call the bridge.

## Safe dry-run adapter command

From the platform repo, with FastAPI running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase20_generate_bridge_routing_network_transport_dry_run_adapter.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase20_bridge_routing_network_transport_dry_run_adapter_<timestamp>
```

## Commit guard

Stage only the Phase 20 Step 8 files. Do not stage generated dry-run adapter reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
