# Phase 19 Step 7 — Streamlit Bridge Review Page

## Purpose

Step 7 brings the bridge-origin SMS review workflow into the actual unified platform Streamlit UI without replacing the existing dashboard and without touching the standalone bridge UI.

Correct local app map:

- `http://127.0.0.1:8501` — unified platform Streamlit dashboard
- `http://127.0.0.1:8010` — unified platform FastAPI backend/API
- `http://127.0.0.1:8000` — original KPS Bridge / Data Hub UI

## What changed

- Added `ui/pages/14_Bridge_Review.py` as a Streamlit multipage app page.
- Added a `Bridge Review` launch link to `ui/Dashboard.py`.
- The page uses existing platform services from Steps 4–6.
- No bridge files are modified.
- No static FastAPI landing page is replaced.

## Safety

The Streamlit page defaults to platform-local review actions. LACRM apply remains guarded by Step 6:

- dry-run defaults on
- live writes require `PLATFORM_LACRM_LIVE_WRITE_ENABLED=true`
- live writes require a configured `LACRM_API_KEY`
- live writes require the operator to turn dry-run off and confirm live write
- idempotency keys are used for note/task actions

## Validation

Start:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.api.main:app --host 127.0.0.1 --port 8010
.\.venv\Scripts\python.exe -m streamlit run ui\Dashboard.py --server.port 8501
```

Open:

```text
http://127.0.0.1:8501
```

Use the sidebar or launchpad to open **Bridge Review**.
