# Phase 19 Step 39 — Bridge Routing Write Audit Plan

## Purpose

Step 39 turns Step 37 bridge routing write rehearsal output into a dry-run audit-row plan.

It uses the Step 38 read-only audit preview endpoint to determine which audit rows would be created later, but it does not create audit rows.

## Files

```text
scripts/phase19_plan_bridge_routing_write_audit.ps1
ui/pages/41_Bridge_Routing_Write_Audit_Plan.py
docs/PHASE19_STEP39_BRIDGE_ROUTING_WRITE_AUDIT_PLAN.md
tests/test_phase19_bridge_routing_write_audit_plan.py
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
- enable live writes

This step is audit-plan-only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate audit plan

From the platform repo, with FastAPI running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_plan_bridge_routing_write_audit.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_bridge_routing_write_audit_plan_<timestamp>
```

The folder contains:

```text
phase19_bridge_routing_write_audit_plan.json
phase19_bridge_routing_write_audit_plan.csv
phase19_bridge_routing_write_audit_plan.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Bridge Routing Write Audit Plan
```

## Commit guard

Stage only the four Step 39 files. Do not stage generated audit plan reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
