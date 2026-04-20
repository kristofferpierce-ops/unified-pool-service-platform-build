# Phase 19 Step 9 — LACRM apply audit workbench

Step 9 adds read-only audit and readiness controls around the guarded LACRM apply path introduced in Step 6 and the LACRM contact candidate flow introduced in Step 8.

## Scope

Platform only. No bridge patch. No Streamlit dashboard replacement. No live LACRM writes are enabled by this step.

## New FastAPI endpoints

- `GET /front-desk/lacrm-apply/readiness`
- `GET /front-desk/lacrm-apply/actions`
- `GET /front-desk/lacrm-apply/actions/{crm_apply_action_id}`
- `GET /front-desk/lacrm-apply/export`

## Streamlit changes

The existing `Bridge Review` page gets a new `Apply Audit` tab for the selected SMS thread. The tab shows:

- dry-run count
- blocked/error/applied count
- live-write readiness blockers
- CRM apply action table
- individual action detail
- JSON export payload

## Safety posture

Live LACRM writes remain blocked unless a later cutover deliberately enables all Step 6 guards:

- `dry_run=false`
- `confirm_live_write=true`
- `PLATFORM_LACRM_LIVE_WRITE_ENABLED=true`
- valid `LACRM_API_KEY`

Step 9 only improves visibility and operator auditability.
