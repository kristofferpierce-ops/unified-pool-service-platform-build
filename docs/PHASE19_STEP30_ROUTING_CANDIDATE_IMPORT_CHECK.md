# Phase 19 Step 30 — Routing Candidate Import Check

## Purpose

Step 30 compares the Step 27 routing import plan against the Step 29 platform `RoutingPreferenceCandidate` table/API.

It is a dry-run checker only. It reports what a future importer would create, update, skip, or block, but it does not import anything.

## Files

```text
scripts/phase19_check_routing_candidate_import.ps1
ui/pages/32_Routing_Candidate_Import_Check.py
docs/PHASE19_STEP30_ROUTING_CANDIDATE_IMPORT_CHECK.md
tests/test_phase19_routing_candidate_import_check.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- save routing rules
- call bridge POST endpoints
- mutate bridge state
- mutate platform records
- import routing candidates
- enable live writes

This step is dry-run-check-only. It does not import candidates, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate check report

From the platform repo, with FastAPI running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_check_routing_candidate_import.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_routing_candidate_import_check_<timestamp>
```

The report folder contains:

```text
phase19_routing_candidate_import_check.json
phase19_routing_candidate_import_check.csv
phase19_routing_candidate_import_check.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Candidate Import Check
```

## Commit guard

Stage only the four Step 30 files. Do not stage generated check reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, or unrelated Replaster Quote files.
