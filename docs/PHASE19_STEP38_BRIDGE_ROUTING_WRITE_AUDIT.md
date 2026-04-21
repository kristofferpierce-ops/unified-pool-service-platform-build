# Phase 19 Step 38 — Bridge Routing Write Audit / Rollback Ledger

## Purpose

Step 38 adds the platform-side audit and rollback ledger foundation for future bridge routing writes.

It introduces a read-only `RoutingBridgeWriteAudit` table/API, but does not create audit rows yet.

## Files

```text
app/models/routing_bridge_write_audit.py
app/services/routing_bridge_write_audit.py
app/api/routes/routing_bridge_write_audit.py
app/api/app.py
scripts/phase19_check_bridge_routing_write_audit.ps1
ui/pages/40_Bridge_Routing_Write_Audit.py
docs/PHASE19_STEP38_BRIDGE_ROUTING_WRITE_AUDIT.md
tests/test_phase19_bridge_routing_write_audit.py
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

This step is schema/read-only only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## API endpoints

```text
GET  /front-desk/routing/bridge-write-audit/status
GET  /front-desk/routing/bridge-write-audit
GET  /front-desk/routing/bridge-write-audit/{audit_id}
POST /front-desk/routing/bridge-write-audit/preview-from-rehearsal
```

The POST endpoint is preview-only. It does not create an audit row or commit changes.

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Bridge Routing Write Audit
```

## Commit guard

Stage only the Step 38 files. Do not stage generated audit check reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
