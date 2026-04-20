# Phase 19 Step 20 â€” Read-only Call Context / HUD Parity

## Purpose

Step 20 starts the first bridge-only parity slice identified by the Step 19 parity matrix: incoming call/HUD context.

This step is intentionally read-only. It gives the platform visibility into the bridge's call/HUD context without replacing the bridge UI.

## Files

```text
scripts/phase19_generate_call_context_snapshot.ps1
ui/pages/22_Call_Context.py
docs/PHASE19_STEP20_CALL_CONTEXT.md
tests/test_phase19_call_context.py
```

## Safety

This step does not call LACRM, does not mutate bridge state, does not create CRM notes or tasks, and does not enable live writes.

This step does not:

- patch the bridge
- call LACRM
- create CRM notes or tasks
- mutate bridge state
- mutate platform records
- enable live writes

## Correct app map

```text
http://127.0.0.1:8501  unified platform Streamlit dashboard
http://127.0.0.1:8010  unified platform FastAPI backend/API
http://127.0.0.1:8000  original KPS Bridge / Data Hub UI
```

## Generate a call-context snapshot

From the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_generate_call_context_snapshot.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_call_context_snapshot_<timestamp>.json
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_call_context_snapshot_<timestamp>.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Call Context
```

## Commit guard

Stage only the four Step 20 files. Do not stage generated snapshots, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, or unrelated Replaster Quote files.

