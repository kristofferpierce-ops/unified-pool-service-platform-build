# Phase 19 Step 37 — Bridge Routing Write Rehearsal

## Purpose

Step 37 adds a guarded bridge routing write rehearsal that is blocked by default.

It accepts bridge apply preview rows from Step 35 and checks all future safety gates, but it does not implement or perform the outbound bridge POST call.

## Files

```text
app/services/routing_bridge_write_rehearsal.py
app/api/routes/routing_bridge_write_rehearsal.py
app/api/app.py
scripts/phase19_run_bridge_routing_write_rehearsal.ps1
ui/pages/39_Bridge_Routing_Write_Rehearsal.py
docs/PHASE19_STEP37_BRIDGE_ROUTING_WRITE_REHEARSAL.md
tests/test_phase19_bridge_routing_write_rehearsal.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- save routing rules
- call bridge POST endpoints
- mutate bridge state
- mutate platform records
- enable live writes

This step is rehearsal-only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

Even if future environment gates are set, Step 37 still reports:

```text
bridge_post_call_implemented = false
bridge_post_called = false
routing_write_endpoint_implemented = false
```

## API endpoints

```text
GET  /front-desk/routing/bridge-write-rehearsal/status
POST /front-desk/routing/bridge-write-rehearsal/rehearse
```

The POST endpoint is a local platform rehearsal endpoint only. It does not call the bridge.

## Safe rehearsal command

From the platform repo, with FastAPI running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_run_bridge_routing_write_rehearsal.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_bridge_routing_write_rehearsal_<timestamp>
```

## Commit guard

Stage only the Step 37 files. Do not stage generated rehearsal reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
