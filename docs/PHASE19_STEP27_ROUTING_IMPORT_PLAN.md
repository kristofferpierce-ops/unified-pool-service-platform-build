# Phase 19 Step 27 — Routing Import Plan

## Purpose

Step 27 turns the validated routing worksheet from Step 26 into a dry-run import plan for future `RoutingPreferenceCandidate` rows.

The plan describes what could be imported later, what is blocked, and why. It does not import anything.

## Files

```text
scripts/phase19_generate_routing_import_plan.ps1
ui/pages/29_Routing_Import_Plan.py
docs/PHASE19_STEP27_ROUTING_IMPORT_PLAN.md
tests/test_phase19_routing_import_plan.py
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

This step is import-plan-only. It does not save routing rules, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate an import plan

From the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_generate_routing_import_plan.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_routing_import_plan_<timestamp>
```

The folder contains:

```text
phase19_routing_import_plan.json
phase19_routing_import_plan.csv
phase19_routing_import_plan.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Import Plan
```

## Commit guard

Stage only the four Step 27 files. Do not stage generated import plans, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, or unrelated Replaster Quote files.
