# Phase 19 Step 25 — Routing Approval Worksheet

## Purpose

Step 25 turns the Step 24 routing approval packet into an editable operator worksheet.

The worksheet is for review handoff only. It does not create platform routing preferences and does not touch bridge routing rules.

## Files

```text
scripts/phase19_generate_routing_approval_worksheet.ps1
ui/pages/27_Routing_Approval_Worksheet.py
docs/PHASE19_STEP25_ROUTING_APPROVAL_WORKSHEET.md
tests/test_phase19_routing_approval_worksheet.py
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

This step is worksheet-only. It does not save routing rules, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate a worksheet

From the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_generate_routing_approval_worksheet.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_routing_approval_worksheet_<timestamp>
```

The worksheet folder contains:

```text
phase19_routing_approval_worksheet.json
phase19_routing_approval_worksheet.csv
phase19_routing_approval_worksheet.md
```

## View and edit

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Approval Worksheet
```

Edits in Streamlit are download-only. They do not write to the platform database or bridge.

## Commit guard

Stage only the four Step 25 files. Do not stage generated worksheets, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, or unrelated Replaster Quote files.
