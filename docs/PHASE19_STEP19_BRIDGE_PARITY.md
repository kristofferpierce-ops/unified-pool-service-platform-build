# Phase 19 Step 19 — Bridge Parity Matrix

## Purpose

Step 19 creates a read-only parity matrix showing which bridge capabilities are already integrated into the platform, which are still bridge-only, and which should become later parity slices.

## Why this matters

The original KPS Bridge / Data Hub remains the operational UI on port `8000`. The unified platform now has ingestion, review, audit, evidence, and manifest tooling, but it should not pretend to have full bridge UI parity until the remaining bridge-only workflows are explicitly ported.

## Files

```text
scripts/phase19_generate_bridge_parity_matrix.ps1
ui/pages/21_Bridge_Parity.py
docs/PHASE19_STEP19_BRIDGE_PARITY.md
tests/test_phase19_bridge_parity.py
```

## Safety

This step is read-only except for writing a local parity matrix JSON/Markdown file into the workspace `backups` folder.

It does not call LACRM, does not mutate the platform database, and does not patch the bridge.

## Generate matrix

From the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_generate_bridge_parity_matrix.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_bridge_parity_matrix_<timestamp>.json
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_bridge_parity_matrix_<timestamp>.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Bridge Parity
```

## Commit guard

Stage only the four Step 19 files. Do not stage generated parity outputs, platform DB, `.env`, `.venv`, bridge folders, backups, evidence packs, or unrelated Replaster Quote files.
