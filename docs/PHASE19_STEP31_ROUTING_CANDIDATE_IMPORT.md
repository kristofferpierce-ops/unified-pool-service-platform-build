# Phase 19 Step 31 — Disabled-by-default Routing Candidate Importer

## Purpose

Step 31 adds a guarded candidate importer for platform `RoutingPreferenceCandidate` rows.

The safe default is dry-run. The importer is disabled and unarmed unless explicit environment gates are set.

## Files

```text
app/services/routing_candidate_import.py
app/api/routes/routing_candidate_import.py
app/api/app.py
scripts/phase19_run_routing_candidate_import.ps1
ui/pages/33_Routing_Candidate_Import.py
docs/PHASE19_STEP31_ROUTING_CANDIDATE_IMPORT.md
tests/test_phase19_routing_candidate_import.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- save bridge routing rules
- call bridge POST endpoints
- mutate bridge state
- enable live writes

This step is disabled-by-default. Dry-run mode performs no platform DB mutation. Execution requires:

```text
PLATFORM_ROUTING_CANDIDATE_IMPORT_ENABLED=true
PLATFORM_ROUTING_CANDIDATE_IMPORT_ARMED=true
confirmation phrase: IMPORT ROUTING CANDIDATES
```

Even execution writes only to the platform-local `RoutingPreferenceCandidate` table. It does not write to the bridge or LACRM.

## API endpoints

```text
GET  /front-desk/routing/candidates/import/status
POST /front-desk/routing/candidates/import-plan
```

The POST endpoint defaults to `dry_run=true`.

## Safe dry-run command

From the platform repo, with FastAPI running:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\phase19_run_routing_candidate_import.ps1
```

## Commit guard

Stage only the Step 31 files. Do not stage generated import runs, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, or unrelated Replaster Quote files.
