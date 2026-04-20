# Phase 19 Step 21 — Read-only EOD SMS Batch Parity

## Purpose

Step 21 starts the second bridge-only parity slice identified by the Step 19 parity matrix: the end-of-day SMS batch workflow.

This step is intentionally read-only. It gives the platform visibility into the bridge's EOD/text-summary workflow without pressing the bridge EOD button or forcing batch rebuilds.

## Files

```text
scripts/phase19_generate_eod_sms_snapshot.ps1
ui/pages/23_EOD_SMS_Batches.py
docs/PHASE19_STEP21_EOD_SMS.md
tests/test_phase19_eod_sms.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- create CRM notes or tasks
- run the bridge EOD batch button
- force rebuild bridge SMS batches
- mutate bridge state
- mutate platform records
- enable live writes

This step does not call LACRM, does not mutate bridge state, does not force SMS batch rebuilds, and does not enable live writes.

## Correct app map

```text
http://127.0.0.1:8501  unified platform Streamlit dashboard
http://127.0.0.1:8010  unified platform FastAPI backend/API
http://127.0.0.1:8000  original KPS Bridge / Data Hub UI
```

## Generate an EOD SMS snapshot

From the platform repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_generate_eod_sms_snapshot.ps1
```

Output:

```text
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_eod_sms_snapshot_<timestamp>.json
C:\Users\krist\Desktop\unified_pool_service_platform_build\backups\phase19_eod_sms_snapshot_<timestamp>.md
```

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
EOD SMS Batches
```

## Commit guard

Stage only the four Step 21 files. Do not stage generated snapshots, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, or unrelated Replaster Quote files.
