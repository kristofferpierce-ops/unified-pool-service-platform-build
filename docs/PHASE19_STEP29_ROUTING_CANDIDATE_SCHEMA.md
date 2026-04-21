# Phase 19 Step 29 — Routing Candidate Schema and Read-only API

## Purpose

Step 29 adds the platform-side schema foundation for future routing candidate persistence.

It introduces the `RoutingPreferenceCandidate` table shape and read-only API endpoints, but does not import rows yet.

## Files

```text
app/models/routing_candidates.py
app/services/routing_candidates.py
app/api/routes/routing_candidates.py
app/api/app.py
ui/pages/31_Routing_Candidates.py
docs/PHASE19_STEP29_ROUTING_CANDIDATE_SCHEMA.md
tests/test_phase19_routing_candidate_schema.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- save routing rules from bridge
- call bridge POST endpoints
- mutate bridge state
- import routing candidates
- enable live writes

This step is schema/read-only only. It does not save routing rules, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## New API endpoints

```text
GET /front-desk/routing/candidates/status
GET /front-desk/routing/candidates
GET /front-desk/routing/candidates/{candidate_id}
```

These endpoints are read-only.

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Candidates
```

## Commit guard

Stage only the Step 29 files. Do not stage generated backups, local databases, `.env`, `.venv`, bridge folders, evidence packs, import-plan artifacts, or unrelated Replaster Quote files.
