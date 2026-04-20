# Phase 19 Step 12 — Integration Health Workbench

## Goal

Step 12 adds a read-only Streamlit Integration Health page for the Phase 19 bridge-to-platform migration.

It is intended to stop UI/app confusion and provide one place to confirm:

- Streamlit dashboard is the unified platform UI on port 8501.
- FastAPI is the platform API/backend on port 8010.
- The original KPS Bridge/Data Hub remains on port 8000.
- Bridge-origin SMS records are present in the platform database.
- LACRM live writes remain disabled, unarmed, and blocked by default.
- Apply audit rows are visible without exposing raw JSON first.

## Files

- `ui/pages/15_Integration_Health.py`
- `docs/PHASE19_STEP12_INTEGRATION_HEALTH.md`
- `tests/test_streamlit_integration_health_page.py`

## Safety

This step is read-only.

It does not:

- Patch the bridge.
- Enable live LACRM writes.
- Write to Less Annoying CRM.
- Mutate RingCentral.
- Replace the Streamlit dashboard.
- Replace the original KPS Bridge/Data Hub UI.

## Expected local app map

```text
http://127.0.0.1:8501
  Unified platform Streamlit dashboard

http://127.0.0.1:8010
  Unified platform FastAPI backend/API

http://127.0.0.1:8000
  Original KPS Bridge / Data Hub UI
```

## Validation

The Step 12 runner smoke test validates the Streamlit page source and checks the FastAPI/Bridge endpoints when servers are running.

The Integration Health page itself shows a checklist for:

- FastAPI health
- Bridge health
- platform SMS data
- live-write disabled
- live-write unarmed
- live-ready false
- no live-applied actions

## Commit

Only commit:

```text
ui/pages/15_Integration_Health.py
docs/PHASE19_STEP12_INTEGRATION_HEALTH.md
tests/test_streamlit_integration_health_page.py
```

Do not commit:

```text
data/unified_pool_service_platform.db
.env
.venv
front_desk_bridge
front_desk_bridge_repo
Replaster Quote files
```
