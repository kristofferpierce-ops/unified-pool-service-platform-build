# Phase 19 Step 14 — Environment Reliability Workbench

Step 14 adds a repeatable local environment control layer for the Phase 19 bridge/platform integration.

## Why this step exists

During Steps 4–13, the local platform environment repeatedly failed or became confusing because of:

- corrupted or partial `pydantic_core` installs in `.venv`
- missing `httpx` for `fastapi.testclient.TestClient`
- confusion between the three local app ports
- menu windows being mistaken for normal PowerShell shells
- FastAPI static test pages being mistaken for the Streamlit dashboard

## Correct local app map

```text
http://127.0.0.1:8501
  Unified platform Streamlit dashboard

http://127.0.0.1:8010
  Unified platform FastAPI backend/API

http://127.0.0.1:8000
  Original KPS Bridge / Data Hub UI
```

## Added scripts

```text
scripts/phase19_repair_platform_venv.ps1
scripts/phase19_start_local_stack.ps1
scripts/phase19_stop_local_stack.ps1
scripts/phase19_verify_local_stack.ps1
```

The repair script does not use `deactivate`. It removes and rebuilds `.venv`, force reinstalls requirements, and hard-checks `pydantic_core._pydantic_core`, `httpx`, and the FastAPI app import.

## Added Streamlit page

```text
ui/pages/17_Environment_Health.py
```

The page is read-only and shows FastAPI health, Streamlit port health, Bridge original UI health, SMS ingestion counts, LACRM live-write safety state, and Git branch/status.

## Safety

This step does not modify bridge code, does not write to LACRM, does not mutate raw SMS records, and does not enable live CRM writes.
