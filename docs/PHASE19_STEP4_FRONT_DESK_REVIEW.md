# Phase 19 Step 4 — Platform Front-Desk Review Parity

Step 4 moves the integration from "events landed" to "operators can inspect bridge-origin SMS threads inside the unified platform."

## Scope

This step is platform-only. It does not change the live bridge runtime and does not move queue ownership yet.

## New platform endpoints

- `GET /front-desk/sms-threads`
  - filters: `status`, `external_phone`, `local_day`, `source`, `limit`, `offset`
- `GET /front-desk/sms-threads/{sms_thread_id}`
  - returns thread details, messages, candidates, tasks, and provenance
- `GET /front-desk/bridge-review-summary`
  - summary counts by status, day, source, latest threads
- `GET /front-desk/bridge-compare/sms-batches`
  - optional runtime comparison against the bridge active SMS batches API

## Display text cleanup

The service adds best-effort display-only cleanup for mojibake such as `donât` so platform review screens are easier to read. Stored raw payloads are not mutated.

## UI

The root platform page now uses the review endpoints to show:

- thread list
- selected thread details
- message timeline
- provenance
- bridge comparison summary

## Validation

Run:

```powershell
pytest -q tests/test_front_desk_review_parity.py tests/test_bridge_platform_integration.py
```

Runtime smoke checks:

```powershell
curl.exe -i http://127.0.0.1:8010/front-desk/bridge-review-summary
curl.exe -i "http://127.0.0.1:8010/front-desk/sms-threads?limit=10"
curl.exe -i "http://127.0.0.1:8010/front-desk/bridge-compare/sms-batches?limit=500"
```
