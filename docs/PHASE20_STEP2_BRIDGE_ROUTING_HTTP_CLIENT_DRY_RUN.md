# Phase 20 Step 2 — Bridge Routing HTTP Client Dry-run Transport

## Purpose

Phase 20 Step 2 adds a dry-run transport simulator for the bridge routing HTTP client path.

It reads the Phase 20 Step 1 HTTP client stub report, validates the no-POST boundary, and builds a simulated request/response pair. It does not include real network transport and does not call the bridge.

## Files

```text
app/services/routing_bridge_http_client_dry_run.py
app/api/routes/routing_bridge_http_client_dry_run.py
app/api/app.py
scripts/phase20_generate_bridge_routing_http_client_dry_run.ps1
ui/pages/54_Bridge_Routing_HTTP_Client_Dry_Run.py
docs/PHASE20_STEP2_BRIDGE_ROUTING_HTTP_CLIENT_DRY_RUN.md
tests/test_phase20_bridge_routing_http_client_dry_run.py
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
- add a live bridge write execution endpoint
- enable live writes

This step is HTTP-client-dry-run-only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## API endpoints

```text
GET  /front-desk/routing/bridge-http-client-dry-run/status
POST /front-desk/routing/bridge-http-client-dry-run/simulate
```

The POST endpoint is a local platform simulation endpoint only. It does not call the bridge.

## Safe dry-run command

From the platform repo, with FastAPI running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase20_generate_bridge_routing_http_client_dry_run.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase20_bridge_routing_http_client_dry_run_<timestamp>
```

## Commit guard

Stage only the Phase 20 Step 2 files. Do not stage generated dry-run reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
