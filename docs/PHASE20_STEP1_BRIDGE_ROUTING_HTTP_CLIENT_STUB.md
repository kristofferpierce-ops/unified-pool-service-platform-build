# Phase 20 Step 1 — Bridge Routing HTTP Client Stub

## Purpose

Phase 20 Step 1 starts the post-checkpoint bridge routing write transition with a stub-only HTTP client preview.

It reads the Phase 19 Step 50 release checkpoint, validates that the no-POST boundary is still intact, and produces a request-template preview for a future bridge routing write client.

## Files

```text
app/services/routing_bridge_http_client_stub.py
app/api/routes/routing_bridge_http_client_stub.py
app/api/app.py
scripts/phase20_generate_bridge_routing_http_client_stub.ps1
ui/pages/53_Bridge_Routing_HTTP_Client_Stub.py
docs/PHASE20_STEP1_BRIDGE_ROUTING_HTTP_CLIENT_STUB.md
tests/test_phase20_bridge_routing_http_client_stub.py
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
- add a live bridge write execution endpoint
- enable live writes

This step is HTTP-client-stub-only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## API endpoints

```text
GET  /front-desk/routing/bridge-http-client-stub/status
POST /front-desk/routing/bridge-http-client-stub/preview
```

The POST endpoint is a local platform preview endpoint only. It does not call the bridge.

## Safe stub command

From the platform repo, with FastAPI running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase20_generate_bridge_routing_http_client_stub.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase20_bridge_routing_http_client_stub_<timestamp>
```

## Commit guard

Stage only the Phase 20 Step 1 files. Do not stage generated stub reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
