# Phase 19 Step 28 — Routing Import Plan Validation

## Purpose

Step 28 validates the Step 27 routing import plan before any platform persistence exists.

This is the final pre-persistence gate before a later step may introduce platform schema for routing candidates.

## Files

```text
scripts/phase19_validate_routing_import_plan.ps1
ui/pages/30_Routing_Import_Plan_Validator.py
docs/PHASE19_STEP28_ROUTING_IMPORT_PLAN_VALIDATION.md
tests/test_phase19_routing_import_plan_validation.py
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
powershell -ExecutionPolicy Bypass -File scripts\phase19_validate_routing_import_plan.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_routing_import_plan_validation_<timestamp>
```

The validation folder contains:

```text
phase19_routing_import_plan_validation.json
phase19_routing_import_plan_validation_issues.csv
phase19_routing_import_plan_validation_rows.csv
phase19_routing_import_plan_validation.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Import Plan Validator
```

## Commit guard

Stage only the four Step 28 files. Do not stage generated validation reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, or unrelated Replaster Quote files.
