# Phase 19 Step 32 — Routing Candidate Workbench

## Purpose

Step 32 adds a read-only routing candidate workbench layer.

It gives operators visibility into platform-local `RoutingPreferenceCandidate` rows and the candidate queue, but does not implement candidate review writes yet.

## Files

```text
app/services/routing_candidate_workbench.py
app/api/routes/routing_candidate_workbench.py
app/api/app.py
scripts/phase19_check_routing_candidate_workbench.ps1
ui/pages/34_Routing_Candidate_Workbench.py
docs/PHASE19_STEP32_ROUTING_CANDIDATE_WORKBENCH.md
tests/test_phase19_routing_candidate_workbench.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- save routing rules
- save candidate review decisions
- call bridge POST endpoints
- mutate bridge state
- enable live writes

This step is read-only. It does not save routing rules, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## API endpoints

```text
GET  /front-desk/routing/candidate-workbench/status
GET  /front-desk/routing/candidate-workbench/queue
POST /front-desk/routing/candidate-workbench/{candidate_id}/review-preview
```

The POST endpoint is a preview endpoint only. It does not commit or mutate records.

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Candidate Workbench
```

## Commit guard

Stage only the Step 32 files. Do not stage generated workbench reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
