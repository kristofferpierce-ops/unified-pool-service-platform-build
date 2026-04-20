# Phase 19 Step 17 — Evidence Index Viewer

## Purpose

Step 17 lets the unified platform inspect extractor-generated Phase 19 evidence packs.

This keeps the intended system boundary:

- platform owns business/workflow state
- bridge remains the original Data Hub and communication ingress
- extractor owns evidence/governance/replay artifacts

## What it adds

```text
scripts/phase19_verify_evidence_pack.ps1
ui/pages/19_Evidence_Index.py
docs/PHASE19_STEP17_EVIDENCE_INDEX_VIEWER.md
tests/test_phase19_evidence_index_viewer.py
```

## Safety

The viewer and verifier are read-only.

They read files from:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_extractor_evidence_*
```

They do not call LACRM, do not mutate platform records, and do not read bridge runtime databases.

## Use

First create an evidence pack from the extractor repo:

```powershell
cd "C:\Users\krist\Desktop\unified_pool_service_platform_build\start_here_extractor_m1_completion"
powershell -ExecutionPolicy Bypass -File scripts\phase19_index_release_checkpoint.ps1
```

Then verify from the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_verify_evidence_pack.ps1
```

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Evidence Index
```

## Commit guard

Stage only the four Step 17 files. Do not stage generated evidence packs, local databases, `.env`, `.venv`, bridge folders, or unrelated Replaster Quote files.
