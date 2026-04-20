# Phase 19 Step 8 — Platform LACRM Contact Candidates

## Purpose

Step 8 connects the platform review workflow to Less Annoying CRM contact search without enabling live CRM writes.

Step 6 proved guarded dry-run LACRM apply actions. Step 7 put bridge review inside the real Streamlit UI. Step 8 adds the missing operator step before apply: finding the correct LACRM contact from the platform and storing it as a `ContactMatchCandidate` using a stable `lacrm_contact:<id>` reference.

## Added endpoints

```text
GET  /front-desk/lacrm/search?q=<terms>&limit=10
POST /front-desk/sms-threads/{sms_thread_id}/lacrm-candidates
```

`/front-desk/lacrm/search` is safe when `LACRM_API_KEY` is not configured. It returns `mode=not_configured` and an empty contact list instead of throwing or writing anything.

`/front-desk/sms-threads/{id}/lacrm-candidates` can derive search terms from phone/name/address/thread text, query LACRM when configured, accept `sample_contacts` for local tests, score candidates using phone and text similarity, and store candidates for approval/dry-run apply.

## Streamlit integration

`ui/pages/14_Bridge_Review.py` now includes a LACRM contact search/import panel in the Candidates tab. The original bridge Data Hub remains on port 8000. The unified Streamlit dashboard remains on port 8501. FastAPI remains on port 8010.

## Safety boundaries

This step does not write to LACRM. Live CRM write remains governed by Step 6 and still requires all live-write gates:

```text
dry_run=false
confirm_live_write=true
PLATFORM_LACRM_LIVE_WRITE_ENABLED=true
LACRM_API_KEY configured
```

## Files changed

```text
app/connectors/lacrm/client.py
app/services/front_desk.py
app/api/routes/front_desk.py
ui/pages/14_Bridge_Review.py
docs/PHASE19_STEP8_LACRM_CONTACT_CANDIDATES.md
tests/test_front_desk_lacrm_candidates.py
tests/test_streamlit_bridge_review_lacrm_candidates.py
```

## Validation

The synthetic validation path ingests a test SMS, imports a sample LACRM contact candidate, verifies the candidate is stored on the SMS thread, and verifies Step 6's LACRM apply preview can resolve the `lacrm_contact:<id>` reference.
