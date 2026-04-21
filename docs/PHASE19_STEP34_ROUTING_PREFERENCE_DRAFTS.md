# Phase 19 Step 34 — Routing Preference Draft Schema and Read-only API

## Purpose

Step 34 adds the platform-side draft schema for future approved routing preferences.

It introduces `RoutingPreferenceDraft` and read-only draft endpoints. It does not create drafts yet.

## Files

```text
app/models/routing_preference_drafts.py
app/services/routing_preference_drafts.py
app/api/routes/routing_preference_drafts.py
app/api/app.py
scripts/phase19_check_routing_preference_drafts.ps1
ui/pages/36_Routing_Preference_Drafts.py
docs/PHASE19_STEP34_ROUTING_PREFERENCE_DRAFTS.md
tests/test_phase19_routing_preference_drafts.py
```

## Safety

This step does not:

- patch the bridge
- call LACRM
- create routing preference drafts
- save routing rules
- call bridge POST endpoints
- mutate bridge state
- enable live writes

This step is schema/read-only only. It does not save routing rules, does not mutate bridge state, does not call LACRM, and does not enable live writes.

## API endpoints

```text
GET  /front-desk/routing/preference-drafts/status
GET  /front-desk/routing/preference-drafts
GET  /front-desk/routing/preference-drafts/{draft_id}
POST /front-desk/routing/preference-drafts/from-candidate-preview/{candidate_id}
```

The POST endpoint is preview-only. It does not create a draft or commit changes.

## View

Open Streamlit:

```text
http://127.0.0.1:8501
```

Then open:

```text
Routing Preference Drafts
```

## Commit guard

Stage only the Step 34 files. Do not stage generated draft reports, local databases, `.env`, `.venv`, bridge folders, backups, evidence packs, import artifacts, or unrelated Replaster Quote files.
