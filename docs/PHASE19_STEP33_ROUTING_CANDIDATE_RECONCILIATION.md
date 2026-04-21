# Phase 19 Step 33 — Routing Candidate Reconciliation

## Purpose

Step 33 compares the latest bridge routing snapshot with platform `RoutingPreferenceCandidate` rows.

It identifies bridge rules that do not yet have platform candidates, platform candidates that are missing from the current bridge snapshot, duplicates, and matches.

## Files

```text
scripts/phase19_reconcile_routing_candidates.ps1
ui/pages/35_Routing_Candidate_Reconciliation.py
docs/PHASE19_STEP33_ROUTING_CANDIDATE_RECONCILIATION.md
tests/test_phase19_routing_candidate_reconciliation.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- save routing rules
- save candidate review decisions
- call bridge POST endpoints
- mutate bridge state
- mutate platform records
- enable live writes

This step is reconciliation-only. It does not save routing rules, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## Generate reconciliation

From the platform repo, with FastAPI running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_reconcile_routing_candidates.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_routing_candidate_reconciliation_<timestamp>
```

The report folder contains:

```text
phase19_routing_candidate_reconciliation.json
phase19_routing_candidate_reconciliation.csv
phase19_routing_candidate_reconciliation.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Candidate Reconciliation
```

## Commit guard

Stage only the four Step 33 files. Do not stage generated reconciliation reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
