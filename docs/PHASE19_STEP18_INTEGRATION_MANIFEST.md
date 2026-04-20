# Phase 19 Step 18 — Cross-Repo Integration Manifest

## Purpose

Step 18 creates a read-only cross-repo integration manifest for the three-project setup:

- unified platform repo
- sanitized bridge repo copy
- start-here-extractor repo

It also preserves the live bridge folder as a non-Git runtime folder.

## Correct app map

```text
http://127.0.0.1:8501  unified platform Streamlit dashboard
http://127.0.0.1:8010  unified platform FastAPI backend/API
http://127.0.0.1:8000  original KPS Bridge / Data Hub UI
```

## Files

```text
scripts/phase19_generate_integration_manifest.ps1
ui/pages/20_Integration_Manifest.py
docs/PHASE19_STEP18_INTEGRATION_MANIFEST.md
tests/test_phase19_integration_manifest.py
```

## Safety

This step is read-only except for writing local manifest files to the workspace `backups` folder.

It does not call LACRM, does not mutate platform records, does not patch the bridge, and does not inspect the bridge runtime database.

## Generate a manifest

From the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_generate_integration_manifest.ps1
```

Output is written to:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_integration_manifest_<timestamp>.json
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_integration_manifest_<timestamp>.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Integration Manifest
```

## Commit guard

Stage only the four Step 18 files. Do not stage local databases, `.env`, `.venv`, bridge folders, generated backups, evidence packs, or unrelated Replaster Quote files.
