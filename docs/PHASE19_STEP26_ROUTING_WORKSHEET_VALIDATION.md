# Phase 19 Step 26 — Routing Worksheet Validation

## Purpose

Step 26 validates the Step 25 routing approval worksheet before any future dry-run import or write workflow exists.

The validation report checks operator decisions for invalid values, high-risk approvals, auto-attach approvals without contacts, and review/block decisions that need notes.

## Files

```text
scripts/phase19_validate_routing_worksheet.ps1
ui/pages/28_Routing_Worksheet_Validator.py
docs/PHASE19_STEP26_ROUTING_WORKSHEET_VALIDATION.md
tests/test_phase19_routing_worksheet_validation.py
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

This step is validation-only. It does not save routing rules, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate validation report

From the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_validate_routing_worksheet.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_routing_worksheet_validation_<timestamp>
```

The validation folder contains:

```text
phase19_routing_worksheet_validation.json
phase19_routing_worksheet_validation_issues.csv
phase19_routing_worksheet_validation_rows.csv
phase19_routing_worksheet_validation.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Worksheet Validator
```

## Commit guard

Stage only the four Step 26 files. Do not stage generated validation reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, or unrelated Replaster Quote files.
