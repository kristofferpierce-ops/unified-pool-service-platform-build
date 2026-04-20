# Phase 19 Step 15 — Release Checkpoint Workbench

## Purpose

Step 15 adds a read-only checkpoint view for the Phase 19 integration work.

It does not modify the bridge, does not enable LACRM live writes, and does not mutate SMS records. It gives the operator one place to verify:

- Streamlit dashboard is on `8501`
- FastAPI backend is on `8010`
- Original KPS Bridge / Data Hub is on `8000`
- RingCentral/SMS ingestion counts are visible
- LACRM live writes remain off
- platform, bridge repo copy, and extractor repo boundaries are still separate
- local runtime files are not accidentally staged

## Files

```text
scripts/phase19_export_release_checkpoint.ps1
ui/pages/18_Release_Checkpoint.py
docs/PHASE19_STEP15_RELEASE_CHECKPOINT.md
tests/test_phase19_release_checkpoint.py
```

## Safety

This step is read-only.

The export script calls GET endpoints and writes a local JSON checkpoint into the workspace backups folder. The Streamlit page uses GET requests and subprocess `git` status checks only.

## Correct app map

```text
http://127.0.0.1:8501  Streamlit dashboard
http://127.0.0.1:8010  FastAPI backend/API
http://127.0.0.1:8000  Original KPS Bridge / Data Hub
```

## Export checkpoint

From the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_export_release_checkpoint.ps1
```

The output is written to:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups
```

## Commit guard

Stage only the four Step 15 files. Do not stage local databases, `.env`, `.venv`, bridge folders, backups, or unrelated Replaster Quote files.
