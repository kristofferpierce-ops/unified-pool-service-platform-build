# Phase 19 Step 22 — Read-only Routing Rules Parity

## Purpose

Step 22 starts the third bridge-only parity slice identified by the Step 19 parity matrix: bridge routing rules.

This step is intentionally read-only. It gives the platform visibility into bridge routing behavior without saving routing preferences or changing bridge state.

## Files

```text
scripts/phase19_generate_routing_rules_snapshot.ps1
ui/pages/24_Routing_Rules.py
docs/PHASE19_STEP22_ROUTING_RULES.md
tests/test_phase19_routing_rules.py
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

This step does not call LACRM, does not mutate bridge state, does not save routing rules, and does not enable live writes.

## Correct app map

```text
http://127.0.0.1:8501  unified platform Streamlit dashboard
http://127.0.0.1:8010  unified platform FastAPI backend/API
http://127.0.0.1:8000  original KPS Bridge / Data Hub UI
```

## Generate a routing snapshot

From the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_generate_routing_rules_snapshot.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_routing_rules_snapshot_<timestamp>.json
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_routing_rules_snapshot_<timestamp>.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Rules
```

## Commit guard

Stage only the four Step 22 files. Do not stage generated snapshots, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, or unrelated Replaster Quote files.
