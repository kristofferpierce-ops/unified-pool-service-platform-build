# Phase 19 Step 47 — Bridge Routing Write Dry-run Bundle Validation

## Purpose

Step 47 validates the Step 46 bridge routing write dry-run bundle.

It checks the bundle safety flags, request-template rows, payload fields, idempotency placeholder, platform status, and current bridge GET-only status.

## Files

```text
scripts/phase19_validate_bridge_routing_write_dry_run_bundle.ps1
ui/pages/49_Bridge_Routing_Write_Dry_Run_Validation.py
docs/PHASE19_STEP47_BRIDGE_ROUTING_WRITE_DRY_RUN_VALIDATION.md
tests/test_phase19_bridge_routing_write_dry_run_validation.py
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
- add a bridge HTTP client
- add a live bridge write execution endpoint
- enable live writes

This step is dry-run-validation-only and bridge GET only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate validation report

From the platform repo, with FastAPI and bridge running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_validate_bridge_routing_write_dry_run_bundle.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_bridge_routing_write_dry_run_validation_<timestamp>
```

The folder contains:

```text
phase19_bridge_routing_write_dry_run_validation.json
phase19_bridge_routing_write_dry_run_validation_rows.csv
phase19_bridge_routing_write_dry_run_validation_issues.csv
phase19_bridge_routing_write_dry_run_validation.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Bridge Routing Write Dry-run Validation
```

## Commit guard

Stage only the four Step 47 files. Do not stage generated dry-run validation reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
