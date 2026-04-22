# Phase 20 Step 3 — Bridge Routing HTTP Client Dry-run Validation

## Purpose

Phase 20 Step 3 validates the Phase 20 Step 2 bridge routing HTTP client dry-run transport simulation.

It checks the dry-run transport artifact, simulated request and response, upstream stub/release artifacts when present, and current runtime status. It verifies that no real network transport or bridge POST implementation exists.

## Files

```text
scripts/phase20_validate_bridge_routing_http_client_dry_run.ps1
ui/pages/55_Bridge_Routing_HTTP_Client_Dry_Run_Validation.py
docs/PHASE20_STEP3_BRIDGE_ROUTING_HTTP_CLIENT_DRY_RUN_VALIDATION.md
tests/test_phase20_bridge_routing_http_client_dry_run_validation.py
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

This step is HTTP-client-dry-run-validation-only and bridge GET only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate validation report

From the platform repo, with FastAPI and bridge running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase20_validate_bridge_routing_http_client_dry_run.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase20_bridge_routing_http_client_dry_run_validation_<timestamp>
```

The folder contains:

```text
phase20_bridge_routing_http_client_dry_run_validation.json
phase20_bridge_routing_http_client_dry_run_validation_gates.csv
phase20_bridge_routing_http_client_dry_run_validation_issues.csv
phase20_bridge_routing_http_client_dry_run_validation_request.csv
phase20_bridge_routing_http_client_dry_run_validation.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Bridge Routing HTTP Client Dry Run Validation
```

## Commit guard

Stage only the four Phase 20 Step 3 files. Do not stage generated dry-run validation reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
