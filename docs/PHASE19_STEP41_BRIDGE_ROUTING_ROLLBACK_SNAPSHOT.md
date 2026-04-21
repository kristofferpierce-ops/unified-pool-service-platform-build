# Phase 19 Step 41 — Bridge Routing Rollback Snapshot

## Purpose

Step 41 captures a read-only bridge routing rollback snapshot.

It reads the latest Step 40 audit writer run and current bridge routing rules, then builds rollback payload previews for rows that can be matched to current bridge routing state.

## Files

```text
scripts/phase19_capture_bridge_routing_rollback_snapshot.ps1
ui/pages/43_Bridge_Routing_Rollback_Snapshot.py
docs/PHASE19_STEP41_BRIDGE_ROUTING_ROLLBACK_SNAPSHOT.md
tests/test_phase19_bridge_routing_rollback_snapshot.py
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

This step is rollback-snapshot-only and bridge GET only. It does not write to the bridge, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate rollback snapshot

From the platform repo, with bridge and FastAPI running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_capture_bridge_routing_rollback_snapshot.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_bridge_routing_rollback_snapshot_<timestamp>
```

The folder contains:

```text
phase19_bridge_routing_rollback_snapshot.json
phase19_bridge_routing_rollback_snapshot.csv
phase19_bridge_routing_rollback_snapshot.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Bridge Routing Rollback Snapshot
```

## Commit guard

Stage only the four Step 41 files. Do not stage generated rollback snapshot reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
