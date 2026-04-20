# Phase 19 Step 11 — Safety / Apply Audit UI Cleanup

## Goal

Step 11 makes the Streamlit Bridge Review safety and LACRM apply audit areas operator-friendly.

Previous steps intentionally exposed raw safety JSON while live-write gates were being built. That was useful for debugging, but it made the `Safety` and `Apply Audit` views noisy and easy to misread. Step 11 keeps the same safety model and does not change the live-write gate logic.

## What changes

- The Safety expander now shows readable safety cards instead of dumping raw JSON by default.
- A clear banner shows whether live LACRM writes are off, partially configured, or ready.
- Current blockers are displayed as bullets.
- Raw safety JSON is still available under an explicit debugging/export expander.
- The Apply Audit tab adds a scope selector, a status filter, and a default-on synthetic Phase 19 test-action filter.
- Apply actions are shown as a table first, with details available per selected action.
- Raw action JSON remains available only behind expanders.

## Safety

This patch is UI/readability only.

It does not:

- enable live LACRM writes
- call Less Annoying CRM
- patch the bridge
- modify RingCentral behavior
- change the Streamlit dashboard entrypoint
- alter the FastAPI root/static pages

The safe default remains `dry_run`.

Live writes remain blocked unless every Step 10 guard is deliberately enabled:

- `dry_run=false`
- `confirm_live_write=true`
- `PLATFORM_LACRM_LIVE_WRITE_ENABLED=true`
- `PLATFORM_LACRM_LIVE_WRITE_ARMED=true`
- valid `LACRM_API_KEY`
- dry-run history exists
- no error apply actions exist
- required confirmation phrase is typed exactly

## Correct app map

- `http://127.0.0.1:8501` — unified platform Streamlit dashboard
- `http://127.0.0.1:8010` — unified platform FastAPI backend/API
- `http://127.0.0.1:8000` — original KPS Bridge / Data Hub UI
